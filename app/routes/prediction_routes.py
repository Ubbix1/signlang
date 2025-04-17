from flask import Blueprint, request, jsonify, current_app
from app.middleware.jwt_required import jwt_required
from app.database.db import get_db, create_prediction, get_user_predictions, delete_prediction
from app.inference.predict import predict_from_base64, predict_from_landmarks
from app.database.mongodb import add_sample_predictions
import logging
import datetime
import json

logger = logging.getLogger(__name__)
prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/predict', methods=['POST'])
@jwt_required
def predict(current_user):
    """
    Make a prediction from an image
    Expects either base64 encoded image or hand landmarks
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in prediction request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    # Get user ID
    user_id = current_user['user_id']
    
    # Check if we have landmarks or image
    if 'landmarks' in data:
        # Convert landmarks from JSON to list of floats
        try:
            landmarks = json.loads(data['landmarks']) if isinstance(data['landmarks'], str) else data['landmarks']
            
            # Make prediction from landmarks
            prediction_result, status_code = predict_from_landmarks(landmarks)
            
        except Exception as e:
            logger.error(f"Error processing landmarks: {e}")
            return jsonify({"error": "Invalid landmarks data"}), 400
            
    elif 'image' in data:
        # Make prediction from base64 image
        prediction_result, status_code = predict_from_base64(data['image'])
        
    else:
        return jsonify({"error": "Either 'image' or 'landmarks' is required"}), 400
    
    # Check if there was an error in prediction
    if status_code != 200:
        return jsonify(prediction_result), status_code
    
    # Add metadata to prediction result
    prediction_result['user_id'] = user_id
    
    # Store prediction in database if requested
    if data.get('save_result', True):
        try:
            # Extract relevant data from prediction_result
            prediction_id = create_prediction(
                user_id=user_id,
                label=prediction_result['label'],
                confidence=prediction_result['confidence'],
                class_id=prediction_result.get('class_id'),
                metadata=prediction_result
            )
            prediction_result['id'] = prediction_id
        except Exception as e:
            logger.error(f"Error saving prediction to database: {e}")
            prediction_result['saved'] = False
    
    return jsonify(prediction_result), 200

@prediction_bp.route('/bulk-predict', methods=['POST'])
@jwt_required
def bulk_predict(current_user):
    """
    Process multiple frames for prediction
    Expects an array of base64 images or landmarks
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in bulk prediction request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    # Get user ID
    user_id = current_user['user_id']
    
    # Initialize results array
    results = []
    
    # Check if we have landmarks or images
    if 'landmarks_array' in data:
        # Process each set of landmarks
        landmarks_array = data['landmarks_array']
        
        for landmarks in landmarks_array:
            # Convert landmarks from JSON to list if needed
            if isinstance(landmarks, str):
                try:
                    landmarks = json.loads(landmarks)
                except Exception as e:
                    logger.error(f"Error parsing landmarks JSON: {e}")
                    results.append({
                        "error": "Invalid landmarks data", 
                        "label": "Error", 
                        "confidence": 0.0
                    })
                    continue
            
            # Make prediction from landmarks
            prediction_result, status_code = predict_from_landmarks(landmarks)
            
            # Add to results
            if status_code == 200:
                results.append(prediction_result)
            else:
                results.append({
                    "error": prediction_result.get("error", "Prediction failed"), 
                    "label": "Error", 
                    "confidence": 0.0
                })
                
    elif 'image_array' in data:
        # Process each base64 image
        image_array = data['image_array']
        
        for image in image_array:
            # Make prediction from base64 image
            prediction_result, status_code = predict_from_base64(image)
            
            # Add to results
            if status_code == 200:
                results.append(prediction_result)
            else:
                results.append({
                    "error": prediction_result.get("error", "Prediction failed"), 
                    "label": "Error", 
                    "confidence": 0.0
                })
    else:
        return jsonify({"error": "Either 'image_array' or 'landmarks_array' is required"}), 400
    
    # Determine majority prediction if requested
    if data.get('get_majority', True) and results:
        # Count occurrences of each label
        label_counts = {}
        for result in results:
            label = result.get('label')
            if label and label != "Error" and label != "Unknown":
                label_counts[label] = label_counts.get(label, 0) + 1
        
        # Find the most common label
        majority_label = max(label_counts.items(), key=lambda x: x[1])[0] if label_counts else "Unknown"
        
        # Calculate confidence as percentage of frames with this label
        majority_confidence = (label_counts.get(majority_label, 0) / len(results)) * 100 if results else 0
        
        # Create majority prediction result
        majority_result = {
            "label": majority_label,
            "confidence": round(majority_confidence, 2),
            "count": label_counts.get(majority_label, 0),
            "total_frames": len(results),
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        # Store majority prediction in database if requested
        if data.get('save_result', True):
            try:
                # Extract relevant data from majority_result
                prediction_id = create_prediction(
                    user_id=user_id,
                    label=majority_label,
                    confidence=majority_result['confidence'],
                    metadata={
                        'count': majority_result['count'],
                        'total_frames': majority_result['total_frames'],
                        'results': results
                    }
                )
                majority_result['id'] = prediction_id
            except Exception as e:
                logger.error(f"Error saving bulk prediction to database: {e}")
                majority_result['saved'] = False
        
        # Return all results and the majority prediction
        return jsonify({
            "results": results,
            "majority_prediction": majority_result
        }), 200
    
    # Return just the individual results
    return jsonify({
        "results": results
    }), 200

@prediction_bp.route('/history', methods=['GET'])
@jwt_required
def get_prediction_history(current_user):
    """Get the current user's prediction history"""
    user_id = current_user['user_id']
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    try:
        # Get predictions for the user with pagination using Firestore
        result = get_user_predictions(user_id, page, per_page)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error retrieving prediction history: {e}")
        return jsonify({"error": f"Failed to retrieve prediction history: {str(e)}"}), 500

@prediction_bp.route('/history/<prediction_id>', methods=['DELETE'])
@jwt_required
def delete_prediction_endpoint(current_user, prediction_id):
    """Delete a specific prediction"""
    user_id = current_user['user_id']
    
    try:
        # Delete prediction from Firestore
        success = delete_prediction(prediction_id, user_id)
        
        if success:
            return jsonify({"message": "Prediction deleted successfully"}), 200
        else:
            return jsonify({"error": "Prediction not found or you don't have permission to delete it"}), 404
    except Exception as e:
        logger.error(f"Error deleting prediction: {e}")
        return jsonify({"error": f"Failed to delete prediction: {str(e)}"}), 500

@prediction_bp.route('/add-samples', methods=['POST'])
@jwt_required
def add_sample_data(current_user):
    """Add sample prediction data for testing"""
    user_id = current_user['user_id']
    
    try:
        # Get count from request or use default
        data = request.get_json() or {}
        count = data.get('count', 5)
        count = min(count, 50)  # Limit to 50 samples max
        
        # Add sample predictions
        sample_ids = add_sample_predictions(user_id, count)
        
        return jsonify({
            "message": f"Added {len(sample_ids)} sample predictions",
            "sample_ids": sample_ids
        }), 200
    except Exception as e:
        logger.error(f"Error adding sample predictions: {e}")
        return jsonify({"error": f"Failed to add sample predictions: {str(e)}"}), 500

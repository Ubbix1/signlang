from flask import Blueprint, request, jsonify, current_app
from app.middleware.jwt_required import jwt_required
from app.database.db import get_db, get_user_by_id, get_user_predictions, delete_prediction
import logging

logger = logging.getLogger(__name__)
user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required
def get_profile(current_user):
    """Get the current user's profile"""
    try:
        user_id = current_user['user_id']
        
        # Find user by ID
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Remove password for security
        if 'password' in user:
            del user['password']
        
        return jsonify(user), 200
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({"error": f"Failed to retrieve profile: {str(e)}"}), 500

@user_bp.route('/profile', methods=['PUT'])
@jwt_required
def update_profile(current_user):
    """Update the current user's profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in update profile request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    db = get_db()
    user_id = current_user['user_id']
    
    # Fields that users are allowed to update
    allowed_fields = ['name', 'email']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400
    
    try:
        # Get user reference
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
        
        # Update user in database
        user_ref.update(update_data)
        
        # Get updated user
        updated_user = user_ref.get().to_dict()
        updated_user['id'] = user_id
        
        # Remove password for security
        if 'password' in updated_user:
            del updated_user['password']
        
        return jsonify({
            "message": "Profile updated successfully",
            "user": updated_user
        }), 200
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500

@user_bp.route('/history', methods=['GET'])
@jwt_required
def get_history(current_user):
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

@user_bp.route('/history/<prediction_id>', methods=['GET'])
@jwt_required
def get_prediction_detail(current_user, prediction_id):
    """Get details of a specific prediction"""
    db = get_db()
    user_id = current_user['user_id']
    
    try:
        # Get prediction by ID
        prediction_ref = db.collection('predictions').document(prediction_id)
        prediction = prediction_ref.get()
        
        if not prediction.exists:
            return jsonify({"error": "Prediction not found"}), 404
        
        # Convert to dict and add ID
        prediction_data = prediction.to_dict()
        prediction_data['id'] = prediction_id
        
        # Check if prediction belongs to user
        if prediction_data.get('user_id') != user_id:
            return jsonify({"error": "Access denied"}), 403
        
        return jsonify(prediction_data), 200
    except Exception as e:
        logger.error(f"Error retrieving prediction: {e}")
        return jsonify({"error": f"Failed to retrieve prediction: {str(e)}"}), 500

@user_bp.route('/history/<prediction_id>', methods=['DELETE'])
@jwt_required
def delete_prediction_endpoint(current_user, prediction_id):
    """Delete a specific prediction"""
    user_id = current_user['user_id']
    
    try:
        # Delete prediction using the function from db.py
        success = delete_prediction(prediction_id, user_id)
        
        if not success:
            return jsonify({"error": "Prediction not found or access denied"}), 404
        
        return jsonify({
            "message": "Prediction deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting prediction: {e}")
        return jsonify({"error": f"Failed to delete prediction: {str(e)}"}), 500

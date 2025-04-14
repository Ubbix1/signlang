import logging
import base64
from flask import current_app, jsonify
from app.inference.model_loader import get_model_and_hands, get_class_names, ML_AVAILABLE
import datetime

logger = logging.getLogger(__name__)

# Only import ML-related libraries if they're available
if ML_AVAILABLE:
    import numpy as np
    import cv2
    from app.inference.utils import preprocess_frame, extract_hand_landmarks
else:
    logger.warning("ML libraries not available in predict.py, using mock implementation")

def predict_from_base64(base64_image):
    """
    Make a prediction from a base64 encoded image
    
    Args:
        base64_image: Base64 encoded image string
        
    Returns:
        dict: Prediction result containing label, confidence, etc.
    """
    # Check if ML is available
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, returning mock prediction")
        return {
            "label": "Mock Prediction",
            "confidence": 75.0,
            "class_id": 0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "note": "ML_DISABLED - This is a mock prediction as ML libraries are not installed"
        }, 200
        
    try:
        # Decode base64 string to image
        image_data = base64.b64decode(base64_image.split(',')[1] if ',' in base64_image else base64_image)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Check if image was properly decoded
        if frame is None:
            logger.error("Failed to decode base64 image")
            return {"error": "Invalid image data"}, 400
        
        # Process image and make prediction
        return predict_from_frame(frame)
        
    except Exception as e:
        logger.error(f"Error in predict_from_base64: {e}")
        return {"error": "Error processing image"}, 500

def predict_from_frame(frame):
    """
    Make a prediction from a video frame
    
    Args:
        frame: OpenCV image frame
        
    Returns:
        dict: Prediction result containing label, confidence, etc.
    """
    # Check if ML is available
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, returning mock prediction")
        # Return one of the class names at random for variety
        import random
        class_names = get_class_names()
        random_class = random.randint(0, len(class_names)-1)
        
        return {
            "label": class_names[random_class],
            "confidence": round(random.uniform(60.0, 95.0), 2),
            "class_id": random_class,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "note": "ML_DISABLED - This is a mock prediction as ML libraries are not installed"
        }, 200
    
    try:
        # Get model and mediapipe hands
        model, hands = get_model_and_hands()
        
        # Preprocess frame
        processed_frame = preprocess_frame(frame)
        
        # Extract hand landmarks using MediaPipe
        landmarks = extract_hand_landmarks(processed_frame, hands)
        
        # Check if hands were detected
        if landmarks is None or len(landmarks) == 0:
            return {
                "error": "No hands detected in the image",
                "label": "Unknown",
                "confidence": 0.0
            }, 200
        
        # Flatten landmarks into feature vector
        # Each landmark has x,y coordinates
        features = np.array(landmarks).flatten()
        
        # If we have less than 2 hands, pad with zeros
        expected_length = 21 * 2 * 2  # 21 landmarks with x,y for 2 hands
        if len(features) < expected_length:
            features = np.pad(features, (0, expected_length - len(features)))
        elif len(features) > expected_length:
            features = features[:expected_length]
        
        # Reshape for model input
        features = features.reshape(1, -1)
        
        # Make prediction
        predictions = model.predict(features)
        
        # Get highest probability class
        predicted_class = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class])
        
        # Get class name
        class_names = get_class_names()
        if predicted_class < len(class_names):
            label = class_names[predicted_class]
        else:
            label = f"Class {predicted_class}"
        
        # Return prediction
        return {
            "label": label,
            "confidence": round(confidence * 100, 2),
            "class_id": int(predicted_class),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }, 200
        
    except Exception as e:
        logger.error(f"Error in predict_from_frame: {e}")
        return {"error": f"Error making prediction: {str(e)}"}, 500

def predict_from_landmarks(landmarks):
    """
    Make a prediction directly from hand landmarks
    
    Args:
        landmarks: List of hand landmark coordinates
        
    Returns:
        dict: Prediction result containing label, confidence, etc.
    """
    # Check if ML is available
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, returning mock prediction")
        # Return one of the class names at random for variety
        import random
        class_names = get_class_names()
        random_class = random.randint(0, len(class_names)-1)
        
        return {
            "label": class_names[random_class],
            "confidence": round(random.uniform(60.0, 95.0), 2),
            "class_id": random_class,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "note": "ML_DISABLED - This is a mock prediction as ML libraries are not installed"
        }, 200
        
    try:
        # Get model
        model, _ = get_model_and_hands()
        
        # Flatten landmarks into feature vector
        features = np.array(landmarks).flatten()
        
        # If we have less than 2 hands, pad with zeros
        expected_length = 21 * 2 * 2  # 21 landmarks with x,y for 2 hands
        if len(features) < expected_length:
            features = np.pad(features, (0, expected_length - len(features)))
        elif len(features) > expected_length:
            features = features[:expected_length]
        
        # Reshape for model input
        features = features.reshape(1, -1)
        
        # Make prediction
        predictions = model.predict(features)
        
        # Get highest probability class
        predicted_class = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class])
        
        # Get class name
        class_names = get_class_names()
        if predicted_class < len(class_names):
            label = class_names[predicted_class]
        else:
            label = f"Class {predicted_class}"
        
        # Return prediction
        return {
            "label": label,
            "confidence": round(confidence * 100, 2),
            "class_id": int(predicted_class),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }, 200
        
    except Exception as e:
        logger.error(f"Error in predict_from_landmarks: {e}")
        return {"error": f"Error making prediction: {str(e)}"}, 500

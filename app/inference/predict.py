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
    from PIL import Image
    import io
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
        return {"error": f"Error processing image: {str(e)}"}, 500

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
        # Get model, hands, and processor (processor will be None with Keras model)
        model, hands, _ = get_model_and_hands()
        
        # Check if we have mock objects
        if isinstance(model, str):
            logger.warning(f"Using mock model: model={model}")
            import random
            class_names = get_class_names()
            if not class_names:
                class_names = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
                               'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
            random_class = random.randint(0, len(class_names)-1)
            
            return {
                "label": class_names[random_class],
                "confidence": round(random.uniform(60.0, 95.0), 2),
                "class_id": random_class,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "note": "MOCK_MODEL - This is a mock prediction as model loading failed"
            }, 200
        
        # Preprocess frame for hand detection
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
        
        # Process image for Keras model - resize to expected input size
        input_size = (224, 224)  # Standard size for many vision models
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_frame = cv2.resize(rgb_frame, input_size)
        
        # Normalize pixel values to [0, 1]
        input_data = resized_frame.astype(np.float32) / 255.0
        
        # Add batch dimension
        input_data = np.expand_dims(input_data, axis=0)
        
        # Run inference with Keras model
        predictions = model.predict(input_data)
        
        # Get predicted class
        predicted_class = np.argmax(predictions[0])
        
        # Get confidence
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
    Make a prediction from hand landmarks
    
    Args:
        landmarks: List of hand landmark coordinates [x,y]
        
    Returns:
        dict: Prediction result containing label, confidence, etc.
    """
    # Check if ML is available
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, returning mock prediction")
        return {
            "label": "Mock Prediction",
            "confidence": 85.0,
            "class_id": 0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "note": "ML_DISABLED - This is a mock prediction as ML libraries are not installed"
        }, 200
    
    try:
        # Create a blank image to draw landmarks on
        img_size = 224  # Standard size for many vision models
        blank_image = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        blank_image.fill(255)  # White background
        
        # Draw landmarks on the image
        for i, landmark in enumerate(landmarks[:21]):  # Only use the first hand
            x, y = int(landmark[0] * img_size), int(landmark[1] * img_size)
            cv2.circle(blank_image, (x, y), 5, (0, 0, 255), -1)  # Red circles
            if i > 0:  # Connect the dots
                prev_x, prev_y = int(landmarks[i-1][0] * img_size), int(landmarks[i-1][1] * img_size)
                cv2.line(blank_image, (prev_x, prev_y), (x, y), (0, 255, 0), 2)  # Green lines
        
        # Now use the image with drawn landmarks for prediction
        return predict_from_frame(blank_image)
        
    except Exception as e:
        logger.error(f"Error in predict_from_landmarks: {e}")
        return {"error": f"Error making prediction: {str(e)}"}, 500
import os
import logging
from flask import current_app, jsonify
import time

logger = logging.getLogger(__name__)

# Check if ML libraries are available
ML_AVAILABLE = False
try:
    import tensorflow as tf
    import mediapipe as mp
    ML_AVAILABLE = True
    logger.info("ML libraries imported successfully in model_loader")
except ImportError:
    logger.warning("ML libraries not available, using mock objects for development")
    tf = None
    mp = None

def load_model():
    """
    Load the sign language recognition model
    Returns loaded TensorFlow model or a placeholder object
    """
    if current_app.ml_model is not None:
        logger.info("Model already loaded, returning cached instance")
        return current_app.ml_model
    
    # Check if ML libraries are available
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, using mock model")
        # Set placeholder objects
        current_app.ml_model = "ML_DISABLED"
        current_app.mp_hands = "ML_DISABLED"
        return current_app.ml_model
    
    logger.info("Loading sign language recognition model...")
    start_time = time.time()
    
    # Check if should use HuggingFace model or local model
    if current_app.config.get('USE_HF_MODEL', False):
        logger.info(f"Loading model from HuggingFace: {current_app.config['MODEL_HF_REPO']}")
        try:
            # Import huggingface_hub
            from huggingface_hub import from_pretrained_keras
            
            # Load the model from HuggingFace
            model = from_pretrained_keras(current_app.config['MODEL_HF_REPO'])
            logger.info(f"Successfully loaded model from HuggingFace in {time.time() - start_time:.2f} seconds")
            
            # Cache the model
            current_app.ml_model = model
            return model
            
        except Exception as e:
            logger.error(f"Error loading model from HuggingFace: {e}")
            logger.info("Falling back to local model")
    
    # Load local model
    model_path = current_app.config['MODEL_PATH']
    
    # Check if model file exists
    if not os.path.exists(model_path):
        logger.error(f"Model file not found at {model_path}")
        
        # Create a minimal placeholder model for testing purposes
        # In production, this should raise an error
        logger.warning("Creating a placeholder model for testing - THIS SHOULD NOT HAPPEN IN PRODUCTION")
        inputs = tf.keras.layers.Input(shape=(21*2*2,))  # 21 landmarks with x,y for 2 hands
        x = tf.keras.layers.Dense(64, activation='relu')(inputs)
        outputs = tf.keras.layers.Dense(10, activation='softmax')(x)  # 10 sample classes
        model = tf.keras.Model(inputs=inputs, outputs=outputs)
    else:
        # Load the model from file
        try:
            model = tf.keras.models.load_model(model_path)
            logger.info(f"Successfully loaded model from {model_path} in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    # Initialize mediapipe hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # Store both the TF model and mediapipe hands in the app context
    current_app.ml_model = model
    current_app.mp_hands = hands
    
    return model

def get_model_and_hands():
    """Get both the TensorFlow model and MediaPipe hands"""
    # Load model if not already loaded
    if current_app.ml_model is None:
        load_model()
    
    return current_app.ml_model, current_app.mp_hands

def get_class_names():
    """Get the class names for the model's output indices"""
    # This would ideally be loaded from a file along with the model
    # For now, using a hardcoded set of common sign language words
    return [
        "Hello", "Thank you", "Yes", "No", "Please",
        "Sorry", "Love", "Good", "Bad", "Okay",
        "Help", "Want", "Need", "More", "Stop",
        "Food", "Water", "Friend", "Family", "Work"
    ]

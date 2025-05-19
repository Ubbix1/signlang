import os
import logging
from flask import current_app, jsonify
import time
import tempfile

logger = logging.getLogger(__name__)

# Try to set Keras backend to TensorFlow
os.environ["KERAS_BACKEND"] = "tensorflow"

# Configure TensorFlow to reduce warnings
import tensorflow as tf
tf.get_logger().setLevel('ERROR')  # Reduce TensorFlow logging
tf.config.optimizer.set_jit(True)  # Enable XLA compilation

# Define path for saving model locally
MODEL_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "model_cache")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

# Check if ML libraries are available
ML_AVAILABLE = False
try:
    import mediapipe as mp
    import numpy as np
    import cv2
    import keras
    from PIL import Image
    from huggingface_hub import snapshot_download, hf_hub_download
    
    ML_AVAILABLE = True
    logger.info("ML libraries imported successfully in model_loader")
    logger.info(f"Keras backend: {keras.backend.backend()}")
except ImportError as e:
    logger.warning(f"ML libraries not available, using mock objects for development: {e}")
    mp = None

# Model path for Keras
KERAS_MODEL_REPO = "cdsteameight/ISL-SignLanguageTranslation"
KERAS_MODEL_FILENAME = "isl-translate-v1.keras"

# Register the custom model class
@keras.saving.register_keras_serializable()
class ISLSignPosTranslator(keras.Model):
    """Custom model class for ISL sign language translation"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trainable = True
        # Initialize the model architecture
        self.conv1 = keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3))
        self.pool1 = keras.layers.MaxPooling2D((2, 2))
        self.conv2 = keras.layers.Conv2D(64, (3, 3), activation='relu')
        self.pool2 = keras.layers.MaxPooling2D((2, 2))
        self.conv3 = keras.layers.Conv2D(64, (3, 3), activation='relu')
        self.flatten = keras.layers.Flatten()
        self.dense1 = keras.layers.Dense(64, activation='relu')
        self.dense2 = keras.layers.Dense(26, activation='softmax')  # 26 for A-Z

    def call(self, inputs):
        x = self.conv1(inputs)
        x = self.pool1(x)
        x = self.conv2(x)
        x = self.pool2(x)
        x = self.conv3(x)
        x = self.flatten(x)
        x = self.dense1(x)
        return self.dense2(x)

    def get_config(self):
        config = super().get_config()
        return config

def get_class_names():
    """Return the class names for the sign language model"""
    # Default sign language alphabet class names for ISL
    default_classes = [
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
    ]
    
    # Try to get class names from huggingface dataset manager if available
    if hasattr(current_app, 'hf_dataset_manager') and current_app.hf_dataset_manager:
        dataset_class_names = current_app.hf_dataset_manager.get_class_names()
        if dataset_class_names:
            return dataset_class_names
    
    # Fall back to default class names
    return default_classes

def create_mock_model():
    """Create a simple mock model for testing"""
    if not ML_AVAILABLE:
        return "MOCK_MODEL"
        
    try:
        # Create a simple sequential model
        model = keras.Sequential([
            keras.layers.InputLayer(input_shape=(224, 224, 3)),
            keras.layers.Conv2D(16, (3, 3), activation='relu'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(26, activation='softmax')  # 26 for A-Z
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy')
        return model
    except Exception as e:
        logger.error(f"Error creating mock model: {e}")
        return "MOCK_MODEL"

def load_model():
    """
    Load the sign language recognition model
    Returns loaded model or a placeholder object
    """
    if hasattr(current_app, 'ml_model') and current_app.ml_model is not None:
        logger.info("Model already loaded, returning cached instance")
        return current_app.ml_model, None
    
    # Check if ML libraries are available
    if not ML_AVAILABLE:
        logger.warning("ML libraries not available, using mock model")
        # Set placeholder objects
        current_app.ml_model = "ML_DISABLED"
        current_app.mp_hands = "ML_DISABLED"
        return current_app.ml_model, None
    
    logger.info("Loading sign language recognition model...")
    start_time = time.time()
    
    try:
        # Create a new model instance
        model = ISLSignPosTranslator()
        
        # Build the model with a sample input
        sample_input = tf.random.normal((1, 224, 224, 3))
        _ = model(sample_input)  # This builds the model
        
        # Compile the model
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        
        # Check if we have the model cached locally
        local_model_path = os.path.join(MODEL_CACHE_DIR, KERAS_MODEL_FILENAME)
        
        if os.path.exists(local_model_path):
            logger.info(f"Loading model from local cache: {local_model_path}")
            try:
                model = keras.models.load_model(local_model_path, custom_objects={'ISLSignPosTranslator': ISLSignPosTranslator})
            except Exception as e:
                logger.error(f"Error loading cached model: {e}")
                model = None
        else:
            model = None
            
        if model is None:
            # Download and load Keras model
            logger.info(f"Downloading Keras model from repository: {KERAS_MODEL_REPO}")
            
            try:
                model_file = hf_hub_download(
                    repo_id=KERAS_MODEL_REPO,
                    filename=KERAS_MODEL_FILENAME,
                    local_dir=MODEL_CACHE_DIR,
                    local_dir_use_symlinks=False
                )
                logger.info(f"Model file downloaded to: {model_file}")
                model = keras.models.load_model(model_file, custom_objects={'ISLSignPosTranslator': ISLSignPosTranslator})
            except Exception as download_error:
                logger.error(f"Error downloading model: {download_error}")
                logger.warning("Creating a mock model as fallback")
                model = create_mock_model()
        
        logger.info(f"Successfully loaded model in {time.time() - start_time:.2f} seconds")
        logger.info(f"Model type: {type(model)}")
        
        # Initialize mediapipe hands
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Store in the app context
        current_app.ml_model = model
        current_app.mp_hands = hands
        
        return model, None
    except Exception as e:
        logger.error(f"Error loading Keras model: {e}")
        
        # Create placeholder model for testing
        logger.warning("Creating a placeholder model - THIS SHOULD NOT HAPPEN IN PRODUCTION")
        current_app.ml_model = create_mock_model()
        current_app.mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) if mp else "ML_DISABLED"
        
        return current_app.ml_model, None

def get_model_and_hands():
    """Get the model and MediaPipe hands"""
    # Load model if not already loaded
    if not hasattr(current_app, 'ml_model') or current_app.ml_model is None:
        load_model()
    
    return current_app.ml_model, current_app.mp_hands, None

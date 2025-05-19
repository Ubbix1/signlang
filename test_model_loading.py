import os
import logging
import tensorflow as tf
from flask import Flask
from app.inference.model_loader import load_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_model_loading():
    """Test loading the sign language model"""
    try:
        # Create Flask app
        app = Flask(__name__)
        
        with app.app_context():
            # Load the model
            logger.info("Attempting to load model...")
            model, _ = load_model()
            
            if isinstance(model, str):
                logger.error(f"Model loading failed: {model}")
                return False
                
            # Test model with a sample input
            logger.info("Testing model with sample input...")
            sample_input = tf.random.normal((1, 224, 224, 3))
            prediction = model.predict(sample_input)
            
            logger.info(f"Model loaded successfully!")
            logger.info(f"Prediction shape: {prediction.shape}")
            return True
        
    except Exception as e:
        logger.error(f"Error testing model: {e}")
        return False

if __name__ == "__main__":
    success = test_model_loading()
    if success:
        logger.info("Model loading test passed!")
    else:
        logger.error("Model loading test failed!") 
import os
import logging
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Attempt to import huggingface_hub
try:
    from huggingface_hub import snapshot_download
    logger.info("huggingface_hub imported successfully")
except ImportError as e:
    logger.error(f"Failed to import huggingface_hub: {e}")
    logger.info("Installing huggingface_hub...")
    import subprocess
    subprocess.check_call(["pip", "install", "huggingface_hub"])
    from huggingface_hub import snapshot_download

# Set the Keras backend
logger.info("Attempting to set Keras backend to JAX")
try:
    os.environ["KERAS_BACKEND"] = "jax"
    logger.info("Set KERAS_BACKEND environment variable to 'jax'")
except Exception as e:
    logger.error(f"Failed to set environment variable: {e}")

# Try to import keras
logger.info("Attempting to import Keras")
try:
    import keras
    logger.info(f"Keras version: {keras.__version__}")
    logger.info(f"Keras backend: {keras.backend.backend()}")
    
    # Check if the backend is not JAX
    if keras.backend.backend() != "jax":
        logger.warning("Keras is not using JAX as the backend. Attempting to force JAX...")
        
        # Try another approach - this may or may not work depending on the Keras version
        try:
            import tensorflow as tf
            logger.info(f"TensorFlow version: {tf.__version__}")
        except ImportError:
            logger.info("TensorFlow not found")
except ImportError as e:
    logger.error(f"Failed to import Keras: {e}")
    exit(1)

# Download the model from HuggingFace Hub
logger.info("Attempting to download the model from HuggingFace Hub")
try:
    repo_id = "cdsteameight/ISL-SignLanguageTranslation"
    logger.info(f"Downloading model from repository: {repo_id}")
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Download the model files
        model_path = snapshot_download(repo_id=repo_id, local_dir=tmpdirname)
        logger.info(f"Model downloaded to: {model_path}")
        
        # Try to load the model using Keras
        logger.info(f"Loading model from {model_path}")
        try:
            model = keras.models.load_model(model_path)
            logger.info("Model loaded successfully")
            
            # Print model summary
            logger.info("Model summary:")
            model.summary()
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
except Exception as e:
    logger.error(f"Failed to download model: {e}")

logger.info("Test completed") 
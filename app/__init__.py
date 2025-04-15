from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
import importlib.util

from app.config import DevelopmentConfig, ProductionConfig
from app.database.db import initialize_db

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if ML libraries are available
ML_AVAILABLE = False
try:
    # First try to import numpy with the right version
    import numpy as np
    logger.info(f"Using NumPy version: {np.__version__}")
    
    # Then try to import TensorFlow
    import tensorflow as tf
    logger.info(f"Using TensorFlow version: {tf.__version__}")
    
    # Finally try to import MediaPipe
    import mediapipe as mp
    logger.info(f"Using MediaPipe version: {mp.__version__}")
    
    ML_AVAILABLE = True
    logger.info("ML libraries found, machine learning features will be available")
except ImportError as e:
    logger.warning(f"ML libraries import error: {e}")
    logger.warning("Machine learning features will be disabled")
except Exception as e:
    logger.error(f"Unexpected error loading ML libraries: {e}")
    logger.warning("Machine learning features will be disabled")

def create_app(config_class=DevelopmentConfig):
    """Application factory function to create and configure the Flask app"""
    app = Flask(__name__)
    
    # Load configuration
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)
    
    # Set secret key from environment variable
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    
    # Enable CORS with more specific configuration
    CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True, "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})
    
    # Add JSON error handling for proper responses
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405
    
    # Initialize Firestore database connection
    initialize_db(app)
    
    # Load ML model (will be initialized on first request)
    with app.app_context():
        app.ml_model = None  # Placeholder, will be loaded lazily
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.prediction_routes import prediction_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(prediction_bp, url_prefix='/api/prediction')
    
    # Register default route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    logger.info("Application initialized successfully")
    return app

from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
import importlib.util

from app.config import DevelopmentConfig, ProductionConfig
from app.database.db import initialize_db as initialize_firebase
from app.database.mongodb import initialize_db as initialize_mongodb

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
    
    # Initialize Firebase for authentication
    try:
        initialize_firebase(app)
        logger.info("Firebase Auth initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
    
    # Initialize MongoDB for application data
    try:
        initialize_mongodb(app)
        logger.info("MongoDB initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing MongoDB: {e}")
    
    # Load ML model (will be initialized on first request)
    with app.app_context():
        app.ml_model = None  # Placeholder, will be loaded lazily
        app.ml_available = ML_AVAILABLE
    
    # Register blueprints
    try:
        from app.auth.routes import auth_bp
        from app.routes.user_routes import user_bp
        from app.routes.admin_routes import admin_bp
        from app.routes.prediction_routes import prediction_bp
        
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(user_bp, url_prefix='/api/user')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(prediction_bp, url_prefix='/api/prediction')
    except Exception as e:
        logger.error(f"Error registering blueprints: {e}")
    
    # Register default route
    @app.route('/')
    def index():
        from flask import render_template
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error loading index template: {e}")
            # Fallback to JSON response if template fails
            return jsonify({"status": "ok", "message": "SignAI API is running", "ml_available": ML_AVAILABLE})
    
    # API checker endpoint
    @app.route('/api_checker')
    def api_checker():
        # Define API endpoints and their descriptions
        apis = [
            {
                "endpoint": "/",
                "method": "GET",
                "description": "API status check - returns basic information about the API",
                "auth_required": False
            },
            {
                "endpoint": "/health",
                "method": "GET", 
                "description": "Health check endpoint for monitoring services like Render",
                "auth_required": False
            },
            {
                "endpoint": "/api_checker",
                "method": "GET",
                "description": "Lists all available API endpoints with descriptions",
                "auth_required": False
            },
            {
                "endpoint": "/api/auth/login",
                "method": "POST",
                "description": "Authenticates a user with Firebase and returns a token",
                "auth_required": False
            },
            {
                "endpoint": "/api/auth/register",
                "method": "POST",
                "description": "Registers a new user in Firebase Authentication",
                "auth_required": False
            },
            {
                "endpoint": "/api/user/profile",
                "method": "GET",
                "description": "Retrieves the authenticated user's profile information",
                "auth_required": True
            },
            {
                "endpoint": "/api/user/profile",
                "method": "PUT",
                "description": "Updates the authenticated user's profile information",
                "auth_required": True
            },
            {
                "endpoint": "/api/prediction/start_session",
                "method": "POST",
                "description": "Starts a new gesture recognition session",
                "auth_required": True
            },
            {
                "endpoint": "/api/prediction/end_session",
                "method": "POST",
                "description": "Ends an active gesture recognition session",
                "auth_required": True
            },
            {
                "endpoint": "/api/prediction/log",
                "method": "POST",
                "description": "Logs a gesture prediction with confidence score",
                "auth_required": True
            },
            {
                "endpoint": "/api/prediction/history",
                "method": "GET",
                "description": "Retrieves prediction history for the authenticated user",
                "auth_required": True
            },
            {
                "endpoint": "/api/prediction/add-samples",
                "method": "POST",
                "description": "Adds sample prediction data for testing",
                "auth_required": True
            },
            {
                "endpoint": "/api/admin/users",
                "method": "GET",
                "description": "Lists all users (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/users/<user_id>",
                "method": "GET",
                "description": "Retrieves detailed information about a specific user (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/users/<user_id>",
                "method": "PUT",
                "description": "Updates a user's information (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/users/<user_id>",
                "method": "DELETE",
                "description": "Deletes a user and their associated data (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/users/<user_id>/status",
                "method": "PUT",
                "description": "Updates a user's status (activate/suspend) (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/users/<user_id>/reset-password",
                "method": "POST",
                "description": "Resets a user's password (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/users/<user_id>/impersonate",
                "method": "POST",
                "description": "Generates a token to login as a specific user (admin only)",
                "auth_required": True,
                "admin_only": True
            },
            {
                "endpoint": "/api/admin/stats",
                "method": "GET",
                "description": "Retrieves system-wide statistics (admin only)",
                "auth_required": True,
                "admin_only": True
            }
        ]
        
        # Try to render HTML template first
        try:
            from flask import render_template
            return render_template('api_checker.html', 
                                  apis=apis, 
                                  ml_available=ML_AVAILABLE, 
                                  total_endpoints=len(apis))
        except Exception as e:
            # Fallback to JSON if template isn't available
            logger.warning(f"Could not render api_checker template: {e}")
            return jsonify({
                "status": "ok",
                "apis": apis,
                "ml_available": ML_AVAILABLE,
                "total_endpoints": len(apis)
            })
    
    # Health check endpoint for Render
    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"}), 200
    
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

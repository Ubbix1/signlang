import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    
    # Firebase settings
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'signai-web-app-firebase-adminsdk-fbsvc-ba097b499b.json')
    
    # MongoDB settings
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/?retryWrites=true&w=majority&appName=signai')
    
    # HuggingFace settings
    HF_DATASET_NAME = os.environ.get('HF_DATASET_NAME', 'NAM27/sign-language')
    HF_CACHE_DIR = os.environ.get('HF_CACHE_DIR', './data/huggingface')
    HF_AUTOLOAD = os.environ.get('HF_AUTOLOAD', 'false').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    # In production, ensure all secrets are properly set in environment variables
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/?retryWrites=true&w=majority&appName=signai')
    
    # Set more strict security settings for production
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    FIREBASE_CREDENTIALS_PATH = os.environ.get('TEST_FIREBASE_CREDENTIALS_PATH', 'signai-web-app-firebase-adminsdk-fbsvc-ba097b499b.json')
    MONGODB_URI = os.environ.get('TEST_MONGODB_URI', 'mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/?retryWrites=true&w=majority&appName=signai')

# Dictionary to easily access different configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])

import os

class Config:
    """Base configuration class"""
    # JWT Settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    
    # Firebase Settings
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'signai-web-app-firebase-adminsdk-fbsvc-ba097b499b.json')
    
    # MongoDB Settings
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/?appName=signai')
    
    # Model Settings
    MODEL_PATH = os.environ.get('MODEL_PATH', './model/sign_language_model.h5')
    MODEL_HF_REPO = os.environ.get('MODEL_HF_REPO', 'your-huggingface-repo/sign-language-model')
    USE_HF_MODEL = os.environ.get('USE_HF_MODEL', 'False').lower() == 'true'
    
    # Flask Settings
    DEBUG = False
    TESTING = False
    HOST = '0.0.0.0'
    PORT = 5000

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    # In production, ensure all secrets are properly set in environment variables
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/?appName=signai')
    
    # Set more strict security settings for production
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    FIREBASE_CREDENTIALS_PATH = os.environ.get('TEST_FIREBASE_CREDENTIALS_PATH', 'signai-web-app-firebase-adminsdk-fbsvc-ba097b499b.json')
    MONGODB_URI = os.environ.get('TEST_MONGODB_URI', 'mongodb+srv://drkgamer194:admin123@signai.uu3gif4.mongodb.net/test?appName=signai')

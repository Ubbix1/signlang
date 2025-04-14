from flask import g
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

def get_db():
    """
    Get database connection from Flask's application context (g)
    Returns MongoDB database object
    """
    if 'db' not in g:
        connect_db()
    return g.db

def connect_db():
    """
    Connect to MongoDB and store connection in Flask's application context (g)
    """
    from flask import current_app
    
    # Get MongoDB URI from configuration
    mongo_uri = current_app.config['MONGO_URI']
    
    try:
        # Create client
        client = MongoClient(mongo_uri)
        
        # Get database name from URI
        # MongoDB URI format: mongodb://username:password@host:port/database
        # or mongodb+srv://username:password@host/database
        db_name = mongo_uri.split('/')[-1]
        if '?' in db_name:
            db_name = db_name.split('?')[0]
        
        # If no database specified, use default
        if not db_name:
            db_name = "signai_db"
        
        # Set database in Flask context
        g.client = client
        g.db = client[db_name]
        
        # Ensure indexes
        create_indexes(g.db)
        
        logger.info(f"Connected to MongoDB database: {db_name}")
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise

def create_indexes(db):
    """
    Create necessary indexes for collections
    """
    # User indexes
    db.users.create_index("email", unique=True)
    
    # Prediction indexes
    db.predictions.create_index("user_id")
    db.predictions.create_index("timestamp")

def close_db(e=None):
    """
    Close MongoDB connection
    """
    client = g.pop('client', None)
    
    if client is not None:
        client.close()
        logger.info("MongoDB connection closed")

def initialize_db(app):
    """
    Initialize database connection and teardown
    """
    app.teardown_appcontext(close_db)

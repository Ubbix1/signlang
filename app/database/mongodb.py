from flask import g, current_app
from pymongo import MongoClient, DESCENDING
from datetime import datetime
import logging
import os
from bson.objectid import ObjectId
import urllib.parse
import random

logger = logging.getLogger(__name__)

def get_db():
    """
    Get MongoDB database instance from Flask's application context (g)
    Returns MongoDB database object
    """
    if 'mongodb' not in g:
        connect_db()
    return g.mongodb

def connect_db():
    """
    Connect to MongoDB and store connection in Flask's application context (g)
    """
    try:
        # Get MongoDB URI from config
        mongodb_uri = current_app.config.get('MONGODB_URI')
        
        # Parse MongoDB URI to ensure a database name is present
        parsed_uri = urllib.parse.urlparse(mongodb_uri)
        
        # If no database specified in URI, add 'signai' as default
        if not parsed_uri.path or parsed_uri.path == '/':
            # Add default database name
            if '?' in mongodb_uri:
                parts = mongodb_uri.split('?', 1)
                mongodb_uri = f"{parts[0]}/signai?{parts[1]}"
            else:
                mongodb_uri = f"{mongodb_uri}/signai"
            
            logger.info(f"Added default database name to MongoDB URI: signai")
        
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client.get_database()
        
        logger.info(f"Connected to MongoDB database: {db.name}")
        
        # Store database in Flask's application context
        g.mongodb = db
        g.mongo_client = client
        
        # Check connection by attempting a simple operation
        db.command('ping')
        
        logger.info("MongoDB connection successful")
        
        # Create indexes for collections if they don't exist
        ensure_indexes(db)
        
        return db
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise

def ensure_indexes(db):
    """
    Ensure indexes exist for all collections
    """
    # User collection indexes (for extended user data beyond Firebase Auth)
    if 'users' not in db.list_collection_names():
        db.create_collection('users')
    db.users.create_index('firebase_uid', unique=True)
    
    # Prediction logs collection indexes
    if 'prediction_logs' not in db.list_collection_names():
        db.create_collection('prediction_logs')
    db.prediction_logs.create_index([('user_id', 1), ('timestamp', -1)])
    db.prediction_logs.create_index('session_id')
    
    # Sessions collection indexes
    if 'sessions' not in db.list_collection_names():
        db.create_collection('sessions')
    db.sessions.create_index('user_id')
    db.sessions.create_index('start_time')
    
    # Error logs collection indexes
    if 'error_logs' not in db.list_collection_names():
        db.create_collection('error_logs')
    db.error_logs.create_index('timestamp')
    
    logger.info("MongoDB indexes created")

def close_db(e=None):
    """
    Close MongoDB connection
    """
    mongo_client = g.pop('mongo_client', None)
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed")
    g.pop('mongodb', None)

def initialize_db(app):
    """
    Initialize database connection and teardown
    """
    app.teardown_appcontext(close_db)
    
    # Test connection during app initialization
    with app.app_context():
        try:
            connect_db()
            logger.info("MongoDB connection test successful")
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")

#
# User operations - only for extended user data beyond Firebase Auth
#

def save_user_profile(firebase_uid, user_data):
    """
    Create or update user profile data in MongoDB
    This is for extended user data beyond what Firebase Auth stores
    
    Args:
        firebase_uid (str): Firebase user ID
        user_data (dict): Additional user data
    
    Returns:
        str: MongoDB ObjectId of the user document
    """
    db = get_db()
    
    # Check if user already exists
    existing_user = db.users.find_one({'firebase_uid': firebase_uid})
    
    if existing_user:
        # Update existing user
        db.users.update_one(
            {'firebase_uid': firebase_uid},
            {'$set': {**user_data, 'updated_at': datetime.utcnow()}}
        )
        return str(existing_user['_id'])
    else:
        # Create new user
        user_data['firebase_uid'] = firebase_uid
        user_data['created_at'] = datetime.utcnow()
        user_data['updated_at'] = datetime.utcnow()
        
        result = db.users.insert_one(user_data)
        return str(result.inserted_id)

def get_user_profile(firebase_uid):
    """
    Get user profile data from MongoDB
    
    Args:
        firebase_uid (str): Firebase user ID
    
    Returns:
        dict: User profile data or None if not found
    """
    db = get_db()
    user = db.users.find_one({'firebase_uid': firebase_uid})
    
    if user:
        user['_id'] = str(user['_id'])
        return user
    
    return None

def get_all_users(page=1, per_page=20):
    """
    Get all users with pagination
    
    Args:
        page (int): Page number (1-based)
        per_page (int): Items per page
    
    Returns:
        dict: Dictionary with users and pagination info
    """
    db = get_db()
    skip = (page - 1) * per_page
    
    # Get total count
    total_count = db.users.count_documents({})
    
    # Get users with pagination
    cursor = db.users.find().skip(skip).limit(per_page)
    users = []
    for user in cursor:
        user['_id'] = str(user['_id'])
        users.append(user)
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    
    return {
        "users": users,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": total_pages
        }
    }

#
# Session operations
#

def create_session(user_id):
    """
    Create a new session for a user
    
    Args:
        user_id (str): User ID (Firebase UID)
    
    Returns:
        str: Session ID
    """
    db = get_db()
    session_data = {
        'user_id': user_id,
        'start_time': datetime.utcnow(),
        'is_active': True,
        'total_gestures_detected': 0
    }
    
    result = db.sessions.insert_one(session_data)
    return str(result.inserted_id)

def end_session(session_id):
    """
    End a session
    
    Args:
        session_id (str): Session ID
    
    Returns:
        bool: True if session was ended successfully
    """
    db = get_db()
    try:
        # Get the session
        session = db.sessions.find_one({'_id': ObjectId(session_id)})
        if not session:
            return False
        
        # Calculate duration and update session
        end_time = datetime.utcnow()
        start_time = session.get('start_time', end_time)
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Update session with end time and duration
        db.sessions.update_one(
            {'_id': ObjectId(session_id)},
            {
                '$set': {
                    'end_time': end_time,
                    'is_active': False,
                    'duration_seconds': duration_seconds
                }
            }
        )
        
        return True
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return False

def get_user_sessions(user_id, page=1, per_page=10):
    """
    Get sessions for a user with pagination
    
    Args:
        user_id (str): User ID (Firebase UID)
        page (int): Page number (1-based)
        per_page (int): Items per page
    
    Returns:
        dict: Dictionary with sessions and pagination info
    """
    db = get_db()
    skip = (page - 1) * per_page
    
    # Get total count
    total_count = db.sessions.count_documents({'user_id': user_id})
    
    # Get sessions with pagination
    cursor = db.sessions.find({'user_id': user_id}) \
                        .sort('start_time', DESCENDING) \
                        .skip(skip) \
                        .limit(per_page)
    
    sessions = []
    for session in cursor:
        session['_id'] = str(session['_id'])
        sessions.append(session)
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    
    return {
        "sessions": sessions,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": total_pages
        }
    }

#
# Prediction operations
#

def log_prediction(user_id, session_id, gesture_label, confidence, landmark_data=None):
    """
    Log a prediction
    
    Args:
        user_id (str): User ID (Firebase UID)
        session_id (str): Session ID
        gesture_label (str): Recognized gesture label
        confidence (float): Confidence score
        landmark_data (dict, optional): Raw landmark data
    
    Returns:
        str: Prediction log ID
    """
    db = get_db()
    
    # Create prediction log
    log_data = {
        'user_id': user_id,
        'session_id': session_id,
        'gesture_label': gesture_label,
        'confidence': confidence,
        'timestamp': datetime.utcnow()
    }
    
    # Add landmark data if provided
    if landmark_data:
        log_data['landmark_data'] = landmark_data
    
    # Insert prediction log
    result = db.prediction_logs.insert_one(log_data)
    
    # Increment total_gestures_detected in the session
    db.sessions.update_one(
        {'_id': ObjectId(session_id)},
        {'$inc': {'total_gestures_detected': 1}}
    )
    
    return str(result.inserted_id)

def get_user_predictions(user_id, page=1, per_page=20):
    """
    Get predictions for a user with pagination
    
    Args:
        user_id (str): User ID (Firebase UID)
        page (int): Page number (1-based)
        per_page (int): Items per page
    
    Returns:
        dict: Dictionary with predictions and pagination info
    """
    db = get_db()
    skip = (page - 1) * per_page
    
    # Get total count
    total_count = db.prediction_logs.count_documents({'user_id': user_id})
    
    # Get predictions with pagination
    cursor = db.prediction_logs.find({'user_id': user_id}) \
                              .sort('timestamp', DESCENDING) \
                              .skip(skip) \
                              .limit(per_page)
    
    predictions = []
    for prediction in cursor:
        prediction['_id'] = str(prediction['_id'])
        if 'session_id' in prediction and isinstance(prediction['session_id'], ObjectId):
            prediction['session_id'] = str(prediction['session_id'])
        predictions.append(prediction)
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    
    return {
        "predictions": predictions,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": total_pages
        }
    }

#
# Error logging
#

def log_error(error_type, message, user_id=None, session_id=None, metadata=None):
    """
    Log an error
    
    Args:
        error_type (str): Type of error
        message (str): Error message
        user_id (str, optional): User ID
        session_id (str, optional): Session ID
        metadata (dict, optional): Additional error metadata
    
    Returns:
        str: Error log ID
    """
    db = get_db()
    
    # Create error log
    log_data = {
        'error_type': error_type,
        'message': message,
        'timestamp': datetime.utcnow()
    }
    
    # Add user_id if provided
    if user_id:
        log_data['user_id'] = user_id
    
    # Add session_id if provided
    if session_id:
        log_data['session_id'] = session_id
    
    # Add metadata if provided
    if metadata:
        log_data['metadata'] = metadata
    
    # Insert error log
    result = db.error_logs.insert_one(log_data)
    return str(result.inserted_id)

#
# Admin dashboard data
#

def get_admin_stats():
    """
    Get statistics for admin dashboard
    
    Returns:
        dict: Statistics including user count, prediction count, etc.
    """
    db = get_db()
    
    stats = {
        'total_users': db.users.count_documents({}),
        'total_sessions': db.sessions.count_documents({}),
        'total_predictions': db.prediction_logs.count_documents({}),
        'active_sessions': db.sessions.count_documents({'is_active': True})
    }
    
    # Get top gestures
    pipeline = [
        {'$group': {'_id': '$gesture_label', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    top_gestures = list(db.prediction_logs.aggregate(pipeline))
    stats['top_gestures'] = top_gestures
    
    # Get most active users
    pipeline = [
        {'$group': {'_id': '$user_id', 'prediction_count': {'$sum': 1}}},
        {'$sort': {'prediction_count': -1}},
        {'$limit': 10}
    ]
    active_users = list(db.prediction_logs.aggregate(pipeline))
    
    # Look up user details for active users
    user_ids = [entry['_id'] for entry in active_users]
    users = {user['firebase_uid']: user for user in db.users.find({'firebase_uid': {'$in': user_ids}})}
    
    for entry in active_users:
        user_id = entry['_id']
        if user_id in users:
            entry['user'] = {
                'email': users[user_id].get('email', 'Unknown'),
                'name': users[user_id].get('name', 'Unknown')
            }
    
    stats['most_active_users'] = active_users
    
    return stats

def add_sample_predictions(user_id, count=5):
    """
    Add sample prediction data for testing
    
    Args:
        user_id (str): User ID to add predictions for
        count (int): Number of sample predictions to add
    
    Returns:
        list: IDs of created predictions
    """
    db = get_db()
    
    gestures = ["Hello", "Thank You", "Yes", "No", "Please", "Sorry", "Help", "Good", "Bad", "Love"]
    ids = []
    
    for i in range(count):
        # Create sample prediction
        gesture = gestures[i % len(gestures)]
        confidence = round(50 + (random.random() * 50), 2)  # Random confidence between 50-100%
        timestamp = datetime.utcnow() - datetime.timedelta(days=i)  # Spread out over days
        
        prediction = {
            'user_id': user_id,
            'gesture_label': gesture,
            'confidence': confidence,
            'timestamp': timestamp,
            'metadata': {
                'device': 'Web Browser',
                'is_sample': True
            }
        }
        
        result = db.prediction_logs.insert_one(prediction)
        ids.append(str(result.inserted_id))
    
    return ids 
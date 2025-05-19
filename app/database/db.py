from flask import g, current_app
import firebase_admin
from firebase_admin import credentials, firestore, auth
import logging
import os
import json

logger = logging.getLogger(__name__)

def get_db():
    """
    Get Firestore database instance from Flask's application context (g)
    Returns Firestore database object
    """
    if 'db' not in g:
        connect_db()
    return g.db

def connect_db():
    """
    Connect to Firebase Firestore and store connection in Flask's application context (g)
    """
    try:
        # Initialize Firebase Admin SDK with credentials
        cred_json = current_app.config.get('FIREBASE_CREDENTIALS')
        
        if not firebase_admin._apps:
            if cred_json:
                # Use credentials from environment variable
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
            else:
                # Fallback to file path for local development
                cred_path = current_app.config.get('FIREBASE_CREDENTIALS_PATH')
                cred = credentials.Certificate(cred_path)
            
            firebase_admin.initialize_app(cred)
        
        # Get Firestore database
        g.db = firestore.client()
        
        logger.info("Connected to Firebase Firestore")
        
    except Exception as e:
        logger.error(f"Error connecting to Firebase Firestore: {e}")
        raise

def close_db(e=None):
    """
    Close Firebase connection (not strictly necessary with Firebase client)
    """
    # Firebase Admin SDK handles connection pooling automatically
    g.pop('db', None)
    logger.info("Firebase Firestore connection removed from context")

def initialize_db(app):
    """
    Initialize database connection and teardown
    """
    app.teardown_appcontext(close_db)

def verify_token(token):
    """
    Verify Firebase JWT token and return user information
    
    Args:
        token (str): Firebase JWT token
        
    Returns:
        dict: User information or None if invalid token
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None
        
def get_user_by_uid(uid):
    """
    Get user information from Firebase Auth
    
    Args:
        uid (str): Firebase user ID
        
    Returns:
        dict: User information or None if not found
    """
    try:
        user = auth.get_user(uid)
        return user
    except Exception as e:
        logger.error(f"Error getting user by UID: {e}")
        return None

# User operations
def create_user(email, password, name, role="user"):
    """
    Create a new user in Firestore
    
    Args:
        email (str): User's email
        password (str): Hashed password
        name (str): User's name
        role (str): User's role
    
    Returns:
        str: Document ID of the created user
    """
    db = get_db()
    user_data = {
        "email": email,
        "password": password,
        "name": name,
        "role": role,
        "created_at": firestore.SERVER_TIMESTAMP
    }
    
    # Check if user already exists
    existing_user = db.collection('users').where('email', '==', email).limit(1).get()
    if len(existing_user) > 0:
        raise ValueError(f"User with email {email} already exists")
    
    # Add user to Firestore
    user_ref = db.collection('users').document()
    user_ref.set(user_data)
    
    return user_ref.id

def get_user_by_email(email):
    """
    Get a user by email from Firestore
    
    Args:
        email (str): User's email address
    
    Returns:
        dict: User document or None if not found
    """
    db = get_db()
    users = db.collection('users').where('email', '==', email).limit(1).get()
    
    for user in users:
        user_data = user.to_dict()
        user_data['id'] = user.id
        return user_data
    
    return None

def get_user_by_id(user_id):
    """
    Get a user by ID from Firestore
    
    Args:
        user_id (str): User document ID
    
    Returns:
        dict: User document or None if not found
    """
    db = get_db()
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get()
    
    if user.exists:
        user_data = user.to_dict()
        user_data['id'] = user.id
        return user_data
    
    return None

# Prediction operations
def create_prediction(user_id, label, confidence, class_id=None, metadata=None):
    """
    Create a new prediction in Firestore
    
    Args:
        user_id (str): ID of the user
        label (str): Prediction label
        confidence (float): Prediction confidence score
        class_id (int, optional): Class ID
        metadata (dict, optional): Additional metadata
    
    Returns:
        str: Document ID of the created prediction
    """
    db = get_db()
    prediction_data = {
        "user_id": user_id,
        "label": label,
        "confidence": confidence,
        "class_id": class_id,
        "metadata": metadata or {},
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    
    # Add prediction to Firestore
    prediction_ref = db.collection('predictions').document()
    prediction_ref.set(prediction_data)
    
    return prediction_ref.id

def get_user_predictions(user_id, page=1, per_page=10):
    """
    Get predictions for a user with pagination from Firestore
    
    Args:
        user_id (str): User document ID
        page (int): Page number (1-based)
        per_page (int): Number of items per page
    
    Returns:
        dict: Dictionary with predictions and pagination info
    """
    db = get_db()
    predictions_ref = db.collection('predictions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING)
    
    # Get total count (this is a limitation in Firestore - we need a separate query)
    total_count = len(list(predictions_ref.get()))
    
    # Calculate start and end indices
    start = (page - 1) * per_page
    
    # Get paginated predictions
    predictions = []
    for i, doc in enumerate(predictions_ref.get()):
        if i >= start and i < start + per_page:
            prediction_data = doc.to_dict()
            prediction_data['id'] = doc.id
            predictions.append(prediction_data)
        elif i >= start + per_page:
            break
    
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

def delete_prediction(prediction_id, user_id):
    """
    Delete a prediction from Firestore
    
    Args:
        prediction_id (str): Prediction document ID
        user_id (str): User document ID for validation
    
    Returns:
        bool: True if deleted, False if not found
    """
    db = get_db()
    prediction_ref = db.collection('predictions').document(prediction_id)
    prediction = prediction_ref.get()
    
    if prediction.exists and prediction.to_dict().get('user_id') == user_id:
        prediction_ref.delete()
        return True
    
    return False

from flask import Blueprint, request, jsonify, current_app
import datetime
import jwt
import bcrypt
from app.database.db import get_db, create_user, get_user_by_email, get_user_by_id
from app.auth.utils import generate_token
from app.middleware.jwt_required import jwt_required
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in registration request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    # Validate required fields
    required_fields = ['email', 'password', 'name']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Check if user already exists
    existing_user = get_user_by_email(data['email'])
    if existing_user:
        return jsonify({"error": "User with this email already exists"}), 409
    
    try:
        # Create new user with specified role or default to "user"
        role = data.get('role', 'user')
        # For security, only allow admin creation in development mode
        if role == 'admin' and not current_app.config.get('DEBUG', False):
            logger.warning(f"Attempt to create admin user from non-debug environment: {data['email']}")
            role = 'user'

        # Hash the password before storing it
        password = data['password']
        if isinstance(password, str):
            password = password.encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
            
        # Create new user in Firestore
        user_id = create_user(
            email=data['email'],
            password=hashed_password,
            name=data['name'],
            role=role
        )
        
        # Generate tokens
        access_token = generate_token(
            {"user_id": user_id, "role": role},
            current_app.config['JWT_SECRET_KEY'],
            current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        refresh_token = generate_token(
            {"user_id": user_id},
            current_app.config['JWT_SECRET_KEY'],
            current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user_id,
                "email": data['email'],
                "name": data['name'],
                "role": role
            }
        }), 201
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return jsonify({"error": f"Failed to register user: {str(e)}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login an existing user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in login request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    # Validate required fields
    if 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Find user
    user = get_user_by_email(data['email'])
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Check password
    password = data['password']
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    stored_password = user['password']
    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')
        
    if not bcrypt.checkpw(password, stored_password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Generate tokens
    access_token = generate_token(
        {"user_id": user['id'], "role": user['role']},
        current_app.config['JWT_SECRET_KEY'],
        current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    )
    
    refresh_token = generate_token(
        {"user_id": user['id']},
        current_app.config['JWT_SECRET_KEY'],
        current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    )
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role']
        }
    }), 200

@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in refresh token request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    if 'refresh_token' not in data:
        return jsonify({"error": "Refresh token is required"}), 400
    
    try:
        # Decode the refresh token
        payload = jwt.decode(
            data['refresh_token'],
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        
        # Find user by ID
        user = get_user_by_id(payload['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Generate new access token
        access_token = generate_token(
            {"user_id": user['id'], "role": user['role']},
            current_app.config['JWT_SECRET_KEY'],
            current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        return jsonify({
            "access_token": access_token
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid refresh token"}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_user_profile(current_user):
    """Get current user profile"""
    # Find user by ID
    user = get_user_by_id(current_user['user_id'])
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Remove password from user data
    if 'password' in user:
        del user['password']
    
    return jsonify({
        "user": user
    }), 200

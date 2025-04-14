from flask import Blueprint, request, jsonify, current_app
import datetime
import jwt
from app.database.sql_models import User
from app.database.db_sql import get_db, create_user, get_user_by_email, get_user_by_id
from app.auth.utils import check_password, generate_token
from app.middleware.jwt_required import jwt_required
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
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
            
        new_user = create_user(
            email=data['email'],
            password=data['password'],  # Password will be hashed in the model
            name=data['name'],
            role=role
        )
        
        # Generate tokens
        access_token = generate_token(
            {"user_id": new_user.id, "role": new_user.role},
            current_app.config['JWT_SECRET_KEY'],
            current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        refresh_token = generate_token(
            {"user_id": new_user.id},
            current_app.config['JWT_SECRET_KEY'],
            current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "role": new_user.role
            }
        }), 201
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return jsonify({"error": "Failed to register user"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login an existing user"""
    data = request.get_json()
    
    # Validate required fields
    if 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Find user
    user = get_user_by_email(data['email'])
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Check password using the model's method
    if not user.check_password(data['password']):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Generate tokens
    access_token = generate_token(
        {"user_id": user.id, "role": user.role},
        current_app.config['JWT_SECRET_KEY'],
        current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    )
    
    refresh_token = generate_token(
        {"user_id": user.id},
        current_app.config['JWT_SECRET_KEY'],
        current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    )
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }), 200

@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    data = request.get_json()
    
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
            {"user_id": user.id, "role": user.role},
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
    
    # Convert to dictionary (excluding password)
    user_data = user.to_dict()
    
    return jsonify({
        "user": user_data
    }), 200

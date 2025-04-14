from functools import wraps
from flask import request, jsonify, current_app
import jwt
from app.auth.utils import extract_token_from_header

def jwt_required(f):
    """
    Decorator to protect routes with JWT authentication
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        
        # Extract token from header
        token = extract_token_from_header(auth_header)
        
        if not token:
            return jsonify({"error": "Missing or invalid authentication token"}), 401
        
        try:
            # Decode token
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # Add user info to kwargs
            return f(current_user=payload, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
    
    return decorated

def admin_required(f):
    """
    Decorator to restrict routes to admin users only
    Must be used after jwt_required
    """
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        # Check if user has admin role
        if current_user.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        return f(current_user=current_user, *args, **kwargs)
    
    return decorated

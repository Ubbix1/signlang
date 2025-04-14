import bcrypt
import jwt
import datetime

def hash_password(password):
    """Hash a password using bcrypt"""
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password, hashed_password):
    """Check if a password matches its hash"""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def generate_token(payload, secret_key, expires_delta):
    """Generate a JWT token with the given payload and expiration"""
    # Set expiration time
    exp = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_delta)
    
    # Add expiration to payload
    payload_copy = payload.copy()
    payload_copy.update({"exp": exp})
    
    # Generate token
    token = jwt.encode(payload_copy, secret_key, algorithm="HS256")
    
    return token

def decode_token(token, secret_key):
    """Decode a JWT token and return the payload"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"

def extract_token_from_header(auth_header):
    """Extract the token from the Authorization header"""
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if parts[0].lower() != 'bearer':
        return None
    elif len(parts) == 1:
        return None
    elif len(parts) > 2:
        return None
    
    return parts[1]

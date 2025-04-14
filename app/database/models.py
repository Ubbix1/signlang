from datetime import datetime
from bson import ObjectId

class User:
    """User model for MongoDB document"""
    
    def __init__(self, email, password, name, role="user", created_at=None):
        """
        Initialize a new User
        
        Args:
            email (str): User's email address
            password (str): Hashed password
            name (str): User's name
            role (str): User's role (user or admin)
            created_at (datetime): Account creation timestamp
        """
        self.email = email
        self.password = password
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert User object to dictionary for MongoDB"""
        return {
            "email": self.email,
            "password": self.password,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create User object from MongoDB document"""
        return cls(
            email=data.get("email"),
            password=data.get("password"),
            name=data.get("name"),
            role=data.get("role", "user"),
            created_at=data.get("created_at")
        )

class Prediction:
    """Prediction model for MongoDB document"""
    
    def __init__(self, user_id, label, confidence, class_id=None, timestamp=None):
        """
        Initialize a new Prediction
        
        Args:
            user_id (str): ID of the user who made the prediction
            label (str): Predicted sign language label
            confidence (float): Confidence score (0-100)
            class_id (int): Numeric class ID from the model
            timestamp (datetime): Prediction timestamp
        """
        self.user_id = user_id
        self.label = label
        self.confidence = confidence
        self.class_id = class_id
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """Convert Prediction object to dictionary for MongoDB"""
        return {
            "user_id": self.user_id,
            "label": self.label,
            "confidence": self.confidence,
            "class_id": self.class_id,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Prediction object from MongoDB document"""
        return cls(
            user_id=data.get("user_id"),
            label=data.get("label"),
            confidence=data.get("confidence"),
            class_id=data.get("class_id"),
            timestamp=data.get("timestamp")
        )

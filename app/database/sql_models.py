from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
import datetime
import bcrypt
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    name = Column(String(128), nullable=False)
    role = Column(String(32), default='user')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship with predictions
    predictions = relationship('Prediction', back_populates='user', cascade='all, delete-orphan')
    
    def __init__(self, email, password, name, role="user", created_at=None):
        self.email = email
        self.password = self._hash_password(password)
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.datetime.utcnow()
    
    def _hash_password(self, password):
        """Hash a password using bcrypt"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check if a password matches its hash"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.checkpw(password, self.password.encode('utf-8'))
    
    def to_dict(self):
        """Convert User object to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    label = Column(String(128), nullable=False)
    confidence = Column(Float, nullable=False)
    class_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    extra_data = Column(JSON, nullable=True)  # Any additional metadata
    
    # Relationship with user
    user = relationship('User', back_populates='predictions')
    
    def __init__(self, user_id, label, confidence, class_id=None, timestamp=None, metadata=None):
        self.user_id = user_id
        self.label = label
        self.confidence = confidence
        self.class_id = class_id
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.extra_data = metadata or {}
    
    def to_dict(self):
        """Convert Prediction object to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "confidence": self.confidence,
            "class_id": self.class_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.extra_data
        }

def init_db(app):
    """Initialize the database"""
    db.init_app(app)
    
    # Create all tables
    with app.app_context():
        db.create_all()
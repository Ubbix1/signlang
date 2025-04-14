from flask import g
from flask_sqlalchemy import SQLAlchemy
import logging
from .sql_models import db, User, Prediction

logger = logging.getLogger(__name__)

def get_db():
    """
    Get database connection from Flask's application context
    """
    return db

def initialize_db(app):
    """
    Initialize database with SQLAlchemy
    """
    logger.info("Initializing SQLAlchemy database connection")
    
    # Initialize SQLAlchemy with Flask app
    db.init_app(app)
    
    # Create all tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

def create_user(email, password, name, role="user"):
    """
    Create a new user
    """
    user = User(email=email, password=password, name=name, role=role)
    db.session.add(user)
    db.session.commit()
    return user

def get_user_by_email(email):
    """
    Get a user by email
    """
    return User.query.filter_by(email=email).first()

def get_user_by_id(user_id):
    """
    Get a user by ID
    """
    return User.query.get(user_id)

def create_prediction(user_id, label, confidence, class_id=None, metadata=None):
    """
    Create a new prediction
    """
    prediction = Prediction(
        user_id=user_id,
        label=label,
        confidence=confidence,
        class_id=class_id,
        metadata=metadata
    )
    db.session.add(prediction)
    db.session.commit()
    return prediction

def get_user_predictions(user_id, page=1, per_page=10):
    """
    Get predictions for a user with pagination
    """
    # Get total count for pagination
    total_count = Prediction.query.filter_by(user_id=user_id).count()
    
    # Calculate offset based on page and per_page
    offset = (page - 1) * per_page
    
    # Get predictions with manual pagination using limit and offset
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.timestamp.desc()).limit(per_page).offset(offset).all()
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
    
    return {
        "predictions": [p.to_dict() for p in predictions],
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": total_pages
        }
    }

def delete_prediction(prediction_id, user_id):
    """
    Delete a prediction
    """
    prediction = Prediction.query.filter_by(id=prediction_id, user_id=user_id).first()
    if prediction:
        db.session.delete(prediction)
        db.session.commit()
        return True
    return False
from flask import Blueprint, request, jsonify, current_app
from app.middleware.jwt_required import jwt_required, admin_required
from app.database.db_sql import get_db
from app.database.sql_models import User, Prediction
from sqlalchemy import func, desc, extract
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required
@admin_required
def admin_dashboard(current_user):
    """Get admin dashboard statistics"""
    db = get_db()
    
    # Get statistics using SQLAlchemy
    total_users = User.query.count()
    total_predictions = Prediction.query.count()
    
    # Get recent users
    recent_users_query = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_users_list = [user.to_dict() for user in recent_users_query]
    
    # Get recent predictions
    recent_predictions_query = Prediction.query.order_by(Prediction.timestamp.desc()).limit(5).all()
    recent_predictions_list = [prediction.to_dict() for prediction in recent_predictions_query]
    
    # Get predictions by day for the past week
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    predictions_by_day = db.session.query(
        extract('year', Prediction.timestamp).label('year'),
        extract('month', Prediction.timestamp).label('month'),
        extract('day', Prediction.timestamp).label('day'),
        func.count(Prediction.id).label('count')
    ).filter(
        Prediction.timestamp >= one_week_ago
    ).group_by(
        'year', 'month', 'day'
    ).order_by(
        'year', 'month', 'day'
    ).all()
    
    predictions_chart_data = []
    for item in predictions_by_day:
        date_str = f"{int(item.year)}-{int(item.month):02d}-{int(item.day):02d}"
        predictions_chart_data.append({
            "date": date_str,
            "count": item.count
        })
    
    # Get most common predictions
    common_predictions_data = db.session.query(
        Prediction.label.label('_id'),
        func.count(Prediction.id).label('count')
    ).group_by(
        Prediction.label
    ).order_by(
        func.count(Prediction.id).desc()
    ).limit(10).all()
    
    common_predictions = [{"_id": item._id, "count": item.count} for item in common_predictions_data]
    
    return jsonify({
        "statistics": {
            "total_users": total_users,
            "total_predictions": total_predictions
        },
        "recent_users": recent_users_list,
        "recent_predictions": recent_predictions_list,
        "predictions_by_day": predictions_chart_data,
        "common_predictions": common_predictions
    }), 200

@admin_bp.route('/users', methods=['GET'])
@jwt_required
@admin_required
def get_users(current_user):
    """Get all users (paginated)"""
    db = get_db()
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Get total count for pagination
    total_count = User.query.count()
    
    # Get users with pagination using SQLAlchemy
    users = User.query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Convert to dict format
    user_list = [user.to_dict() for user in users]
    
    return jsonify({
        "users": user_list,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": (total_count + per_page - 1) // per_page
        }
    }), 200

@admin_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required
@admin_required
def get_user(current_user, user_id):
    """Get a specific user's details"""
    db = get_db()
    
    try:
        # Convert user_id to integer
        user_id_int = int(user_id)
        
        # Get user by ID
        user = User.query.get(user_id_int)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Convert user to dictionary
        user_data = user.to_dict()
        
        # Get user's prediction count
        prediction_count = Prediction.query.filter_by(user_id=user_id_int).count()
        user_data['prediction_count'] = prediction_count
        
        # Get user's recent predictions
        recent_predictions = Prediction.query.filter_by(user_id=user_id_int).order_by(Prediction.timestamp.desc()).limit(5).all()
        
        # Convert predictions to dictionary format
        prediction_list = [prediction.to_dict() for prediction in recent_predictions]
        user_data['recent_predictions'] = prediction_list
        
        return jsonify(user_data), 200
        
    except ValueError:
        logger.error(f"Invalid user ID format: {user_id}")
        return jsonify({"error": "Invalid user ID format"}), 400
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        return jsonify({"error": f"Error retrieving user: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@jwt_required
@admin_required
def update_user(current_user, user_id):
    """Update a user's details"""
    db = get_db()
    data = request.get_json()
    
    try:
        # Convert user_id to integer
        user_id_int = int(user_id)
        
        # Find user by ID
        user = User.query.get(user_id_int)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Fields that admins are allowed to update
        allowed_fields = ['name', 'email', 'role']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        # Update user fields
        for key, value in update_data.items():
            setattr(user, key, value)
        
        # Commit changes to database
        db.session.commit()
        
        # Return updated user
        return jsonify({
            "message": "User updated successfully",
            "user": user.to_dict()
        }), 200
        
    except ValueError:
        logger.error(f"Invalid user ID format: {user_id}")
        return jsonify({"error": "Invalid user ID format"}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user: {e}")
        return jsonify({"error": f"Error updating user: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@jwt_required
@admin_required
def delete_user(current_user, user_id):
    """Delete a user"""
    db = get_db()
    
    try:
        # Convert user_id to integer
        user_id_int = int(user_id)
        
        # Check if user exists
        user = User.query.get(user_id_int)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Delete user's predictions
        Prediction.query.filter_by(user_id=user_id_int).delete()
        
        # Delete user
        db.session.delete(user)
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            "message": "User and associated data deleted successfully"
        }), 200
        
    except ValueError:
        logger.error(f"Invalid user ID format: {user_id}")
        return jsonify({"error": "Invalid user ID format"}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {e}")
        return jsonify({"error": f"Error deleting user: {str(e)}"}), 500

@admin_bp.route('/export/users', methods=['GET'])
@jwt_required
@admin_required
def export_users(current_user):
    """Export all users to JSON"""
    # Get all users using SQLAlchemy
    users = User.query.all()
    
    # Convert user objects to dictionaries
    user_list = [user.to_dict() for user in users]
    
    return jsonify(user_list), 200

@admin_bp.route('/export/predictions', methods=['GET'])
@jwt_required
@admin_required
def export_predictions(current_user):
    """Export all predictions to JSON"""
    # Get all predictions using SQLAlchemy
    predictions = Prediction.query.all()
    
    # Convert prediction objects to dictionaries
    prediction_list = [prediction.to_dict() for prediction in predictions]
    
    return jsonify(prediction_list), 200

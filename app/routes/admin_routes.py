from flask import Blueprint, request, jsonify, current_app
from app.middleware.jwt_required import jwt_required, admin_required
from app.database.db import get_db
from firebase_admin import firestore
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
    
    try:
        # Get total users
        users_ref = db.collection('users')
        total_users = len(list(users_ref.get()))
        
        # Get total predictions
        predictions_ref = db.collection('predictions')
        total_predictions = len(list(predictions_ref.get()))
        
        # Get recent users
        recent_users_query = users_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(5)
        recent_users = list(recent_users_query.get())
        recent_users_list = []
        for user in recent_users:
            user_data = user.to_dict()
            user_data['id'] = user.id
            # Remove password for security
            if 'password' in user_data:
                del user_data['password']
            recent_users_list.append(user_data)
        
        # Get recent predictions
        recent_predictions_query = predictions_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5)
        recent_predictions = list(recent_predictions_query.get())
        recent_predictions_list = []
        for prediction in recent_predictions:
            prediction_data = prediction.to_dict()
            prediction_data['id'] = prediction.id
            recent_predictions_list.append(prediction_data)
        
        # Get predictions by day for the past week
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        
        # This is different in Firestore - we'll get all predictions for the past week
        # and then group them by date manually
        predictions_week_query = predictions_ref.where('timestamp', '>=', one_week_ago).get()
        
        # Group by day
        predictions_by_day = {}
        for prediction in predictions_week_query:
            prediction_data = prediction.to_dict()
            timestamp = prediction_data.get('timestamp')
            
            # Handle server timestamp
            if isinstance(timestamp, datetime):
                date_str = timestamp.strftime('%Y-%m-%d')
                predictions_by_day[date_str] = predictions_by_day.get(date_str, 0) + 1
            
        # Convert to chart data format
        predictions_chart_data = []
        for date_str, count in predictions_by_day.items():
            predictions_chart_data.append({
                "date": date_str,
                "count": count
            })
        
        # Sort by date
        predictions_chart_data.sort(key=lambda x: x["date"])
        
        # Get most common predictions
        all_predictions = list(predictions_ref.get())
        label_counts = {}
        
        for prediction in all_predictions:
            prediction_data = prediction.to_dict()
            label = prediction_data.get('label')
            if label:
                label_counts[label] = label_counts.get(label, 0) + 1
        
        # Convert to list and sort by count
        common_predictions = [{"_id": label, "count": count} for label, count in label_counts.items()]
        common_predictions.sort(key=lambda x: x["count"], reverse=True)
        
        # Limit to top 10
        common_predictions = common_predictions[:10]
        
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
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({"error": f"Error getting dashboard data: {str(e)}"}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required
@admin_required
def get_users(current_user):
    """Get all users (paginated)"""
    db = get_db()
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    try:
        # Get all users for count
        users_ref = db.collection('users')
        all_users = list(users_ref.get())
        total_count = len(all_users)
        
        # Sort by created_at descending
        users_query = users_ref.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Get paginated users - Firestore doesn't support offset directly
        # So we'll get all and manually paginate
        users = list(users_query.get())
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Get the page slice
        page_users = users[start_idx:end_idx] if start_idx < len(users) else []
        
        # Convert to dict format
        user_list = []
        for user in page_users:
            user_data = user.to_dict()
            user_data['id'] = user.id
            # Remove password for security
            if 'password' in user_data:
                del user_data['password']
            user_list.append(user_data)
        
        return jsonify({
            "users": user_list,
            "pagination": {
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "pages": (total_count + per_page - 1) // per_page if total_count > 0 else 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": f"Error getting users: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required
@admin_required
def get_user(current_user, user_id):
    """Get a specific user's details"""
    db = get_db()
    
    try:
        # Get user by ID
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
        
        # Convert user to dictionary
        user_data = user.to_dict()
        user_data['id'] = user.id
        
        # Remove password for security
        if 'password' in user_data:
            del user_data['password']
        
        # Get user's prediction count
        predictions_query = db.collection('predictions').where('user_id', '==', user_id).get()
        prediction_count = len(list(predictions_query))
        user_data['prediction_count'] = prediction_count
        
        # Get user's recent predictions
        recent_predictions_query = db.collection('predictions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5)
        recent_predictions = list(recent_predictions_query.get())
        
        # Convert predictions to dictionary format
        prediction_list = []
        for prediction in recent_predictions:
            prediction_data = prediction.to_dict()
            prediction_data['id'] = prediction.id
            prediction_list.append(prediction_data)
        
        user_data['recent_predictions'] = prediction_list
        
        return jsonify(user_data), 200
        
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        return jsonify({"error": f"Error retrieving user: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@jwt_required
@admin_required
def update_user(current_user, user_id):
    """Update a user's details"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in update user request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    db = get_db()
    
    try:
        # Find user by ID
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
        
        # Fields that admins are allowed to update
        allowed_fields = ['name', 'email', 'role']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        # Update user fields
        user_ref.update(update_data)
        
        # Get updated user
        updated_user = user_ref.get()
        updated_user_data = updated_user.to_dict()
        updated_user_data['id'] = updated_user.id
        
        # Remove password for security
        if 'password' in updated_user_data:
            del updated_user_data['password']
        
        # Return updated user
        return jsonify({
            "message": "User updated successfully",
            "user": updated_user_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({"error": f"Error updating user: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@jwt_required
@admin_required
def delete_user(current_user, user_id):
    """Delete a user"""
    db = get_db()
    
    try:
        # Check if user exists
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
        
        # Get user's predictions
        predictions_query = db.collection('predictions').where('user_id', '==', user_id).get()
        
        # Delete user's predictions
        for prediction in predictions_query:
            prediction.reference.delete()
        
        # Delete user
        user_ref.delete()
        
        return jsonify({
            "message": "User and associated data deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({"error": f"Error deleting user: {str(e)}"}), 500

@admin_bp.route('/export/users', methods=['GET'])
@jwt_required
@admin_required
def export_users(current_user):
    """Export all users to JSON"""
    db = get_db()
    
    try:
        # Get all users
        users_ref = db.collection('users')
        users = list(users_ref.get())
        
        # Convert user objects to dictionaries
        user_list = []
        for user in users:
            user_data = user.to_dict()
            user_data['id'] = user.id
            # Remove password for security
            if 'password' in user_data:
                del user_data['password']
            user_list.append(user_data)
        
        return jsonify(user_list), 200
    
    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        return jsonify({"error": f"Error exporting users: {str(e)}"}), 500

@admin_bp.route('/export/predictions', methods=['GET'])
@jwt_required
@admin_required
def export_predictions(current_user):
    """Export all predictions to JSON"""
    db = get_db()
    
    try:
        # Get all predictions
        predictions_ref = db.collection('predictions')
        predictions = list(predictions_ref.get())
        
        # Convert prediction objects to dictionaries
        prediction_list = []
        for prediction in predictions:
            prediction_data = prediction.to_dict()
            prediction_data['id'] = prediction.id
            prediction_list.append(prediction_data)
        
        return jsonify(prediction_list), 200
    
    except Exception as e:
        logger.error(f"Error exporting predictions: {e}")
        return jsonify({"error": f"Error exporting predictions: {str(e)}"}), 500

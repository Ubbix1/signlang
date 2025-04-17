from flask import Blueprint, request, jsonify, current_app
from app.middleware.jwt_required import jwt_required, admin_required
from app.database.db import get_db
from app.database.mongodb import get_db as get_mongodb_db, DESCENDING
from firebase_admin import firestore
import logging
from datetime import datetime, timedelta
import json
from firebase_admin import auth

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
        # Get user by ID from MongoDB
        user = db.users.find_one({'firebase_uid': user_id})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Convert ObjectId to string
        user['_id'] = str(user['_id'])
        
        # Remove password for security
        if 'password' in user:
            del user['password']
        
        # Get user's prediction count
        prediction_count = db.prediction_logs.count_documents({'user_id': user_id})
        user['prediction_count'] = prediction_count
        
        # Get user's recent predictions
        recent_predictions = list(db.prediction_logs.find({'user_id': user_id})
                                 .sort('timestamp', DESCENDING)
                                 .limit(5))
        
        # Convert ObjectId to string in predictions
        for prediction in recent_predictions:
            prediction['_id'] = str(prediction['_id'])
        
        user['recent_predictions'] = recent_predictions
        
        return jsonify(user), 200
        
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

@admin_bp.route('/users/<user_id>/status', methods=['PUT'])
@jwt_required
@admin_required
def update_user_status(current_user, user_id):
    """Update a user's status (active/suspended)"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Status field is required"}), 400
        
        # Validate status
        status = data['status']
        if status not in ['active', 'suspended']:
            return jsonify({"error": "Invalid status. Must be 'active' or 'suspended'"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in update user status request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    db = get_db()
    
    try:
        # Find user by ID
        user = db.users.find_one({'firebase_uid': user_id})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update user status
        db.users.update_one(
            {'firebase_uid': user_id},
            {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
        )
        
        action_text = "suspended" if status == 'suspended' else "activated"
        return jsonify({
            "message": f"User has been {action_text} successfully",
            "status": status
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        return jsonify({"error": f"Error updating user status: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>/reset-password', methods=['POST'])
@jwt_required
@admin_required
def reset_user_password(current_user, user_id):
    """Reset a user's password"""
    try:
        data = request.get_json()
        if not data or 'method' not in data:
            return jsonify({"error": "Method field is required"}), 400
        
        # Validate method
        method = data['method']
        if method not in ['email', 'manual']:
            return jsonify({"error": "Invalid method. Must be 'email' or 'manual'"}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON in reset password request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    
    db = get_db()
    
    try:
        # Find user by ID
        user = db.users.find_one({'firebase_uid': user_id})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get Firebase Auth client
        firebase_auth = current_app.firebase_auth
        
        if method == 'email':
            # Send password reset email
            try:
                firebase_auth.generate_password_reset_link(user_id)
                return jsonify({
                    "message": "Password reset email sent successfully",
                    "method": "email"
                }), 200
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}")
                return jsonify({"error": "Failed to send password reset email"}), 500
        else:  # manual reset
            # Check if new password is provided
            if 'new_password' not in data or not data['new_password']:
                return jsonify({"error": "New password is required for manual reset"}), 400
            
            # Update password in Firebase Auth
            try:
                firebase_auth.update_user(user_id, password=data['new_password'])
                
                # Log the password change
                db.users.update_one(
                    {'firebase_uid': user_id},
                    {'$set': {'password_reset_at': datetime.utcnow(), 'updated_at': datetime.utcnow()}}
                )
                
                return jsonify({
                    "message": "Password has been reset successfully",
                    "method": "manual"
                }), 200
            except Exception as e:
                logger.error(f"Error updating user password: {e}")
                return jsonify({"error": "Failed to reset password"}), 500
        
    except Exception as e:
        logger.error(f"Error resetting user password: {e}")
        return jsonify({"error": f"Error resetting user password: {str(e)}"}), 500

@admin_bp.route('/users/<user_id>/impersonate', methods=['POST'])
@jwt_required
@admin_required
def impersonate_user(current_user, user_id):
    """Generate a token to login as a specific user"""
    db = get_db()
    
    try:
        # Check if user exists
        user = None
        
        # Try to get from MongoDB first
        mongodb_db = get_mongodb_db()
        user = mongodb_db.users.find_one({'firebase_uid': user_id})
        
        # If not found in MongoDB, try Firebase
        if not user:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if not user_doc.exists:
                return jsonify({"error": "User not found"}), 404
            user = user_doc.to_dict()
            user['id'] = user_doc.id
        
        # Generate a special admin token with both user and admin info
        # Create custom token with claims
        custom_token = auth.create_custom_token(
            user_id, 
            {
                'admin_impersonation': True,
                'original_admin_id': current_user['user_id'],
                'expiration': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }
        )
        
        # Convert bytes to string if needed
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode('utf-8')
        
        return jsonify({
            "message": f"Successfully generated token to login as {user.get('name', 'user')}",
            "custom_token": custom_token,
            "user": {
                "id": user_id,
                "name": user.get('name', ''),
                "email": user.get('email', ''),
                "role": user.get('role', 'user')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error impersonating user: {e}")
        return jsonify({"error": f"Error impersonating user: {str(e)}"}), 500

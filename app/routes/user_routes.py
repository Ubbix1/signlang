from flask import Blueprint, request, jsonify, current_app
from app.middleware.jwt_required import jwt_required
from app.database.db import get_db
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)
user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required
def get_profile(current_user):
    """Get the current user's profile"""
    db = get_db()
    
    user_id = current_user['user_id']
    
    # Find user by ID
    user = db.users.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Convert ObjectId to string for JSON serialization
    user['_id'] = str(user['_id'])
    
    return jsonify(user), 200

@user_bp.route('/profile', methods=['PUT'])
@jwt_required
def update_profile(current_user):
    """Update the current user's profile"""
    db = get_db()
    data = request.get_json()
    
    user_id = current_user['user_id']
    
    # Fields that users are allowed to update
    allowed_fields = ['name', 'email']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400
    
    # Update user in database
    result = db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        return jsonify({"error": "Failed to update profile or no changes made"}), 400
    
    # Get updated user
    updated_user = db.users.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    updated_user['_id'] = str(updated_user['_id'])
    
    return jsonify({
        "message": "Profile updated successfully",
        "user": updated_user
    }), 200

@user_bp.route('/history', methods=['GET'])
@jwt_required
def get_history(current_user):
    """Get the current user's prediction history"""
    db = get_db()
    user_id = current_user['user_id']
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Calculate skip value for pagination
    skip = (page - 1) * per_page
    
    # Get total count for pagination
    total_count = db.predictions.count_documents({"user_id": user_id})
    
    # Get predictions for the user with pagination
    predictions = db.predictions.find(
        {"user_id": user_id}
    ).sort("timestamp", -1).skip(skip).limit(per_page)
    
    # Convert cursor to list and format results
    prediction_list = []
    for prediction in predictions:
        prediction['_id'] = str(prediction['_id'])
        prediction_list.append(prediction)
    
    return jsonify({
        "predictions": prediction_list,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "pages": (total_count + per_page - 1) // per_page
        }
    }), 200

@user_bp.route('/history/<prediction_id>', methods=['GET'])
@jwt_required
def get_prediction_detail(current_user, prediction_id):
    """Get details of a specific prediction"""
    db = get_db()
    user_id = current_user['user_id']
    
    try:
        # Convert prediction_id to ObjectId
        prediction = db.predictions.find_one({
            "_id": ObjectId(prediction_id),
            "user_id": user_id
        })
    except Exception as e:
        logger.error(f"Invalid prediction ID: {e}")
        return jsonify({"error": "Invalid prediction ID"}), 400
    
    if not prediction:
        return jsonify({"error": "Prediction not found or access denied"}), 404
    
    # Convert ObjectId to string
    prediction['_id'] = str(prediction['_id'])
    
    return jsonify(prediction), 200

@user_bp.route('/history/<prediction_id>', methods=['DELETE'])
@jwt_required
def delete_prediction(current_user, prediction_id):
    """Delete a specific prediction"""
    db = get_db()
    user_id = current_user['user_id']
    
    try:
        # Delete prediction
        result = db.predictions.delete_one({
            "_id": ObjectId(prediction_id),
            "user_id": user_id
        })
    except Exception as e:
        logger.error(f"Invalid prediction ID: {e}")
        return jsonify({"error": "Invalid prediction ID"}), 400
    
    if result.deleted_count == 0:
        return jsonify({"error": "Prediction not found or access denied"}), 404
    
    return jsonify({
        "message": "Prediction deleted successfully"
    }), 200

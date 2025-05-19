from flask import current_app, request, jsonify, Blueprint
import logging

logger = logging.getLogger(__name__)

# Check if necessary for your file structure, adjust as needed
# bp = Blueprint('api', __name__)

@bp.route('/hf/load', methods=['POST'])
def load_huggingface_dataset():
    """Endpoint to load the HuggingFace dataset"""
    try:
        # Check if manager exists
        if not current_app.hf_dataset_manager:
            return jsonify({
                'success': False,
                'error': 'HuggingFace dataset manager not initialized'
            }), 500
        
        # Get dataset name from request if provided
        data = request.get_json() or {}
        dataset_name = data.get('dataset_name')
        
        if dataset_name:
            current_app.hf_dataset_manager.dataset_name = dataset_name
        
        # Load the dataset
        success = current_app.hf_dataset_manager.load_dataset()
        
        if success:
            class_names = current_app.hf_dataset_manager.get_class_names() or []
            return jsonify({
                'success': True,
                'dataset': current_app.hf_dataset_manager.dataset_name,
                'classes': class_names,
                'size': len(current_app.hf_dataset_manager.dataset['train']) if current_app.hf_dataset_manager.dataset else 0
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to load dataset'
            }), 500
            
    except Exception as e:
        logger.error(f"Error loading HuggingFace dataset: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/hf/info', methods=['GET'])
def get_huggingface_info():
    """Get information about the loaded HuggingFace dataset"""
    try:
        # Check if manager exists
        if not current_app.hf_dataset_manager:
            return jsonify({
                'loaded': False,
                'error': 'HuggingFace dataset manager not initialized'
            })
        
        # Check if dataset is loaded
        if not current_app.hf_dataset_manager.dataset:
            return jsonify({
                'loaded': False,
                'dataset_name': current_app.hf_dataset_manager.dataset_name
            })
        
        # Get dataset info
        class_names = current_app.hf_dataset_manager.get_class_names() or []
        
        return jsonify({
            'loaded': True,
            'dataset_name': current_app.hf_dataset_manager.dataset_name,
            'classes': class_names,
            'train_size': len(current_app.hf_dataset_manager.dataset['train']) if 'train' in current_app.hf_dataset_manager.dataset else 0,
            'test_size': len(current_app.hf_dataset_manager.dataset['test']) if 'test' in current_app.hf_dataset_manager.dataset else 0
        })
        
    except Exception as e:
        logger.error(f"Error getting HuggingFace dataset info: {e}")
        return jsonify({
            'loaded': False,
            'error': str(e)
        })

@bp.route('/process/with_landmarks', methods=['POST'])
def process_with_landmarks():
    """Process an image and return the prediction with visualized landmarks"""
    from app.inference.predict import predict_from_base64
    from app.inference.utils import draw_landmarks, create_debug_frame
    import base64
    import cv2
    import numpy as np
    
    try:
        # Get image data from request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Process the image
        image_data = data['image']
        prediction, status_code = predict_from_base64(image_data)
        
        # If there was an error, return it
        if status_code != 200 or 'error' in prediction:
            return jsonify(prediction), status_code
        
        # Decode the image to get the frame
        try:
            # Extract just the base64 data
            if ',' in image_data:
                image_data = image_data.split(',')[1]
                
            # Decode to image
            img_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Get landmarks
            # This assumes that during prediction, landmarks were stored somewhere
            # If not, you may need to extract them again
            landmarks = []
            if hasattr(current_app, 'last_landmarks') and current_app.last_landmarks is not None:
                landmarks = current_app.last_landmarks
            
            # Create debug frame with landmarks and prediction
            debug_frame = create_debug_frame(frame, landmarks, prediction)
            
            # Convert back to base64
            _, buffer = cv2.imencode('.jpg', debug_frame)
            debug_image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Add the debug image to the response
            prediction['debug_image'] = f"data:image/jpeg;base64,{debug_image_base64}"
            
            return jsonify(prediction)
            
        except Exception as e:
            logger.error(f"Error creating debug image: {e}")
            # Still return the prediction even if visualization failed
            return jsonify(prediction)
            
    except Exception as e:
        logger.error(f"Error in process_with_landmarks: {e}")
        return jsonify({'error': str(e)}), 500 
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

def preprocess_frame(frame):
    """
    Preprocess a video frame for hand landmark detection
    
    Args:
        frame: OpenCV image frame
        
    Returns:
        processed_frame: Preprocessed frame ready for MediaPipe
    """
    # Convert BGR to RGB (MediaPipe uses RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Resize to a standard size if needed
    # This may improve consistency across different video sources
    # rgb_frame = cv2.resize(rgb_frame, (640, 480))
    
    return rgb_frame

def extract_hand_landmarks(frame, hands):
    """
    Extract hand landmarks from a frame using MediaPipe
    
    Args:
        frame: Preprocessed RGB frame
        hands: MediaPipe hands solution object
        
    Returns:
        landmarks: List of hand landmark coordinates [x,y] for each hand
    """
    try:
        # Get hand landmarks using MediaPipe
        results = hands.process(frame)
        
        # Check if any hands were detected
        if not results.multi_hand_landmarks:
            return []
        
        all_landmarks = []
        
        # Process each detected hand (up to 2)
        for hand_landmarks in results.multi_hand_landmarks[:2]:
            # Extract landmarks
            landmarks = []
            for landmark in hand_landmarks.landmark:
                # Normalize coordinates to [0,1] range
                landmarks.append([landmark.x, landmark.y])
            
            all_landmarks.extend(landmarks)
        
        return all_landmarks
        
    except Exception as e:
        logger.error(f"Error extracting hand landmarks: {e}")
        return []

def normalize_landmarks(landmarks, frame_width, frame_height):
    """
    Normalize landmark coordinates relative to frame size
    
    Args:
        landmarks: List of hand landmark coordinates
        frame_width: Width of the frame
        frame_height: Height of the frame
        
    Returns:
        normalized_landmarks: List of normalized coordinates
    """
    normalized = []
    for landmark in landmarks:
        # Normalize x,y coordinates to [0,1] range
        norm_x = landmark[0] / frame_width
        norm_y = landmark[1] / frame_height
        normalized.append([norm_x, norm_y])
    
    return normalized

def draw_landmarks(frame, landmarks):
    """
    Draw hand landmarks on a frame for visualization
    
    Args:
        frame: OpenCV image frame
        landmarks: List of hand landmark coordinates
        
    Returns:
        annotated_frame: Frame with landmarks drawn
    """
    # Create a copy of the frame
    annotated_frame = frame.copy()
    
    # Get frame dimensions
    height, width = annotated_frame.shape[:2]
    
    # Draw each landmark
    for i, landmark in enumerate(landmarks):
        # Convert normalized coordinates to pixel coordinates
        x = int(landmark[0] * width)
        y = int(landmark[1] * height)
        
        # Draw circle at landmark position
        cv2.circle(annotated_frame, (x, y), 5, (0, 255, 0), -1)
        
        # Draw landmark index
        cv2.putText(annotated_frame, str(i), (x, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    return annotated_frame

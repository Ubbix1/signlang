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
        # Check if hands is a valid MediaPipe hands instance
        if isinstance(hands, str):
            logger.warning(f"Invalid hands object: {hands}")
            return []
            
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

# Hand landmark connections for visualization
# Based on MediaPipe hand landmark model
# https://google.github.io/mediapipe/solutions/hands.html
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring finger
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm
    (5, 9), (9, 13), (13, 17)
]

def draw_landmarks(frame, landmarks, draw_connections=True, draw_indices=True, 
                   point_color=(0, 255, 0), connection_color=(255, 0, 0), 
                   text_color=(255, 255, 255)):
    """
    Draw hand landmarks on a frame for visualization with enhanced visualization
    
    Args:
        frame: OpenCV image frame
        landmarks: List of hand landmark coordinates
        draw_connections: Whether to draw connections between landmarks
        draw_indices: Whether to draw landmark indices
        point_color: Color for landmark points (BGR)
        connection_color: Color for connections (BGR)
        text_color: Color for index text (BGR)
        
    Returns:
        annotated_frame: Frame with landmarks drawn
    """
    # Create a copy of the frame
    annotated_frame = frame.copy()
    
    # Get frame dimensions
    height, width = annotated_frame.shape[:2]
    
    # If no landmarks, return original frame
    if not landmarks or len(landmarks) == 0:
        return annotated_frame
    
    # Determine if we have one or two hands
    hand_count = 1
    if len(landmarks) > 21:
        hand_count = 2
    
    # Process each hand
    for hand_idx in range(hand_count):
        # Get offset for current hand
        offset = hand_idx * 21
        
        # Process hand landmarks
        hand_landmarks = landmarks[offset:offset+21]
        
        # Draw connections first so they appear behind points
        if draw_connections:
            for connection in HAND_CONNECTIONS:
                start_idx = connection[0]
                end_idx = connection[1]
                
                if start_idx < len(hand_landmarks) and end_idx < len(hand_landmarks):
                    # Get pixel coordinates
                    start_x = int(hand_landmarks[start_idx][0] * width)
                    start_y = int(hand_landmarks[start_idx][1] * height)
                    end_x = int(hand_landmarks[end_idx][0] * width)
                    end_y = int(hand_landmarks[end_idx][1] * height)
                    
                    # Draw line
                    cv2.line(annotated_frame, (start_x, start_y), 
                             (end_x, end_y), connection_color, 2)
        
        # Draw landmarks
        for i, landmark in enumerate(hand_landmarks):
            # Convert normalized coordinates to pixel coordinates
            x = int(landmark[0] * width)
            y = int(landmark[1] * height)
            
            # Draw circle at landmark position
            # Use different colors for different finger groups
            if i == 0:  # Wrist
                color = (255, 0, 0)
            elif 1 <= i <= 4:  # Thumb
                color = (255, 100, 0)
            elif 5 <= i <= 8:  # Index finger
                color = (255, 255, 0)
            elif 9 <= i <= 12:  # Middle finger
                color = (0, 255, 0)
            elif 13 <= i <= 16:  # Ring finger
                color = (0, 255, 255)
            elif 17 <= i <= 20:  # Pinky
                color = (255, 0, 255)
            else:
                color = point_color
                
            # Draw circle with dynamic size based on the frame dimensions
            radius = max(3, int(min(width, height) / 150))
            cv2.circle(annotated_frame, (x, y), radius, color, -1)
            
            # Optionally draw landmark index
            if draw_indices:
                # Choose text size based on frame dimensions
                text_scale = max(0.3, min(width, height) / 1000)
                cv2.putText(annotated_frame, str(i + offset), (x + 5, y - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_color, 
                            max(1, int(text_scale * 2)))
    
    return annotated_frame

def create_debug_frame(frame, landmarks, prediction=None):
    """
    Create a debug frame with landmarks and prediction information
    
    Args:
        frame: Original frame
        landmarks: Hand landmarks
        prediction: Prediction result or None
        
    Returns:
        debug_frame: Frame with debug information
    """
    # Draw landmarks
    debug_frame = draw_landmarks(frame, landmarks)
    
    # If we have prediction data, add it to the frame
    if prediction:
        height, width = debug_frame.shape[:2]
        
        # Add prediction text
        label = prediction.get('label', 'Unknown')
        confidence = prediction.get('confidence', 0)
        
        # Create text with prediction info
        text = f"{label}: {confidence:.1f}%"
        
        # Add background for better readability
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        cv2.rectangle(debug_frame, 
                      (10, 10), 
                      (text_size[0] + 20, text_size[1] + 20), 
                      (0, 0, 0), -1)
        
        # Add text
        cv2.putText(debug_frame, text, (15, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return debug_frame

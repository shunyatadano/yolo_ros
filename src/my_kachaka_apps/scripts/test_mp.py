#!/usr/bin/env python3
"""
RealSense D435 Face Detection and Tracking with MediaPipe
This script uses MediaPipe for face detection on RealSense camera feed
"""

import cv2
import mediapipe as mp
import numpy as np

mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

def get_face_depth_robust(depth_frame, bbox, w, h):
    """
    Get robust depth measurement from face region using multiple sampling points.
    
    Args:
        depth_frame: RealSense depth frame
        bbox: MediaPipe relative bounding box
        w, h: Image width and height
        
    Returns:
        float: Median depth value in meters, or None if no valid readings
    """
    x = int(bbox.xmin * w)
    y = int(bbox.ymin * h)
    width = int(bbox.width * w)
    height = int(bbox.height * h)
    
    # Ensure bounding box is within image bounds
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    width = min(width, w - x)
    height = min(height, h - y)
    
    # Sample multiple points in face region - concentrated around center for better reliability
    depths = []
    # Use smaller offsets closer to center to avoid background
    # Sample pattern: center + 8 surrounding points in a tight grid
    center_x = x + width // 2
    center_y = y + height // 2
    
    # Define sampling offsets relative to face size (smaller than 1/4 to stay within face)
    offset_ratios = [-0.15, 0.0, 0.15]  # 15% of face size from center
    
    for dx_ratio in offset_ratios:
        for dy_ratio in offset_ratios:
            # Calculate absolute pixel positions
            px = int(center_x + dx_ratio * width)
            py = int(center_y + dy_ratio * height)
            
            # Ensure we're within image and bounding box bounds
            if (x <= px < x + width and 
                y <= py < y + height and 
                0 <= px < w and 0 <= py < h):
                depth = depth_frame.get_distance(px, py)
                # Filter out invalid depth readings
                if 0.1 < depth < 10.0:  # Valid depth range (10cm to 10m)
                    depths.append(depth)
    
    if depths:
        # Use median to reduce noise from outliers
        median_depth = np.median(depths)
        return median_depth
    else:
        return None

print("RealSense D435 Face Detection and Tracking Starting...")
print("Make sure RealSense camera is connected and drivers are installed")
print("Press 'q' or ESC to quit")

# Try to use RealSense SDK if available, otherwise fallback to OpenCV
try:
    import pyrealsense2 as rs
    USE_REALSENSE_SDK = True
    print("Using RealSense SDK")
except ImportError:
    USE_REALSENSE_SDK = False
    print("RealSense SDK not found, using OpenCV (may not get depth info)")

if USE_REALSENSE_SDK:
    # RealSense pipeline configuration
    pipeline = rs.pipeline()
    config = rs.config()
    
    # Configure streams
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    
    # Start streaming
    try:
        pipeline.start(config)
        
        # Create alignment object to align depth to color
        align_to = rs.stream.color
        align = rs.align(align_to)
        print("RealSense pipeline started successfully with depth-color alignment")
        
    except Exception as e:
        print(f"Failed to start RealSense pipeline: {e}")
        print("Falling back to OpenCV")
        USE_REALSENSE_SDK = False

if not USE_REALSENSE_SDK:
    # Fallback to OpenCV VideoCapture
    cap = cv2.VideoCapture(0)  # Try default camera first
    if not cap.isOpened():
        # Try other camera indices commonly used by RealSense
        for i in range(1, 5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"Using camera index {i}")
                break
        else:
            print("No camera found")
            exit(1)

try:
    with mp_face_detection.FaceDetection(
        min_detection_confidence=0.5) as face_detection:
        
        while True:
            if USE_REALSENSE_SDK:
                # RealSense SDK method with alignment
                frames = pipeline.wait_for_frames()
                
                # Align depth frame to color frame
                aligned_frames = align.process(frames)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                
                if not aligned_depth_frame or not color_frame:
                    continue
                
                depth_image = np.asanyarray(aligned_depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                
                # Use aligned depth frame for depth measurements
                depth_frame = aligned_depth_frame
                
            else:
                # OpenCV method
                ret, color_image = cap.read()
                if not ret:
                    print("Failed to read frame")
                    continue
                depth_image = None

            # Convert BGR to RGB for MediaPipe
            rgb_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            rgb_image.flags.writeable = False
            results = face_detection.process(rgb_image)

            # Draw face detection annotations
            rgb_image.flags.writeable = True
            color_image_annotated = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            
            if results.detections:
                for detection in results.detections:
                    mp_drawing.draw_detection(color_image_annotated, detection)
                    
                    if USE_REALSENSE_SDK and depth_frame:
                        # Get bounding box for depth analysis
                        bbox = detection.location_data.relative_bounding_box
                        h, w = color_image.shape[:2]
                        x = int(bbox.xmin * w)
                        y = int(bbox.ymin * h)
                        width = int(bbox.width * w)
                        height = int(bbox.height * h)
                        
                        # Get robust depth measurement using multiple sampling points
                        depth_value = get_face_depth_robust(depth_frame, bbox, w, h)
                        
                        if depth_value is not None:
                            # Display depth with enhanced information
                            cv2.putText(color_image_annotated, f"Depth: {depth_value:.2f}m", 
                                      (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            # Add distance category for better understanding
                            if depth_value < 0.5:
                                distance_category = "Very Close"
                                color = (0, 0, 255)  # Red
                            elif depth_value < 1.0:
                                distance_category = "Close"
                                color = (0, 165, 255)  # Orange
                            elif depth_value < 2.0:
                                distance_category = "Near"
                                color = (0, 255, 255)  # Yellow
                            else:
                                distance_category = "Far"
                                color = (0, 255, 0)  # Green
                            
                            cv2.putText(color_image_annotated, f"({distance_category})", 
                                      (x, y + height + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        else:
                            # No valid depth reading
                            cv2.putText(color_image_annotated, "Depth: N/A", 
                                      (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            if USE_REALSENSE_SDK and depth_image is not None:
                # Create depth colormap and stack images
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
                images = np.hstack((color_image_annotated, depth_colormap))
                window_name = 'RealSense Face Detection (Color + Depth)'
            else:
                images = color_image_annotated
                window_name = 'Face Detection'

            # Show images
            cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
            cv2.imshow(window_name, images)
            
            if cv2.waitKey(1) & 0xFF == ord('q') or cv2.waitKey(1) & 0xFF == 27:
                break

finally:
    # Cleanup
    if USE_REALSENSE_SDK:
        pipeline.stop()
    else:
        cap.release()
    cv2.destroyAllWindows()
    print("Cleanup completed")
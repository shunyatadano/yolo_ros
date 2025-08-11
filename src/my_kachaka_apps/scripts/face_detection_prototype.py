#!/usr/bin/env python3
"""
Face Detection Prototype using MediaPipe BlazeFace Full-Range Model with RealSense D435i
This script demonstrates face detection with model_selection=1 and depth information
"""

import cv2
import mediapipe as mp
import numpy as np

mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

print("Face Detection Prototype Starting...")
print("Using BlazeFace full-range model (model_selection=1)")
print("RealSense D435i Camera")
print("Press 'q' or ESC to quit")

# Initialize RealSense
try:
    import pyrealsense2 as rs
    USE_REALSENSE = True
    print("RealSense SDK found")
except ImportError:
    print("ERROR: RealSense SDK not found. Please install pyrealsense2")
    exit(1)

# Configure RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()

# Enable streams with higher resolution
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30) # 640, 480 / 1280, 720
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
try:
    pipeline.start(config)
    print("RealSense D435i pipeline started successfully")
except Exception as e:
    print(f"Failed to start RealSense pipeline: {e}")
    print("Make sure RealSense D435i is connected")
    exit(1)

try:
    with mp_face_detection.FaceDetection(
        model_selection=1,  # Use full-range model for better detection
        min_detection_confidence=0.5) as face_detection:
        
        frame_count = 0
        
        while True:
            # Get frameset from RealSense
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                continue
            
            frame_count += 1
            
            # Convert images to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            # Convert BGR to RGB for MediaPipe
            rgb_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            rgb_image.flags.writeable = False
            
            # Perform face detection
            results = face_detection.process(rgb_image)
            
            # Convert back to BGR for display
            rgb_image.flags.writeable = True
            annotated_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            
            # Draw detections
            detection_count = 0
            if results.detections:
                detection_count = len(results.detections)
                for detection in results.detections:
                    mp_drawing.draw_detection(annotated_image, detection)
                    
                    # Get detection confidence
                    confidence = detection.score[0]
                    
                    # Get bounding box coordinates
                    bbox = detection.location_data.relative_bounding_box
                    h, w = annotated_image.shape[:2]
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    # Calculate center point for depth reading
                    center_x = x + width // 2
                    center_y = y + height // 2
                    
                    # Get depth value at face center
                    if 0 <= center_x < w and 0 <= center_y < h:
                        depth_value = depth_frame.get_distance(center_x, center_y)
                        cv2.putText(annotated_image, f"Conf: {confidence:.2f} | Depth: {depth_value:.2f}m", 
                                  (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        cv2.putText(annotated_image, f"Conf: {confidence:.2f}", 
                                  (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Create depth colormap
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            
            # Stack images horizontally
            images = np.hstack((annotated_image, depth_colormap))
            
            # Display info
            cv2.putText(images, f"Frame: {frame_count} | Faces: {detection_count}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(images, "Model: BlazeFace Full-Range (model_selection=1) | RealSense D435i", 
                      (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(images, "Color + Depth View", 
                      (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame with resizable window
            cv2.namedWindow('RealSense D435i Face Detection', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('RealSense D435i Face Detection', 1600, 800)
            cv2.imshow('RealSense D435i Face Detection', images)
            
            # Exit on 'q' or ESC
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print("RealSense D435i face detection prototype finished")
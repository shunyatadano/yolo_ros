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
        print("RealSense pipeline started successfully")
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
                # RealSense SDK method
                frames = pipeline.wait_for_frames()
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                if not depth_frame or not color_frame:
                    continue
                
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                
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
                        
                        # Calculate center point for depth reading
                        center_x = x + width // 2
                        center_y = y + height // 2
                        
                        # Get depth value at face center
                        if 0 <= center_x < w and 0 <= center_y < h:
                            depth_value = depth_frame.get_distance(center_x, center_y)
                            cv2.putText(color_image_annotated, f"Depth: {depth_value:.2f}m", 
                                      (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

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
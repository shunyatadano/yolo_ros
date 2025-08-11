#!/usr/bin/env python3
"""
Face Detection Comparison Script using same model as face_tracker_node.py
This script uses default MediaPipe settings (model_selection=0) for performance comparison
"""

import cv2
import mediapipe as mp
import numpy as np
import time

mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

print("Face Detection Comparison Script Starting...")
print("Using default BlazeFace model (model_selection=0, same as face_tracker_node.py)")
print("RealSense D435i Camera")
print("Press 'q' or ESC to quit")

# Initialize RealSense
try:
    import pyrealsense2 as rs
    print("RealSense SDK found")
except ImportError:
    print("ERROR: RealSense SDK not found. Please install pyrealsense2")
    exit(1)

# Configure RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()

# Enable streams (same resolution as face_tracker_node.py)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
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
    # Initialize face detection with same settings as face_tracker_node.py
    with mp_face_detection.FaceDetection(
        min_detection_confidence=0.5) as face_detection:  # No model_selection specified = default (0)
        
        frame_count = 0
        fps_counter = 0
        fps_start_time = time.time()
        current_fps = 0.0
        
        while True:
            # Get frameset from RealSense
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                continue
            
            frame_count += 1
            fps_counter += 1
            
            # Convert images to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            # Convert BGR to RGB for MediaPipe (same as face_tracker_node.py)
            rgb_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            rgb_image.flags.writeable = False
            
            # Perform face detection
            results = face_detection.process(rgb_image)
            
            # Convert back to BGR for display
            rgb_image.flags.writeable = True
            annotated_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            
            # Draw detections and find largest face (same logic as face_tracker_node.py)
            detection_count = 0
            largest_detection = None
            largest_area = 0
            
            if results.detections:
                detection_count = len(results.detections)
                
                for detection in results.detections:
                    # Draw detection
                    mp_drawing.draw_detection(annotated_image, detection)
                    
                    # Calculate bounding box area to find largest face (same as face_tracker_node.py)
                    bbox = detection.location_data.relative_bounding_box
                    area = bbox.width * bbox.height
                    
                    if area > largest_area:
                        largest_area = area
                        largest_detection = detection
                
                if largest_detection:
                    # Calculate face center from the largest detection
                    bbox = largest_detection.location_data.relative_bounding_box
                    h, w = color_image.shape[:2]
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    face_center_x = x + width // 2
                    face_center_y = y + height // 2
                    
                    # Get depth value at face center (same logic as face_tracker_node.py)
                    if 0 <= face_center_x < w and 0 <= face_center_y < h:
                        # Extract 5x5 region around face center for distance calculation
                        if face_center_x >= 2 and face_center_y >= 2 and face_center_x < w-2 and face_center_y < h-2:
                            region = depth_image[face_center_y-2:face_center_y+3, face_center_x-2:face_center_x+3]
                            
                            # Remove invalid values and calculate median (same as face_tracker_node.py)
                            valid_depths = []
                            for row in region:
                                for pixel_depth in row:
                                    if pixel_depth > 0 and not np.isnan(pixel_depth) and pixel_depth < 10000:
                                        valid_depths.append(pixel_depth)
                            
                            if len(valid_depths) >= 3:
                                median_depth = np.median(valid_depths)
                                # Convert mm to meters (assuming uint16 format)
                                distance_meters = median_depth / 1000.0 if depth_image.dtype == np.uint16 else float(median_depth)
                                
                                # Get detection confidence
                                confidence = largest_detection.score[0]
                                cv2.putText(annotated_image, f"Conf: {confidence:.2f} | Dist: {distance_meters:.2f}m", 
                                          (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            else:
                                confidence = largest_detection.score[0]
                                cv2.putText(annotated_image, f"Conf: {confidence:.2f} | Dist: invalid", 
                                          (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Calculate FPS
            current_time = time.time()
            if current_time - fps_start_time >= 1.0:
                current_fps = fps_counter / (current_time - fps_start_time)
                fps_counter = 0
                fps_start_time = current_time
            
            # Create depth colormap
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            
            # Stack images horizontally
            images = np.hstack((annotated_image, depth_colormap))
            
            # Display info
            cv2.putText(images, f"Frame: {frame_count} | Faces: {detection_count} | FPS: {current_fps:.1f}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(images, "Model: BlazeFace Default (model_selection=0) | Same as face_tracker_node.py", 
                      (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(images, "Color + Depth View | Performance Comparison", 
                      (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            cv2.namedWindow('RealSense D435i Face Detection Comparison', cv2.WINDOW_AUTOSIZE)
            cv2.imshow('RealSense D435i Face Detection Comparison', images)
            
            # Exit on 'q' or ESC
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print("RealSense D435i face detection comparison finished")
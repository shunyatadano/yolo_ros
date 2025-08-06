#!/usr/bin/env python3
"""
RealSense D435 Face Detection and Tracking with MediaPipe using ROS2
This script subscribes to RealSense camera topics and performs face detection
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import mediapipe as mp
import numpy as np

class FaceDetectionNode(Node):
    def __init__(self):
        super().__init__('face_detection_node')
        
        # MediaPipe setup
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)
        
        # ROS2 setup
        self.bridge = CvBridge()
        
        # Subscribe to RealSense topics
        self.color_subscription = self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.color_callback,
            10)
        
        self.depth_subscription = self.create_subscription(
            Image,
            '/camera/camera/depth/image_rect_raw',
            self.depth_callback,
            10)
        
        # Store latest images
        self.latest_color_image = None
        self.latest_depth_image = None
        
        # Create timer for processing
        self.timer = self.create_timer(0.033, self.process_images)  # ~30 FPS
        
        self.get_logger().info('Face Detection Node started. Subscribing to RealSense topics...')
        print("Face Detection Node started")
        print("Press 'q' or ESC in the OpenCV window to quit")

    def color_callback(self, msg):
        try:
            self.latest_color_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Error converting color image: {e}')

    def depth_callback(self, msg):
        try:
            self.latest_depth_image = self.bridge.imgmsg_to_cv2(msg, "passthrough")
        except Exception as e:
            self.get_logger().error(f'Error converting depth image: {e}')

    def process_images(self):
        if self.latest_color_image is None:
            return
        
        # Convert BGR to RGB for MediaPipe
        rgb_image = cv2.cvtColor(self.latest_color_image, cv2.COLOR_BGR2RGB)
        rgb_image.flags.writeable = False
        results = self.face_detection.process(rgb_image)

        # Draw face detection annotations
        rgb_image.flags.writeable = True
        color_image_annotated = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        
        if results.detections:
            for detection in results.detections:
                self.mp_drawing.draw_detection(color_image_annotated, detection)
                
                # Add depth information if available
                if self.latest_depth_image is not None:
                    bbox = detection.location_data.relative_bounding_box
                    h, w = self.latest_color_image.shape[:2]
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    # Calculate center point for depth reading
                    center_x = x + width // 2
                    center_y = y + height // 2
                    
                    # Get depth value at face center
                    if (0 <= center_x < self.latest_depth_image.shape[1] and 
                        0 <= center_y < self.latest_depth_image.shape[0]):
                        depth_value = self.latest_depth_image[center_y, center_x]
                        # Convert from mm to meters
                        depth_meters = depth_value / 1000.0
                        cv2.putText(color_image_annotated, f"Depth: {depth_meters:.2f}m", 
                                  (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display the result
        if self.latest_depth_image is not None:
            # Create depth colormap and stack images
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(self.latest_depth_image, alpha=0.03), 
                cv2.COLORMAP_JET)
            images = np.hstack((color_image_annotated, depth_colormap))
            window_name = 'RealSense Face Detection (Color + Depth)'
        else:
            images = color_image_annotated
            window_name = 'RealSense Face Detection'

        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        cv2.imshow(window_name, images)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # 'q' or ESC
            self.get_logger().info('Shutting down...')
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = FaceDetectionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\nShutdown requested by user')
    finally:
        cv2.destroyAllWindows()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
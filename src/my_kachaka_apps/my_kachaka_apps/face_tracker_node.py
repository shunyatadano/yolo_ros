#!/usr/bin/env python3

import os
# Set Qt platform to avoid wayland issues
os.environ['QT_QPA_PLATFORM'] = 'xcb'

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist

# Handle OpenCV and cv_bridge import with better error handling
try:
    import cv2
    import numpy as np
    # Set NumPy compatibility for cv_bridge
    np._no_nep50_warning = True
    from cv_bridge import CvBridge
    OPENCV_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OpenCV or cv_bridge not available: {e}")
    OPENCV_AVAILABLE = False
except AttributeError as e:
    print(f"Warning: NumPy compatibility issue with cv_bridge: {e}")
    print("Trying fallback import...")
    try:
        import cv2
        import numpy as np
        # Try downgrading NumPy API compatibility
        os.environ['NPY_DISABLE_SVML'] = '1'
        from cv_bridge import CvBridge
        OPENCV_AVAILABLE = True
    except Exception as e2:
        print(f"Fallback import failed: {e2}")
        OPENCV_AVAILABLE = False


class FaceTrackerNode(Node):
    def __init__(self):
        super().__init__('face_tracker_node')
        
        # Check if OpenCV is available
        if not OPENCV_AVAILABLE:
            self.get_logger().error('OpenCV or cv_bridge is not available. Please install python3-opencv and cv_bridge.')
            return
        
        # Parameters with descriptions for Task 2-B tuning
        turn_gain_desc = ParameterDescriptor(description='P-control gain for angular velocity (rad/s per pixel)')
        dead_zone_desc = ParameterDescriptor(description='Dead zone percentage to prevent oscillation')
        
        self.declare_parameter('turn_gain', 0.003, turn_gain_desc)
        self.declare_parameter('dead_zone_percent', 15, dead_zone_desc)
        
        self.turn_gain = self.get_parameter('turn_gain').get_parameter_value().double_value
        self.dead_zone_percent = self.get_parameter('dead_zone_percent').get_parameter_value().integer_value
        
        # Enable dynamic parameter updates for Task 2-B tuning
        self.add_on_set_parameters_callback(self.parameter_callback)
        
        # Initialize OpenCV components
        self.bridge = CvBridge()
        
        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # QoS profile for sensor data - best effort reliability
        sensor_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE
        )
        
        # Publishers and subscribers
        # Task 2-A: カチャカへの制御コマンド送信 - Publish to Kachaka manual control topic
        self.cmd_vel_publisher = self.create_publisher(
            Twist, '/kachaka/manual_control/cmd_vel', 10
        )
        
        self.image_subscriber = self.create_subscription(
            Image, 
            '/camera/camera/color/image_raw', 
            self.image_callback, 
            sensor_qos
        )
        
        # Timer for publishing commands
        self.timer = self.create_timer(0.1, self.publish_cmd_vel)
        
        # State variables
        self.latest_twist = Twist()
        self.face_detected = False
        self.face_center_x = 0
        self.image_width = 640  # Default width, will be updated from image
        self.frame_count = 0
        
        self.get_logger().info(f'Face tracker initialized with turn_gain={self.turn_gain}, dead_zone_percent={self.dead_zone_percent}%')
        self.get_logger().info('OpenCV window should appear when camera data is received...')
        self.get_logger().info('Task 2-A: Publishing control commands to /kachaka/manual_control/cmd_vel topic')
        self.get_logger().info('Task 2-B: Dynamic parameter tuning enabled - use ros2 param set to adjust gain values')
    
    def destroy_node(self):
        """Clean up resources when node is destroyed."""
        if OPENCV_AVAILABLE:
            cv2.destroyAllWindows()
        super().destroy_node()
    
    def parameter_callback(self, params):
        """Handle dynamic parameter updates for Task 2-B tuning."""
        from rcl_interfaces.msg import SetParametersResult
        
        for param in params:
            if param.name == 'turn_gain':
                old_gain = self.turn_gain
                self.turn_gain = param.value
                self.get_logger().info(f'Task 2-B: Updated turn_gain from {old_gain:.6f} to {self.turn_gain:.6f}')
            elif param.name == 'dead_zone_percent':
                old_zone = self.dead_zone_percent
                self.dead_zone_percent = param.value
                self.get_logger().info(f'Task 2-B: Updated dead_zone_percent from {old_zone}% to {self.dead_zone_percent}%')
        
        return SetParametersResult(successful=True)

    def image_callback(self, msg):
        if not OPENCV_AVAILABLE:
            return
            
        try:
            # Convert ROS image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            self.image_width = cv_image.shape[1]
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            # Draw bounding boxes around detected faces
            display_image = cv_image.copy()
            
            if len(faces) > 0:
                # Draw rectangles around all detected faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Find the largest face (closest person)
                largest_face = max(faces, key=lambda face: face[2] * face[3])
                x, y, w, h = largest_face
                
                # Calculate face center
                self.face_center_x = x + w // 2
                self.face_detected = True
                
                self.get_logger().debug(f'Face detected at x={self.face_center_x}, image_width={self.image_width}')
            else:
                self.face_detected = False
                self.get_logger().debug('No face detected')
            
            # Display the image with face detection results
            try:
                cv2.imshow('Face Detection', display_image)
                cv2.waitKey(1)  # Allow OpenCV to process GUI events
                
                # Save a test image every 30 frames (for debugging)
                self.frame_count += 1
                if self.frame_count % 30 == 0:
                    filename = f"/tmp/face_detection_test_{self.frame_count}.jpg"
                    cv2.imwrite(filename, display_image)
                    self.get_logger().info(f'Saved test image: {filename}')
                    
            except Exception as e:
                self.get_logger().error(f'Error displaying image: {str(e)}')
                
        except Exception as e:
            self.get_logger().error(f'Error processing image: {str(e)}')
            self.face_detected = False

    def publish_cmd_vel(self):
        twist = Twist()
        
        if not self.face_detected:
            # No face detected, stop rotation
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            print("No face detected - angular velocity: 0.0")
        else:
            # Task 1-B: 旋回制御ロジックの実装 + Task 2-A: カチャカへの制御コマンド送信
            
            # 1. Calculate face center x coordinate (already done in image_callback)
            # 2. Calculate image center x coordinate
            image_center_x = self.image_width // 2
            
            # 3. Calculate error (face center - image center)
            error_x = - (self.face_center_x - image_center_x) # for front camera
            # error_x = self.face_center_x - image_center_x # for back camera
            
            # 4. Apply dead zone logic (Task 2-B improvement)
            dead_zone_pixels = (self.dead_zone_percent / 100.0) * self.image_width / 2
            
            if abs(error_x) <= dead_zone_pixels:
                # Within dead zone - stop rotation to prevent oscillation
                angular_velocity = 0.0
                face_position = "center (dead zone)"
            else:
                # Outside dead zone - apply P-control
                angular_velocity = self.turn_gain * error_x
                face_position = "right" if error_x > 0 else "left"
            
            # 5. Print calculated angular velocity to terminal
            print(f"Face at {face_position} | Error: {error_x:4.0f}px | Angular vel: {angular_velocity:+6.3f} rad/s | Gain: {self.turn_gain:.6f}")
            
            # Task 2-A: Send calculated angular velocity to Kachaka
            # Fixed linear.x = 0 (no forward/backward movement)
            twist.linear.x = 0.0
            twist.angular.z = angular_velocity  # Send calculated angular velocity
        
        # Task 2-A: Publish Twist message to /cmd_vel topic
        self.cmd_vel_publisher.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    
    face_tracker = FaceTrackerNode()
    
    try:
        rclpy.spin(face_tracker)
    except KeyboardInterrupt:
        pass
    finally:
        face_tracker.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
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

# Handle OpenCV, MediaPipe and cv_bridge import with better error handling
try:
    import cv2
    import numpy as np
    import mediapipe as mp
    # Set NumPy compatibility for cv_bridge
    np._no_nep50_warning = True
    from cv_bridge import CvBridge
    OPENCV_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OpenCV, MediaPipe or cv_bridge not available: {e}")
    OPENCV_AVAILABLE = False
except AttributeError as e:
    print(f"Warning: NumPy compatibility issue with cv_bridge: {e}")
    print("Trying fallback import...")
    try:
        import cv2
        import numpy as np
        import mediapipe as mp
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
        
        # Image enhancement parameters for backlight conditions
        clahe_clip_desc = ParameterDescriptor(description='CLAHE clip limit for contrast enhancement (higher = more contrast)')
        clahe_grid_desc = ParameterDescriptor(description='CLAHE tile grid size (smaller = more local adaptation)')
        gamma_desc = ParameterDescriptor(description='Gamma correction value (>1.0 brightens dark areas)')
        enable_bilateral_desc = ParameterDescriptor(description='Enable bilateral filtering for noise reduction')
        enable_enhancement_desc = ParameterDescriptor(description='Enable all image enhancements (false = use raw image)')
        
        self.declare_parameter('turn_gain', 0.003, turn_gain_desc)
        self.declare_parameter('dead_zone_percent', 15, dead_zone_desc)
        self.declare_parameter('clahe_clip_limit', 8.0, clahe_clip_desc)
        self.declare_parameter('clahe_grid_size', 6, clahe_grid_desc)
        self.declare_parameter('gamma_correction', 1.5, gamma_desc)
        self.declare_parameter('enable_bilateral_filter', True, enable_bilateral_desc)
        self.declare_parameter('enable_image_enhancement', False, enable_enhancement_desc)
        
        self.turn_gain = self.get_parameter('turn_gain').get_parameter_value().double_value
        self.dead_zone_percent = self.get_parameter('dead_zone_percent').get_parameter_value().integer_value
        
        # Image enhancement parameters
        self.clahe_clip_limit = self.get_parameter('clahe_clip_limit').get_parameter_value().double_value
        self.clahe_grid_size = self.get_parameter('clahe_grid_size').get_parameter_value().integer_value
        self.gamma_correction = self.get_parameter('gamma_correction').get_parameter_value().double_value
        self.enable_bilateral_filter = self.get_parameter('enable_bilateral_filter').get_parameter_value().bool_value
        self.enable_image_enhancement = self.get_parameter('enable_image_enhancement').get_parameter_value().bool_value
        
        # Enable dynamic parameter updates for Task 2-B tuning
        self.add_on_set_parameters_callback(self.parameter_callback)
        
        # Initialize OpenCV and MediaPipe components
        self.bridge = CvBridge()
        
        # Initialize MediaPipe face detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)
        
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
            elif param.name == 'clahe_clip_limit':
                old_val = self.clahe_clip_limit
                self.clahe_clip_limit = param.value
                self.get_logger().info(f'Updated CLAHE clip limit from {old_val:.1f} to {self.clahe_clip_limit:.1f}')
            elif param.name == 'clahe_grid_size':
                old_val = self.clahe_grid_size
                self.clahe_grid_size = param.value
                self.get_logger().info(f'Updated CLAHE grid size from {old_val} to {self.clahe_grid_size}')
            elif param.name == 'gamma_correction':
                old_val = self.gamma_correction
                self.gamma_correction = param.value
                self.get_logger().info(f'Updated gamma correction from {old_val:.2f} to {self.gamma_correction:.2f}')
            elif param.name == 'enable_bilateral_filter':
                old_val = self.enable_bilateral_filter
                self.enable_bilateral_filter = param.value
                self.get_logger().info(f'Updated bilateral filter from {old_val} to {self.enable_bilateral_filter}')
            elif param.name == 'enable_image_enhancement':
                old_val = self.enable_image_enhancement
                self.enable_image_enhancement = param.value
                self.get_logger().info(f'Updated image enhancement from {old_val} to {self.enable_image_enhancement}')
        
        return SetParametersResult(successful=True)

    def image_callback(self, msg):
        if not OPENCV_AVAILABLE:
            return
            
        try:
            # Convert ROS image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            self.image_width = cv_image.shape[1]
            
            # Apply image enhancements for better face detection in difficult lighting
            if self.enable_image_enhancement:
                enhanced_image = cv_image.copy()
                
                # 1. Bilateral filter to reduce noise while preserving edges
                if self.enable_bilateral_filter:
                    enhanced_image = cv2.bilateralFilter(enhanced_image, 9, 75, 75)
                
                # 2. Gamma correction to brighten dark areas
                if self.gamma_correction != 1.0:
                    # Build lookup table for gamma correction
                    inv_gamma = 1.0 / self.gamma_correction
                    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                    enhanced_image = cv2.LUT(enhanced_image, table)
                
                # 3. CLAHE for local contrast enhancement on each channel
                clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=(self.clahe_grid_size, self.clahe_grid_size))
                lab_image = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2LAB)
                lab_image[:, :, 0] = clahe.apply(lab_image[:, :, 0])
                enhanced_image = cv2.cvtColor(lab_image, cv2.COLOR_LAB2BGR)
            else:
                # Use raw image without any enhancements
                enhanced_image = cv_image
            
            # Convert BGR to RGB for MediaPipe
            rgb_image = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
            rgb_image.flags.writeable = False
            results = self.face_detection.process(rgb_image)
            
            # Draw face detection annotations
            rgb_image.flags.writeable = True
            display_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            
            if results.detections:
                # Find the largest face (closest person) based on bounding box area
                largest_detection = None
                largest_area = 0
                
                for detection in results.detections:
                    # Draw detection
                    self.mp_drawing.draw_detection(display_image, detection)
                    
                    # Calculate bounding box area to find largest face
                    bbox = detection.location_data.relative_bounding_box
                    area = bbox.width * bbox.height
                    
                    if area > largest_area:
                        largest_area = area
                        largest_detection = detection
                
                if largest_detection:
                    # Calculate face center from the largest detection
                    bbox = largest_detection.location_data.relative_bounding_box
                    h, w = cv_image.shape[:2]
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    self.face_center_x = x + width // 2
                    self.face_detected = True
                    
                    self.get_logger().debug(f'Face detected at x={self.face_center_x}, image_width={self.image_width}')
                else:
                    self.face_detected = False
                    self.get_logger().debug('No face detected')
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
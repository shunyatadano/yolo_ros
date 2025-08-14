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
            self.logger.error('OpenCV or cv_bridge is not available. Please install python3-opencv and cv_bridge.')
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
        
        # Distance control parameters (new)
        target_distance_desc = ParameterDescriptor(description='Target distance to maintain from person (meters)')
        linear_gain_desc = ParameterDescriptor(description='P-control gain for forward/backward movement (m/s per meter)')
        distance_dead_zone_desc = ParameterDescriptor(description='Distance dead zone radius (meters) to prevent oscillation')
        
        # Activity control parameter for mission_controller
        is_active_desc = ParameterDescriptor(description='Enable/disable face tracking and cmd_vel publishing')
        
        self.declare_parameter('turn_gain', 0.003, turn_gain_desc)
        self.declare_parameter('dead_zone_percent', 15, dead_zone_desc)
        self.declare_parameter('clahe_clip_limit', 0.7, clahe_clip_desc) # higher value = more contrast
        self.declare_parameter('clahe_grid_size', 4, clahe_grid_desc) # higher value = more local adaptation
        self.declare_parameter('gamma_correction', 1.5, gamma_desc)
        self.declare_parameter('enable_bilateral_filter', True, enable_bilateral_desc)
        self.declare_parameter('enable_image_enhancement', False, enable_enhancement_desc)
        
        # New distance control parameters
        self.declare_parameter('target_distance', 0.8, target_distance_desc)  # Closer target distance
        self.declare_parameter('linear_gain', 0.8, linear_gain_desc)          # Higher gain for faster response
        self.declare_parameter('distance_dead_zone', 0.1, distance_dead_zone_desc)  # Smaller dead zone
        
        # Activity control parameter
        self.declare_parameter('is_active', True, is_active_desc)
        
        self.turn_gain = self.get_parameter('turn_gain').get_parameter_value().double_value
        self.dead_zone_percent = self.get_parameter('dead_zone_percent').get_parameter_value().integer_value
        
        # Image enhancement parameters
        self.clahe_clip_limit = self.get_parameter('clahe_clip_limit').get_parameter_value().double_value
        self.clahe_grid_size = self.get_parameter('clahe_grid_size').get_parameter_value().integer_value
        self.gamma_correction = self.get_parameter('gamma_correction').get_parameter_value().double_value
        self.enable_bilateral_filter = self.get_parameter('enable_bilateral_filter').get_parameter_value().bool_value
        self.enable_image_enhancement = self.get_parameter('enable_image_enhancement').get_parameter_value().bool_value
        
        # Distance control parameters
        self.target_distance = self.get_parameter('target_distance').get_parameter_value().double_value
        self.linear_gain = self.get_parameter('linear_gain').get_parameter_value().double_value
        self.distance_dead_zone = self.get_parameter('distance_dead_zone').get_parameter_value().double_value
        
        # Activity control parameter
        self.is_active = self.get_parameter('is_active').get_parameter_value().bool_value
        
        # Enable dynamic parameter updates for Task 2-B tuning
        self.add_on_set_parameters_callback(self.parameter_callback)
        
        # Initialize OpenCV and MediaPipe components
        self.bridge = CvBridge()
        
        # Initialize MediaPipe face detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        # Use full-range model (model_selection=1) as in face_detection_prototype.py
        # This provides better detection capability compared to the short-range model
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # Use full-range model for better detection
            min_detection_confidence=0.5
        )
        
        # QoS profile for sensor data - must match publisher (RELIABLE)
        sensor_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
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
        
        # Aligned depth image subscriber for distance measurement
        # Use aligned depth which is registered to color camera coordinates
        self.depth_subscriber = self.create_subscription(
            Image,
            '/camera/camera/aligned_depth_to_color/image_raw',
            self.aligned_depth_callback,
            sensor_qos
        )
        
        # Timer for publishing commands
        self.timer = self.create_timer(0.1, self.publish_cmd_vel)
        
        # State variables
        self.latest_twist = Twist()
        self.face_detected = False
        self.face_center_x = 0
        self.face_center_y = 0
        self.image_width = 1280  # 640: Default width, will be updated from image
        self.frame_count = 0
        
        # Distance measurement variables
        self.latest_depth_image = None
        self.current_distance = None
        self.distance_measurement_valid = False
        self.depth_callback_count = 0
        self.depth_debug_timer = self.create_timer(5.0, self.debug_depth_status)
        
        # OpenCV window will be created when first image is received
        self.window_created = False
        
        self.logger = self.get_logger()

        self.logger.info(f'Face tracker initialized with turn_gain={self.turn_gain}, dead_zone_percent={self.dead_zone_percent}%')
        self.logger.info(f'Distance control: target={self.target_distance:.2f}m, linear_gain={self.linear_gain:.3f}, dead_zone={self.distance_dead_zone:.2f}m')
        self.logger.info(f'Activity control: is_active={self.is_active}')
        self.logger.info('OpenCV window created and waiting for camera data...')
        self.logger.info('Task 2-A: Publishing control commands to /kachaka/manual_control/cmd_vel topic')
        self.logger.info('Task 2-B: Dynamic parameter tuning enabled - use ros2 param set to adjust gain values')
        self.logger.info('Subscribed to: /camera/camera/color/image_raw')
        self.logger.info('Using aligned depth-to-color for accurate depth measurement')
        self.logger.info('Robust depth sampling: 3x3 grid centered on face with median filtering')
        self.logger.info('Publishing both linear.x and angular.z to robot for full person tracking')
    
    LOG_TEMPLATE = {
        'turn_gain': 'Task 2-B: Updated turn_gain from {old:.6f} to {new:.6f}',
        'dead_zone_percent': 'Task 2-B: Updated dead_zone_percent from {old}% to {new}%',
        'clahe_clip_limit': 'Updated CLAHE clip limit from {old:.1f} to {new:.1f}',
        'clahe_grid_size': 'Updated CLAHE grid size from {old} to {new}',
        'gamma_correction': 'Updated gamma correction from {old:.2f} to {new:.2f}',
        'enable_bilateral_filter': 'Updated bilateral filter from {old} to {new}',
        'enable_image_enhancement': 'Updated image enhancement from {old} to {new}',
        'target_distance': 'Updated target distance from {old:.2f}m to {new:.2f}m',
        'linear_gain': 'Updated linear gain from {old:.3f} to {new:.3f}',
        'distance_dead_zone': 'Updated distance dead zone from {old:.2f}m to {new:.2f}m',
        'is_active': 'Face tracking activity changed from {old} to {new}',
    }

    def destroy_node(self):
        """Clean up resources when node is destroyed."""
        if OPENCV_AVAILABLE:
            cv2.destroyAllWindows()
        super().destroy_node()
    
    def parameter_callback(self, params):
        """Handle dynamic parameter updates for Task 2-B tuning."""
        from rcl_interfaces.msg import SetParametersResult
        
        # Check if parameters are valid
        for param in params:
            param_name = param.name

            if hasattr(self, param_name):
                old_val = getattr(self, param_name)
                new_val = param.value
                setattr(self, param_name, new_val)

                # generate log message based on parameter name
                template = self.LOG_TEMPLATE.get(param_name, 'Updated {name} from {old} to {new}')
                if template:
                    self.logger.info(template.format(name=param_name, old=old_val, new=new_val))
                else:
                    self.logger.info(f'Updated {param_name} from {old_val} to {new_val}')
        
        return SetParametersResult(successful=True)

    def image_callback(self, msg):
        if not OPENCV_AVAILABLE:
            return
        
        # Check if face tracking is active
        if not self.is_active:
            # Still process image for display but don't update face detection state
            self.face_detected = False
            return
        
        # Debug: Log that callback was called
        if self.frame_count == 0:
            self.logger.info('First image callback received!')
            
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
                    self.face_center_y = y + height // 2
                    self.face_detected = True
                    
                    self.logger.debug(f'Face detected at x={self.face_center_x}, image_width={self.image_width}')
                else:
                    self.face_detected = False
                    self.logger.debug('No face detected')
            else:
                self.face_detected = False
                self.logger.debug('No face detected')
            
            # Display the image with face detection results
            try:
                # Create window only when first image is received (like in test_mp.py)
                if not self.window_created:
                    cv2.namedWindow('Face Detection', cv2.WINDOW_AUTOSIZE)
                    self.window_created = True
                    self.logger.info('OpenCV window created successfully')
                
                cv2.imshow('Face Detection', display_image)
                cv2.waitKey(1)  # Allow OpenCV to process GUI events
                
                # Save a test image every 30 frames (for debugging)
                self.frame_count += 1
                if self.frame_count % 30 == 0:
                    filename = f"/tmp/face_detection_test_{self.frame_count}.jpg"
                    cv2.imwrite(filename, display_image)
                    self.logger.info(f'Saved test image: {filename}')
                    
            except Exception as e:
                self.logger.error(f'Error displaying image: {str(e)}')
                
        except Exception as e:
            self.logger.error(f'Error processing image: {str(e)}')
            self.face_detected = False

    def debug_depth_status(self):
        """Debug callback to check depth camera status."""
        self.logger.info(f'Depth status: callbacks received={self.depth_callback_count}, valid_measurement={self.distance_measurement_valid}')
        if self.depth_callback_count == 0:
            self.logger.warn('No aligned depth callbacks received - check if aligned depth camera is publishing')

    def aligned_depth_callback(self, msg):
        """Process aligned depth image for distance measurement."""
        if not OPENCV_AVAILABLE:
            return
        
        self.depth_callback_count += 1
        if self.depth_callback_count == 1:
            self.logger.info('First aligned depth callback received!')
            
        try:
            # Store the latest depth image for distance calculation
            self.latest_depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            
            # Calculate distance if face is detected
            if self.face_detected:
                distance = self.calculate_distance_to_face()
                if distance is not None:
                    self.current_distance = distance
                    self.distance_measurement_valid = True
                    # Step 1: Console output only - print distance
                    self.logger.info(f'Distance to face: {distance:.3f}m at position ({self.face_center_x}, {self.face_center_y})')
                else:
                    self.distance_measurement_valid = False
                    self.logger.debug('Distance measurement failed - invalid depth data')
            else:
                self.distance_measurement_valid = False
                
        except Exception as e:
            self.logger.error(f'Error processing depth image: {str(e)}')
            self.distance_measurement_valid = False

    def calculate_distance_to_face(self):
        """Calculate distance to detected face using robust sampling of aligned depth image.
        
        Uses aligned depth image which is already registered to color camera coordinates.
        Implements robust multi-point sampling centered around face for better accuracy.
        
        Returns:
            float: Distance in meters, or None if calculation failed
        """
        if self.latest_depth_image is None:
            return None
            
        try:
            h, w = self.latest_depth_image.shape[:2]
            cx, cy = self.face_center_x, self.face_center_y
            
            # Ensure face center is within reasonable bounds
            if cx < 10 or cy < 10 or cx >= w-10 or cy >= h-10:
                self.logger.debug(f'Face center ({cx}, {cy}) too close to image edge for robust sampling')
                return None
            
            # Get robust depth measurement using multiple sampling points
            # centered around face for better accuracy
            depths = []
            
            # Create a face region estimate based on typical face proportions
            # Assume face width/height is roughly 15% of image width for sampling area
            face_region_size = max(int(0.15 * min(w, h)), 30)  # At least 30 pixels
            
            # Define sampling offsets relative to face region size (15% from center)
            offset_ratios = [-0.15, 0.0, 0.15]  # 3x3 grid centered on face
            
            for dx_ratio in offset_ratios:
                for dy_ratio in offset_ratios:
                    # Calculate absolute pixel positions
                    px = int(cx + dx_ratio * face_region_size)
                    py = int(cy + dy_ratio * face_region_size)
                    
                    # Ensure we're within image bounds
                    if 0 <= px < w and 0 <= py < h:
                        # Get depth value (aligned depth is typically in mm)
                        depth_value = self.latest_depth_image[py, px]
                        
                        # Convert to meters and validate
                        if self.latest_depth_image.dtype == np.uint16:
                            depth_m = depth_value / 1000.0  # Convert mm to meters
                        else:
                            depth_m = float(depth_value)
                        
                        # Filter out invalid depth readings
                        if 0.1 < depth_m < 10.0 and not np.isnan(depth_m):
                            depths.append(depth_m)
            
            if len(depths) < 3:  # Need at least 3 valid points for reliable median
                self.logger.debug(f'Insufficient valid depth points: {len(depths)}/9 in robust sampling')
                return None
            
            # Use median to reduce noise from outliers
            median_depth = np.median(depths)
            
            self.logger.debug(f'Robust depth measurement: {len(depths)} valid points, median: {median_depth:.3f}m')
            return median_depth
            
        except Exception as e:
            self.logger.error(f'Error calculating robust distance: {str(e)}')
            return None

    def publish_cmd_vel(self):
        twist = Twist()
        
        # Check if face tracking is active - if not, stop all movement
        if not self.is_active:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_vel_publisher.publish(twist)
            return
        
        if not self.face_detected:
            # No face detected, stop all movement (safety requirement FR5)
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            print("No face detected - all movement stopped (linear: 0.0, angular: 0.0)")
        else:
            # Task 1-B: 旋回制御ロジックの実装 + Task 2-A: カチャカへの制御コマンド送信
            
            # 1. Calculate face center x coordinate (already done in image_callback)
            # 2. Calculate image center x coordinate
            image_center_x = self.image_width // 2
            
            # 3. Calculate error (face center - image center)
            # error_x = - (self.face_center_x - image_center_x) # for front camera
            error_x = self.face_center_x - image_center_x # for back camera
            
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
            
            # Forward/backward movement control (Step 2: Console output only)
            linear_velocity = 0.0  # Default no movement
            distance_status = "no_distance"
            
            if self.distance_measurement_valid and self.current_distance is not None:
                # Calculate distance error
                error_dist = self.current_distance - self.target_distance
                
                # Apply distance dead zone logic
                if abs(error_dist) <= self.distance_dead_zone:
                    # Within dead zone - no forward/backward movement
                    linear_velocity = 0.0
                    distance_status = "dead_zone"
                else:
                    # Outside dead zone - apply P-control for forward/backward movement
                    # Note: negative sign so robot moves forward when distance is too large
                    # base_velocity = self.linear_gain * error_dist # if error_dist < 0: base_velocity < 0
                    base_velocity = -self.linear_gain * error_dist # if error_dist < 0: base_velocity > 0 
                    
                    # Apply more aggressive control for larger distance errors
                    if abs(error_dist) > 1.0:  # Very far (>1m error)
                        linear_velocity = base_velocity * 1.5  # Boost speed
                    elif abs(error_dist) > 0.5:  # Moderately far (>0.5m error)
                        linear_velocity = base_velocity * 1.2  # Slight boost
                    else:
                        linear_velocity = base_velocity
                    
                    distance_status = "too_far" if error_dist > 0 else "too_close"
                    
                    # Apply velocity clipping for safety (as per specification)
                    linear_velocity = max(-0.2, min(0.2, linear_velocity))
                
                # Step 2: Console output for distance control (linear.x calculation)
                print(f"Distance: {self.current_distance:.3f}m | Target: {self.target_distance:.3f}m | Error: {error_dist:+.3f}m | Status: {distance_status} | Linear vel: {linear_velocity:+6.3f} m/s")
            else:
                # No valid distance measurement - stop forward/backward movement for safety (FR5)
                linear_velocity = 0.0
                distance_status = "no_distance"
                if self.face_detected:
                    print(f"Distance: invalid | Linear vel: {linear_velocity:+6.3f} m/s (no depth data - safety stop)")
            
            # 5. Print calculated angular velocity to terminal
            print(f"Face at {face_position} | Error: {error_x:4.0f}px | Angular vel: {angular_velocity:+6.3f} rad/s | Gain: {self.turn_gain:.6f}")
            
            # Apply velocity clipping for safety (as per specification 5.5.2)
            # linear.x: [-0.2, 0.2] m/s, angular.z: [-0.5, 0.5] rad/s
            linear_velocity_clipped = max(-0.2, min(0.2, linear_velocity))
            angular_velocity_clipped = max(-0.5, min(0.5, angular_velocity))
            
            # Step 3: Enable full control - send both linear and angular velocities to Kachaka
            twist.linear.x = linear_velocity_clipped
            twist.angular.z = angular_velocity_clipped
        
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
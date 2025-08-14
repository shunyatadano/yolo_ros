#!/usr/bin/env python3
"""
Mission Controller Node for Kachaka Speaker Detection and Following System

This node implements the state machine described in specification.md:
- PATROLLING: Uses Nav2 waypoint follower to patrol predefined routes
- APPROACHING: Navigates to detected person using Nav2
- TRACKING: Activates face_tracker_node for close-range person following

State transitions:
- PATROLLING → APPROACHING: When YOLO detects a person
- APPROACHING → TRACKING: When robot reaches near the person (distance < 1.5m)
- TRACKING → PATROLLING: When face tracking loses the person for 5+ seconds
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.action import ActionClient
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from geometry_msgs.msg import PoseStamped, Twist, PointStamped
from sensor_msgs.msg import Image, CameraInfo
from yolo_msgs.msg import DetectionArray
from nav2_msgs.action import NavigateToPose, FollowWaypoints
from std_msgs.msg import Header, String
from std_srvs.srv import Trigger
import tf2_ros
import tf2_geometry_msgs
from tf2_ros import TransformException
import numpy as np
import cv2
from cv_bridge import CvBridge
import time
from enum import Enum
import math

class MissionState(Enum):
    """State enumeration for the mission controller state machine."""
    PATROLLING = "PATROLLING"
    APPROACHING = "APPROACHING" 
    TRACKING = "TRACKING"

class MissionController(Node):
    """Mission Controller implementing the speaker detection and following system."""
    
    def __init__(self):
        super().__init__('mission_controller')
        
        # State machine variables
        self.current_state = MissionState.PATROLLING
        self.state_start_time = time.time()
        self.last_person_detected_time = time.time()
        self.person_lost_timeout = 5.0  # seconds
        
        # Detection and navigation variables
        self.latest_detection = None
        self.current_goal = None
        self.navigation_active = False
        self.face_tracker_active = False
        
        # Parameters
        approach_distance_desc = ParameterDescriptor(description='Distance threshold to switch from APPROACHING to TRACKING (meters)')
        patrol_waypoints_desc = ParameterDescriptor(description='List of patrol waypoint coordinates as [x1,y1,x2,y2,...]')
        detection_timeout_desc = ParameterDescriptor(description='Time to wait without person detection before returning to patrol (seconds)')
        
        self.declare_parameter('approach_distance_threshold', 1.5, approach_distance_desc)
        self.declare_parameter('patrol_waypoints', [1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0], patrol_waypoints_desc)
        self.declare_parameter('person_lost_timeout', 5.0, detection_timeout_desc)
        
        self.approach_distance = self.get_parameter('approach_distance_threshold').get_parameter_value().double_value
        self.patrol_waypoints = self.get_parameter('patrol_waypoints').get_parameter_value().double_array_value
        self.person_lost_timeout = self.get_parameter('person_lost_timeout').get_parameter_value().double_value
        
        # TF2 setup for coordinate transformations
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # CV Bridge for image processing
        self.cv_bridge = CvBridge()
        
        # Camera info for 3D projection
        self.camera_info = None
        self.latest_depth_image = None
        
        # QoS profiles
        sensor_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE
        )
        
        # Subscribers
        self.yolo_subscriber = self.create_subscription(
            DetectionArray,
            '/yolo/detections',
            self.yolo_callback,
            10
        )
        
        self.camera_info_subscriber = self.create_subscription(
            CameraInfo,
            '/camera/camera/color/camera_info',
            self.camera_info_callback,
            sensor_qos
        )
        
        self.depth_image_subscriber = self.create_subscription(
            Image,
            '/camera/camera/depth/image_rect_raw',
            self.depth_image_callback,
            sensor_qos
        )
        
        # Action clients for Nav2
        self.navigate_to_pose_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.follow_waypoints_client = ActionClient(self, FollowWaypoints, 'follow_waypoints')
        
        # Publisher for mission state
        self.mission_state_publisher = self.create_publisher(String, '/mission_state', 10)
        
        # Service for manual state transitions (testing)
        self.force_approaching_service = self.create_service(
            Trigger, 'force_approaching_state', self.force_approaching_callback
        )
        self.force_tracking_service = self.create_service(
            Trigger, 'force_tracking_state', self.force_tracking_callback
        )
        self.force_patrolling_service = self.create_service(
            Trigger, 'force_patrolling_state', self.force_patrolling_callback
        )
        
        # Timer for state machine processing - reduced frequency to avoid navigation interrupts
        self.state_timer = self.create_timer(1.0, self.state_machine_update)  # 1Hz update rate
        
        # Timer for periodic state publishing and debugging
        self.state_publish_timer = self.create_timer(2.0, self.periodic_state_update)  # 0.5Hz for visibility
        
        # Initialize patrol waypoints
        self.patrol_poses = self.create_patrol_poses()
        
        self.logger = self.get_logger()

        self.logger.info('Mission Controller initialized')
        self.logger.info(f'Starting in {self.current_state.value} state')
        self.logger.info(f'Approach distance threshold: {self.approach_distance:.2f}m')
        self.logger.info(f'Person lost timeout: {self.person_lost_timeout:.1f}s')
        self.logger.info(f'Configured {len(self.patrol_poses)} patrol waypoints')
        
        # Start patrolling
        self.start_patrolling()
        
        # Publish initial state
        self.publish_mission_state()
    
    def create_patrol_poses(self):
        """Create PoseStamped messages from patrol waypoint parameters."""
        poses = []
        waypoints = self.patrol_waypoints
        
        # Convert flat list [x1,y1,x2,y2,...] to pose list
        for i in range(0, len(waypoints), 2):
            if i + 1 < len(waypoints):
                pose = PoseStamped()
                pose.header.frame_id = 'map'
                pose.pose.position.x = waypoints[i]
                pose.pose.position.y = waypoints[i + 1]
                pose.pose.position.z = 0.0
                # Default orientation (facing forward)
                pose.pose.orientation.w = 1.0
                poses.append(pose)
        
        return poses
    
    def should_update_goal(self, new_goal):
        """Check if we should update the current navigation goal to avoid flickering."""
        if self.current_goal is None:
            return True
        
        # Calculate distance between current and new goal
        dx = new_goal.pose.position.x - self.current_goal.pose.position.x
        dy = new_goal.pose.position.y - self.current_goal.pose.position.y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Only update if new goal is significantly different (>0.5m)
        return distance > 0.5
    
    def publish_mission_state(self):
        """Publish current mission state."""
        msg = String()
        msg.data = self.current_state.value
        self.mission_state_publisher.publish(msg)
        self.logger.info(f'Published mission state: {self.current_state.value}')
    
    def periodic_state_update(self):
        """Periodic state publishing and debugging information."""
        # Always publish current state for visibility
        self.publish_mission_state()
        
        # Debug information
        current_time = time.time()
        time_since_last_detection = current_time - self.last_person_detected_time
        
        if self.current_state == MissionState.PATROLLING:
            self.logger.debug(f'PATROLLING: Time since last person detection: {time_since_last_detection:.1f}s')
            if self.latest_detection is not None:
                self.logger.debug(f'Person detected with confidence: {self.latest_detection.score:.2f}')
        elif self.current_state == MissionState.APPROACHING:
            distance = self.get_distance_to_current_goal()
            if distance is not None:
                self.logger.debug(f'APPROACHING: Distance to goal: {distance:.2f}m, Time since detection: {time_since_last_detection:.1f}s')
            else:
                self.logger.debug(f'APPROACHING: No distance available, Time since detection: {time_since_last_detection:.1f}s')
        elif self.current_state == MissionState.TRACKING:
            self.logger.debug(f'TRACKING: Time since last detection: {time_since_last_detection:.1f}s')
    
    def yolo_callback(self, msg):
        """Process YOLO detection results."""
        # Look for person detections
        person_detections = []
        total_detections = len(msg.detections)
        
        self.logger.debug(f'Received YOLO callback with {total_detections} detections')
        
        for detection in msg.detections:
            # Log all detections for debugging
            self.logger.debug(f'Detection: class_id={detection.class_id}, class_name="{detection.class_name}", score={detection.score:.2f}')
            
            # Check for person using both class_name and class_id (for compatibility)
            is_person = (detection.class_name == 'person' or 
                        detection.class_id == 0 or  # COCO person class_id
                        str(detection.class_id) == 'person')
            
            if is_person and detection.score > 0.5:
                person_detections.append(detection)
                self.logger.info(f'Valid person detection: score={detection.score:.2f}')
        
        if person_detections:
            # Update detection time and store the best detection (highest confidence)
            self.last_person_detected_time = time.time()
            self.latest_detection = max(person_detections, key=lambda d: d.score)
            self.logger.info(f'🚶 Person detected with confidence {self.latest_detection.score:.2f} (current state: {self.current_state.value})')
            
            # Force state transition check if in PATROLLING
            if self.current_state == MissionState.PATROLLING:
                self.logger.info('🔄 Triggering immediate transition check from PATROLLING to APPROACHING')
        else:
            self.latest_detection = None
            if total_detections > 0:
                self.logger.debug(f'Received {total_detections} detections but no persons above 0.5 confidence')
            else:
                self.logger.debug('No detections in YOLO message')
    
    def camera_info_callback(self, msg):
        """Store camera intrinsic parameters."""
        self.camera_info = msg
    
    def depth_image_callback(self, msg):
        """Store latest depth image for 3D coordinate calculation."""
        self.latest_depth_image = msg
    
    def state_machine_update(self):
        """Main state machine update loop."""
        current_time = time.time()
        time_in_state = current_time - self.state_start_time
        time_since_last_detection = current_time - self.last_person_detected_time
        
        if self.current_state == MissionState.PATROLLING:
            self.handle_patrolling_state(time_since_last_detection)
        elif self.current_state == MissionState.APPROACHING:
            self.handle_approaching_state(time_since_last_detection)
        elif self.current_state == MissionState.TRACKING:
            self.handle_tracking_state(time_since_last_detection)
    
    def handle_patrolling_state(self, time_since_last_detection):
        """Handle PATROLLING state logic."""
        # Debug current conditions
        has_detection = self.latest_detection is not None
        detection_recent = time_since_last_detection < 2.0
        
        self.logger.debug(f'PATROLLING conditions: has_detection={has_detection}, time_since_last={time_since_last_detection:.1f}s, recent={detection_recent}')
        
        # Transition to APPROACHING if person detected
        if has_detection and detection_recent:
            self.logger.info(f'✅ Conditions met for PATROLLING → APPROACHING: detection_confidence={self.latest_detection.score:.2f}')
            self.transition_to_approaching()
        elif has_detection and not detection_recent:
            self.logger.debug(f'⏰ Person detected but too old ({time_since_last_detection:.1f}s > 2.0s)')
        elif not has_detection:
            self.logger.debug('👁️ No person detection available')
    
    def handle_approaching_state(self, time_since_last_detection):
        """Handle APPROACHING state logic."""
        # Debug current conditions
        person_lost = time_since_last_detection > self.person_lost_timeout
        has_goal = self.current_goal is not None
        distance_to_goal = self.get_distance_to_current_goal() if has_goal else None
        close_enough = distance_to_goal is not None and distance_to_goal < self.approach_distance
        
        distance_str = f'{distance_to_goal:.2f}m' if distance_to_goal else 'N/A'
        self.logger.debug(f'APPROACHING conditions: person_lost={person_lost}({time_since_last_detection:.1f}s), has_goal={has_goal}, distance={distance_str}, close_enough={close_enough}')
        
        # Check if we've lost the person
        if person_lost:
            self.logger.info(f'⚠️ Person lost for {time_since_last_detection:.1f}s > {self.person_lost_timeout}s, APPROACHING → PATROLLING')
            self.transition_to_patrolling()
            return
        
        # Check if we're close enough to start tracking
        if has_goal and close_enough:
            self.logger.info(f'🎯 Close to target ({distance_to_goal:.2f}m < {self.approach_distance}m), APPROACHING → TRACKING')
            self.transition_to_tracking()
            return
        
        # Update navigation goal if we have a new detection - with goal stability check
        if self.latest_detection is not None:
            new_goal = self.get_goal_pose_from_detection(self.latest_detection)
            if new_goal is not None and self.should_update_goal(new_goal):
                self.logger.info(f'🗺️ Updating navigation goal to new person position')
                self.navigate_to_pose(new_goal)
            elif new_goal is not None:
                self.logger.debug(f'🔒 Goal update skipped - new goal too close to current goal')
    
    def handle_tracking_state(self, time_since_last_detection):
        """Handle TRACKING state logic."""
        # Check if we've lost the person for too long
        if time_since_last_detection > self.person_lost_timeout:
            self.transition_to_patrolling()
    
    def transition_to_patrolling(self):
        """Transition to PATROLLING state."""
        if self.current_state == MissionState.PATROLLING:
            return
        
        self.logger.info(f'State transition: {self.current_state.value} → PATROLLING')
        self.current_state = MissionState.PATROLLING
        self.state_start_time = time.time()
        self.publish_mission_state()
        
        # Stop face tracking
        self.set_face_tracker_active(False)
        
        # Cancel current navigation and start patrolling
        self.cancel_current_navigation()
        self.start_patrolling()
    
    def transition_to_approaching(self):
        """Transition to APPROACHING state."""
        if self.current_state == MissionState.APPROACHING:
            return
        
        self.logger.info(f'State transition: {self.current_state.value} → APPROACHING')
        self.current_state = MissionState.APPROACHING
        self.state_start_time = time.time()
        self.publish_mission_state()
        
        # Stop face tracking if it was active
        self.set_face_tracker_active(False)
        
        # Cancel current navigation with delay to avoid race condition
        self.cancel_current_navigation()
        time.sleep(0.2)  # Brief delay to ensure cancellation completes
        
        # Navigate to detected person
        if self.latest_detection is not None:
            goal_pose = self.get_goal_pose_from_detection(self.latest_detection)
            if goal_pose is not None:
                self.navigate_to_pose(goal_pose)
    
    def transition_to_tracking(self):
        """Transition to TRACKING state."""
        if self.current_state == MissionState.TRACKING:
            return
        
        self.logger.info(f'State transition: {self.current_state.value} → TRACKING')
        self.current_state = MissionState.TRACKING
        self.state_start_time = time.time()
        self.publish_mission_state()
        
        # Cancel navigation and start face tracking
        self.cancel_current_navigation()
        self.set_face_tracker_active(True)
    
    def start_patrolling(self):
        """Start waypoint following for patrolling."""
        if not self.patrol_poses:
            self.logger.warn('No patrol waypoints configured')
            return
        
        self.logger.info(f'Starting patrol with {len(self.patrol_poses)} waypoints')
        
        # Wait for the action server
        if not self.follow_waypoints_client.wait_for_server(timeout_sec=5.0):
            self.logger.error('Follow waypoints action server not available')
            return
        
        # Create and send waypoint following goal
        goal_msg = FollowWaypoints.Goal()
        goal_msg.poses = self.patrol_poses
        
        self.navigation_active = True
        future = self.follow_waypoints_client.send_goal_async(goal_msg)
        future.add_done_callback(self.patrol_goal_response_callback)
    
    def navigate_to_pose(self, pose):
        """Navigate to a specific pose using Nav2."""
        self.logger.info(f'Navigating to pose: ({pose.pose.position.x:.2f}, {pose.pose.position.y:.2f})')
        
        # Wait for the action server
        if not self.navigate_to_pose_client.wait_for_server(timeout_sec=5.0):
            self.logger.error('Navigate to pose action server not available')
            return
        
        # Create and send navigation goal
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose
        
        self.current_goal = pose
        self.navigation_active = True
        future = self.navigate_to_pose_client.send_goal_async(goal_msg)
        future.add_done_callback(self.navigation_goal_response_callback)
    
    def patrol_goal_response_callback(self, future):
        """Handle patrol goal response."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.logger.error('Patrol goal rejected')
            self.navigation_active = False
            return
        
        self.logger.info('Patrol goal accepted')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.patrol_result_callback)
    
    def navigation_goal_response_callback(self, future):
        """Handle navigation goal response."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.logger.error('Navigation goal rejected')
            self.navigation_active = False
            return
        
        self.logger.info('Navigation goal accepted')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.navigation_result_callback)
    
    def patrol_result_callback(self, future):
        """Handle patrol result."""
        self.navigation_active = False
        self.logger.info('Patrol completed')
    
    def navigation_result_callback(self, future):
        """Handle navigation result."""
        self.navigation_active = False
        result = future.result().result
        self.logger.info(f'Navigation completed with result: {result}')
    
    def cancel_current_navigation(self):
        """Cancel any active navigation."""
        if self.navigation_active:
            self.logger.info('Cancelling current navigation')
            # Note: In a full implementation, we would cancel the active goal here
            self.navigation_active = False
    
    def set_face_tracker_active(self, active):
        """Set the face_tracker_node is_active parameter."""
        if self.face_tracker_active == active:
            return
        
        self.face_tracker_active = active
        self.logger.info(f'Setting face_tracker_node is_active to {active}')
        
        # Use ros2 param set to control face tracker
        import subprocess
        try:
            result = subprocess.run([
                'ros2', 'param', 'set', '/face_tracker_node', 'is_active', str(active).lower()
            ], capture_output=True, text=True, timeout=5.0)
            
            if result.returncode == 0:
                self.logger.info(f'Successfully set face_tracker is_active to {active}')
            else:
                self.logger.error(f'Failed to set face_tracker is_active: {result.stderr}')
        except Exception as e:
            self.logger.error(f'Error setting face_tracker parameter: {str(e)}')
    
    def get_distance_to_current_goal(self):
        """Calculate distance to current navigation goal."""
        if self.current_goal is None:
            return None
        
        try:
            # Get current robot position in map frame
            transform = self.tf_buffer.lookup_transform(
                'map', 'base_link', rclpy.time.Time()
            )
            
            robot_x = transform.transform.translation.x
            robot_y = transform.transform.translation.y
            goal_x = self.current_goal.pose.position.x
            goal_y = self.current_goal.pose.position.y
            
            distance = math.sqrt((goal_x - robot_x)**2 + (goal_y - robot_y)**2)
            return distance
            
        except TransformException as e:
            self.logger.debug(f'Could not get robot position: {str(e)}')
            return None
    
    def get_goal_pose_from_detection(self, detection):
        """Convert YOLO detection to navigation goal pose in map frame.
        
        This implements the 2D detection to 3D navigation goal conversion
        as specified in Task 4 of the specification.
        """
        if self.camera_info is None or self.latest_depth_image is None:
            self.logger.debug('Missing camera info or depth image for 3D conversion')
            return None
        
        try:
            # Step 1: Calculate detection bounding box center pixel coordinates
            bbox = detection.bbox
            center_u = int(bbox.center.position.x)
            center_v = int(bbox.center.position.y)
            
            # Step 2: Get depth value from depth image
            depth_image = self.cv_bridge.imgmsg_to_cv2(self.latest_depth_image, desired_encoding='passthrough')
            
            # Ensure pixel coordinates are within image bounds
            if (center_u < 0 or center_v < 0 or 
                center_u >= depth_image.shape[1] or center_v >= depth_image.shape[0]):
                self.logger.debug(f'Detection center ({center_u}, {center_v}) outside image bounds')
                return None
            
            # Get depth value (handle different encodings)
            depth_value = depth_image[center_v, center_u]
            if depth_image.dtype == np.uint16:
                depth_meters = depth_value / 1000.0  # Convert mm to meters
            else:
                depth_meters = float(depth_value)  # Already in meters
            
            # Check for valid depth
            if depth_meters <= 0 or depth_meters > 10.0:  # Reasonable range check
                self.logger.debug(f'Invalid depth value: {depth_meters}')
                return None
            
            # Step 3: Convert to 3D coordinates in camera frame
            # Using camera intrinsic parameters
            fx = self.camera_info.k[0]  # Focal length x
            fy = self.camera_info.k[4]  # Focal length y  
            cx = self.camera_info.k[2]  # Principal point x
            cy = self.camera_info.k[5]  # Principal point y
            
            # Calculate 3D point in camera coordinate system
            x_cam = (center_u - cx) * depth_meters / fx
            y_cam = (center_v - cy) * depth_meters / fy
            z_cam = depth_meters
            
            # Step 4: Transform from camera frame to map frame
            camera_point = PointStamped()
            camera_point.header.frame_id = 'camera_color_optical_frame'  # RealSense optical frame
            camera_point.header.stamp = self.get_clock().now().to_msg()
            camera_point.point.x = z_cam  # Forward direction in camera frame
            camera_point.point.y = -x_cam  # Left direction in camera frame  
            camera_point.point.z = -y_cam  # Up direction in camera frame
            
            # Transform to map frame
            map_point = self.tf_buffer.transform(camera_point, 'map')
            
            # Step 5: Create navigation goal pose
            goal_pose = PoseStamped()
            goal_pose.header.frame_id = 'map'
            goal_pose.header.stamp = self.get_clock().now().to_msg()
            goal_pose.pose.position.x = map_point.point.x
            goal_pose.pose.position.y = map_point.point.y
            goal_pose.pose.position.z = 0.0  # Ground level for navigation
            goal_pose.pose.orientation.w = 1.0  # Default orientation
            
            self.logger.info(f'Converted detection to goal: ({goal_pose.pose.position.x:.2f}, {goal_pose.pose.position.y:.2f}) at {depth_meters:.2f}m depth')
            return goal_pose
            
        except Exception as e:
            self.logger.error(f'Error converting detection to goal pose: {str(e)}')
            return None
    
    def force_approaching_callback(self, request, response):
        """Service callback to force transition to APPROACHING state."""
        self.logger.info('🔧 Manual transition to APPROACHING state requested')
        self.transition_to_approaching()
        response.success = True
        response.message = f"Forced transition to APPROACHING state"
        return response
    
    def force_tracking_callback(self, request, response):
        """Service callback to force transition to TRACKING state."""
        self.logger.info('🔧 Manual transition to TRACKING state requested')
        self.transition_to_tracking()
        response.success = True
        response.message = f"Forced transition to TRACKING state"
        return response
    
    def force_patrolling_callback(self, request, response):
        """Service callback to force transition to PATROLLING state."""
        self.logger.info('🔧 Manual transition to PATROLLING state requested')
        self.transition_to_patrolling()
        response.success = True
        response.message = f"Forced transition to PATROLLING state"
        return response


def main(args=None):
    rclpy.init(args=args)
    
    mission_controller = MissionController()
    
    try:
        rclpy.spin(mission_controller)
    except KeyboardInterrupt:
        pass
    finally:
        mission_controller.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
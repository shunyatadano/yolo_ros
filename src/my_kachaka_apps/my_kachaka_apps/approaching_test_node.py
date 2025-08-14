#!/usr/bin/env python3
"""
APPROACHING State Test Node

This node tests the APPROACHING phase of the mission system by:
1. Starting in PATROLLING mode
2. Simulating person detection to trigger APPROACHING state
3. Navigating towards the detected person position
4. Testing transition to TRACKING when close enough

Author: Generated for Kachaka Mission System Testing
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Point, Twist
from yolo_msgs.msg import DetectionArray, Detection, BoundingBox
from std_msgs.msg import String, Header
from std_srvs.srv import Trigger
from nav2_msgs.action import NavigateToPose
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import time
import math
import random


class ApproachingTestNode(Node):
    def __init__(self):
        super().__init__('approaching_test_node')
        
        # Parameters
        self.declare_parameter('test_person_x', 2.0)
        self.declare_parameter('test_person_y', -2.0)
        self.declare_parameter('approach_distance', 1.5)
        self.declare_parameter('detection_confidence', 0.8)
        self.declare_parameter('enable_auto_test', True)
        
        self.test_person_x = self.get_parameter('test_person_x').value
        self.test_person_y = self.get_parameter('test_person_y').value
        self.approach_distance = self.get_parameter('approach_distance').value
        self.detection_confidence = self.get_parameter('detection_confidence').value
        self.enable_auto_test = self.get_parameter('enable_auto_test').value
        
        # Test state variables
        self.test_phase = "WAITING"  # WAITING, PATROLLING, DETECTING, APPROACHING, TRACKING
        self.mission_state = "UNKNOWN"
        self.current_position = Point()
        self.person_detected = False
        self.approach_started = False
        self.tracking_triggered = False
        
        # Test timing
        self.test_start_time = time.time()
        self.detection_start_time = None
        self.approach_start_time = None
        
        # Publishers
        self.detection_pub = self.create_publisher(
            DetectionArray, '/yolo/detections', 10
        )
        self.cmd_vel_pub = self.create_publisher(
            Twist, '/cmd_vel', 10
        )
        
        # Subscribers
        self.mission_state_sub = self.create_subscription(
            String, '/mission_state', 
            self.mission_state_callback, 10
        )
        self.robot_pose_sub = self.create_subscription(
            PoseStamped, '/robot_pose',
            self.robot_pose_callback, 10
        )
        
        # Services
        self.trigger_detection_service = self.create_service(
            Trigger, 'trigger_person_detection', self.trigger_detection_callback
        )
        self.reset_test_service = self.create_service(
            Trigger, 'reset_approaching_test', self.reset_test_callback
        )
        
        # Timer for test logic
        self.test_timer = self.create_timer(1.0, self.test_timer_callback)
        
        # Timer for publishing fake detections
        self.detection_timer = self.create_timer(0.5, self.detection_timer_callback)
        
        self.get_logger().info('APPROACHING Test Node initialized')
        self.get_logger().info(f'Test person position: ({self.test_person_x:.2f}, {self.test_person_y:.2f})')
        self.get_logger().info(f'Approach distance threshold: {self.approach_distance:.2f}m')
        
        if self.enable_auto_test:
            self.get_logger().info('Auto-test enabled: Will automatically trigger detection after 10 seconds')
    
    def mission_state_callback(self, msg):
        """Track mission controller state changes."""
        old_state = self.mission_state
        self.mission_state = msg.data
        
        if old_state != self.mission_state:
            self.get_logger().info(f'Mission state changed: {old_state} → {self.mission_state}')
            
            # Update test phase based on mission state
            if self.mission_state == "PATROLLING":
                if self.test_phase == "WAITING":
                    self.test_phase = "PATROLLING"
                    self.get_logger().info('Test phase: WAITING → PATROLLING')
            elif self.mission_state == "APPROACHING":
                if self.test_phase in ["PATROLLING", "DETECTING"]:
                    self.test_phase = "APPROACHING"
                    self.approach_start_time = time.time()
                    self.approach_started = True
                    self.get_logger().info('Test phase: → APPROACHING')
            elif self.mission_state == "TRACKING":
                if self.test_phase == "APPROACHING":
                    self.test_phase = "TRACKING"
                    self.tracking_triggered = True
                    self.get_logger().info('Test phase: APPROACHING → TRACKING')
    
    def robot_pose_callback(self, msg):
        """Track robot position for distance calculations."""
        self.current_position = msg.pose.position
    
    def test_timer_callback(self):
        """Main test logic timer."""
        current_time = time.time()
        elapsed_time = current_time - self.test_start_time
        
        # Auto-trigger detection after 10 seconds if enabled
        if (self.enable_auto_test and 
            self.test_phase == "PATROLLING" and 
            elapsed_time > 10.0 and 
            not self.person_detected):
            self.trigger_person_detection()
        
        # Check if we're close enough to trigger tracking
        if self.test_phase == "APPROACHING" and not self.tracking_triggered:
            distance_to_person = self.get_distance_to_person()
            if distance_to_person is not None and distance_to_person < self.approach_distance:
                self.get_logger().info(
                    f'Robot close to person (distance: {distance_to_person:.2f}m < {self.approach_distance:.2f}m), '
                    'expecting transition to TRACKING...'
                )
        
        # Print test status periodically
        if int(elapsed_time) % 10 == 0 and elapsed_time > 0:
            self.print_test_status()
    
    def detection_timer_callback(self):
        """Publish person detection messages when detection is active."""
        if not self.person_detected:
            return
        
        # Create fake detection message
        detection_msg = DetectionArray()
        detection_msg.header = Header()
        detection_msg.header.stamp = self.get_clock().now().to_msg()
        detection_msg.header.frame_id = "camera_link"
        
        # Create person detection
        detection = Detection()
        detection.class_name = "person"
        detection.score = self.detection_confidence
        
        # Simulate bounding box (center of image for simplicity)
        bbox = BoundingBox()
        bbox.center.x = 320.0  # Image center x
        bbox.center.y = 240.0  # Image center y  
        bbox.size_x = 100.0    # Box width
        bbox.size_y = 200.0    # Box height
        detection.bbox = bbox
        
        detection_msg.detections = [detection]
        
        # Publish detection
        self.detection_pub.publish(detection_msg)
    
    def trigger_person_detection(self):
        """Start simulating person detection."""
        if self.person_detected:
            self.get_logger().warn('Person detection already active')
            return
        
        self.person_detected = True
        self.detection_start_time = time.time()
        self.test_phase = "DETECTING"
        
        self.get_logger().info('=== TRIGGERING PERSON DETECTION ===')
        self.get_logger().info(f'Publishing person detections at ({self.test_person_x:.2f}, {self.test_person_y:.2f})')
        self.get_logger().info('Expecting state transition: PATROLLING → APPROACHING')
    
    def trigger_detection_callback(self, request, response):
        """Service callback to manually trigger person detection."""
        self.trigger_person_detection()
        response.success = True
        response.message = "Person detection triggered"
        return response
    
    def reset_test_callback(self, request, response):
        """Service callback to reset the test."""
        self.reset_test()
        response.success = True
        response.message = "Test reset"
        return response
    
    def reset_test(self):
        """Reset test to initial state."""
        self.person_detected = False
        self.approach_started = False
        self.tracking_triggered = False
        self.test_phase = "WAITING"
        self.mission_state = "UNKNOWN"
        self.test_start_time = time.time()
        self.detection_start_time = None
        self.approach_start_time = None
        
        self.get_logger().info('=== TEST RESET ===')
    
    def get_distance_to_person(self):
        """Calculate distance from robot to test person position."""
        dx = self.current_position.x - self.test_person_x
        dy = self.current_position.y - self.test_person_y
        return math.sqrt(dx*dx + dy*dy)
    
    def print_test_status(self):
        """Print current test status."""
        current_time = time.time()
        elapsed_time = current_time - self.test_start_time
        
        status = f"\n=== APPROACHING TEST STATUS (t={elapsed_time:.1f}s) ==="
        status += f"\nTest Phase: {self.test_phase}"
        status += f"\nMission State: {self.mission_state}"
        status += f"\nPerson Detected: {self.person_detected}"
        status += f"\nApproach Started: {self.approach_started}"
        status += f"\nTracking Triggered: {self.tracking_triggered}"
        
        if hasattr(self, 'current_position'):
            distance = self.get_distance_to_person()
            if distance is not None:
                status += f"\nDistance to person: {distance:.2f}m"
        
        if self.detection_start_time:
            detection_time = current_time - self.detection_start_time
            status += f"\nDetection active for: {detection_time:.1f}s"
        
        if self.approach_start_time:
            approach_time = current_time - self.approach_start_time
            status += f"\nApproaching for: {approach_time:.1f}s"
        
        status += f"\n{'='*50}"
        
        self.get_logger().info(status)
    
    def get_test_results(self):
        """Get test results summary."""
        results = "\n=== APPROACHING PHASE TEST RESULTS ==="
        
        # Check if all expected transitions occurred
        patrolling_ok = self.test_phase != "WAITING"
        detection_ok = self.person_detected
        approaching_ok = self.approach_started
        tracking_ok = self.tracking_triggered
        
        results += f"\n✓ PATROLLING State: {'PASS' if patrolling_ok else 'FAIL'}"
        results += f"\n✓ Person Detection: {'PASS' if detection_ok else 'FAIL'}"
        results += f"\n✓ APPROACHING State: {'PASS' if approaching_ok else 'FAIL'}"
        results += f"\n✓ TRACKING Transition: {'PASS' if tracking_ok else 'FAIL'}"
        
        overall_pass = patrolling_ok and detection_ok and approaching_ok and tracking_ok
        results += f"\n\nOVERALL TEST: {'PASS' if overall_pass else 'FAIL'}"
        
        if self.approach_start_time:
            approach_duration = time.time() - self.approach_start_time
            results += f"\nApproach Duration: {approach_duration:.1f}s"
        
        results += f"\n{'='*50}"
        
        return results


def main(args=None):
    rclpy.init(args=args)
    node = ApproachingTestNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Test interrupted by user")
    finally:
        # Print final test results
        if hasattr(node, 'get_test_results'):
            print(node.get_test_results())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
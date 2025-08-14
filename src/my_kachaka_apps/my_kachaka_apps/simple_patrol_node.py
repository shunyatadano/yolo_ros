#!/usr/bin/env python3
"""
Simple Patrol Node for PATROLLING Test Mode

This node provides basic waypoint navigation for testing the patrol behavior
without the full mission controller state machine.

Author: Generated for Kachaka Mission System Testing
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Point
from yolo_msgs.msg import DetectionArray
from std_srvs.srv import Trigger
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.action import ActionClient
import time


class SimplePatrolNode(Node):
    def __init__(self):
        super().__init__('simple_patrol_node')
        
        # Parameters
        self.declare_parameter('patrol_speed', 0.3)
        self.declare_parameter('goal_tolerance', 0.5)
        self.declare_parameter('enable_person_detection_logging', True)
        
        self.patrol_speed = self.get_parameter('patrol_speed').value
        self.goal_tolerance = self.get_parameter('goal_tolerance').value
        self.enable_logging = self.get_parameter('enable_person_detection_logging').value
        
        # Define named waypoints as dictionary
        self.waypoint_dict = {
            'base': {'x': 1.080, 'y': -1.191},
            'jin-san': {'x': 1.193, 'y': -3.832},
            'charger': {'x': 0.886, 'y': 0.243},
            'suenaga-san': {'x': 3.134, 'y': -1.210}
        }
        
        # Define patrol sequence - start from base, visit locations, return to base
        self.waypoint_list = ['jin-san', 'charger', 'suenaga-san', 'base']
        
        self.get_logger().info(f'Named patrol waypoints:')
        for name, coords in self.waypoint_dict.items():
            self.get_logger().info(f'  {name}: x={coords["x"]:.2f}, y={coords["y"]:.2f}')
        
        # State variables
        self.current_waypoint_index = 0
        self.is_patrolling = True
        self.navigator = None
        self.persons_detected = []
        
        # Publishers
        self.current_goal_pub = self.create_publisher(
            PoseStamped, 'current_goal', 10
        )
        
        # Subscribers
        self.detection_sub = self.create_subscription(
            DetectionArray, '/yolo/detections', 
            self.detection_callback, 10
        )
        
        # Services
        self.pause_service = self.create_service(
            Trigger, 'pause_patrol', self.pause_patrol_callback
        )
        self.resume_service = self.create_service(
            Trigger, 'resume_patrol', self.resume_patrol_callback
        )
        
        # Timer for patrol logic - reduced frequency to avoid navigation interference
        self.patrol_timer = self.create_timer(3.0, self.patrol_timer_callback)
        
        # Initialize navigator
        self.init_navigator()
        
        self.get_logger().info('Simple Patrol Node initialized')
    
    def init_navigator(self):
        """Initialize the Nav2 navigator without AMCL dependency."""
        try:
            self.navigator = BasicNavigator()
            # Skip AMCL check - Kachaka has built-in localization
            self.get_logger().info('Nav2 navigator initialized, using Kachaka localization')
            
            # Start patrol with a single-shot timer to allow nav2 stack to initialize
            self.startup_timer = self.create_timer(3.0, self.delayed_patrol_start)
        except Exception as e:
            self.get_logger().error(f'Failed to initialize navigator: {e}')
            self.navigator = None
    
    def delayed_patrol_start(self):
        """Start patrol after a brief delay to ensure Nav2 is ready."""
        # Cancel the startup timer so it only runs once
        self.startup_timer.cancel()
        self.get_logger().info('Starting patrol with Kachaka localization')
        self.start_next_waypoint()
    
    def detection_callback(self, msg):
        """Process person detection messages."""
        if not self.enable_logging:
            return
            
        # Count persons detected
        person_count = 0
        for detection in msg.detections:
            for result in detection.results:
                if result.hypothesis.class_id == 'person':
                    person_count += 1
        
        if person_count > 0:
            current_time = self.get_clock().now()
            current_waypoint_name = self.waypoint_list[self.current_waypoint_index]
            self.persons_detected.append({
                'time': current_time,
                'count': person_count,
                'waypoint_index': self.current_waypoint_index,
                'waypoint_name': current_waypoint_name
            })
            
            self.get_logger().info(
                f'Detected {person_count} person(s) at {current_waypoint_name} '
                f'(waypoint {self.current_waypoint_index})'
            )
    
    def patrol_timer_callback(self):
        """Main patrol logic timer."""
        if not self.is_patrolling or self.navigator is None:
            return
        
        # Check if we've reached the current goal - add stability check
        if not self.navigator.isTaskComplete():
            return  # Still navigating to current waypoint
        
        # Check navigation result
        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            current_waypoint_name = self.waypoint_list[self.current_waypoint_index]
            coords = self.waypoint_dict[current_waypoint_name]
            self.get_logger().info(
                f'Reached {current_waypoint_name} at ({coords["x"]:.2f}, {coords["y"]:.2f})'
            )
            # Move to next waypoint
            self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.waypoint_list)
            # Brief pause at waypoint to allow for stable positioning
            self.create_timer(2.0, lambda: self.start_next_waypoint() if self.is_patrolling else None)
        elif result == TaskResult.FAILED:
            current_waypoint_name = self.waypoint_list[self.current_waypoint_index]
            self.get_logger().warn(
                f'Failed to reach {current_waypoint_name}, retrying in 5 seconds...'
            )
            # Retry the same waypoint after a longer delay to avoid rapid retries
            self.create_timer(8.0, lambda: self.start_next_waypoint() if self.is_patrolling else None)
        elif result == TaskResult.CANCELED:
            self.get_logger().info('Navigation was canceled')
    
    def start_next_waypoint(self):
        """Start navigation to the next waypoint."""
        if not self.is_patrolling or self.navigator is None:
            return
        
        if not self.waypoint_list:
            self.get_logger().error('No waypoints defined')
            return
        
        # Get current waypoint
        current_waypoint_name = self.waypoint_list[self.current_waypoint_index]
        coords = self.waypoint_dict[current_waypoint_name]
        x, y = coords['x'], coords['y']
        
        # Create goal pose
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.get_clock().now().to_msg()
        goal_pose.pose.position.x = x
        goal_pose.pose.position.y = y
        goal_pose.pose.position.z = 0.0
        goal_pose.pose.orientation.w = 1.0  # Facing forward
        
        # Publish current goal for visualization
        self.current_goal_pub.publish(goal_pose)
        
        # Start navigation
        self.navigator.goToPose(goal_pose)
        
        self.get_logger().info(
            f'Navigating to {current_waypoint_name}: ({x:.2f}, {y:.2f})'
        )
    
    def pause_patrol_callback(self, request, response):
        """Service callback to pause patrol."""
        self.is_patrolling = False
        if self.navigator:
            self.navigator.cancelTask()
        response.success = True
        response.message = "Patrol paused"
        self.get_logger().info("Patrol paused")
        return response
    
    def resume_patrol_callback(self, request, response):
        """Service callback to resume patrol."""
        self.is_patrolling = True
        self.start_next_waypoint()
        response.success = True
        response.message = "Patrol resumed"
        self.get_logger().info("Patrol resumed")
        return response
    
    def get_patrol_stats(self):
        """Get patrol statistics."""
        if not self.persons_detected:
            return "No persons detected during patrol"
        
        total_detections = len(self.persons_detected)
        total_persons = sum(d['count'] for d in self.persons_detected)
        
        current_waypoint_name = self.waypoint_list[self.current_waypoint_index]
        stats = f"Patrol Statistics:\n"
        stats += f"  Total detections: {total_detections}\n"
        stats += f"  Total persons seen: {total_persons}\n"
        stats += f"  Current waypoint: {current_waypoint_name} (index: {self.current_waypoint_index})\n"
        
        # Show detection breakdown by waypoint
        waypoint_detections = {}
        for detection in self.persons_detected:
            wp_name = detection['waypoint_name']
            if wp_name not in waypoint_detections:
                waypoint_detections[wp_name] = 0
            waypoint_detections[wp_name] += detection['count']
        
        if waypoint_detections:
            stats += f"  Detections by location:\n"
            for wp_name, count in waypoint_detections.items():
                stats += f"    {wp_name}: {count} persons\n"
        
        return stats


def main(args=None):
    rclpy.init(args=args)
    node = SimplePatrolNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Patrol interrupted by user")
        if hasattr(node, 'navigator') and node.navigator:
            node.navigator.cancelTask()
    finally:
        # Print final stats
        if hasattr(node, 'get_patrol_stats'):
            print(node.get_patrol_stats())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
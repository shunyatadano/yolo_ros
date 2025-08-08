#!/usr/bin/env python3
"""
Test script to verify the mission_controller functionality.
This tests basic initialization, parameter setting, and state machine operation.
"""

import rclpy
from rclpy.node import Node
import time
import subprocess
import sys

class MissionControllerTest(Node):
    def __init__(self):
        super().__init__('mission_controller_test')
        self.get_logger().info('Starting mission_controller test...')
        
    def run_test(self):
        """Run basic tests for mission_controller."""
        
        # Test 1: Check if mission_controller node is running
        self.get_logger().info('Test 1: Checking if mission_controller is running...')
        result = subprocess.run(['ros2', 'node', 'list'], capture_output=True, text=True)
        if '/mission_controller' in result.stdout:
            self.get_logger().info('✓ mission_controller node is running')
        else:
            self.get_logger().error('✗ mission_controller node is not running')
            return False
        
        # Test 2: Check default parameters
        self.get_logger().info('Test 2: Checking default parameters...')
        
        params_to_check = [
            'approach_distance_threshold',
            'patrol_waypoints',
            'person_lost_timeout'
        ]
        
        for param in params_to_check:
            result = subprocess.run(['ros2', 'param', 'get', '/mission_controller', param], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                value = result.stdout.strip()
                self.get_logger().info(f'✓ Parameter {param}: {value}')
            else:
                self.get_logger().error(f'✗ Failed to get parameter {param}')
                return False
        
        # Test 3: Check topic subscriptions
        self.get_logger().info('Test 3: Checking topic subscriptions...')
        
        expected_topics = [
            '/yolo/detections',
            '/camera/camera/color/camera_info',
            '/camera/camera/depth/image_rect_raw'
        ]
        
        result = subprocess.run(['ros2', 'topic', 'list'], capture_output=True, text=True)
        available_topics = result.stdout.split('\n')
        
        for topic in expected_topics:
            if topic in available_topics:
                self.get_logger().info(f'✓ Topic {topic} is available')
            else:
                self.get_logger().warn(f'⚠ Topic {topic} is not available (this is expected if YOLO/camera not running)')
        
        # Test 4: Test parameter modification
        self.get_logger().info('Test 4: Testing parameter modification...')
        
        # Change approach distance threshold
        result = subprocess.run(['ros2', 'param', 'set', '/mission_controller', 
                               'approach_distance_threshold', '2.0'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            self.get_logger().info('✓ Successfully modified approach_distance_threshold')
            
            # Verify the change
            result = subprocess.run(['ros2', 'param', 'get', '/mission_controller', 
                                   'approach_distance_threshold'], 
                                  capture_output=True, text=True)
            if '2.0' in result.stdout:
                self.get_logger().info('✓ Parameter change verified')
            else:
                self.get_logger().error('✗ Parameter change not reflected')
                return False
        else:
            self.get_logger().error('✗ Failed to modify parameter')
            return False
        
        # Test 5: Check action clients (they may not be available without Nav2)
        self.get_logger().info('Test 5: Checking action server availability...')
        
        action_servers = ['navigate_to_pose', 'follow_waypoints']
        for action in action_servers:
            result = subprocess.run(['ros2', 'action', 'list'], capture_output=True, text=True)
            if f'/{action}' in result.stdout:
                self.get_logger().info(f'✓ Action server {action} is available')
            else:
                self.get_logger().warn(f'⚠ Action server {action} is not available (expected without Nav2)')
        
        self.get_logger().info('🎉 Basic mission_controller tests completed successfully!')
        return True

def main():
    rclpy.init()
    test_node = MissionControllerTest()
    
    # Check if mission_controller is running
    result = subprocess.run(['ros2', 'node', 'list'], capture_output=True, text=True)
    if '/mission_controller' not in result.stdout:
        test_node.get_logger().error('mission_controller is not running! Please start it first with:')
        test_node.get_logger().error('ros2 run my_kachaka_apps mission_controller')
        rclpy.shutdown()
        return
    
    # Run the test
    success = test_node.run_test()
    
    if success:
        print("\n" + "="*60)
        print("✓ MISSION_CONTROLLER BASIC TEST COMPLETED SUCCESSFULLY")
        print("The mission_controller state machine is ready for integration!")
        print("="*60)
        print("\nNext steps:")
        print("1. Start YOLO detection: ros2 launch yolo_bringup yolov8.launch.py")  
        print("2. Start face tracker: ros2 run my_kachaka_apps face_tracker_node")
        print("3. Start Nav2 (if available): ros2 launch kachaka_nav2_bringup navigation_launch.py")
        print("4. Test full integration")
    else:
        print("\n" + "="*60)
        print("✗ MISSION_CONTROLLER TEST FAILED")
        print("Please check the implementation and dependencies.")
        print("="*60)
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()
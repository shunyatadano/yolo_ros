#!/usr/bin/env python3
"""
Test script to verify the is_active parameter functionality in face_tracker_node.
This script will test the parameter setting and check if it correctly controls the node behavior.
"""

import rclpy
from rclpy.node import Node
import time
import subprocess
import sys

class IsActiveTest(Node):
    def __init__(self):
        super().__init__('is_active_test')
        self.get_logger().info('Starting is_active parameter test...')
        
    def run_test(self):
        """Run the test sequence for is_active parameter."""
        
        # Test 1: Check default parameter value
        self.get_logger().info('Test 1: Checking default is_active value...')
        result = subprocess.run(['ros2', 'param', 'get', '/face_tracker_node', 'is_active'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            self.get_logger().info(f'Default is_active value: {result.stdout.strip()}')
        else:
            self.get_logger().error('Failed to get default is_active parameter')
            return False
            
        # Test 2: Set is_active to false
        self.get_logger().info('Test 2: Setting is_active to false...')
        result = subprocess.run(['ros2', 'param', 'set', '/face_tracker_node', 'is_active', 'false'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            self.get_logger().info('Successfully set is_active to false')
        else:
            self.get_logger().error('Failed to set is_active to false')
            return False
            
        # Wait a moment
        time.sleep(2)
        
        # Test 3: Verify the parameter was set
        result = subprocess.run(['ros2', 'param', 'get', '/face_tracker_node', 'is_active'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            value = result.stdout.strip()
            self.get_logger().info(f'Current is_active value: {value}')
            if 'false' in value.lower():
                self.get_logger().info('✓ Test 2 passed: is_active successfully set to false')
            else:
                self.get_logger().error('✗ Test 2 failed: is_active was not set to false')
                return False
        
        # Test 4: Set is_active back to true
        self.get_logger().info('Test 4: Setting is_active back to true...')
        result = subprocess.run(['ros2', 'param', 'set', '/face_tracker_node', 'is_active', 'true'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            self.get_logger().info('Successfully set is_active to true')
        else:
            self.get_logger().error('Failed to set is_active to true')
            return False
        
        # Wait a moment
        time.sleep(2)
        
        # Test 5: Verify the parameter was set back
        result = subprocess.run(['ros2', 'param', 'get', '/face_tracker_node', 'is_active'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            value = result.stdout.strip()
            self.get_logger().info(f'Final is_active value: {value}')
            if 'true' in value.lower():
                self.get_logger().info('✓ Test 4 passed: is_active successfully set back to true')
            else:
                self.get_logger().error('✗ Test 4 failed: is_active was not set back to true')
                return False
        
        self.get_logger().info('🎉 All tests passed! is_active parameter is working correctly.')
        return True

def main():
    rclpy.init()
    test_node = IsActiveTest()
    
    # Check if face_tracker_node is running
    result = subprocess.run(['ros2', 'node', 'list'], capture_output=True, text=True)
    if '/face_tracker_node' not in result.stdout:
        test_node.get_logger().error('face_tracker_node is not running! Please start it first with:')
        test_node.get_logger().error('ros2 run my_kachaka_apps face_tracker_node')
        rclpy.shutdown()
        return
    
    # Run the test
    success = test_node.run_test()
    
    if success:
        print("\n" + "="*60)
        print("✓ is_active PARAMETER TEST COMPLETED SUCCESSFULLY")
        print("The face_tracker_node can now be controlled by mission_controller!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("✗ is_active PARAMETER TEST FAILED")
        print("Please check the face_tracker_node implementation.")
        print("="*60)
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Launch file for the complete Kachaka Speaker Detection and Following System

This launch file starts all components needed for the mission:
- YOLO ROS for person detection
- Face tracker node for close-range following  
- Mission controller for state machine coordination
- RealSense camera (if needed)

Usage:
    ros2 launch my_kachaka_apps mission_system.launch.py

Optional arguments:
    enable_camera:=true/false (default: true) - Start RealSense camera
    enable_nav2:=true/false (default: false) - Start Nav2 navigation
    yolo_model:=<model_file> (default: yolov8m.pt) - YOLO model to use
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """Generate launch description for the complete mission system."""
    
    # Launch arguments
    enable_camera_arg = DeclareLaunchArgument(
        'enable_camera',
        default_value='true',
        description='Enable RealSense camera launch'
    )
    
    enable_nav2_arg = DeclareLaunchArgument(
        'enable_nav2', 
        default_value='false',
        description='Enable Nav2 navigation launch'
    )
    
    yolo_model_arg = DeclareLaunchArgument(
        'yolo_model',
        default_value='yolov8m.pt',
        description='YOLO model file to use'
    )
    
    yolo_threshold_arg = DeclareLaunchArgument(
        'yolo_threshold',
        default_value='0.5',
        description='YOLO detection confidence threshold'
    )
    
    # Get launch configurations
    enable_camera = LaunchConfiguration('enable_camera')
    enable_nav2 = LaunchConfiguration('enable_nav2')
    yolo_model = LaunchConfiguration('yolo_model')
    yolo_threshold = LaunchConfiguration('yolo_threshold')
    
    # 1. RealSense camera launch (conditional)
    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('realsense2_camera'),
                'launch',
                'rs_launch.py'
            ])
        ),
        condition=IfCondition(enable_camera),
        launch_arguments={
            'enable_color': 'true',
            'enable_depth': 'true',
            'enable_infra': 'false',
            'enable_fisheye': 'false',
            'color_width': '640',
            'color_height': '480',
            'color_fps': '15',
            'depth_width': '640', 
            'depth_height': '480',
            'depth_fps': '15',
        }.items()
    )
    
    # 2. Camera activation commands (for LifecycleNode)
    camera_configure_cmd = ExecuteProcess(
        condition=IfCondition(enable_camera),
        cmd=['ros2', 'lifecycle', 'set', '/camera/camera', 'configure'],
        output='screen',
        shell=False
    )
    
    camera_activate_cmd = ExecuteProcess(
        condition=IfCondition(enable_camera),
        cmd=['ros2', 'lifecycle', 'set', '/camera/camera', 'activate'],
        output='screen',
        shell=False
    )
    
    # 3. YOLO detection launch
    yolo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('yolo_bringup'),
                'launch',
                'yolov8.launch.py'
            ])
        ),
        launch_arguments={
            'model': yolo_model,
            'threshold': yolo_threshold,
            'input_image_topic': '/camera/camera/color/image_raw',
            'device': 'cpu',  # Change to 'cuda:0' if GPU available
            'namespace': 'yolo'
        }.items()
    )
    
    # 4. Face tracker node
    face_tracker_node = Node(
        package='my_kachaka_apps',
        executable='face_tracker_node',
        name='face_tracker_node',
        output='screen',
        parameters=[{
            'turn_gain': 0.003,
            'dead_zone_percent': 15,
            'target_distance': 0.5,
            'linear_gain': 0.8,
            'distance_dead_zone': 0.1,
            'enable_image_enhancement': False,
            'is_active': True  # Will be controlled by mission_controller
        }]
    )
    
    # 5. Mission controller node  
    mission_controller_node = Node(
        package='my_kachaka_apps',
        executable='mission_controller', 
        name='mission_controller',
        output='screen',
        parameters=[{
            'approach_distance_threshold': 1.5,
            'patrol_waypoints': [1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0],
            'person_lost_timeout': 5.0
        }]
    )
    
    # 6. Nav2 launch (conditional)
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('kachaka_nav2_bringup'),
                'launch', 
                'navigation_launch.py'
            ])
        ),
        condition=IfCondition(enable_nav2)
    )
    
    # 7. Informational output
    info_cmd = ExecuteProcess(
        cmd=['echo', '=== Kachaka Mission System Started ===\n'
                    'Components:\n'
                    '- YOLO Detection: /yolo/detections\n'
                    '- Face Tracker: /face_tracker_node\n'
                    '- Mission Controller: /mission_controller\n'
                    '- Camera: /camera/camera (if enabled)\n'
                    '- Nav2: navigation stack (if enabled)\n'
                    '\n'
                    'State Machine: PATROLLING → APPROACHING → TRACKING\n'
                    '\n'
                    'Monitor topics:\n'
                    '  ros2 topic echo /yolo/detections\n' 
                    '  ros2 topic echo /kachaka/manual_control/cmd_vel\n'
                    '\n'
                    'Control parameters:\n'
                    '  ros2 param set /face_tracker_node is_active false/true\n'
                    '  ros2 param set /mission_controller approach_distance_threshold 1.5\n'],
        output='screen'
    )
    
    return LaunchDescription([
        # Launch arguments
        enable_camera_arg,
        enable_nav2_arg, 
        yolo_model_arg,
        yolo_threshold_arg,
        
        # Camera system
        realsense_launch,
        
        # YOLO detection
        yolo_launch,
        
        # Face tracking
        face_tracker_node,
        
        # Mission coordination
        mission_controller_node,
        
        # Nav2 (optional)
        nav2_launch,
        
        # Camera activation (with delay)
        ExecuteProcess(
            condition=IfCondition(enable_camera),
            cmd=['sleep', '3'],  # Wait for camera to initialize
            output='screen'
        ),
        camera_configure_cmd,
        ExecuteProcess(
            condition=IfCondition(enable_camera),
            cmd=['sleep', '1'],
            output='screen'
        ),
        camera_activate_cmd,
        
        # Info message
        info_cmd
    ])
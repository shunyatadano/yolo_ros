#!/usr/bin/env python3
"""
Launch file for testing PATROLLING mode only

This launch file focuses on testing waypoint navigation and person detection
visualization without the full mission controller state machine.

Components included:
- YOLO ROS for person detection
- Nav2 navigation stack
- Simple waypoint navigation node
- Person detection visualization

Usage:
    ros2 launch my_kachaka_apps patrol_test.launch.py

Optional arguments:
    enable_camera:=true/false (default: false) - Start RealSense camera
    yolo_model:=<model_file> (default: yolov8m.pt) - YOLO model to use
    waypoints:="x1,y1,x2,y2,..." (default: "1.0,1.0,-1.0,1.0,-1.0,-1.0,1.0,-1.0")
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for PATROLLING test mode."""
    
    # Launch arguments
    enable_camera_arg = DeclareLaunchArgument(
        'enable_camera',
        default_value='false',
        description='Enable RealSense camera launch (for real testing)'
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
    
    waypoints_arg = DeclareLaunchArgument(
        'waypoints',
        default_value='1.0,1.0,-1.0,1.0,-1.0,-1.0,1.0,-1.0',
        description='Patrol waypoints as comma-separated list: x1,y1,x2,y2,...'
    )
    
    # Get launch configurations
    enable_camera = LaunchConfiguration('enable_camera')
    yolo_model = LaunchConfiguration('yolo_model')
    yolo_threshold = LaunchConfiguration('yolo_threshold')
    waypoints = LaunchConfiguration('waypoints')
    
    # 1. RealSense camera launch (conditional - for real testing)
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
    
    # 2. YOLO detection launch
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
            'device': 'cpu',
            'namespace': 'yolo'
        }.items()
    )
    
    # 3. Using Kachaka's existing localization (no AMCL needed)
    # Kachaka robot provides map->odom->base_link transforms
    
    # 4. Nav2 navigation launch (required for patrolling)
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('kachaka_nav2_bringup'),
                'launch', 
                'navigation_launch.py'
            ])
        )
    )
    
    # 5. Simple patrol node for waypoint navigation
    patrol_node = Node(
        package='my_kachaka_apps',
        executable='simple_patrol_node',
        name='simple_patrol_node',
        output='screen',
        parameters=[{
            'patrol_waypoints': waypoints,
            'patrol_speed': 0.3,
            'goal_tolerance': 0.5,
            'enable_person_detection_logging': True
        }]
    )
    
    # 6. Person detection visualizer node
    person_viz_node = Node(
        package='my_kachaka_apps',
        executable='person_detection_visualizer',
        name='person_detection_visualizer',
        output='screen',
        parameters=[{
            'marker_lifetime': 10.0,
            'detection_topic': '/yolo/detections',
            'marker_topic': '/person_detection_markers'
        }]
    )
    
    # # 7. RViz2 for visualization
    # rviz_config_file = PathJoinSubstitution([
    #     FindPackageShare('kachaka_description'),
    #     'config',
    #     'kachaka.rviz'
    # ])
    
    # rviz_node = Node(
    #     package='rviz2',
    #     executable='rviz2',
    #     name='rviz2',
    #     arguments=['-d', rviz_config_file],
    #     output='screen'
    # )
    
    # 8. Camera activation commands (for real camera testing)
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
    
    # 9. Informational output
    info_cmd = ExecuteProcess(
        cmd=['echo', '=== PATROLLING Test Mode Started ===\n'
                    'Components:\n'
                    '- Kachaka Localization: built-in\n'
                    '- Nav2 Navigation: /navigate_to_pose\n'
                    '- Simple Patrol: /simple_patrol_node\n'
                    '- YOLO Detection: /yolo/detections\n'
                    '- Person Visualizer: /person_detection_visualizer\n'
                    '- RViz2: visualization\n'
                    '\n'
                    'Monitor topics:\n'
                    '  ros2 topic echo /yolo/detections\n'
                    '  ros2 topic echo /simple_patrol_node/current_goal\n'
                    '  ros2 topic echo /person_detection_markers\n'
                    '\n'
                    'Control commands:\n'
                    '  ros2 param set /simple_patrol_node patrol_speed 0.2\n'
                    '  ros2 service call /simple_patrol_node/pause_patrol std_srvs/srv/Trigger\n'
                    '  ros2 service call /simple_patrol_node/resume_patrol std_srvs/srv/Trigger\n'],
        output='screen'
    )
    
    return LaunchDescription([
        # Launch arguments
        enable_camera_arg,
        yolo_model_arg,
        yolo_threshold_arg,
        waypoints_arg,
        
        # Localization: Using Kachaka's built-in localization
        
        # Navigation system (required)
        nav2_launch,
        
        # Camera system (optional for testing)
        realsense_launch,
        
        # YOLO detection
        yolo_launch,
        
        # Patrol navigation
        patrol_node,
        
        # Person detection visualization
        person_viz_node,
        
        # Visualization: RViz removed - user runs their own
        
        # Camera activation (with delay, for real camera)
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
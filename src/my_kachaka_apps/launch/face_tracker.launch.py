#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare launch arguments
    ip_address_arg = DeclareLaunchArgument(
        'ip_address',
        default_value='192.168.118.188',
        description='IP address of Kachaka robot'
    )
    
    turn_gain_arg = DeclareLaunchArgument(
        'turn_gain',
        default_value='0.002',
        description='Turn gain for face tracking P-controller'
    )
    
    dead_zone_percent_arg = DeclareLaunchArgument(
        'dead_zone_percent',
        default_value='20',
        description='Dead zone percentage for face tracking'
    )
    
    kick_duration_arg = DeclareLaunchArgument(
        'kick_duration',
        default_value='0.2',
        description='Kick-start duration in seconds to overcome static friction'
    )
    
    kick_speed_arg = DeclareLaunchArgument(
        'kick_speed',
        default_value='0.4',
        description='Kick-start angular velocity in rad/s'
    )
    
    min_angular_speed_arg = DeclareLaunchArgument(
        'min_angular_speed',
        default_value='0.15',
        description='Minimum angular velocity in rad/s for sustained tracking'
    )
    
    enable_camera_arg = DeclareLaunchArgument(
        'enable_camera',
        default_value='true',
        description='Enable RealSense camera launch'
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
        default_value='jin-san,charger,suenaga-san,base',
        description='Patrol waypoints as comma-separated list of waypoint names'
    )

    # Get launch configurations
    enable_camera = LaunchConfiguration('enable_camera')
    yolo_model = LaunchConfiguration('yolo_model')
    yolo_threshold = LaunchConfiguration('yolo_threshold')
    waypoints = LaunchConfiguration('waypoints')
    
    # RealSense camera launch (conditional)
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
            'align_depth.enable': 'true',  # Enable depth-color alignment
            'color_width': '640',
            'color_height': '480',
            'color_fps': '15',
            'depth_width': '640', 
            'depth_height': '480',
            'depth_fps': '15',
        }.items()
    )
    
    # YOLO detection launch
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
    
    # Nav2 navigation launch (for PATROLLING state)
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('kachaka_nav2_bringup'),
                'launch', 
                'navigation_launch.py'
            ])
        )
    )
    
    # Simple patrol node for waypoint navigation
    patrol_node = Node(
        package='my_kachaka_apps',
        executable='simple_patrol_node',
        name='simple_patrol_node',
        output='screen',
        parameters=[{
            'patrol_speed': 0.3,
            'goal_tolerance': 0.5,
            'enable_person_detection_logging': True
        }]
    )
    
    # Person detection visualizer node
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

    # Kachaka gRPC bridge launch 
    kachaka_bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('kachaka_grpc_ros2_bridge'),
                'launch',
                'grpc_ros2_bridge.launch.xml'
            ])
        ]),
        launch_arguments={
            'server_uri': [LaunchConfiguration('ip_address'), ':26400']
        }.items()
    )

    # Face tracker node
    face_tracker_node = Node(
        package='my_kachaka_apps',
        executable='face_tracker_node',
        name='face_tracker_node',
        parameters=[{
            'turn_gain': LaunchConfiguration('turn_gain'),
            'dead_zone_percent': LaunchConfiguration('dead_zone_percent'),
            'kick_duration': LaunchConfiguration('kick_duration'),
            'kick_speed': LaunchConfiguration('kick_speed'),
            'min_angular_speed': LaunchConfiguration('min_angular_speed'),
        }],
        output='screen'
    )
    
    # Camera activation commands (for real camera testing)
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

    return LaunchDescription([
        # Launch arguments
        ip_address_arg,
        turn_gain_arg,
        dead_zone_percent_arg,
        kick_duration_arg,
        kick_speed_arg,
        min_angular_speed_arg,
        enable_camera_arg,
        yolo_model_arg,
        yolo_threshold_arg,
        waypoints_arg,
        
        # Core systems
        realsense_launch,
        kachaka_bridge_launch,
        
        # Navigation system (for PATROLLING state)
        nav2_launch,
        
        # YOLO detection (for person detection in PATROLLING)
        yolo_launch,
        
        # Patrol navigation (for PATROLLING state)
        patrol_node,
        
        # Person detection visualization
        person_viz_node,
        
        # Face tracking (primary functionality)
        face_tracker_node,
        
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
    ])
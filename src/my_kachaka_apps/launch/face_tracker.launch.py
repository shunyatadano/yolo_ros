#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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
        default_value='0.004',
        description='Turn gain for face tracking P-controller'
    )
    
    dead_zone_percent_arg = DeclareLaunchArgument(
        'dead_zone_percent',
        default_value='10',
        description='Dead zone percentage for face tracking'
    )

    # RealSense camera launch
    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('realsense2_camera'),
                'launch',
                'rs_launch.py'
            ])
        ]),
        launch_arguments={
            'enable_color': 'true',
            'enable_depth': 'true',
            'color_width': '640',
            'color_height': '480',
            'color_fps': '30.0',
        }.items()
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
        }],
        output='screen'
    )

    return LaunchDescription([
        ip_address_arg,
        turn_gain_arg,
        dead_zone_percent_arg,
        realsense_launch,
        kachaka_bridge_launch,
        face_tracker_node,
    ])
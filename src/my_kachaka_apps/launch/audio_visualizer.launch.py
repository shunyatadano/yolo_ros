#!/usr/bin/env python3
"""
Launch file for Audio Source Visualizer
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'odas_frame',
            default_value='odas',
            description='ODAS coordinate frame'
        ),
        DeclareLaunchArgument(
            'map_frame',
            default_value='map',
            description='Map coordinate frame'
        ),
        DeclareLaunchArgument(
            'base_frame',
            default_value='base_link',
            description='Robot base coordinate frame'
        ),
        DeclareLaunchArgument(
            'max_range',
            default_value='3.0',
            description='Maximum range to project audio sources (meters)'
        ),
        DeclareLaunchArgument(
            'marker_size',
            default_value='0.2',
            description='Size of visualization markers'
        ),
        DeclareLaunchArgument(
            'activity_threshold',
            default_value='0.1',
            description='Minimum activity threshold for SST sources'
        ),
        
        # Audio Source Visualizer Node
        Node(
            package='my_kachaka_apps',
            executable='audio_source_visualizer',
            name='audio_source_visualizer',
            parameters=[{
                'odas_frame': LaunchConfiguration('odas_frame'),
                'map_frame': LaunchConfiguration('map_frame'),
                'base_frame': LaunchConfiguration('base_frame'),
                'max_range': LaunchConfiguration('max_range'),
                'marker_size': LaunchConfiguration('marker_size'),
                'activity_threshold': LaunchConfiguration('activity_threshold'),
            }],
            output='screen',
            emulate_tty=True
        ),
        
        # Static transform from base_link to odas (adjust as needed for your setup)
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='odas_to_base_transform',
            arguments=['0', '0', '0.1', '0', '0', '0', 'base_link', 'odas'],
            output='screen'
        ),
    ])
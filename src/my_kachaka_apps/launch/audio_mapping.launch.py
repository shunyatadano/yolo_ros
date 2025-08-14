#!/usr/bin/env python3
"""
Launch file for complete audio source mapping system
Launches ODAS and audio source visualization together
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'rviz',
            default_value='true',
            description='Launch RViz for visualization'
        ),
        DeclareLaunchArgument(
            'max_range',
            default_value='3.0',
            description='Maximum range to project audio sources (meters)'
        ),
        
        # Include ODAS launch file
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('odas_ros'),
                    'launch',
                    'odas.launch.xml'
                ])
            ]),
            launch_arguments={
                'rviz': 'false',  # We'll launch our own RViz
                'visualization': 'false'  # Disable ODAS visualization, use our own
            }.items()
        ),
        
        # Audio Source Visualizer Node
        Node(
            package='my_kachaka_apps',
            executable='audio_source_visualizer',
            name='audio_source_visualizer',
            parameters=[{
                'odas_frame': 'odas',
                'map_frame': 'map',
                'base_frame': 'base_link',
                'max_range': LaunchConfiguration('max_range'),
                'marker_size': 0.2,
                'activity_threshold': 0.1,
            }],
            output='screen',
            emulate_tty=True
        ),
        
        # Static transform from map to base_link (temporary for testing)
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='map_to_base_transform',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'base_link'],
            output='screen'
        ),
        
        # RViz for visualization
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', PathJoinSubstitution([
                FindPackageShare('my_kachaka_apps'),
                'rviz',
                'audio_mapping.rviz'
            ])],
            condition=lambda context: LaunchConfiguration('rviz').perform(context) == 'true',
            output='screen'
        ),
    ])
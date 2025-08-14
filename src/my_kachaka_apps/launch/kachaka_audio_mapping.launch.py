#!/usr/bin/env python3
"""
Launch file for Kachaka with Audio Source Mapping
Integrates ODAS audio visualization with the Kachaka robot system
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource, AnyLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'rviz',
            default_value='true',
            description='Launch RViz with Kachaka and audio visualization'
        ),
        DeclareLaunchArgument(
            'max_range',
            default_value='3.0',
            description='Maximum range to project audio sources (meters)'
        ),
        DeclareLaunchArgument(
            'robot_description',
            default_value='true',
            description='Launch robot description'
        ),
        
        # Note: Robot description should be launched separately if needed
        # Include Kachaka robot description
        # IncludeLaunchDescription(
        #     PythonLaunchDescriptionSource([
        #         PathJoinSubstitution([
        #             FindPackageShare('kachaka_description'),
        #             'launch',
        #             'robot_description.launch.py'
        #         ])
        #     ]),
        #     condition=IfCondition(LaunchConfiguration('robot_description'))
        # ),
        
        # Include ODAS launch file (without RViz)
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource([
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
                'odas_frame': 'base_link',  # Use existing Kachaka frame
                'map_frame': 'map',
                'base_frame': 'base_link',
                'max_range': LaunchConfiguration('max_range'),
                'marker_size': 0.15,  # Smaller for Kachaka scale
                'activity_threshold': 0.1,
            }],
            output='screen',
            emulate_tty=True
        ),
        
        # RViz with Kachaka + Audio visualization
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', PathJoinSubstitution([
                FindPackageShare('my_kachaka_apps'),
                'rviz',
                'kachaka_with_audio.rviz'
            ])],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen'
        ),
    ])
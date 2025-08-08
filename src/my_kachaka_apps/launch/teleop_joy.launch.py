#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
import os


def generate_launch_description():
    # Joy node to read joystick input
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        output='screen'
    )

    # Teleop twist joy node with remapped cmd_vel and config
    teleop_joy_node = Node(
        package='teleop_twist_joy',
        executable='teleop_node',
        name='teleop_twist_joy',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('my_kachaka_apps'),
                'config',
                'teleop_joy.yaml'
            ])
        ],
        remappings=[
            ('cmd_vel', '/kachaka/manual_control/cmd_vel')
        ],
        output='screen'
    )

    return LaunchDescription([
        joy_node,
        teleop_joy_node,
    ])
#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Teleop twist keyboard node with remapped cmd_vel
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        remappings=[
            ('cmd_vel', '/kachaka/manual_control/cmd_vel')
        ],
        prefix='gnome-terminal -- ',
        output='screen'
    )

    return LaunchDescription([
        teleop_node,
    ])
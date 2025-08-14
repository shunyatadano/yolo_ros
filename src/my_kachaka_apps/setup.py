from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'my_kachaka_apps'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'rviz'), glob(os.path.join('rviz', '*.rviz'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Shunya Tadano',
    maintainer_email='shunya.tadano@example.com',
    description='KachakaTalk: Face tracking and following applications for Kachaka robot',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'face_tracker_node = my_kachaka_apps.face_tracker_node:main',
            'mission_controller = my_kachaka_apps.mission_controller:main',
            'simple_patrol_node = my_kachaka_apps.simple_patrol_node:main',
            'person_detection_visualizer = my_kachaka_apps.person_detection_visualizer:main',
            'audio_source_visualizer = my_kachaka_apps.audio_source_visualizer:main',
        ],
    },
)
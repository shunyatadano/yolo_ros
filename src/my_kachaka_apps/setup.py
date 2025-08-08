from setuptools import find_packages, setup

package_name = 'my_kachaka_apps'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/face_tracker.launch.py', 'launch/teleop_keyboard.launch.py', 'launch/teleop_joy.launch.py']),
        ('share/' + package_name + '/config', ['config/teleop_joy.yaml']),
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
        ],
    },
)
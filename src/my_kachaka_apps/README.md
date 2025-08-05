# KachakaTalk Face Tracker

This package implements Function 4.1 (人物追従機能) from the KachakaTalk project specification - a face tracking system that detects faces from RealSense camera input and controls the Kachaka robot to keep the detected face centered in the camera view.

## Features

- **Face Detection**: Uses OpenCV Haar Cascade classifier to detect human faces
- **Visual Display**: Shows camera feed with green bounding boxes around detected faces via cv2.imshow
- **P-Controller**: Implements proportional control for robot rotation based on face position
- **Terminal Output**: Real-time display of face position and calculated angular velocity values
- **Dead Zone**: Configurable dead zone to prevent oscillation when face is centered
- **ROS2 Integration**: Fully integrated with ROS2 ecosystem
- **Test Image Saving**: Automatically saves detection results to `/tmp/face_detection_test_*.jpg` for debugging

## Architecture

```
[RealSense Camera] --/camera/color/image_raw--> [Face Tracker Node] --/cmd_vel--> [Kachaka Robot]
```

## Requirements

### Hardware
- Kachaka robot (Preferred Robotics)
- Intel RealSense D435 (or compatible RGB-D camera)
- Control PC with ROS2 Humble

### Software Dependencies
- ROS2 Humble Hawksbill
- Python packages:
  - `python3-opencv`
  - `cv_bridge`
  - `rclpy`
  - `sensor_msgs`
  - `geometry_msgs`

## Installation

1. Make sure you have the Kachaka workspace set up as per the main README.md
2. Install RealSense ROS2 package (required for camera input):
   ```bash
   sudo apt install ros-humble-realsense2-camera
   ```
3. Build the package:
   ```bash
   cd ~/kachaka_ws
   source /opt/ros/humble/setup.bash
   colcon build --packages-select my_kachaka_apps
   source install/setup.bash
   ```

## Usage

### Method 1: Complete System Launch (Recommended)

**Prerequisites:** Install RealSense package first:
```bash
sudo apt install ros-humble-realsense2-camera
```

Launch all required components (RealSense camera, Kachaka bridge, and face tracker) with a single command:

```bash
# Set environment variables
export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
export ROS_DOMAIN_ID=0
export FRAME_PREFIX="kachaka"
source ~/kachaka_ws/install/setup.bash

# Launch the complete system
ros2 launch my_kachaka_apps face_tracker.launch.py ip_address:=<KACHAKA_IP_ADDRESS>
```

Example:
```bash
ros2 launch my_kachaka_apps face_tracker.launch.py ip_address:=192.168.118.188
```

### Method 2: Manual Launch (If RealSense package not available)

If you don't have the RealSense package installed, launch components individually:

1. **Start RealSense camera (if package available):**
   ```bash
   ros2 launch realsense2_camera rs_launch.py enable_color:=true enable_depth:=true
   ```
   
   **Alternative - Use any USB camera:**
   ```bash
   # Install USB camera package
   sudo apt install ros-humble-usb-cam
   
   # Launch USB camera (adjust device as needed)
   ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:=/dev/video0 -p image_width:=640 -p image_height:=480 -p pixel_format:=yuyv -r __ns:=/camera -r image_raw:=color/image_raw
   ```

2. **Start Kachaka gRPC bridge:**
   ```bash
   ros2 launch kachaka_grpc_ros2_bridge grpc_ros2_bridge.launch.xml server_uri:=<KACHAKA_IP>:26400
   ```

3. **Start face tracker node:**
   ```bash
   ros2 run my_kachaka_apps face_tracker_node
   ```

### Method 3: Direct Node Execution

**Prerequisites**: Camera topics must be available.

**Simple execution:**
```bash
cd ~/ws_kachaka
source install/setup.bash
ros2 run my_kachaka_apps face_tracker_node
```

#### Expected Behavior
- **OpenCV Window**: "Face Detection" window showing live camera feed
- **Green Rectangles**: Bounding boxes around detected faces
- **Console Output**: Face position and calculated angular velocity
- **Control Commands**: Published to `/cmd_vel` topic
- **Test Images**: Saved to `/tmp/face_detection_test_*.jpg` every 30 frames

### Method 4: Face Tracker Only (Testing without hardware)

For testing the face tracker logic without actual robot hardware:

```bash
# Start face tracker node only
ros2 run my_kachaka_apps face_tracker_node

# In another terminal, monitor robot commands being generated
ros2 topic echo /kachaka/manual_control/cmd_vel
```

## Parameters

The face tracker node accepts the following parameters:

- `turn_gain` (double, default: 0.004): Proportional gain for angular velocity control
- `dead_zone_percent` (int, default: 10): Dead zone width as percentage of image width

### Parameter Usage Examples

```bash
# Launch with custom parameters
ros2 launch my_kachaka_apps face_tracker.launch.py ip_address:=192.168.1.100 turn_gain:=0.006 dead_zone_percent:=15

# Or run node directly with parameters
ros2 run my_kachaka_apps face_tracker_node --ros-args -p turn_gain:=0.006 -p dead_zone_percent:=15
```

## Topics

### Subscribed Topics
- `/camera/color/image_raw` (sensor_msgs/msg/Image): RGB camera input from RealSense

### Published Topics  
- `/kachaka/manual_control/cmd_vel` (geometry_msgs/msg/Twist): Velocity commands to Kachaka robot

## Algorithm Details

### Face Detection
- Uses OpenCV's Haar Cascade classifier (`haarcascade_frontalface_default.xml`)
- Detects multiple faces and selects the largest one (closest person)
- Processes images at 10Hz for real-time performance

### Control Algorithm
1. Calculate face center X coordinate
2. Compute error: `error_x = face_center_x - image_center_x`
3. Check if error exceeds dead zone: `|error_x| > dead_zone_pixels`
4. If outside dead zone: `angular_velocity = -turn_gain * error_x`
5. Publish Twist message with calculated angular velocity

### Dead Zone Logic
- Dead zone prevents oscillation when face is approximately centered
- Dead zone width = `(dead_zone_percent / 100) * image_width / 2`
- Robot stops turning when face is within dead zone

## Troubleshooting

### RealSense package not found
```
ERROR: package 'realsense2_camera' not found
```
**Solution:**
```bash
# Install RealSense ROS2 package
sudo apt install ros-humble-realsense2-camera

# Or use alternative camera setup (see Method 2 above)
sudo apt install ros-humble-usb-cam
```

### No face detected
- Ensure adequate lighting
- Check if person is facing the camera
- Verify camera is publishing images: `ros2 topic echo /camera/color/image_raw --once`
- Try adjusting camera position/angle

### Robot not moving
- Check if Kachaka bridge is connected: `ros2 topic list | grep kachaka`
- Verify cmd_vel topic is being published: `ros2 topic echo /kachaka/manual_control/cmd_vel`
- Check robot is not in manual mode
- Verify IP address is correct: `ping <KACHAKA_IP>`

### OpenCV/cv_bridge errors
- Install required packages: `sudo apt install python3-opencv ros-humble-cv-bridge`
- If NumPy compatibility issues occur, try: `pip install numpy<2`
- Check ROS2 environment is properly sourced

### Launch file errors
- Ensure all required packages are installed
- Check ROS2 workspace is built and sourced
- Verify IP address format (e.g., `ip_address:=192.168.118.188`)

### Performance issues
- Reduce image resolution in camera launch parameters
- Adjust face detection parameters for your specific use case
- Check system CPU usage during operation

## Testing

### P-Control Logic Test
To test the face tracking control logic:

1. **Run the node:**
   ```bash
   ros2 run my_kachaka_apps face_tracker_node
   ```

2. **Test movements:**
   - Position yourself 1-2 meters from camera
   - Move face LEFT → Should see NEGATIVE angular velocity values
   - Move face RIGHT → Should see POSITIVE angular velocity values
   - Center face → Should see values near 0.000

### Expected Output Format
```
Face at [position] | Error: [±XXX]px | Angular vel: [±X.XXX] rad/s
```

### Control Command Verification
Monitor the `/cmd_vel` topic in a separate terminal:
```bash
ros2 topic echo /cmd_vel
```
Should show Twist messages with:
- `linear.x`: Always 0.0 (no forward movement)  
- `angular.z`: Calculated angular velocity based on face position

## Troubleshooting

### Common Issues

**Problem: No camera data received**
```
No face detected - angular velocity: 0.0  ← Continuous output
```
**Solution:**
- Verify camera topics exist: `ros2 topic list | grep camera`
- Check camera data: `ros2 topic echo /camera/camera/color/image_raw --once`

**Problem: No face detection**
- Ensure good lighting conditions
- Position face 1-2 meters from camera
- Face the camera directly

**Problem: Robot not responding**
- Check if `/cmd_vel` topic has subscribers: `ros2 topic info /cmd_vel`
- Verify robot is in correct control mode

### Parameter Tuning

**Optimized Parameters (Task 2-B Results):**
- `turn_gain`: 0.002 (reduced from 0.004 to prevent hunting/oscillation)
- `dead_zone_percent`: 20% (increased from 10% for better center stability)

**Dynamic Parameter Adjustment:**
```bash
# Real-time parameter tuning while node is running
ros2 param set /face_tracker_node turn_gain 0.002
ros2 param set /face_tracker_node dead_zone_percent 20

# Check current parameters
ros2 param get /face_tracker_node turn_gain
ros2 param get /face_tracker_node dead_zone_percent
```

**Custom Parameter Launch:**
```bash
# Launch with different parameters
ros2 run my_kachaka_apps face_tracker_node --ros-args -p turn_gain:=0.003 -p dead_zone_percent:=15
```


## Development Notes

This implementation follows the MVP (Minimum Viable Product) approach for Function 4.1 as specified in the project requirements:

- ✅ Face detection using OpenCV Haar Cascade
- ✅ P-controller for angular velocity
- ✅ Configurable parameters (turn_gain, dead_zone_percent)  
- ✅ ROS2 integration with proper QoS settings
- ✅ Launch file for easy system startup

Future enhancements could include:
- Multiple face tracking
- Distance-based approach behavior
- Integration with SLAM for position recording
- More robust face detection algorithms (e.g., DNN-based)
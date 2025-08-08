# Kachaka Mission System - Complete Integration Guide

## Overview

The Kachaka Mission System implements a complete speaker detection and following pipeline as specified in `specification.md`. The system uses a state machine to coordinate between patrolling, approaching detected persons, and close-range face tracking.

## System Architecture

```
[RealSense Camera] → [YOLO Detection] → [Mission Controller] → [Nav2 Navigation]
                                             ↓
[Face Tracker] ← [Mission Controller State Machine]
```

### State Machine Flow:
1. **PATROLLING**: Robot follows predefined waypoints using Nav2
2. **APPROACHING**: When YOLO detects person, robot navigates toward them
3. **TRACKING**: When close enough (< 1.5m), activates face tracker for close following

## Quick Start

### 1. Basic System Launch
```bash
cd ~/ws_kachaka
source install/setup.bash

# Launch complete system (camera + YOLO + mission controller + face tracker)
ros2 launch my_kachaka_apps mission_system.launch.py
```

### 2. Launch Options
```bash
# Launch without camera (use existing camera)
ros2 launch my_kachaka_apps mission_system.launch.py enable_camera:=false

# Launch with Nav2 navigation
ros2 launch my_kachaka_apps mission_system.launch.py enable_nav2:=true

# Custom YOLO model and threshold
ros2 launch my_kachaka_apps mission_system.launch.py yolo_model:=yolov8n.pt yolo_threshold:=0.6
```

### 3. Individual Component Testing
```bash
# Test YOLO detection only
ros2 launch yolo_bringup yolov8.launch.py

# Test face tracker only
ros2 run my_kachaka_apps face_tracker_node

# Test mission controller only
ros2 run my_kachaka_apps mission_controller
```

## System Components

### 1. YOLO Detection (`yolo_ros`)
- **Purpose**: Detect persons at long range (2m+)
- **Topics**: 
  - Subscribes: `/camera/camera/color/image_raw`
  - Publishes: `/yolo/detections`, `/yolo/dbg_image`
- **Configuration**: Uses YOLOv8m model, 50% confidence threshold

### 2. Face Tracker (`face_tracker_node`)
- **Purpose**: Close-range person following with distance control
- **Topics**:
  - Subscribes: `/camera/camera/color/image_raw`, `/camera/camera/depth/image_rect_raw`
  - Publishes: `/kachaka/manual_control/cmd_vel`
- **Control**: Activated/deactivated via `is_active` parameter

### 3. Mission Controller (`mission_controller`)
- **Purpose**: State machine coordination and navigation control
- **Topics**:
  - Subscribes: `/yolo/detections`, camera topics
  - Controls: Nav2 actions, face_tracker parameters
- **Features**: 2D→3D coordinate conversion, TF transformations

## Monitoring and Control

### Monitor System Status
```bash
# Check all running nodes
ros2 node list

# Monitor person detections
ros2 topic echo /yolo/detections

# Monitor robot control commands
ros2 topic echo /kachaka/manual_control/cmd_vel

# Check current state (look at mission_controller logs)
ros2 node info /mission_controller
```

### Parameter Control
```bash
# Mission Controller Parameters
ros2 param set /mission_controller approach_distance_threshold 2.0
ros2 param set /mission_controller person_lost_timeout 10.0
ros2 param set /mission_controller patrol_waypoints "[2.0,2.0,-2.0,2.0,-2.0,-2.0,2.0,-2.0]"

# Face Tracker Parameters
ros2 param set /face_tracker_node is_active false  # Disable tracking
ros2 param set /face_tracker_node is_active true   # Enable tracking
ros2 param set /face_tracker_node target_distance 0.8
ros2 param set /face_tracker_node turn_gain 0.002

# YOLO Parameters (if supported)
ros2 param list /yolo_node
```

### Manual Control Override
```bash
# Stop all autonomous movement
ros2 param set /face_tracker_node is_active false

# Manual teleop control
ros2 launch my_kachaka_apps teleop_keyboard.launch.py
# or
ros2 launch my_kachaka_apps teleop_joy.launch.py
```

## Testing Procedures

### Test 1: Component Integration
1. Start the complete system: `ros2 launch my_kachaka_apps mission_system.launch.py`
2. Check that all nodes are running: `ros2 node list`
3. Verify YOLO detections: `ros2 topic echo /yolo/detections`
4. Stand in front of camera and verify person detection in YOLO debug image

### Test 2: State Machine Transitions
1. Start system in PATROLLING mode
2. Walk into camera view → Should transition to APPROACHING
3. Walk close to robot → Should transition to TRACKING  
4. Walk away/hide → Should return to PATROLLING after timeout

### Test 3: Face Tracking Control
```bash
# Test is_active parameter control
python3 test_is_active.py

# Test mission controller
python3 test_mission_controller.py
```

## Troubleshooting

### Common Issues

**1. "No camera data"**
```bash
# Check camera status
ros2 topic list | grep camera
ros2 topic echo /camera/camera/color/image_raw --once

# Manually activate camera
ros2 lifecycle set /camera/camera configure
ros2 lifecycle set /camera/camera activate
```

**2. "No YOLO detections"**
```bash
# Check YOLO topics
ros2 topic echo /yolo/detections
ros2 topic echo /yolo/dbg_image

# Verify model file exists
ls -la ~/ws_kachaka/yolov8m.pt
```

**3. "Mission controller not working"**
```bash
# Check dependencies
ros2 pkg list | grep nav2
ros2 pkg list | grep yolo

# Check TF frames
ros2 run tf2_tools view_frames
```

**4. "Face tracker not responding"**
```bash
# Check is_active parameter
ros2 param get /face_tracker_node is_active

# Check control topic
ros2 topic echo /kachaka/manual_control/cmd_vel
```

### Debug Commands
```bash
# View all system parameters
ros2 param list /mission_controller
ros2 param list /face_tracker_node

# Check action servers (Nav2)
ros2 action list
ros2 action info /navigate_to_pose

# Monitor TF transforms
ros2 topic echo /tf
ros2 run tf2_ros tf2_echo map base_link
```

## Expected Behavior

### Normal Operation Sequence:
1. **System starts** → Mission controller initializes in PATROLLING state
2. **Person detected** → YOLO publishes detection, mission controller transitions to APPROACHING
3. **Navigation active** → Robot moves toward detected person using Nav2
4. **Close approach** → When < 1.5m from person, transitions to TRACKING
5. **Face tracking** → Face tracker takes control, maintains target distance
6. **Person lost** → After 5s timeout, returns to PATROLLING

### Visual Indicators:
- **OpenCV window**: Shows face detection results from face_tracker
- **YOLO debug**: Shows person detections with bounding boxes
- **Console logs**: State transitions and system status
- **Robot movement**: Smooth transitions between autonomous and tracking modes

## Performance Tuning

### For Better Detection:
```bash
# Lower YOLO threshold for more sensitive detection
ros2 launch my_kachaka_apps mission_system.launch.py yolo_threshold:=0.3

# Enable image enhancement for low light
ros2 param set /face_tracker_node enable_image_enhancement true
ros2 param set /face_tracker_node gamma_correction 2.0
```

### For Smoother Movement:
```bash
# Adjust face tracking gains
ros2 param set /face_tracker_node turn_gain 0.002
ros2 param set /face_tracker_node linear_gain 0.6
ros2 param set /face_tracker_node dead_zone_percent 20
```

### For Different Environments:
```bash
# Larger patrol area
ros2 param set /mission_controller patrol_waypoints "[3.0,3.0,-3.0,3.0,-3.0,-3.0,3.0,-3.0]"

# Longer approach distance
ros2 param set /mission_controller approach_distance_threshold 2.5
```

## System Integration Complete ✅

The mission system successfully implements all requirements from `specification.md`:

- ✅ **Task 1**: YOLO ROS integration for person detection
- ✅ **Task 2**: Face tracker external control via `is_active` parameter
- ✅ **Task 3**: Mission controller state machine (PATROLLING/APPROACHING/TRACKING)
- ✅ **Task 4**: 2D detection to 3D navigation coordinate conversion
- ✅ **Task 5**: Complete state transition logic and component integration
- ✅ **Task 6**: Comprehensive launch file for full system deployment

The system is ready for deployment and testing!
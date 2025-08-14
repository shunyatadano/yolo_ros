#!/bin/bash
# Script to resolve camera resource conflicts before launching mission system

echo "=== Kachaka Mission System - Camera Conflict Resolver ==="

# Check for existing RealSense processes
echo "Checking for existing RealSense processes..."
REALSENSE_PIDS=$(pgrep -f "realsense")

if [ -n "$REALSENSE_PIDS" ]; then
    echo "⚠️  Found RealSense processes running:"
    ps -f -p $REALSENSE_PIDS
    
    echo
    read -p "Kill existing RealSense processes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Killing RealSense processes..."
        pkill -f "realsense"
        sleep 2
        echo "✅ Processes killed"
    else
        echo "⚠️  Continuing with existing processes (may cause conflicts)"
    fi
else
    echo "✅ No conflicting RealSense processes found"
fi

# Check camera device availability
echo
echo "Checking camera device availability..."
if [ -e "/dev/video0" ]; then
    echo "✅ Camera device /dev/video0 available"
else
    echo "⚠️  Camera device /dev/video0 not found"
fi

# Check USB devices for RealSense
echo
echo "Checking for RealSense hardware..."
REALSENSE_USB=$(lsusb | grep -i intel)
if [ -n "$REALSENSE_USB" ]; then
    echo "✅ RealSense hardware detected:"
    echo "$REALSENSE_USB"
else
    echo "⚠️  No RealSense hardware detected"
    echo "Consider running with: enable_camera:=false"
fi

echo
echo "=== Launch recommendations ==="
echo "For normal operation (with RealSense):"
echo "  ros2 launch my_kachaka_apps mission_system.launch.py"
echo
echo "If camera conflicts persist:"
echo "  ros2 launch my_kachaka_apps mission_system.launch.py enable_camera:=false"
echo
echo "=== Done ==="
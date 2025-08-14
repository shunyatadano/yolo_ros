#!/usr/bin/env python3
"""
Script to check for camera resource conflicts before launching
"""
import subprocess
import sys
import os

def check_realsense_processes():
    """Check if RealSense processes are already running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'realsense'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"Warning: Found {len(pids)} RealSense processes running:")
            for pid in pids:
                ps_result = subprocess.run(['ps', '-p', pid, '-o', 'pid,cmd'], 
                                         capture_output=True, text=True)
                print(f"  {ps_result.stdout.strip().split(chr(10))[-1]}")
            return True
        return False
    except Exception as e:
        print(f"Error checking processes: {e}")
        return False

def check_camera_topics():
    """Check if camera topics are already being published"""
    try:
        result = subprocess.run(['ros2', 'topic', 'list'], 
                              capture_output=True, text=True, timeout=5)
        topics = result.stdout.strip().split('\n')
        camera_topics = [t for t in topics if '/camera/camera' in t]
        if camera_topics:
            print(f"Warning: Found {len(camera_topics)} camera topics already active:")
            for topic in camera_topics[:5]:  # Show first 5
                print(f"  {topic}")
            return True
        return False
    except Exception as e:
        print(f"Error checking topics: {e}")
        return False

def main():
    print("Checking for camera resource conflicts...")
    
    has_processes = check_realsense_processes()
    has_topics = check_camera_topics()
    
    if has_processes or has_topics:
        print("\n⚠️  Camera resource conflict detected!")
        print("Recommendations:")
        print("1. Kill existing camera processes: pkill -f realsense")
        print("2. Or run with camera disabled: enable_camera:=false")
        print("3. Or use Kachaka's built-in cameras instead")
        return 1
    else:
        print("✅ No camera conflicts detected. Safe to launch.")
        return 0

if __name__ == '__main__':
    sys.exit(main())
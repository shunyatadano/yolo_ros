#!/usr/bin/env python3
"""
Simple RealSense connection test
"""
import pyrealsense2 as rs

print("Testing RealSense connection...")

try:
    # Create a context object. This object owns the handles to all connected realsense devices
    ctx = rs.context()
    
    # Get a snapshot of currently connected devices
    devices = ctx.query_devices()
    
    print(f"Found {len(devices)} RealSense device(s)")
    
    if len(devices) == 0:
        print("No RealSense devices found!")
        exit(1)
    
    for i, device in enumerate(devices):
        print(f"Device {i}:")
        print(f"  Name: {device.get_info(rs.camera_info.name)}")
        print(f"  Serial: {device.get_info(rs.camera_info.serial_number)}")
        print(f"  Product ID: {device.get_info(rs.camera_info.product_id)}")
        
        # Check available sensors
        sensors = device.query_sensors()
        print(f"  Available sensors: {len(sensors)}")
        for j, sensor in enumerate(sensors):
            print(f"    Sensor {j}: {sensor.get_info(rs.camera_info.name)}")
    
    # Try to create pipeline
    print("\nTesting pipeline creation...")
    pipeline = rs.pipeline()
    config = rs.config()
    
    # Configure streams
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    
    # Start streaming
    pipeline.start(config)
    print("Pipeline started successfully!")
    
    # Get a few frames
    for i in range(5):
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        print(f"Frame {i}: depth={depth_frame is not None}, color={color_frame is not None}")
    
    pipeline.stop()
    print("Pipeline stopped successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
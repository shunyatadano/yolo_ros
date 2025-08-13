#!/usr/bin/env python3
"""
Test Script for PATROLLING Mode

This script helps test the isolated PATROLLING functionality including:
- Waypoint navigation
- Person detection visualization
- System monitoring

Usage:
    python3 test_patrol_mode.py <KACHAKA_IP>

Example:
    python3 test_patrol_mode.py 192.168.118.95
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path


class PatrolTestManager:
    def __init__(self, kachaka_ip):
        self.kachaka_ip = kachaka_ip
        self.processes = []
        self.test_active = False
        
    def print_header(self):
        """Print test header information."""
        print("=" * 60)
        print("🤖 KACHAKA PATROLLING MODE TEST")
        print("=" * 60)
        print(f"Target Robot: {self.kachaka_ip}")
        print(f"Test Components:")
        print(f"  ✓ Nav2 Navigation Stack")
        print(f"  ✓ Simple Patrol Node (waypoint navigation)")
        print(f"  ✓ YOLO Person Detection")
        print(f"  ✓ Person Detection Visualizer")
        print(f"  ✓ RViz2 Visualization")
        print("=" * 60)
        
    def check_prerequisites(self):
        """Check if required components are available."""
        print("🔍 Checking prerequisites...")
        
        # Check if workspace is built
        install_path = Path("~/ws_kachaka/install").expanduser()
        if not install_path.exists():
            print("❌ Workspace not built. Please run:")
            print("   cd ~/ws_kachaka && colcon build")
            return False
            
        # Check if gRPC bridge script exists
        bridge_script = Path("~/kachaka-api/tools/ros2_bridge/start_bridge.sh").expanduser()
        if not bridge_script.exists():
            print("❌ gRPC bridge script not found. Please check kachaka-api installation.")
            return False
            
        print("✅ Prerequisites OK")
        return True
        
    def start_grpc_bridge(self):
        """Start the Kachaka gRPC bridge."""
        print(f"🌉 Starting gRPC bridge for {self.kachaka_ip}...")
        
        bridge_dir = Path("~/kachaka-api/tools/ros2_bridge").expanduser()
        env = os.environ.copy()
        env['RMW_IMPLEMENTATION'] = 'rmw_fastrtps_cpp'
        env['ROS_DOMAIN_ID'] = '0'
        
        try:
            process = subprocess.Popen(
                ['sudo', '-E', './start_bridge.sh', f"{self.kachaka_ip}:26400"],
                cwd=bridge_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(('grpc_bridge', process))
            
            print("⏳ Waiting for gRPC bridge to initialize...")
            time.sleep(10)  # Give bridge time to start
            
            if process.poll() is None:
                print("✅ gRPC bridge started successfully")
                return True
            else:
                print("❌ gRPC bridge failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start gRPC bridge: {e}")
            return False
    
    def start_patrol_test(self):
        """Start the patrol test launch file."""
        print("🚁 Starting PATROLLING test mode...")
        
        ws_dir = Path("~/ws_kachaka").expanduser()
        env = os.environ.copy()
        env['ROS_DOMAIN_ID'] = '0'
        
        # Source workspace
        source_cmd = f"source {ws_dir}/install/setup.bash && "
        launch_cmd = "ros2 launch my_kachaka_apps patrol_test.launch.py"
        full_cmd = source_cmd + launch_cmd
        
        try:
            process = subprocess.Popen(
                full_cmd,
                shell=True,
                cwd=ws_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            self.processes.append(('patrol_test', process))
            
            print("⏳ Waiting for patrol system to initialize...")
            time.sleep(5)
            
            if process.poll() is None:
                print("✅ Patrol test system started successfully")
                return True
            else:
                print("❌ Patrol test system failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start patrol test: {e}")
            return False
    
    def monitor_system(self):
        """Monitor the running system and provide status updates."""
        print("\n📊 System Status Monitor")
        print("Press Ctrl+C to stop the test")
        print("-" * 40)
        
        try:
            while self.test_active:
                self.print_status()
                time.sleep(10)  # Update every 10 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
    
    def print_status(self):
        """Print current system status."""
        print(f"⏰ {time.strftime('%H:%M:%S')} - System Status:")
        
        # Check process status
        for name, process in self.processes:
            if process.poll() is None:
                print(f"  ✅ {name}: Running")
            else:
                print(f"  ❌ {name}: Stopped")
        
        print("  📡 Monitor topics:")
        print("    ros2 topic echo /yolo/detections")
        print("    ros2 topic echo /simple_patrol_node/current_goal")
        print("    ros2 topic echo /person_detection_markers")
        print()
    
    def cleanup(self):
        """Clean up all processes."""
        print("🧹 Cleaning up processes...")
        
        for name, process in self.processes:
            if process.poll() is None:
                print(f"  Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"  Force killing {name}...")
                    process.kill()
        
        print("✅ Cleanup complete")
    
    def run_test(self):
        """Run the complete patrol test."""
        self.print_header()
        
        if not self.check_prerequisites():
            return False
        
        # Set up signal handler for clean shutdown
        def signal_handler(sig, frame):
            self.test_active = False
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # Start gRPC bridge
            if not self.start_grpc_bridge():
                return False
            
            # Start patrol test
            if not self.start_patrol_test():
                return False
            
            print("\n🎯 PATROLLING Test Ready!")
            print("Expected behavior:")
            print("  1. Robot should navigate between waypoints")
            print("  2. Person detections should appear as markers in RViz")
            print("  3. Patrol node should log detected persons")
            print("\nIn RViz, you should see:")
            print("  - Map and robot model")
            print("  - Person detection markers (cylinders)")
            print("  - Navigation goals and paths")
            
            self.test_active = True
            self.monitor_system()
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
        
        finally:
            self.cleanup()
        
        return True


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_patrol_mode.py <KACHAKA_IP>")
        print("Example: python3 test_patrol_mode.py 192.168.118.95")
        sys.exit(1)
    
    kachaka_ip = sys.argv[1]
    test_manager = PatrolTestManager(kachaka_ip)
    
    success = test_manager.run_test()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
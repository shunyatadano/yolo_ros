#!/usr/bin/env python3
"""
Test script for audio source visualization
Runs the audio visualizer and shows instructions for testing
"""

import subprocess
import sys
import time

def main():
    print("🎵 Audio Source Visualization Test")
    print("=" * 50)
    print()
    
    print("This script will help you test the audio source visualization.")
    print("Make sure you have:")
    print("1. ✅ ODAS running with your ReSpeaker 4 Mic Array")
    print("2. ✅ Audio sources available (play music, speak, etc.)")
    print("3. ✅ RViz ready for visualization")
    print()
    
    response = input("Ready to start? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return
    
    print("\n🚀 Starting audio visualization...")
    print("You should see:")
    print("- Green/yellow spheres for active sound sources (SST)")
    print("- Blue spheres for potential sources (SSL)")  
    print("- Text labels showing source info")
    print("- Sources projected onto the map within 3m range")
    print()
    
    try:
        # Source the workspace and run the launch file
        cmd = [
            "bash", "-c",
            "source install/setup.bash && ros2 launch my_kachaka_apps audio_mapping.launch.py"
        ]
        
        print("Launching audio mapping system...")
        print("Command:", " ".join(cmd))
        print()
        print("🔍 Check RViz for audio source visualization!")
        print("Press Ctrl+C to stop when done testing.")
        print()
        
        subprocess.run(cmd, cwd="/home/reazon/ws_kachaka")
        
    except KeyboardInterrupt:
        print("\n✅ Test completed!")
        print()
        print("📊 Expected results:")
        print("- Audio sources appear as colored spheres in RViz")
        print("- SST sources (tracked) show as green/yellow with activity levels")
        print("- SSL sources (potential) show as blue with energy levels")
        print("- Text labels provide source information")
        print()
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Make sure:")
        print("1. ODAS is running and detecting audio")
        print("2. Workspace is built: colcon build")
        print("3. Environment is sourced: source install/setup.bash")

if __name__ == "__main__":
    main()
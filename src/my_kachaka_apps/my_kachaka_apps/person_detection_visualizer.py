#!/usr/bin/env python3
"""
Person Detection Visualizer Node

This node visualizes detected persons on the map using RViz markers.
It subscribes to YOLO detections and creates visualization markers.

Author: Generated for Kachaka Mission System Testing
"""

import rclpy
from rclpy.node import Node
from yolo_msgs.msg import DetectionArray
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point, Vector3
from std_msgs.msg import ColorRGBA
from tf2_ros import Buffer, TransformListener
import tf2_geometry_msgs
import math
import time


class PersonDetectionVisualizer(Node):
    def __init__(self):
        super().__init__('person_detection_visualizer')
        
        # Parameters
        self.declare_parameter('marker_lifetime', 10.0)
        self.declare_parameter('detection_topic', '/yolo/detections')
        self.declare_parameter('marker_topic', '/person_detection_markers')
        self.declare_parameter('camera_frame', 'camera_color_frame')
        self.declare_parameter('map_frame', 'map')
        
        self.marker_lifetime = self.get_parameter('marker_lifetime').value
        self.detection_topic = self.get_parameter('detection_topic').value
        self.marker_topic = self.get_parameter('marker_topic').value
        self.camera_frame = self.get_parameter('camera_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        
        # TF2 buffer and listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Publishers
        self.marker_pub = self.create_publisher(
            MarkerArray, self.marker_topic, 10
        )
        
        # Subscribers
        self.detection_sub = self.create_subscription(
            DetectionArray, self.detection_topic,
            self.detection_callback, 10
        )
        
        # State variables
        self.marker_id_counter = 0
        self.active_markers = {}
        
        # Timer for marker cleanup
        self.cleanup_timer = self.create_timer(1.0, self.cleanup_expired_markers)
        
        self.get_logger().info(
            f'Person Detection Visualizer initialized\n'
            f'  Listening to: {self.detection_topic}\n'
            f'  Publishing to: {self.marker_topic}\n'
            f'  Marker lifetime: {self.marker_lifetime}s'
        )
    
    def detection_callback(self, msg):
        """Process detection messages and create visualization markers."""
        if not msg.detections:
            return
        
        current_time = self.get_clock().now()
        marker_array = MarkerArray()
        
        for detection in msg.detections:
            # Check if this detection contains persons
            persons = []
            for result in detection.results:
                if result.hypothesis.class_id == 'person':
                    persons.append(result)
            
            if not persons:
                continue
            
            # Try to get transform from camera to map
            try:
                transform = self.tf_buffer.lookup_transform(
                    self.map_frame,
                    self.camera_frame,
                    rclpy.time.Time()
                )
            except Exception as e:
                self.get_logger().warn(
                    f'Could not get transform from {self.camera_frame} to {self.map_frame}: {e}'
                )
                # Use identity transform as fallback (assume camera is at origin)
                transform = None
            
            # Create markers for each person detection
            for person in persons:
                marker = self.create_person_marker(
                    detection, person, transform, current_time
                )
                if marker:
                    marker_array.markers.append(marker)
                    
                    # Store marker info for cleanup
                    self.active_markers[marker.id] = {
                        'timestamp': current_time,
                        'marker': marker
                    }
        
        # Publish markers
        if marker_array.markers:
            self.marker_pub.publish(marker_array)
            self.get_logger().debug(f'Published {len(marker_array.markers)} person markers')
    
    def create_person_marker(self, detection, person_result, transform, timestamp):
        """Create a visualization marker for a detected person."""
        marker = Marker()
        marker.header.frame_id = self.map_frame
        marker.header.stamp = timestamp.to_msg()
        marker.ns = "detected_persons"
        marker.id = self.marker_id_counter
        marker.type = Marker.CYLINDER
        marker.action = Marker.ADD
        
        # Calculate position
        if transform:
            # Use transform to place marker in map frame
            # For simplicity, assume person is 2m in front of camera
            camera_point = Point()
            camera_point.x = 2.0  # Assume 2m distance
            camera_point.y = 0.0
            camera_point.z = 0.0
            
            try:
                # Transform point to map frame
                map_point = tf2_geometry_msgs.do_transform_point(camera_point, transform)
                marker.pose.position = map_point.point
            except Exception as e:
                self.get_logger().warn(f'Transform error: {e}')
                # Fallback to camera frame position
                marker.pose.position.x = 2.0
                marker.pose.position.y = 0.0
                marker.pose.position.z = 0.0
        else:
            # Fallback: place marker at fixed position
            marker.pose.position.x = 2.0
            marker.pose.position.y = 0.0
            marker.pose.position.z = 0.0
        
        # Set orientation
        marker.pose.orientation.w = 1.0
        
        # Set scale (cylinder representing person)
        marker.scale.x = 0.3  # Diameter
        marker.scale.y = 0.3  # Diameter  
        marker.scale.z = 1.7  # Height (typical person height)
        
        # Set color based on confidence
        confidence = person_result.hypothesis.score
        marker.color = self.confidence_to_color(confidence)
        
        # Set lifetime
        marker.lifetime.sec = int(self.marker_lifetime)
        marker.lifetime.nanosec = int((self.marker_lifetime - int(self.marker_lifetime)) * 1e9)
        
        # Add text with confidence
        text_marker = Marker()
        text_marker.header = marker.header
        text_marker.ns = "person_labels"
        text_marker.id = self.marker_id_counter + 10000  # Offset to avoid ID conflicts
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD
        text_marker.pose = marker.pose
        text_marker.pose.position.z += 2.0  # Place text above cylinder
        text_marker.scale.z = 0.3  # Text size
        text_marker.color.r = 1.0
        text_marker.color.g = 1.0
        text_marker.color.b = 1.0
        text_marker.color.a = 1.0
        text_marker.text = f"Person\n{confidence:.2f}"
        text_marker.lifetime = marker.lifetime
        
        self.marker_id_counter += 1
        
        return marker
    
    def confidence_to_color(self, confidence):
        """Convert detection confidence to color (green=high, red=low)."""
        color = ColorRGBA()
        
        # Interpolate between red (low confidence) and green (high confidence)
        color.r = max(0.0, 2.0 * (1.0 - confidence))  # Red component
        color.g = max(0.0, 2.0 * confidence - 1.0) if confidence > 0.5 else 2.0 * confidence
        color.b = 0.2  # Small blue component
        color.a = 0.8  # Semi-transparent
        
        return color
    
    def cleanup_expired_markers(self):
        """Remove expired markers from visualization."""
        current_time = self.get_clock().now()
        expired_ids = []
        
        for marker_id, marker_info in self.active_markers.items():
            age = (current_time - marker_info['timestamp']).nanoseconds / 1e9
            if age > self.marker_lifetime:
                expired_ids.append(marker_id)
        
        # Remove expired markers
        if expired_ids:
            delete_markers = MarkerArray()
            for marker_id in expired_ids:
                # Create delete marker for person
                delete_marker = Marker()
                delete_marker.header.frame_id = self.map_frame
                delete_marker.header.stamp = current_time.to_msg()
                delete_marker.ns = "detected_persons"
                delete_marker.id = marker_id
                delete_marker.action = Marker.DELETE
                delete_markers.markers.append(delete_marker)
                
                # Create delete marker for label
                delete_label = Marker()
                delete_label.header = delete_marker.header
                delete_label.ns = "person_labels"
                delete_label.id = marker_id + 10000
                delete_label.action = Marker.DELETE
                delete_markers.markers.append(delete_label)
                
                # Remove from tracking
                del self.active_markers[marker_id]
            
            self.marker_pub.publish(delete_markers)
            self.get_logger().debug(f'Cleaned up {len(expired_ids)} expired markers')


def main(args=None):
    rclpy.init(args=args)
    node = PersonDetectionVisualizer()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Person Detection Visualizer interrupted by user")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Audio Source Visualizer Node

This node subscribes to ODAS audio source tracking data and publishes
visualization markers to display sound sources on the Kachaka map in RViz.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import tf2_ros
import tf2_geometry_msgs
from geometry_msgs.msg import PointStamped, Point, Vector3
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA, Header
from odas_ros_msgs.msg import OdasSstArrayStamped, OdasSslArrayStamped
import math
from typing import Dict, List


class AudioSourceVisualizer(Node):
    """Visualizes audio sources from ODAS on the robot map"""
    
    def __init__(self):
        super().__init__('audio_source_visualizer')
        
        # Parameters
        self.declare_parameter('odas_frame', 'base_link')  # Use base_link since odas frame may not exist
        self.declare_parameter('map_frame', 'base_link')  # Use base_link since map may not exist
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('max_range', 3.0)  # Max range to project audio sources (meters)
        self.declare_parameter('marker_size', 0.2)  # Size of visualization markers
        self.declare_parameter('activity_threshold', 0.1)  # Minimum activity to show SST sources
        
        self.odas_frame = self.get_parameter('odas_frame').value
        self.map_frame = self.get_parameter('map_frame').value  
        self.base_frame = self.get_parameter('base_frame').value
        self.max_range = self.get_parameter('max_range').value
        self.marker_size = self.get_parameter('marker_size').value
        self.activity_threshold = self.get_parameter('activity_threshold').value
        
        # TF2 buffer and listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # QoS profile for audio topics
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribers
        self.sst_sub = self.create_subscription(
            OdasSstArrayStamped,
            '/sst',
            self.sst_callback,
            qos_profile
        )
        
        self.ssl_sub = self.create_subscription(
            OdasSslArrayStamped,
            '/ssl', 
            self.ssl_callback,
            qos_profile
        )
        
        # Publishers
        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/audio_sources/markers',
            10
        )
        
        # Store current audio sources
        self.sst_sources: Dict[int, any] = {}
        self.ssl_sources: List[any] = []
        
        # Marker ID counter
        self.marker_id = 0
        
        self.get_logger().info("Audio Source Visualizer initialized")
        
    def sst_callback(self, msg: OdasSstArrayStamped):
        """Process sound source tracking data"""
        self.sst_sources.clear()
        
        for source in msg.sources:
            if source.activity > self.activity_threshold:
                self.sst_sources[source.id] = {
                    'position': [source.x, source.y, source.z],
                    'activity': source.activity,
                    'timestamp': msg.header.stamp
                }
        
        self.publish_markers(msg.header)
        
    def ssl_callback(self, msg: OdasSslArrayStamped):
        """Process sound source localization data"""
        self.ssl_sources = []
        
        for source in msg.sources:
            self.ssl_sources.append({
                'position': [source.x, source.y, source.z],
                'energy': source.e,
                'timestamp': msg.header.stamp
            })
        
        # SSL updates more frequently, only update if we don't have recent SST data
        if not self.sst_sources:
            self.publish_markers(msg.header)
    
    def sphere_to_cartesian(self, unit_vector: List[float], max_range: float) -> List[float]:
        """Convert unit sphere coordinates to cartesian coordinates at max range"""
        x, y, z = unit_vector
        return [x * max_range, y * max_range, z * max_range]
    
    def transform_point_to_map(self, point: List[float], source_frame: str) -> Point:
        """Transform a point from source frame to map frame"""
        try:
            # Create point in source frame
            point_stamped = PointStamped()
            point_stamped.header.frame_id = source_frame
            point_stamped.header.stamp = self.get_clock().now().to_msg()
            point_stamped.point.x = float(point[0])
            point_stamped.point.y = float(point[1])
            point_stamped.point.z = float(point[2])
            
            # Transform to map frame
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                source_frame,
                rclpy.time.Time()
            )
            
            transformed_point = tf2_geometry_msgs.do_transform_point(point_stamped, transform)
            return transformed_point.point
            
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            self.get_logger().warn(f"Failed to transform point: {e}")
            return Point(x=float(point[0]), y=float(point[1]), z=float(point[2]))
    
    def create_sphere_marker(self, position: Point, color: ColorRGBA, marker_id: int, 
                           scale: float = None, frame_id: str = None) -> Marker:
        """Create a sphere marker for visualization"""
        marker = Marker()
        marker.header.frame_id = frame_id or self.map_frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "audio_sources"
        marker.id = marker_id
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        
        marker.pose.position = position
        marker.pose.orientation.w = 1.0
        
        size = scale or self.marker_size
        marker.scale = Vector3(x=size, y=size, z=size)
        marker.color = color
        
        return marker
    
    def create_text_marker(self, position: Point, text: str, marker_id: int, 
                          frame_id: str = None) -> Marker:
        """Create a text marker for labels"""
        marker = Marker()
        marker.header.frame_id = frame_id or self.map_frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "audio_labels"
        marker.id = marker_id
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        
        # Position text slightly above the sphere
        marker.pose.position.x = position.x
        marker.pose.position.y = position.y  
        marker.pose.position.z = position.z + 0.3
        marker.pose.orientation.w = 1.0
        
        marker.scale.z = 0.1  # Text height
        marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)  # White text
        marker.text = text
        
        return marker
    
    def publish_markers(self, header: Header):
        """Publish visualization markers for audio sources"""
        markers = MarkerArray()
        self.marker_id = 0
        
        # Clear previous markers
        clear_marker = Marker()
        clear_marker.header = header
        clear_marker.header.frame_id = self.map_frame
        clear_marker.ns = "audio_sources"
        clear_marker.action = Marker.DELETEALL
        markers.markers.append(clear_marker)
        
        clear_text_marker = Marker()
        clear_text_marker.header = header
        clear_text_marker.header.frame_id = self.map_frame  
        clear_text_marker.ns = "audio_labels"
        clear_text_marker.action = Marker.DELETEALL
        markers.markers.append(clear_text_marker)
        
        # Add SST markers (tracked sources)
        for source_id, source_data in self.sst_sources.items():
            # Convert unit sphere to cartesian coordinates
            cart_pos = self.sphere_to_cartesian(source_data['position'], self.max_range)
            
            # Transform to map coordinates
            map_position = self.transform_point_to_map(cart_pos, self.odas_frame)
            
            # Color based on activity (green = active, yellow = less active)
            activity = source_data['activity']
            color = ColorRGBA()
            color.r = min(1.0, 2.0 * (1.0 - activity))  # Red component decreases with activity
            color.g = min(1.0, 2.0 * activity)          # Green component increases with activity
            color.b = 0.0
            color.a = 0.8
            
            # Scale marker size based on activity
            scale = self.marker_size * (0.5 + activity)
            
            # Create sphere marker
            marker = self.create_sphere_marker(map_position, color, self.marker_id, scale)
            markers.markers.append(marker)
            
            # Create text label
            label = f"SST-{source_id}\nActivity: {activity:.2f}"
            text_marker = self.create_text_marker(map_position, label, self.marker_id + 1000)
            markers.markers.append(text_marker)
            
            self.marker_id += 1
        
        # Add SSL markers (potential sources) if no SST data
        if not self.sst_sources:
            for i, source_data in enumerate(self.ssl_sources[:5]):  # Limit to top 5
                # Convert unit sphere to cartesian coordinates  
                cart_pos = self.sphere_to_cartesian(source_data['position'], self.max_range)
                
                # Transform to map coordinates
                map_position = self.transform_point_to_map(cart_pos, self.odas_frame)
                
                # Color based on energy (blue tones)
                energy = source_data['energy']
                color = ColorRGBA()
                color.r = 0.0
                color.g = 0.3
                color.b = min(1.0, energy * 5.0)  # Scale energy for visibility
                color.a = 0.6
                
                # Create sphere marker
                marker = self.create_sphere_marker(map_position, color, self.marker_id, 
                                                 self.marker_size * 0.7)
                markers.markers.append(marker)
                
                # Create text label
                label = f"SSL-{i}\nEnergy: {energy:.3f}"
                text_marker = self.create_text_marker(map_position, label, self.marker_id + 1000)
                markers.markers.append(text_marker)
                
                self.marker_id += 1
        
        # Publish markers
        self.marker_pub.publish(markers)
        
        # Log current sources
        if self.sst_sources:
            self.get_logger().info(f"Visualizing {len(self.sst_sources)} SST sources")
        elif self.ssl_sources:
            self.get_logger().info(f"Visualizing {min(5, len(self.ssl_sources))} SSL sources")


def main(args=None):
    rclpy.init(args=args)
    
    node = AudioSourceVisualizer()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
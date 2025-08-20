from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Float, ForeignKey, Index, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tracking(Base):
    """Tracking model for storing object tracking data across frames."""
    
    __tablename__ = "tracking"
    
    # Primary key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Camera and track identification
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    track_id = Column(BigInteger, nullable=False, index=True)  # Unique track ID per camera
    
    # Object information
    object_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    
    # Temporal information
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)  # When track was first created
    last_seen = Column(DateTime(timezone=True), nullable=True)   # When track was last updated
    
    # Spatial information (bounding box coordinates)
    location = Column(JSON, nullable=True)  # {"x1": 100, "y1": 50, "x2": 200, "y2": 150}
    center_x = Column(Float, nullable=True)  # Center point X for quick queries
    center_y = Column(Float, nullable=True)  # Center point Y for quick queries
    
    # Track metadata
    track_status = Column(String(20), default="active", nullable=False)  # active, lost, terminated
    frames_tracked = Column(BigInteger, default=1, nullable=False)  # Number of frames this track appeared
    frames_lost = Column(BigInteger, default=0, nullable=False)    # Number of consecutive frames track was lost
    
    # Movement information
    velocity = Column(JSON, nullable=True)     # {"vx": 5.2, "vy": -1.8} pixels per frame
    direction = Column(Float, nullable=True)   # Direction in degrees (0-360)
    distance_traveled = Column(Float, nullable=True)  # Total distance traveled in pixels
    
    # Additional tracking data
    attributes = Column(JSON, nullable=True)   # Additional object attributes
    
    # Processing metadata
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    camera = relationship("Camera", back_populates="tracking_data")
    
    # Indexes for better performance
    __table_args__ = (
        Index("idx_tracking_camera_track", "camera_id", "track_id"),
        Index("idx_tracking_camera_timestamp", "camera_id", "timestamp"),
        Index("idx_tracking_object_type", "object_type"),
        Index("idx_tracking_status", "track_status"),
    )
    
    def __repr__(self) -> str:
        return f"<Tracking(id={self.id}, camera_id='{self.camera_id}', track_id={self.track_id}, object_type='{self.object_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracking to dictionary."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "object_type": self.object_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "location": self.location,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "track_status": self.track_status,
            "frames_tracked": self.frames_tracked,
            "frames_lost": self.frames_lost,
            "velocity": self.velocity,
            "direction": self.direction,
            "distance_traveled": self.distance_traveled,
            "attributes": self.attributes,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
    
    @classmethod
    def parse_ros2_tracking(cls, camera_id: str, timestamp: datetime, raw_data: str) -> List["Tracking"]:
        """
        Parse ROS2 tracking string and create Tracking objects.
        
        Example input: "[HotelLobby] 1:person:0.85,2:car:0.92"
        """
        tracking_objects = []
        
        if raw_data and "]" in raw_data:
            # Extract tracking part after camera_id
            tracking_part = raw_data.split("]", 1)[1].strip()
            
            # Parse individual tracks
            for track_data in tracking_part.split(","):
                track_data = track_data.strip()
                if ":" in track_data:
                    parts = track_data.split(":")
                    if len(parts) >= 3:
                        try:
                            track_id = int(parts[0])
                            object_type = parts[1]
                            confidence = float(parts[2])
                            
                            tracking_obj = cls(
                                camera_id=camera_id,
                                track_id=track_id,
                                object_type=object_type,
                                confidence=confidence,
                                timestamp=timestamp,
                                first_seen=timestamp,
                                last_seen=timestamp,
                            )
                            tracking_objects.append(tracking_obj)
                            
                        except (ValueError, IndexError):
                            continue
        
        return tracking_objects
    
    def update_location(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Update object location with bounding box coordinates."""
        self.location = {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "width": x2 - x1,
            "height": y2 - y1
        }
        
        # Update center coordinates
        self.center_x = (x1 + x2) / 2
        self.center_y = (y1 + y2) / 2
    
    def calculate_velocity(self, prev_track: "Tracking") -> None:
        """Calculate velocity based on previous track position."""
        if not prev_track or not self.center_x or not self.center_y:
            return
        
        if not prev_track.center_x or not prev_track.center_y:
            return
        
        # Calculate time difference
        time_diff = (self.timestamp - prev_track.timestamp).total_seconds()
        if time_diff <= 0:
            return
        
        # Calculate velocity (pixels per second)
        dx = self.center_x - prev_track.center_x
        dy = self.center_y - prev_track.center_y
        
        vx = dx / time_diff
        vy = dy / time_diff
        
        self.velocity = {"vx": vx, "vy": vy}
        
        # Calculate direction (degrees)
        import math
        self.direction = math.degrees(math.atan2(dy, dx))
        if self.direction < 0:
            self.direction += 360
    
    def update_distance_traveled(self, prev_track: "Tracking") -> None:
        """Update total distance traveled."""
        if not prev_track or not self.center_x or not self.center_y:
            return
        
        if not prev_track.center_x or not prev_track.center_y:
            return
        
        # Calculate distance moved
        import math
        dx = self.center_x - prev_track.center_x
        dy = self.center_y - prev_track.center_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Add to total distance
        prev_distance = prev_track.distance_traveled or 0
        self.distance_traveled = prev_distance + distance
    
    @property
    def is_active(self) -> bool:
        """Check if track is currently active."""
        return self.track_status == "active"
    
    @property
    def is_lost(self) -> bool:
        """Check if track is lost."""
        return self.track_status == "lost"
    
    @property
    def age_seconds(self) -> float:
        """Get track age in seconds."""
        if not self.first_seen:
            return 0.0
        
        end_time = self.last_seen or datetime.utcnow()
        start_time = self.first_seen.replace(tzinfo=None) if self.first_seen.tzinfo else self.first_seen
        end_time = end_time.replace(tzinfo=None) if hasattr(end_time, 'tzinfo') and end_time.tzinfo else end_time
        
        return (end_time - start_time).total_seconds()
    
    @property
    def tracking_duration(self) -> float:
        """Get total tracking duration in seconds."""
        return self.age_seconds
    
    @property
    def average_confidence(self) -> float:
        """Get average confidence (would need to calculate from all track points)."""
        return self.confidence  # Simplified - could be enhanced with historical data
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a custom attribute."""
        if not self.attributes:
            self.attributes = {}
        self.attributes[key] = value
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a custom attribute."""
        if not self.attributes:
            return default
        return self.attributes.get(key, default)


class TrackingSummary(Base):
    """Summary table for tracking statistics."""
    
    __tablename__ = "tracking_summaries"
    
    id = Column(BigInteger, primary_key=True, index=True)
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(10), nullable=False)  # 'hour', 'day', 'week', 'month'
    
    # Track statistics
    total_tracks = Column(BigInteger, default=0, nullable=False)
    active_tracks = Column(BigInteger, default=0, nullable=False)
    completed_tracks = Column(BigInteger, default=0, nullable=False)
    lost_tracks = Column(BigInteger, default=0, nullable=False)
    
    # Object type statistics
    object_type_counts = Column(JSON, nullable=True)  # Count per object type
    person_tracks = Column(BigInteger, default=0, nullable=False)
    
    # Movement statistics
    avg_track_duration = Column(Float, nullable=True)
    max_track_duration = Column(Float, nullable=True)
    avg_distance_traveled = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    camera = relationship("Camera")
    
    def __repr__(self) -> str:
        return f"<TrackingSummary(camera_id='{self.camera_id}', period='{self.period_type}', tracks={self.total_tracks})>"
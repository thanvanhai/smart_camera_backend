from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Camera(Base):
    """Camera model for storing camera information and configuration."""
    
    __tablename__ = "cameras"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Camera identification
    camera_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Location information
    location = Column(String(200), nullable=True)
    zone = Column(String(50), nullable=True)  # e.g., "lobby", "parking", "entrance"
    floor = Column(String(20), nullable=True)
    building = Column(String(100), nullable=True)
    
    # Camera status and configuration
    status = Column(String(20), default="active", nullable=False)  # active, inactive, maintenance, error
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Technical configuration
    config = Column(JSON, nullable=True)  # Camera-specific configuration
    stream_url = Column(String(500), nullable=True)  # Stream URL if available
    resolution = Column(String(20), nullable=True)  # e.g., "1920x1080"
    fps = Column(Integer, nullable=True)
    
    # AI processing configuration
    enable_detection = Column(Boolean, default=True, nullable=False)
    enable_tracking = Column(Boolean, default=True, nullable=False)
    enable_face_recognition = Column(Boolean, default=True, nullable=False)
    
    # Detection thresholds
    detection_threshold = Column(JSON, nullable=True)  # Per-object type thresholds
    tracking_config = Column(JSON, nullable=True)      # Tracking-specific settings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)  # Last time data received
    
    # Relationships
    detections = relationship("Detection", back_populates="camera", cascade="all, delete-orphan")
    tracking_data = relationship("Tracking", back_populates="camera", cascade="all, delete-orphan")
    face_recognitions = relationship("FaceRecognition", back_populates="camera", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, camera_id='{self.camera_id}', name='{self.name}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert camera to dictionary."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "zone": self.zone,
            "floor": self.floor,
            "building": self.building,
            "status": self.status,
            "is_enabled": self.is_enabled,
            "config": self.config,
            "stream_url": self.stream_url,
            "resolution": self.resolution,
            "fps": self.fps,
            "enable_detection": self.enable_detection,
            "enable_tracking": self.enable_tracking,
            "enable_face_recognition": self.enable_face_recognition,
            "detection_threshold": self.detection_threshold,
            "tracking_config": self.tracking_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
    
    @property
    def is_online(self) -> bool:
        """Check if camera is online based on last_seen timestamp."""
        if not self.last_seen:
            return False
        
        # Consider camera online if seen within last 5 minutes
        time_diff = datetime.utcnow() - self.last_seen.replace(tzinfo=None)
        return time_diff.total_seconds() < 300  # 5 minutes
    
    @property
    def uptime_status(self) -> str:
        """Get camera uptime status."""
        if not self.is_enabled:
            return "disabled"
        elif self.status != "active":
            return self.status
        elif self.is_online:
            return "online"
        else:
            return "offline"
    
    def update_last_seen(self) -> None:
        """Update the last_seen timestamp to current time."""
        self.last_seen = datetime.utcnow()
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if not self.config:
            self.config = {}
        self.config[key] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        if not self.config:
            return default
        return self.config.get(key, default)
    
    def set_detection_threshold(self, object_type: str, threshold: float) -> None:
        """Set detection threshold for specific object type."""
        if not self.detection_threshold:
            self.detection_threshold = {}
        self.detection_threshold[object_type] = threshold
    
    def get_detection_threshold(self, object_type: str, default: float = 0.5) -> float:
        """Get detection threshold for specific object type."""
        if not self.detection_threshold:
            return default
        return self.detection_threshold.get(object_type, default)
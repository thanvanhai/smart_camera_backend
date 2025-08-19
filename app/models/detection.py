from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Text, Float, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Detection(Base):
    """Detection model for storing object detection results from YOLO."""
    
    __tablename__ = "detections"
    
    # Primary key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Camera reference
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    
    # Detection metadata
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    frame_id = Column(String(100), nullable=True)  # Optional frame identifier
    
    # Detection results
    objects = Column(JSON, nullable=False)  # Array of detected objects with details
    object_count = Column(BigInteger, default=0, nullable=False)  # Total number of objects
    
    # Raw data for debugging/reprocessing
    raw_data = Column(Text, nullable=True)  # Original detection string from ROS2
    confidence_avg = Column(Float, nullable=True)  # Average confidence score
    confidence_max = Column(Float, nullable=True)  # Maximum confidence score
    
    # Processing metadata
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processing_time_ms = Column(Float, nullable=True)  # Processing time in milliseconds
    
    # Relationships
    camera = relationship("Camera", back_populates="detections")
    
    # Indexes for better query performance
    __table_args__ = (
        Index("idx_detections_camera_timestamp", "camera_id", "timestamp"),
        Index("idx_detections_timestamp_desc", "timestamp", postgresql_using="btree"),
        Index("idx_detections_object_count", "object_count"),
    )
    
    def __repr__(self) -> str:
        return f"<Detection(id={self.id}, camera_id='{self.camera_id}', objects={self.object_count}, timestamp='{self.timestamp}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "frame_id": self.frame_id,
            "objects": self.objects,
            "object_count": self.object_count,
            "raw_data": self.raw_data,
            "confidence_avg": self.confidence_avg,
            "confidence_max": self.confidence_max,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_time_ms": self.processing_time_ms,
        }
    
    @classmethod
    def parse_ros2_detection(cls, camera_id: str, timestamp: datetime, raw_data: str) -> "Detection":
        """
        Parse ROS2 detection string and create Detection object.
        
        Example input: "[HotelLobby] person:0.73,potted plant:0.60,chair:0.36"
        """
        import re
        from statistics import mean
        
        # Parse the detection string
        objects = []
        confidences = []
        
        # Extract objects and confidence scores
        if raw_data and "]" in raw_data:
            # Extract detection part after camera_id
            detection_part = raw_data.split("]", 1)[1].strip()
            
            # Parse individual detections
            for detection in detection_part.split(","):
                detection = detection.strip()
                if ":" in detection:
                    object_type, confidence_str = detection.rsplit(":", 1)
                    try:
                        confidence = float(confidence_str)
                        objects.append({
                            "type": object_type.strip(),
                            "confidence": confidence,
                            "timestamp": timestamp.isoformat() if timestamp else None
                        })
                        confidences.append(confidence)
                    except ValueError:
                        continue
        
        # Calculate statistics
        confidence_avg = mean(confidences) if confidences else 0.0
        confidence_max = max(confidences) if confidences else 0.0
        object_count = len(objects)
        
        return cls(
            camera_id=camera_id,
            timestamp=timestamp,
            objects=objects,
            object_count=object_count,
            raw_data=raw_data,
            confidence_avg=confidence_avg,
            confidence_max=confidence_max,
        )
    
    def get_objects_by_type(self, object_type: str) -> List[Dict[str, Any]]:
        """Get all objects of a specific type."""
        if not self.objects:
            return []
        
        return [obj for obj in self.objects if obj.get("type", "").lower() == object_type.lower()]
    
    def get_object_types(self) -> List[str]:
        """Get list of unique object types in this detection."""
        if not self.objects:
            return []
        
        return list(set(obj.get("type", "") for obj in self.objects))
    
    def has_object_type(self, object_type: str) -> bool:
        """Check if detection contains specific object type."""
        return any(obj.get("type", "").lower() == object_type.lower() for obj in self.objects or [])
    
    def get_high_confidence_objects(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get objects with confidence above threshold."""
        if not self.objects:
            return []
        
        return [obj for obj in self.objects if obj.get("confidence", 0) >= threshold]
    
    def count_objects_by_type(self) -> Dict[str, int]:
        """Count objects by type."""
        if not self.objects:
            return {}
        
        counts = {}
        for obj in self.objects:
            obj_type = obj.get("type", "unknown")
            counts[obj_type] = counts.get(obj_type, 0) + 1
        
        return counts
    
    @property
    def has_person(self) -> bool:
        """Check if detection contains a person."""
        return self.has_object_type("person")
    
    @property
    def person_count(self) -> int:
        """Get number of persons detected."""
        return len(self.get_objects_by_type("person"))
    
    @property
    def age_seconds(self) -> float:
        """Get age of detection in seconds."""
        if not self.timestamp:
            return 0.0
        
        now = datetime.utcnow()
        detection_time = self.timestamp.replace(tzinfo=None) if self.timestamp.tzinfo else self.timestamp
        return (now - detection_time).total_seconds()
    
    @property
    def is_recent(self, seconds: int = 60) -> bool:
        """Check if detection is recent (within specified seconds)."""
        return self.age_seconds <= seconds


class DetectionSummary(Base):
    """Summary table for detection statistics (for faster analytics queries)."""
    
    __tablename__ = "detection_summaries"
    
    id = Column(BigInteger, primary_key=True, index=True)
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(10), nullable=False)  # 'hour', 'day', 'week', 'month'
    
    # Statistics
    total_detections = Column(BigInteger, default=0, nullable=False)
    total_objects = Column(BigInteger, default=0, nullable=False)
    unique_object_types = Column(JSON, nullable=True)  # List of unique object types
    object_type_counts =
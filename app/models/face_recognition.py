from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Float, ForeignKey, Index, LargeBinary, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class FaceRecognition(Base):
    """Face recognition model for storing face recognition results."""
    
    __tablename__ = "face_recognitions"
    
    # Primary key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Camera reference
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    
    # Person identification
    person_id = Column(String(100), nullable=True, index=True)  # Recognized person ID
    person_name = Column(String(200), nullable=True)           # Display name
    confidence = Column(Float, nullable=False)
    
    # Temporal information
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Face location and features
    face_location = Column(JSON, nullable=True)     # Bounding box coordinates
    face_embedding = Column(LargeBinary, nullable=True)  # Face encoding for matching
    face_landmarks = Column(JSON, nullable=True)    # Facial landmark points
    
    # Face image data (optional storage)
    face_image_crop = Column(LargeBinary, nullable=True)  # Cropped face image
    face_image_path = Column(String(500), nullable=True)  # Path to stored image file
    
    # Recognition metadata
    recognition_method = Column(String(50), nullable=True)  # e.g., 'face_recognition', 'deepface'
    model_version = Column(String(50), nullable=True)      # Model version used
    
    # Quality metrics
    face_quality_score = Column(Float, nullable=True)      # Face image quality score
    face_size = Column(JSON, nullable=True)               # {"width": 150, "height": 180}
    is_frontal = Column(Boolean, default=True, nullable=False)  # Is face looking forward
    
    # Associated tracking information
    track_id = Column(BigInteger, nullable=True, index=True)  # Associated track ID if available
    
    # Verification flags
    is_verified = Column(Boolean, default=False, nullable=False)  # Human verified
    is_false_positive = Column(Boolean, default=False, nullable=False)  # Marked as false positive
    
    # Additional attributes
    attributes = Column(JSON, nullable=True)  # Age, gender, emotion, etc.
    
    # Processing metadata
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processing_time_ms = Column(Float, nullable=True)  # Processing time
    
    # Relationships
    camera = relationship("Camera", back_populates="face_recognitions")
    
    # Indexes for better performance
    __table_args__ = (
        Index("idx_face_camera_timestamp", "camera_id", "timestamp"),
        Index("idx_face_person_timestamp", "person_id", "timestamp"),
        Index("idx_face_confidence", "confidence"),
        Index("idx_face_track_id", "track_id"),
    )
    
    def __repr__(self) -> str:
        return f"<FaceRecognition(id={self.id}, camera_id='{self.camera_id}', person_id='{self.person_id}', confidence={self.confidence})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert face recognition to dictionary."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "person_id": self.person_id,
            "person_name": self.person_name,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "face_location": self.face_location,
            "face_landmarks": self.face_landmarks,
            "face_image_path": self.face_image_path,
            "recognition_method": self.recognition_method,
            "model_version": self.model_version,
            "face_quality_score": self.face_quality_score,
            "face_size": self.face_size,
            "is_frontal": self.is_frontal,
            "track_id": self.track_id,
            "is_verified": self.is_verified,
            "is_false_positive": self.is_false_positive,
            "attributes": self.attributes,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_time_ms": self.processing_time_ms,
        }
    
    @classmethod
    def parse_ros2_face_recognition(cls, camera_id: str, timestamp: datetime, raw_data: str) -> List["FaceRecognition"]:
        """
        Parse ROS2 face recognition string and create FaceRecognition objects.
        
        Example input: "[HotelLobby] John Doe,Unknown,Jane Smith"
        """
        face_objects = []
        
        if raw_data and "]" in raw_data:
            # Extract face recognition part after camera_id
            faces_part = raw_data.split("]", 1)[1].strip()
            
            # Parse individual face recognitions
            for face_identity in faces_part.split(","):
                face_identity = face_identity.strip()
                if face_identity:
                    # Determine if it's a known person or unknown
                    person_id = None
                    person_name = face_identity
                    confidence = 0.5  # Default confidence when not specified
                    
                    if face_identity.lower() == "unknown":
                        person_id = None
                        person_name = None
                        confidence = 0.0
                    else:
                        person_id = face_identity.lower().replace(" ", "_")
                        confidence = 0.8  # Higher confidence for recognized persons
                    
                    face_obj = cls(
                        camera_id=camera_id,
                        person_id=person_id,
                        person_name=person_name,
                        confidence=confidence,
                        timestamp=timestamp,
                        recognition_method="ros2_bridge",
                    )
                    face_objects.append(face_obj)
        
        return face_objects
    
    def update_face_location(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Update face location with bounding box coordinates."""
        self.face_location = {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "width": x2 - x1,
            "height": y2 - y1,
            "center_x": (x1 + x2) / 2,
            "center_y": (y1 + y2) / 2
        }
        
        # Update face size
        self.face_size = {
            "width": x2 - x1,
            "height": y2 - y1
        }
    
    def set_face_embedding(self, embedding: bytes) -> None:
        """Set face embedding for future matching."""
        self.face_embedding = embedding
    
    def get_face_embedding(self) -> Optional[bytes]:
        """Get face embedding."""
        return self.face_embedding
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a custom attribute (age, gender, emotion, etc.)."""
        if not self.attributes:
            self.attributes = {}
        self.attributes[key] = value
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a custom attribute."""
        if not self.attributes:
            return default
        return self.attributes.get(key, default)
    
    @property
    def is_known_person(self) -> bool:
        """Check if this is a recognized known person."""
        return self.person_id is not None and self.person_id != ""
    
    @property
    def is_unknown_person(self) -> bool:
        """Check if this is an unknown person."""
        return not self.is_known_person
    
    @property
    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if recognition has high confidence."""
        return self.confidence >= threshold
    
    @property
    def age_seconds(self) -> float:
        """Get age of recognition in seconds."""
        if not self.timestamp:
            return 0.0
        
        now = datetime.utcnow()
        recognition_time = self.timestamp.replace(tzinfo=None) if self.timestamp.tzinfo else self.timestamp
        return (now - recognition_time).total_seconds()
    
    @property
    def is_recent(self, seconds: int = 300) -> bool:
        """Check if recognition is recent (within specified seconds, default 5 minutes)."""
        return self.age_seconds <= seconds
    
    def mark_as_verified(self, verified: bool = True) -> None:
        """Mark recognition as verified by human."""
        self.is_verified = verified
    
    def mark_as_false_positive(self, false_positive: bool = True) -> None:
        """Mark recognition as false positive."""
        self.is_false_positive = false_positive
        if false_positive:
            self.is_verified = True  # Also mark as verified (reviewed)


class KnownPerson(Base):
    """Model for storing known persons database."""
    
    __tablename__ = "known_persons"
    
    # Primary key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Person identification
    person_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(300), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Person metadata
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    employee_id = Column(String(50), nullable=True)
    
    # Face encodings and images
    face_encodings = Column(JSON, nullable=True)  # Multiple face encodings
    profile_image_path = Column(String(500), nullable=True)
    
    # Status and permissions
    is_active = Column(Boolean, default=True, nullable=False)
    access_level = Column(String(50), default="standard", nullable=False)  # standard, admin, visitor
    
    # Additional information
    notes = Column(String(1000), nullable=True)
    attributes = Column(JSON, nullable=True)  # Custom attributes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<KnownPerson(id={self.id}, person_id='{self.person_id}', name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert known person to dictionary."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "department": self.department,
            "position": self.position,
            "employee_id": self.employee_id,
            "profile_image_path": self.profile_image_path,
            "is_active": self.is_active,
            "access_level": self.access_level,
            "notes": self.notes,
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
    
    def add_face_encoding(self, encoding: List[float]) -> None:
        """Add a new face encoding."""
        if not self.face_encodings:
            self.face_encodings = []
        self.face_encodings.append(encoding)
    
    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        self.last_seen = datetime.utcnow()
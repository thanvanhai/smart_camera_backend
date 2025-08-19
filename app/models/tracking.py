from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, BigInteger, String, Integer, Float, TIMESTAMP, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Tracking(Base):
    __tablename__ = "tracking"

    id = Column(BigInteger, primary_key=True, index=True)
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False)
    track_id = Column(Integer, nullable=False)
    object_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    location = Column(JSON)  # Bounding box coordinates

    camera = relationship("Camera", back_populates="tracking_data")

    __table_args__ = (
        Index("idx_tracking_camera_track", "camera_id", "track_id"),
        Index("idx_tracking_timestamp", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "object_type": self.object_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "location": self.location,
        }

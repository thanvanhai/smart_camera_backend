from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, BigInteger, String, Float, TIMESTAMP, LargeBinary, Index, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class FaceRecognition(Base):
    __tablename__ = "face_recognitions"

    id = Column(BigInteger, primary_key=True, index=True)
    camera_id = Column(String(50), ForeignKey("cameras.camera_id"), nullable=False)
    person_id = Column(String(100))
    confidence = Column(Float, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    face_embedding = Column(LargeBinary)  # Face encoding
    image_crop = Column(LargeBinary)      # Cropped face image

    camera = relationship("Camera", back_populates="face_recognitions")

    __table_args__ = (
        Index("idx_face_camera_timestamp", "camera_id", "timestamp"),
        Index("idx_face_person_timestamp", "person_id", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "person_id": self.person_id,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "face_embedding": self.face_embedding.hex() if self.face_embedding else None,
            "image_crop": self.image_crop.hex() if self.image_crop else None,
        }

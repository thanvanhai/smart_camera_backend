from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.detection import Detection
from app.schemas.detection import DetectionCreate, DetectionUpdate


class DetectionService:
    def __init__(self, db: Session):
        self.db = db

    # -----------------------
    # Create detection
    # -----------------------
    def create(self, detection_in: DetectionCreate) -> Detection:
        detection = Detection(**detection_in.dict())
        self.db.add(detection)
        self.db.commit()
        self.db.refresh(detection)
        return detection

    # -----------------------
    # Get detection by ID
    # -----------------------
    def get(self, detection_id: int) -> Optional[Detection]:
        return self.db.query(Detection).filter(Detection.id == detection_id).first()

    # -----------------------
    # List detections
    # -----------------------
    def list(
        self,
        camera_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Detection]:
        query = self.db.query(Detection)
        if camera_id:
            query = query.filter(Detection.camera_id == camera_id)
        return query.order_by(Detection.timestamp.desc()).offset(skip).limit(limit).all()

    # -----------------------
    # Update detection
    # -----------------------
    def update(self, detection: Detection, detection_in: DetectionUpdate) -> Detection:
        for field, value in detection_in.dict(exclude_unset=True).items():
            setattr(detection, field, value)
        self.db.commit()
        self.db.refresh(detection)
        return detection

    # -----------------------
    # Delete detection
    # -----------------------
    def delete(self, detection: Detection) -> None:
        self.db.delete(detection)
        self.db.commit()

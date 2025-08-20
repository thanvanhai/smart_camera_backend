from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate


class CameraService:
    def __init__(self, db: Session):
        self.db = db

    # -----------------------
    # Create camera
    # -----------------------
    def create(self, camera_in: CameraCreate) -> Camera:
        camera = Camera(**camera_in.dict())
        self.db.add(camera)
        self.db.commit()
        self.db.refresh(camera)
        return camera

    # -----------------------
    # Get camera by ID
    # -----------------------
    def get(self, camera_id: str) -> Optional[Camera]:
        return self.db.query(Camera).filter(Camera.camera_id == camera_id).first()

    # -----------------------
    # List cameras
    # -----------------------
    def list(self, skip: int = 0, limit: int = 100) -> List[Camera]:
        return self.db.query(Camera).offset(skip).limit(limit).all()

    # -----------------------
    # Update camera
    # -----------------------
    def update(self, camera: Camera, camera_in: CameraUpdate) -> Camera:
        for field, value in camera_in.dict(exclude_unset=True).items():
            setattr(camera, field, value)
        camera.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(camera)
        return camera

    # -----------------------
    # Delete camera
    # -----------------------
    def delete(self, camera: Camera) -> None:
        self.db.delete(camera)
        self.db.commit()

    # -----------------------
    # Update last_seen
    # -----------------------
    def update_last_seen(self, camera: Camera) -> Camera:
        camera.update_last_seen()
        self.db.commit()
        self.db.refresh(camera)
        return camera

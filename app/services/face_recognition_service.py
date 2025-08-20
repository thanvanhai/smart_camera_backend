from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.face_recognition import FaceRecognition
from app.schemas.face_recognition import FaceRecognitionCreate, FaceRecognitionUpdate


class FaceRecognitionService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, fr_in: FaceRecognitionCreate) -> FaceRecognition:
        fr = FaceRecognition(**fr_in.dict())
        self.db.add(fr)
        self.db.commit()
        self.db.refresh(fr)
        return fr

    def get(self, fr_id: int) -> Optional[FaceRecognition]:
        return self.db.query(FaceRecognition).filter(FaceRecognition.id == fr_id).first()

    def list(
        self,
        camera_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[FaceRecognition]:
        query = self.db.query(FaceRecognition)
        if camera_id:
            query = query.filter(FaceRecognition.camera_id == camera_id)
        return query.order_by(FaceRecognition.timestamp.desc()).offset(skip).limit(limit).all()

    def update(self, fr: FaceRecognition, fr_in: FaceRecognitionUpdate) -> FaceRecognition:
        for field, value in fr_in.dict(exclude_unset=True).items():
            setattr(fr, field, value)
        self.db.commit()
        self.db.refresh(fr)
        return fr

    def delete(self, fr: FaceRecognition) -> None:
        self.db.delete(fr)
        self.db.commit()

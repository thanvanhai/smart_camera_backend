from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.tracking import Tracking
from app.schemas.tracking import TrackingCreate, TrackingUpdate


class TrackingService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, tracking_in: TrackingCreate) -> Tracking:
        tracking = Tracking(**tracking_in.dict())
        self.db.add(tracking)
        self.db.commit()
        self.db.refresh(tracking)
        return tracking

    def get(self, tracking_id: int) -> Optional[Tracking]:
        return self.db.query(Tracking).filter(Tracking.id == tracking_id).first()

    def list(
        self,
        camera_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tracking]:
        query = self.db.query(Tracking)
        if camera_id:
            query = query.filter(Tracking.camera_id == camera_id)
        return query.order_by(Tracking.timestamp.desc()).offset(skip).limit(limit).all()

    def update(self, tracking: Tracking, tracking_in: TrackingUpdate) -> Tracking:
        for field, value in tracking_in.dict(exclude_unset=True).items():
            setattr(tracking, field, value)
        self.db.commit()
        self.db.refresh(tracking)
        return tracking

    def delete(self, tracking: Tracking) -> None:
        self.db.delete(tracking)
        self.db.commit()

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.tracking import TrackingRead, TrackingCreate, TrackingUpdate
from app.services.tracking_service import TrackingService
from app.core.database import get_db

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.post("/", response_model=TrackingRead, status_code=status.HTTP_201_CREATED)
def create_tracking(tracking_in: TrackingCreate, db: Session = Depends(get_db)):
    service = TrackingService(db)
    return service.create(tracking_in)


@router.get("/{tracking_id}", response_model=TrackingRead)
def get_tracking(tracking_id: int, db: Session = Depends(get_db)):
    service = TrackingService(db)
    tracking = service.get(tracking_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return tracking


@router.get("/", response_model=List[TrackingRead])
def list_tracking(camera_id: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = TrackingService(db)
    return service.list(camera_id=camera_id, skip=skip, limit=limit)


@router.put("/{tracking_id}", response_model=TrackingRead)
def update_tracking(tracking_id: int, tracking_in: TrackingUpdate, db: Session = Depends(get_db)):
    service = TrackingService(db)
    tracking = service.get(tracking_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return service.update(tracking, tracking_in)


@router.delete("/{tracking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tracking(tracking_id: int, db: Session = Depends(get_db)):
    service = TrackingService(db)
    tracking = service.get(tracking_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    service.delete(tracking)

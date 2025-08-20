from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.detection import DetectionRead, DetectionCreate, DetectionUpdate
from app.services.detection_service import DetectionService
from app.core.database import get_db

router = APIRouter(prefix="/detections", tags=["detections"])


@router.post("/", response_model=DetectionRead, status_code=status.HTTP_201_CREATED)
def create_detection(detection_in: DetectionCreate, db: Session = Depends(get_db)):
    service = DetectionService(db)
    return service.create(detection_in)


@router.get("/{detection_id}", response_model=DetectionRead)
def get_detection(detection_id: int, db: Session = Depends(get_db)):
    service = DetectionService(db)
    detection = service.get(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection


@router.get("/", response_model=List[DetectionRead])
def list_detections(camera_id: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = DetectionService(db)
    return service.list(camera_id=camera_id, skip=skip, limit=limit)


@router.put("/{detection_id}", response_model=DetectionRead)
def update_detection(detection_id: int, detection_in: DetectionUpdate, db: Session = Depends(get_db)):
    service = DetectionService(db)
    detection = service.get(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return service.update(detection, detection_in)


@router.delete("/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_detection(detection_id: int, db: Session = Depends(get_db)):
    service = DetectionService(db)
    detection = service.get(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    service.delete(detection)

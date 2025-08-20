from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.camera import CameraRead, CameraCreate, CameraUpdate
from app.services.camera_service import CameraService
from app.core.database import get_db

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post("/", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: CameraCreate, db: Session = Depends(get_db)):
    service = CameraService(db)
    return service.create(camera_in)


@router.get("/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    service = CameraService(db)
    camera = service.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.get("/", response_model=List[CameraRead])
def list_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = CameraService(db)
    return service.list(skip=skip, limit=limit)


@router.put("/{camera_id}", response_model=CameraRead)
def update_camera(camera_id: str, camera_in: CameraUpdate, db: Session = Depends(get_db)):
    service = CameraService(db)
    camera = service.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return service.update(camera, camera_in)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    service = CameraService(db)
    camera = service.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    service.delete(camera)

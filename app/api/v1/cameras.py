from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.camera import CameraResponse, CameraCreate, CameraUpdate
from app.services.camera_service import CameraService
from app.core.database import get_db_session

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(camera_in: CameraCreate, db: Session = Depends(get_db_session)):
    service = CameraService(db)
    return await service.create_camera(camera_in)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: Session = Depends(get_db_session)):
    service = CameraService(db)
    camera = service.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.get("/", response_model=List[CameraResponse])
async def list_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session)):
    service = CameraService(db)
    return service.list(skip=skip, limit=limit)


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: int, camera_in: CameraUpdate, db: Session = Depends(get_db_session)):
    service = CameraService(db)
    camera = service.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return service.update(camera, camera_in)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, db: Session = Depends(get_db_session)):
    service = CameraService(db)
    camera = service.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    service.delete(camera)

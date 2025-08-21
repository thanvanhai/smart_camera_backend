from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.camera import CameraResponse, CameraCreate, CameraUpdate
from app.services.camera_service import CameraService
from app.core.database import get_db_session
from app.workers.rabbitmq_utils import publish_camera_event

router = APIRouter(prefix="/cameras", tags=["cameras"])

@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(camera_in: CameraCreate, db: AsyncSession = Depends(get_db_session)):
    service = CameraService(db)
    camera = await service.create_camera(camera_in)
    
    # Gửi message cho worker
    await publish_camera_event("add", camera.model_dump())
    
    return camera

@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db_session)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.get("/", response_model=List[CameraResponse])
async def list_cameras(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db_session)):
    service = CameraService(db)
    cameras = await service.get_cameras(skip=skip, limit=limit)
    return cameras

@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: int, camera_in: CameraUpdate, db: AsyncSession = Depends(get_db_session)):
    service = CameraService(db)
    camera = await service.update_camera(camera_id, camera_in)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db_session)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    await service.delete_camera(camera_id)
    
    # Gửi message cho worker
    await publish_camera_event("remove", {"camera_id": camera.camera_id})
    
    return

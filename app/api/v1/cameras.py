from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.camera import CameraResponse, CameraCreate, CameraUpdate
from app.services.camera_service import CameraService
from app.core.database import get_db_session
from app.services.rabbitmq_service import publish_camera_event

router = APIRouter(tags=["cameras"])

def _build_camera_created_message(camera: CameraResponse) -> dict:
    """
    Chuẩn hóa payload gửi sang RabbitMQ cho event created.
    Ưu tiên các field phổ biến: camera_id, camera_url/stream_url.
    """
    data = camera.model_dump() if hasattr(camera, "model_dump") else dict(camera)  # pydantic v2/v1
    camera_id = data.get("camera_id") # chú ý camera_id đang có ký tự đặc biệt vì ROS sử dụng camera_id để tạo thư mục topic
    camera_url = data.get("stream_url") or data.get("camera_url") or data.get("rtsp_url")

    payload = {
        "action": "created",
        "camera_id": str(camera_id) if camera_id is not None else "",
        "camera_url": str(camera_url),
    }

    return payload

def _build_camera_removed_message(camera_id: str | int) -> dict:
    return {
        "action": "removed",
        "camera_id": str(camera_id),
    }


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_in: CameraCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    service = CameraService(db)
    camera = await service.create_camera(camera_in)

    # Publish sang RabbitMQ (exchange fanout "camera.events")
    payload = _build_camera_created_message(camera)
    # 👇 debug nhanh dữ liệu trước khi gửi RabbitMQ
    # print("DEBUG payload before publish:", payload)
    background_tasks.add_task(publish_camera_event, payload)

    return camera


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db_session)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.get("/", response_model=List[CameraResponse])
async def list_cameras(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    service = CameraService(db)
    cameras = await service.get_cameras(skip=skip, limit=limit)
    return cameras


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_in: CameraUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    service = CameraService(db)
    camera = await service.update_camera(camera_id, camera_in)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    await service.delete_camera(camera_id)

    # Publish removed event
    payload = _build_camera_removed_message(camera.camera_id if hasattr(camera, "camera_id") else camera_id)
    background_tasks.add_task(publish_camera_event, payload)

    return None

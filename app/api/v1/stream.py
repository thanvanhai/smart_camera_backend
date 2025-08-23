from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.services.stream_service import get_stream_service, StreamService

router = APIRouter(prefix="/cameras", tags=["stream"])

@router.get("/{camera_id}/stream")
async def stream_camera(camera_id: str, stream_service: StreamService = Depends(get_stream_service)):
    """Stream video từ camera."""
    return await stream_service.create_streaming_response(camera_id)

@router.get("/{camera_id}/info")
async def get_camera_info(camera_id: str, stream_service: StreamService = Depends(get_stream_service)):
    """Lấy metadata camera."""
    info = await stream_service.get_stream_info(camera_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return info

@router.get("/{camera_id}/status")
async def check_camera_status(camera_id: str, stream_service: StreamService = Depends(get_stream_service)):
    """Kiểm tra trạng thái camera (active/inactive)."""
    is_active = await stream_service.check_camera_active(camera_id)
    return {"camera_id": camera_id, "status": "active" if is_active else "inactive"}

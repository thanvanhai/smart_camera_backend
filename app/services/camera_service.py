import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.camera import Camera
from ..models.detection import Detection
from ..models.tracking import Tracking
from ..models.face_recognition import FaceRecognition
from ..schemas.camera import (
    CameraCreate, CameraUpdate, CameraStatusUpdate,
    CameraStats, CameraStatus, CameraResponse
)


class CameraService:
    """Async service for camera management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_camera(self, camera_data: CameraCreate) -> CameraResponse:
        """Create a new camera with automatic camera_id if not provided"""
        camera_id = camera_data.camera_id or str(uuid.uuid4().hex)#chuyển đổi camera_id thành chuỗi UUID không có dấu gạch ngang để ROS tạo topic không lỗi
        
        db_camera = Camera(
            camera_id=camera_id,
            name=camera_data.name,
            camera_type=camera_data.camera_type.value,
            stream_url=camera_data.stream_url,
            location=camera_data.location,
            description=camera_data.description,
            settings=camera_data.settings or {},
            status=CameraStatus.INACTIVE.value
        )
        self.db.add(db_camera)
        await self.db.commit()
        await self.db.refresh(db_camera)
        return CameraResponse.from_orm(db_camera)
    
    async def get_camera(self, camera_id: int) -> Optional[Camera]:
        result = await self.db.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        return result.scalars().first()
    
    async def get_camera_by_camera_id(self, camera_id_str: str) -> Optional[Camera]:
        """Lấy camera theo camera_id (chuỗi)"""
        result = await self.db.execute(
            select(Camera).where(Camera.camera_id == camera_id_str)
        )
        return result.scalars().first()
    
    async def get_cameras(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[CameraStatus] = None,
        camera_type: Optional[str] = None
    ) -> List[Camera]:
        stmt = select(Camera)
        if status:
            stmt = stmt.where(Camera.status == status.value)
        if camera_type:
            stmt = stmt.where(Camera.camera_type == camera_type)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def update_camera(
        self, 
        camera_id: int, 
        camera_data: CameraUpdate
    ) -> Optional[CameraResponse]:
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        update_data = camera_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_camera, field, value)
        db_camera.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(db_camera)
        return CameraResponse.from_orm(db_camera)
    
    async def delete_camera(self, camera_id: int) -> bool:
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return False
        await self.db.delete(db_camera)
        await self.db.commit()
        return True
    
    async def update_camera_status(
        self, 
        camera_id: int, 
        status_data: CameraStatusUpdate
    ) -> Optional[CameraResponse]:
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        db_camera.status = status_data.status.value
        db_camera.last_seen = status_data.last_seen or datetime.utcnow()
        if getattr(status_data, 'error_message', None):
            if not db_camera.settings:
                db_camera.settings = {}
            db_camera.settings['last_error'] = status_data.error_message
        db_camera.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(db_camera)
        return CameraResponse.from_orm(db_camera)
    
    async def get_camera_stats(self, camera_id: int) -> Optional[CameraStats]:
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        
        uptime_hours = 0.0
        if db_camera.last_seen and db_camera.created_at:
            uptime_hours = (db_camera.last_seen - db_camera.created_at).total_seconds() / 3600
        
        detection_stats = await self.db.execute(
            select(func.count(Detection.id), func.max(Detection.timestamp))
            .where(Detection.camera_id == camera_id)
        )
        total_detections, last_detection_at = detection_stats.first() or (0, None)
        
        tracking_stats = await self.db.execute(
            select(func.count(Tracking.id), func.max(Tracking.timestamp))
            .where(Tracking.camera_id == camera_id)
        )
        total_tracks, last_track_at = tracking_stats.first() or (0, None)
        
        face_stats = await self.db.execute(
            select(func.count(FaceRecognition.id), func.max(FaceRecognition.timestamp))
            .where(FaceRecognition.camera_id == camera_id)
        )
        total_faces, last_face_at = face_stats.first() or (0, None)
        
        return CameraStats(
            camera_id=db_camera.camera_id,
            total_detections=total_detections,
            total_tracks=total_tracks,
            total_faces=total_faces,
            uptime_hours=uptime_hours,
            last_detection_at=last_detection_at,
            last_track_at=last_track_at,
            last_face_at=last_face_at
        )
    
    async def get_active_cameras(self) -> List[Camera]:
        result = await self.db.execute(
            select(Camera).where(Camera.status == CameraStatus.ACTIVE.value)
        )
        return result.scalars().all()
    
    async def get_inactive_cameras(self, minutes: int = 5) -> List[Camera]:
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        result = await self.db.execute(
            select(Camera)
            .where(Camera.last_seen < cutoff_time, Camera.status == CameraStatus.ACTIVE.value)
        )
        return result.scalars().all()
    
    async def check_camera_connectivity(self, camera_id: int) -> Dict[str, Any]:
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return {"status": "not_found", "message": "Camera not found"}
        
        if not db_camera.last_seen:
            return {"status": "never_connected", "message": "Camera has never been seen"}
        
        time_since_last_seen = datetime.utcnow() - db_camera.last_seen
        if time_since_last_seen > timedelta(minutes=5):
            return {
                "status": "disconnected",
                "message": f"Last seen {time_since_last_seen} ago",
                "last_seen": db_camera.last_seen
            }
        return {"status": "connected", "message": "Camera is active", "last_seen": db_camera.last_seen}

"""
Camera management service
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..models.camera import Camera
from ..models.detection import Detection
from ..models.tracking import Tracking
from ..models.face_recognition import FaceRecognition
from ..schemas.camera import (
    CameraCreate, CameraUpdate, CameraStatusUpdate,
    CameraStats, CameraStatus
)

class CameraService:
    """Service for camera management operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_camera(self, camera_data: CameraCreate) -> Camera:
        """Create a new camera"""
        db_camera = Camera(
            name=camera_data.name,
            camera_type=camera_data.camera_type,
            stream_url=camera_data.stream_url,
            location=camera_data.location,
            description=camera_data.description,
            settings=camera_data.settings or {},
            status=CameraStatus.INACTIVE
        )
        
        self.db.add(db_camera)
        self.db.commit()
        self.db.refresh(db_camera)
        return db_camera
    
    async def get_camera(self, camera_id: int) -> Optional[Camera]:
        """Get camera by ID"""
        return self.db.query(Camera).filter(Camera.id == camera_id).first()
    
    async def get_cameras(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[CameraStatus] = None,
        camera_type: Optional[str] = None
    ) -> List[Camera]:
        """Get list of cameras with filters"""
        query = self.db.query(Camera)
        
        if status:
            query = query.filter(Camera.status == status)
        if camera_type:
            query = query.filter(Camera.camera_type == camera_type)
            
        return query.offset(skip).limit(limit).all()
    
    async def update_camera(
        self, 
        camera_id: int, 
        camera_data: CameraUpdate
    ) -> Optional[Camera]:
        """Update camera information"""
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        
        update_data = camera_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_camera, field, value)
        
        db_camera.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_camera)
        return db_camera
    
    async def delete_camera(self, camera_id: int) -> bool:
        """Delete camera"""
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return False
        
        self.db.delete(db_camera)
        self.db.commit()
        return True
    
    async def update_camera_status(
        self, 
        camera_id: int, 
        status_data: CameraStatusUpdate
    ) -> Optional[Camera]:
        """Update camera status and last_seen"""
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        
        db_camera.status = status_data.status
        if status_data.last_seen:
            db_camera.last_seen = status_data.last_seen
        else:
            db_camera.last_seen = datetime.utcnow()
        
        # Store error message in settings if provided
        if hasattr(status_data, 'error_message') and status_data.error_message:
            if not db_camera.settings:
                db_camera.settings = {}
            db_camera.settings['last_error'] = status_data.error_message
        
        db_camera.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_camera)
        return db_camera
    
    async def get_camera_stats(self, camera_id: int) -> Optional[CameraStats]:
        """Get camera statistics"""
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        
        # Calculate uptime (assuming last_seen indicates active time)
        uptime_hours = 0.0
        if db_camera.last_seen and db_camera.created_at:
            uptime_delta = db_camera.last_seen - db_camera.created_at
            uptime_hours = uptime_delta.total_seconds() / 3600
        
        # Get detection stats
        detection_stats = self.db.query(
            func.count(Detection.id),
            func.max(Detection.timestamp)
        ).filter(Detection.camera_id == camera_id).first()
        
        total_detections = detection_stats[0] if detection_stats[0] else 0
        last_detection_at = detection_stats[1]
        
        # Get tracking stats
        tracking_stats = self.db.query(
            func.count(Tracking.id.distinct()),
            func.max(Tracking.timestamp)
        ).filter(Tracking.camera_id == camera_id).first()
        
        total_tracks = tracking_stats[0] if tracking_stats[0] else 0
        last_track_at = tracking_stats[1]
        
        # Get face recognition stats
        face_stats = self.db.query(
            func.count(FaceRecognition.id),
            func.max(FaceRecognition.timestamp)
        ).filter(FaceRecognition.camera_id == camera_id).first()
        
        total_faces = face_stats[0] if face_stats[0] else 0
        last_face_at = face_stats[1]
        
        return CameraStats(
            camera_id=camera_id,
            total_detections=total_detections,
            total_tracks=total_tracks,
            total_faces=total_faces,
            uptime_hours=uptime_hours,
            last_detection_at=last_detection_at,
            last_track_at=last_track_at,
            last_face_at=last_face_at
        )
    
    async def get_active_cameras(self) -> List[Camera]:
        """Get all active cameras"""
        return self.db.query(Camera).filter(
            Camera.status == CameraStatus.ACTIVE
        ).all()
    
    async def get_inactive_cameras(self, minutes: int = 5) -> List[Camera]:
        """Get cameras that haven't been seen for specified minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return self.db.query(Camera).filter(
            Camera.last_seen < cutoff_time,
            Camera.status == CameraStatus.ACTIVE
        ).all()
    
    async def check_camera_connectivity(self, camera_id: int) -> Dict[str, Any]:
        """Check camera connectivity status"""
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return {"status": "not_found", "message": "Camera not found"}
        
        # Simple connectivity check based on last_seen
        if not db_camera.last_seen:
            return {
                "status": "never_connected",
                "message": "Camera has never been seen"
            }
        
        time_since_last_seen = datetime.utcnow() - db_camera.last_seen
        if time_since_last_seen > timedelta(minutes=5):
            return {
                "status": "disconnected",
                "message": f"Last seen {time_since_last_seen} ago",
                "last_seen": db_camera.last_seen
            }
        
        return {
            "status": "connected",
            "message": "Camera is active",
            "last_seen": db_camera.last_seen
        }
    
    async def update_camera_settings(
        self, 
        camera_id: int, 
        settings: Dict[str, Any]
    ) -> Optional[Camera]:
        """Update camera settings"""
        db_camera = await self.get_camera(camera_id)
        if not db_camera:
            return None
        
        if not db_camera.settings:
            db_camera.settings = {}
        
        db_camera.settings.update(settings)
        db_camera.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_camera)
        return db_camera
    
    async def get_cameras_by_location(self, location: str) -> List[Camera]:
        """Get cameras by location"""
        return self.db.query(Camera).filter(
            Camera.location.ilike(f"%{location}%")
        ).all()
    
    async def get_camera_health_summary(self) -> Dict[str, Any]:
        """Get overall camera health summary"""
        total_cameras = self.db.query(func.count(Camera.id)).scalar()
        
        status_counts = self.db.query(
            Camera.status,
            func.count(Camera.id)
        ).group_by(Camera.status).all()
        
        status_summary = {status.value: 0 for status in CameraStatus}
        for status, count in status_counts:
            status_summary[status] = count
        
        # Cameras not seen in last 5 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        stale_cameras = self.db.query(func.count(Camera.id)).filter(
            Camera.last_seen < cutoff_time,
            Camera.status == CameraStatus.ACTIVE
        ).scalar()
        
        return {
            "total_cameras": total_cameras,
            "status_summary": status_summary,
            "stale_cameras": stale_cameras,
            "health_percentage": (
                (total_cameras - stale_cameras) / total_cameras * 100
                if total_cameras > 0 else 0
            )
        }
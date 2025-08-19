from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# =======================
# Base schema
# =======================
class CameraBase(BaseModel):
    camera_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    location: Optional[str] = None
    zone: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    status: Optional[str] = "active"
    is_enabled: Optional[bool] = True
    config: Optional[Dict[str, Any]] = None
    stream_url: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    enable_detection: Optional[bool] = True
    enable_tracking: Optional[bool] = True
    enable_face_recognition: Optional[bool] = True
    detection_threshold: Optional[Dict[str, float]] = None
    tracking_config: Optional[Dict[str, Any]] = None

# =======================
# Schema for creating a camera
# =======================
class CameraCreate(CameraBase):
    pass

# =======================
# Schema for updating a camera
# =======================
class CameraUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    zone: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    status: Optional[str] = None
    is_enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    stream_url: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    enable_detection: Optional[bool] = None
    enable_tracking: Optional[bool] = None
    enable_face_recognition: Optional[bool] = None
    detection_threshold: Optional[Dict[str, float]] = None
    tracking_config: Optional[Dict[str, Any]] = None

# =======================
# Schema for reading a camera (API response)
# =======================
class CameraRead(CameraBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    is_online: Optional[bool] = None
    uptime_status: Optional[str] = None

    class Config:
        orm_mode = True

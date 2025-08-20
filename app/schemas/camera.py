"""
Camera-related schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class CameraType(str, Enum):
    """Camera type enum"""
    IP_CAMERA = "ip_camera"
    USB_CAMERA = "usb_camera"
    RTSP_STREAM = "rtsp_stream"

class CameraStatus(str, Enum):
    """Camera status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class CameraCreate(BaseModel):
    """Schema for creating a camera"""
    name: str = Field(..., min_length=1, max_length=100)
    camera_type: CameraType
    stream_url: str = Field(..., min_length=1, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = None
    
    @validator('stream_url')
    def validate_stream_url(cls, v):
        """Validate stream URL format"""
        if not (v.startswith('rtsp://') or v.startswith('http://') or 
                v.startswith('https://') or v.startswith('/dev/')):
            raise ValueError('Invalid stream URL format')
        return v

class CameraUpdate(BaseModel):
    """Schema for updating a camera"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    stream_url: Optional[str] = Field(None, min_length=1, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[CameraStatus] = None
    settings: Optional[Dict[str, Any]] = None
    
    @validator('stream_url')
    def validate_stream_url(cls, v):
        if v and not (v.startswith('rtsp://') or v.startswith('http://') or 
                     v.startswith('https://') or v.startswith('/dev/')):
            raise ValueError('Invalid stream URL format')
        return v

class CameraResponse(BaseModel):
    """Schema for camera response"""
    id: int
    name: str
    camera_type: CameraType
    stream_url: str
    location: Optional[str]
    description: Optional[str]
    status: CameraStatus
    settings: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime]
    
    class Config:
        from_attributes = True

class CameraStatusUpdate(BaseModel):
    """Schema for updating camera status"""
    status: CameraStatus
    last_seen: Optional[datetime] = None
    error_message: Optional[str] = None

class CameraStreamInfo(BaseModel):
    """Schema for camera stream information"""
    camera_id: int
    stream_url: str
    status: CameraStatus
    fps: Optional[float] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    
class CameraSettings(BaseModel):
    """Schema for camera settings"""
    resolution: Optional[str] = None
    fps: Optional[int] = Field(None, ge=1, le=60)
    quality: Optional[int] = Field(None, ge=1, le=100)
    brightness: Optional[int] = Field(None, ge=-100, le=100)
    contrast: Optional[int] = Field(None, ge=-100, le=100)
    saturation: Optional[int] = Field(None, ge=-100, le=100)
    auto_focus: Optional[bool] = None
    night_vision: Optional[bool] = None
    motion_detection: Optional[bool] = None
    audio_enabled: Optional[bool] = None
    
class CameraStats(BaseModel):
    """Schema for camera statistics"""
    camera_id: int
    total_detections: int = 0
    total_tracks: int = 0
    total_faces: int = 0
    uptime_hours: float = 0.0
    avg_fps: Optional[float] = None
    last_detection_at: Optional[datetime] = None
    last_track_at: Optional[datetime] = None
    last_face_at: Optional[datetime] = None
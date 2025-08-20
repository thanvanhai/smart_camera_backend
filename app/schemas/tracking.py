"""
Tracking-related schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TrackingCreate(BaseModel):
    """Schema for creating a tracking record"""
    camera_id: int
    track_id: str = Field(..., min_length=1, max_length=100)
    object_class: str = Field(..., min_length=1, max_length=50)
    bbox_x: float = Field(..., ge=0.0, le=1.0)
    bbox_y: float = Field(..., ge=0.0, le=1.0)
    bbox_width: float = Field(..., ge=0.0, le=1.0)
    bbox_height: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime
    frame_id: Optional[str] = None
    velocity_x: Optional[float] = None
    velocity_y: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = None

class TrackingResponse(BaseModel):
    """Schema for tracking response"""
    id: int
    camera_id: int
    track_id: str
    object_class: str
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float
    timestamp: datetime
    frame_id: Optional[str]
    velocity_x: Optional[float]
    velocity_y: Optional[float]
    additional_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TrackingSummaryResponse(BaseModel):
    """Schema for tracking summary response"""
    id: int
    camera_id: int
    track_id: str
    object_class: str
    first_seen: datetime
    last_seen: datetime
    total_frames: int
    avg_confidence: float
    path_length: float
    max_velocity: Optional[float]
    summary_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TrackingFilter(BaseModel):
    """Schema for filtering tracking data"""
    camera_id: Optional[int] = None
    track_ids: Optional[List[str]] = None
    object_classes: Optional[List[str]] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_duration: Optional[int] = None  # minimum tracking duration in seconds
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class TrackingPath(BaseModel):
    """Schema for tracking path visualization"""
    track_id: str
    object_class: str
    camera_id: int
    path_points: List[Dict[str, Any]]  # [{x, y, timestamp, confidence}, ...]
    start_time: datetime
    end_time: datetime
    total_distance: float
    avg_velocity: Optional[float]

class TrackingStats(BaseModel):
    """Schema for tracking statistics"""
    total_tracks: int
    active_tracks: int
    tracks_by_class: Dict[str, int]
    avg_track_duration: float
    longest_track_duration: float
    total_distance_traveled: float
    tracks_by_camera: List[Dict[str, Any]]

class ActiveTrack(BaseModel):
    """Schema for active tracking objects"""
    track_id: str
    camera_id: int
    object_class: str
    current_bbox: Dict[str, float]
    confidence: float
    first_seen: datetime
    last_seen: datetime
    frame_count: int
    current_velocity: Optional[Dict[str, float]] = None

class TrackingAlert(BaseModel):
    """Schema for tracking alerts (loitering, intrusion, etc.)"""
    track_id: str
    camera_id: int
    alert_type: str  # "loitering", "intrusion", "speeding", etc.
    object_class: str
    duration: Optional[float] = None
    area: Optional[str] = None
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

class TrackingHeatmap(BaseModel):
    """Schema for movement heatmap data"""
    camera_id: int
    object_class: Optional[str] = None
    time_range: Dict[str, datetime]
    heatmap_data: List[List[int]]
    width: int
    height: int
    max_intensity: int
    generated_at: datetime
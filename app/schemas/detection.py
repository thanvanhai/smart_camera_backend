from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =======================
# Base schema for Detection
# =======================
class DetectionBase(BaseModel):
    camera_id: int
    timestamp: datetime
    frame_id: Optional[str] = None
    class_name: Optional[str] = None
    confidence: Optional[float] = None
    bbox: Optional[Dict[str, float]] = None   # {x, y, width, height}
    additional_data: Optional[Dict[str, Any]] = None


# =======================
# Schema for creating Detection
# =======================
class DetectionCreate(DetectionBase):
    camera_id: int
    class_name: str
    confidence: float
    bbox: Dict[str, float]


# =======================
# Bulk creation
# =======================
class BulkDetectionCreate(BaseModel):
    detections: List[DetectionCreate]


# =======================
# Filtering schema
# =======================
class DetectionFilter(BaseModel):
    camera_id: Optional[int] = None
    class_names: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# =======================
# Stats schemas
# =======================
class DetectionStats(BaseModel):
    total_detections: int
    detections_by_class: Dict[str, int]
    detections_by_hour: Dict[str, int]
    avg_confidence: float
    confidence_distribution: Dict[str, int]
    top_cameras: List[Dict[str, Any]]


class HourlyDetectionStats(BaseModel):
    hour: int
    detection_count: int
    avg_confidence: float
    top_classes: List[Dict[str, Any]]


# =======================
# Heatmap schema
# =======================
class DetectionHeatmap(BaseModel):
    camera_id: int
    width: int
    height: int
    heatmap_data: List[List[int]]
    max_value: int
    generated_at: datetime


# =======================
# Alert schema
# =======================
class DetectionAlert(BaseModel):
    camera_id: int
    timestamp: datetime
    class_name: str
    confidence: float
    message: str


# =======================
# Summary schema (daily/periodic)
# =======================
class DetectionSummary(BaseModel):
    camera_id: int
    summary_date: datetime
    total_detections: int
    detections_by_class: Dict[str, int]
    avg_confidence: float
    peak_hour: Optional[int] = None
    peak_detections: Optional[int] = None

    class Config:
        orm_mode = True

# =======================
# Update schema
# =======================
class DetectionUpdate(BaseModel):
    frame_id: Optional[str] = None
    class_name: Optional[str] = None
    confidence: Optional[float] = None
    bbox: Optional[Dict[str, float]] = None
    additional_data: Optional[Dict[str, Any]] = None


# =======================
# Read schema (for responses)
# =======================
class DetectionRead(DetectionBase):
    id: int

    class Config:
        orm_mode = True   # hoặc from_attributes = True nếu bạn dùng SQLAlchemy 2.x
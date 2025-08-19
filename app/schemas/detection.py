from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# =======================
# Base schema for Detection
# =======================
class DetectionBase(BaseModel):
    camera_id: str = Field(..., max_length=50)
    timestamp: datetime
    frame_id: Optional[str] = None
    objects: List[Dict[str, Any]] = Field(default_factory=list)
    object_count: Optional[int] = 0
    raw_data: Optional[str] = None
    confidence_avg: Optional[float] = None
    confidence_max: Optional[float] = None
    processing_time_ms: Optional[float] = None

# =======================
# Schema for creating Detection
# =======================
class DetectionCreate(DetectionBase):
    pass

# =======================
# Schema for reading Detection (API response)
# =======================
class DetectionRead(DetectionBase):
    id: int
    processed_at: Optional[datetime] = None
    age_seconds: Optional[float] = None
    is_recent: Optional[bool] = None
    has_person: Optional[bool] = None
    person_count: Optional[int] = None

    class Config:
        orm_mode = True

# =======================
# Schema for updating Detection (optional)
# =======================
class DetectionUpdate(BaseModel):
    objects: Optional[List[Dict[str, Any]]] = None
    object_count: Optional[int] = None
    confidence_avg: Optional[float] = None
    confidence_max: Optional[float] = None
    processed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    raw_data: Optional[str] = None

# =======================
# Schema for Detection summary
# =======================
class DetectionSummaryRead(BaseModel):
    camera_id: str
    period_start: datetime
    period_end: datetime
    period_type: str  # 'hour', 'day', 'week', 'month'
    total_detections: int
    total_objects: int
    unique_object_types: Optional[List[str]] = None
    object_type_counts: Optional[Dict[str, int]] = None

    class Config:
        orm_mode = True

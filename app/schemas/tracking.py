from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

# =======================
# Base schema for Tracking
# =======================
class TrackingBase(BaseModel):
    camera_id: str = Field(..., max_length=50)
    track_id: int
    object_type: str
    confidence: float
    timestamp: datetime
    location: Optional[Dict[str, Any]] = None  # Bounding box coordinates

# =======================
# Schema for creating Tracking
# =======================
class TrackingCreate(TrackingBase):
    pass

# =======================
# Schema for reading Tracking (API response)
# =======================
class TrackingRead(TrackingBase):
    id: int

    class Config:
        orm_mode = True

# =======================
# Schema for updating Tracking (optional)
# =======================
class TrackingUpdate(BaseModel):
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    location: Optional[Dict[str, Any]] = None

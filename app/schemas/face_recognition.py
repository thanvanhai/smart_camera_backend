from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

# =======================
# Base schema for FaceRecognition
# =======================
class FaceRecognitionBase(BaseModel):
    camera_id: str = Field(..., max_length=50)
    person_id: Optional[str] = None
    confidence: float
    timestamp: datetime
    face_embedding: Optional[bytes] = None  # Stored as base64 in API
    image_crop: Optional[bytes] = None      # Stored as base64 in API

# =======================
# Schema for creating FaceRecognition
# =======================
class FaceRecognitionCreate(FaceRecognitionBase):
    pass

# =======================
# Schema for reading FaceRecognition (API response)
# =======================
class FaceRecognitionRead(FaceRecognitionBase):
    id: int

    class Config:
        orm_mode = True

# =======================
# Schema for updating FaceRecognition (optional)
# =======================
class FaceRecognitionUpdate(BaseModel):
    person_id: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    face_embedding: Optional[bytes] = None
    image_crop: Optional[bytes] = None

"""
Face recognition-related schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FaceRecognitionCreate(BaseModel):
    """Schema for creating a face recognition record"""
    camera_id: int
    known_person_id: Optional[int] = None
    bbox_x: float = Field(..., ge=0.0, le=1.0)
    bbox_y: float = Field(..., ge=0.0, le=1.0)
    bbox_width: float = Field(..., ge=0.0, le=1.0)
    bbox_height: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime
    frame_id: Optional[str] = None
    face_encoding: Optional[str] = None  # Base64 encoded face features
    emotions: Optional[Dict[str, float]] = None
    age_estimate: Optional[int] = Field(None, ge=0, le=150)
    gender_estimate: Optional[str] = None
    additional_attributes: Optional[Dict[str, Any]] = None

class FaceRecognitionResponse(BaseModel):
    """Schema for face recognition response"""
    id: int
    camera_id: int
    known_person_id: Optional[int]
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: float
    timestamp: datetime
    frame_id: Optional[str]
    emotions: Optional[Dict[str, float]]
    age_estimate: Optional[int]
    gender_estimate: Optional[str]
    additional_attributes: Optional[Dict[str, Any]]
    created_at: datetime
    
    # Nested known person data
    known_person: Optional["KnownPersonResponse"] = None
    
    class Config:
        from_attributes = True

class KnownPersonCreate(BaseModel):
    """Schema for creating a known person"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    face_encodings: List[str] = Field(..., min_items=1)  # Base64 encoded face features
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True

class KnownPersonUpdate(BaseModel):
    """Schema for updating a known person"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class KnownPersonResponse(BaseModel):
    """Schema for known person response"""
    id: int
    name: str
    description: Optional[str]
    face_encodings_count: int
    metadata: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime]
    recognition_count: int
    
    class Config:
        from_attributes = True

class FaceRecognitionFilter(BaseModel):
    """Schema for filtering face recognition data"""
    camera_id: Optional[int] = None
    known_person_id: Optional[int] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    has_known_person: Optional[bool] = None
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    emotions: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class FaceRecognitionStats(BaseModel):
    """Schema for face recognition statistics"""
    total_recognitions: int
    known_persons_detected: int
    unknown_faces_detected: int
    recognitions_by_person: Dict[str, int]
    age_distribution: Dict[str, int]  # age ranges
    gender_distribution: Dict[str, int]
    emotion_distribution: Dict[str, int]
    recognitions_by_camera: List[Dict[str, Any]]

class FaceSearchRequest(BaseModel):
    """Schema for face search request"""
    face_encoding: str  # Base64 encoded face features
    similarity_threshold: float = Field(0.6, ge=0.0, le=1.0)
    max_results: int = Field(10, ge=1, le=100)

class FaceSearchResult(BaseModel):
    """Schema for face search results"""
    known_person_id: int
    known_person_name: str
    similarity_score: float
    last_recognition: Optional[datetime]
    recognition_count: int

class FaceBulkRecognitionCreate(BaseModel):
    """Schema for bulk face recognition creation"""
    recognitions: List[FaceRecognitionCreate] = Field(..., max_items=500)
    batch_id: Optional[str] = None

class FaceRecognitionAlert(BaseModel):
    """Schema for face recognition alerts"""
    recognition_id: int
    camera_id: int
    known_person_id: Optional[int]
    alert_type: str  # "vip_detected", "blacklist_detected", "unknown_frequent", etc.
    message: str
    confidence: float
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

class PersonRecognitionHistory(BaseModel):
    """Schema for person recognition history"""
    known_person_id: int
    known_person_name: str
    recognitions: List[Dict[str, Any]]  # recognition data with camera info
    first_seen: datetime
    last_seen: datetime
    total_recognitions: int
    cameras_detected: List[int]
    frequent_times: List[int]  # hours of day when frequently detected

# Forward reference resolution
FaceRecognitionResponse.model_rebuild()
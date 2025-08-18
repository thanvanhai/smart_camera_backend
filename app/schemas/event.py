from pydantic import BaseModel
from datetime import datetime

class PersonEventBase(BaseModel):
    person_id: int
    camera_id: int
    score: float
    passed: bool
    bbox: str  # JSON string
    timestamp: datetime | None = None

class PersonEventCreate(PersonEventBase):
    pass

class PersonEventRead(PersonEventBase):
    id: int

    class Config:
        orm_mode = True

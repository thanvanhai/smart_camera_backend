from pydantic import BaseModel

class CameraBase(BaseModel):
    name: str
    topic: str
    location: str | None = None

class CameraCreate(CameraBase):
    pass

class CameraRead(CameraBase):
    id: int

    class Config:
        orm_mode = True

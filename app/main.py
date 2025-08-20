from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, engine
from app.models import camera, detection, tracking, face_recognition
from app.schemas.camera import CameraCreate, CameraRead
from app.schemas.detection import DetectionCreate, DetectionRead
from app.schemas.tracking import TrackingCreate, TrackingRead
from app.schemas.face_recognition import FaceRecognitionCreate, FaceRecognitionRead
from app.services import camera_service, detection_service, tracking_service, face_recognition_service

app = FastAPI(title="Smart Camera Backend")

# Tạo database nếu chưa có
async def init_models():
    async with engine.begin() as conn:
        # Tạo tất cả bảng
        await conn.run_sync(camera.Base.metadata.create_all)
        await conn.run_sync(detection.Base.metadata.create_all)
        await conn.run_sync(tracking.Base.metadata.create_all)
        await conn.run_sync(face_recognition.Base.metadata.create_all)

@app.on_event("startup")
async def on_startup():
    await init_models()

# === Camera Routes ===
@app.get("/cameras", response_model=list[CameraRead])
async def read_cameras(db: AsyncSession = Depends(get_db)):
    return await camera_service.get_cameras(db)

@app.post("/cameras", response_model=CameraRead)
async def create_camera(camera_in: CameraCreate, db: AsyncSession = Depends(get_db)):
    return await camera_service.create_camera(db, camera_in)

# === Detection Routes ===
@app.get("/detections", response_model=list[DetectionRead])
async def read_detections(db: AsyncSession = Depends(get_db)):
    return await detection_service.get_detections(db)

@app.post("/detections", response_model=DetectionRead)
async def create_detection(detection_in: DetectionCreate, db: AsyncSession = Depends(get_db)):
    return await detection_service.create_detection(db, detection_in)

# === Tracking Routes ===
@app.get("/tracking", response_model=list[TrackingRead])
async def read_tracking(db: AsyncSession = Depends(get_db)):
    return await tracking_service.get_tracking_data(db)

@app.post("/tracking", response_model=TrackingRead)
async def create_tracking(tracking_in: TrackingCreate, db: AsyncSession = Depends(get_db)):
    return await tracking_service.create_tracking(db, tracking_in)

# === Face Recognition Routes ===
@app.get("/faces", response_model=list[FaceRecognitionRead])
async def read_faces(db: AsyncSession = Depends(get_db)):
    return await face_recognition_service.get_faces(db)

@app.post("/faces", response_model=FaceRecognitionRead)
async def create_face(face_in: FaceRecognitionCreate, db: AsyncSession = Depends(get_db)):
    return await face_recognition_service.create_face(db, face_in)

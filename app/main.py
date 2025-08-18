from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, engine
from app import models
from app.schemas.camera import CameraCreate, CameraRead
from app.schemas.person import PersonCreate, PersonRead
from app.schemas.event import PersonEventCreate, PersonEventRead
from app.crud import camera as crud_camera, person as crud_person, event as crud_event

app = FastAPI(title="Smart Camera Backend")

# Tạo database nếu chưa có
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# ✅ gọi init_models khi app start
@app.on_event("startup")
async def on_startup():
    await init_models()

# Routes Camera
@app.get("/cameras", response_model=list[CameraRead])
async def read_cameras(db: AsyncSession = Depends(get_db)):
    return await crud_camera.get_cameras(db)

@app.post("/cameras", response_model=CameraRead)
async def create_camera(camera: CameraCreate, db: AsyncSession = Depends(get_db)):
    return await crud_camera.create_camera(db, camera)

# Routes Person
@app.get("/persons", response_model=list[PersonRead])
async def read_persons(db: AsyncSession = Depends(get_db)):
    return await crud_person.get_persons(db)

@app.post("/persons", response_model=PersonRead)
async def create_person(person: PersonCreate, db: AsyncSession = Depends(get_db)):
    return await crud_person.create_person(db, person)

# Routes Event
@app.get("/events", response_model=list[PersonEventRead])
async def read_events(db: AsyncSession = Depends(get_db)):
    return await crud_event.get_events(db)

@app.post("/events", response_model=PersonEventRead)
async def create_event(event: PersonEventCreate, db: AsyncSession = Depends(get_db)):
    return await crud_event.create_event(db, event)

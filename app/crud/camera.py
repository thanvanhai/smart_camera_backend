from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Camera
from app.schemas.camera import CameraCreate

async def get_cameras(db: AsyncSession):
    result = await db.execute(select(Camera))
    return result.scalars().all()

async def create_camera(db: AsyncSession, camera: CameraCreate):
    db_camera = Camera(name=camera.name, topic=camera.topic, location=camera.location)
    db.add(db_camera)
    await db.commit()
    await db.refresh(db_camera)
    return db_camera

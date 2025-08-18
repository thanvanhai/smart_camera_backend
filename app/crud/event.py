from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import PersonEvent
from app.schemas.event import PersonEventCreate

async def get_events(db: AsyncSession):
    result = await db.execute(select(PersonEvent))
    return result.scalars().all()

async def create_event(db: AsyncSession, event: PersonEventCreate):
    db_event = PersonEvent(
        person_id=event.person_id,
        camera_id=event.camera_id,
        score=event.score,
        passed=event.passed,
        bbox=event.bbox,
        timestamp=event.timestamp
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event

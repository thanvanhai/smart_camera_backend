from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Person

async def get_person(db: AsyncSession, person_id: int):
    result = await db.execute(select(Person).where(Person.id == person_id))
    return result.scalar_one_or_none()

async def get_all_persons(db: AsyncSession):
    result = await db.execute(select(Person))
    return result.scalars().all()

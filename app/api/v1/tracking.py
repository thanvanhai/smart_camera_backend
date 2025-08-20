from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tracking import TrackingResponse, TrackingCreate
from app.services.tracking_service import TrackingService
from app.core.database import get_db_session

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.post("/", response_model=TrackingResponse, status_code=status.HTTP_201_CREATED)
async def create_tracking(tracking_in: TrackingCreate, db: AsyncSession = Depends(get_db_session)):
    service = TrackingService(db)
    return await service.create(tracking_in)


@router.get("/{tracking_id}", response_model=TrackingResponse)
async def get_tracking(tracking_id: int, db: AsyncSession = Depends(get_db_session)):
    service = TrackingService(db)
    tracking = await service.get(tracking_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return tracking


@router.get("/", response_model=List[TrackingResponse])
async def list_tracking(
    camera_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    service = TrackingService(db)
    return await service.list(camera_id=camera_id, skip=skip, limit=limit)


@router.put("/{tracking_id}", response_model=TrackingResponse)
async def update_tracking(tracking_id: int, tracking_in: TrackingCreate, db: AsyncSession = Depends(get_db_session)):
    """
    Tạm dùng TrackingCreate làm input cho update.
    Nếu muốn update một phần thì cần thêm TrackingUpdate schema với field Optional.
    """
    service = TrackingService(db)
    tracking = await service.get(tracking_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return await service.update(tracking, tracking_in)


@router.delete("/{tracking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracking(tracking_id: int, db: AsyncSession = Depends(get_db_session)):
    service = TrackingService(db)
    tracking = await service.get(tracking_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    await service.delete(tracking)

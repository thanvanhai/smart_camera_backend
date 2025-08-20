# app/api/v1/analytics.py

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/ping")
async def ping():
    return {"msg": "analytics module is working"}

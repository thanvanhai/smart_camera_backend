from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.face_recognition import FaceRecognitionRead, FaceRecognitionCreate, FaceRecognitionUpdate
from app.services.face_recognition_service import FaceRecognitionService
from app.core.database import get_db

router = APIRouter(prefix="/face_recognition", tags=["face_recognition"])


@router.post("/", response_model=FaceRecognitionRead, status_code=status.HTTP_201_CREATED)
def create_face_recognition(fr_in: FaceRecognitionCreate, db: Session = Depends(get_db)):
    service = FaceRecognitionService(db)
    return service.create(fr_in)


@router.get("/{fr_id}", response_model=FaceRecognitionRead)
def get_face_recognition(fr_id: int, db: Session = Depends(get_db)):
    service = FaceRecognitionService(db)
    fr = service.get(fr_id)
    if not fr:
        raise HTTPException(status_code=404, detail="FaceRecognition not found")
    return fr


@router.get("/", response_model=List[FaceRecognitionRead])
def list_face_recognition(camera_id: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = FaceRecognitionService(db)
    return service.list(camera_id=camera_id, skip=skip, limit=limit)


@router.put("/{fr_id}", response_model=FaceRecognitionRead)
def update_face_recognition(fr_id: int, fr_in: FaceRecognitionUpdate, db: Session = Depends(get_db)):
    service = FaceRecognitionService(db)
    fr = service.get(fr_id)
    if not fr:
        raise HTTPException(status_code=404, detail="FaceRecognition not found")
    return service.update(fr, fr_in)


@router.delete("/{fr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_face_recognition(fr_id: int, db: Session = Depends(get_db)):
    service = FaceRecognitionService(db)
    fr = service.get(fr_id)
    if not fr:
        raise HTTPException(status_code=404, detail="FaceRecognition not found")
    service.delete(fr)

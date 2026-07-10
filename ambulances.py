from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ambulance import Ambulance
from app.schemas.ambulance_schema import AmbulanceCreate, AmbulanceUpdate, AmbulanceOut

router = APIRouter(prefix="/ambulances", tags=["Ambulances"])


@router.get("/", response_model=List[AmbulanceOut])
def list_ambulances(status: Optional[str] = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Ambulance)
    if status:
        query = query.filter(Ambulance.status == status)
    return query.all()


@router.get("/{ambulance_id}", response_model=AmbulanceOut)
def get_ambulance(ambulance_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not ambulance:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    return ambulance


@router.post("/", response_model=AmbulanceOut)
def create_ambulance(ambulance: AmbulanceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    new_ambulance = Ambulance(**ambulance.model_dump())
    db.add(new_ambulance)
    db.commit()
    db.refresh(new_ambulance)
    return new_ambulance


@router.put("/{ambulance_id}", response_model=AmbulanceOut)
def update_ambulance(ambulance_id: int, updates: AmbulanceUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not ambulance:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(ambulance, key, value)
    db.commit()
    db.refresh(ambulance)
    return ambulance


@router.delete("/{ambulance_id}")
def delete_ambulance(ambulance_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not ambulance:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    db.delete(ambulance)
    db.commit()
    return {"detail": "Ambulance deleted successfully"}

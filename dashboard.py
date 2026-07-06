from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.patient import Patient
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.doctor import Doctor
from app.models.ambulance import Ambulance
from app.models.inventory import Inventory
from app.models.medicine import Medicine

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total_patients = db.query(func.count(Patient.id)).scalar()

    active_admissions = db.query(func.count(Admission.id)).filter(Admission.status == "admitted").scalar()

    total_icu_beds = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar()
    occupied_icu_beds = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu", Bed.status == "occupied").scalar()
    icu_occupancy_rate = round((occupied_icu_beds / total_icu_beds) * 100, 2) if total_icu_beds > 0 else 0

    total_beds = db.query(func.count(Bed.id)).scalar()
    available_beds = db.query(func.count(Bed.id)).filter(Bed.status == "available").scalar()

    total_doctors = db.query(func.count(Doctor.id)).scalar()

    total_ambulances = db.query(func.count(Ambulance.id)).scalar()
    available_ambulances = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "available").scalar()

    low_stock_medicines = db.query(func.count(Inventory.id)).filter(Inventory.current_stock <= Inventory.reorder_level).scalar()

    return {
        "total_patients": total_patients,
        "active_admissions": active_admissions,
        "icu_occupancy_rate_percent": icu_occupancy_rate,
        "total_beds": total_beds,
        "available_beds": available_beds,
        "total_doctors": total_doctors,
        "total_ambulances": total_ambulances,
        "available_ambulances": available_ambulances,
        "low_stock_medicine_alerts": low_stock_medicines
    }

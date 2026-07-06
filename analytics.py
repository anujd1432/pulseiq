from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.inventory import Inventory
from app.models.medicine import Medicine
from app.models.ambulance import Ambulance
from app.models.patient import Patient

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/bed-turnover-rate")
def bed_turnover_rate(days: int = 30, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    since = datetime.utcnow() - timedelta(days=days)
    discharges = db.query(func.count(Admission.id)).filter(
        Admission.discharge_date.isnot(None),
        Admission.discharge_date >= since
    ).scalar()
    total_beds = db.query(func.count(Bed.id)).scalar()
    rate = round(discharges / total_beds, 2) if total_beds > 0 else 0
    return {
        "period_days": days,
        "discharges_in_period": discharges,
        "total_beds": total_beds,
        "bed_turnover_rate": rate
    }

@router.get("/average-length-of-stay")
def average_length_of_stay(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    discharged = db.query(Admission).filter(Admission.discharge_date.isnot(None)).all()
    if not discharged:
        return {"average_length_of_stay_days": 0, "sample_size": 0}
    total_days = sum((a.discharge_date - a.admission_date).days for a in discharged)
    alos = round(total_days / len(discharged), 2)
    return {
        "average_length_of_stay_days": alos,
        "sample_size": len(discharged)
    }

@router.get("/doctor-workload")
def doctor_workload(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doctors = db.query(Doctor).all()
    result = []
    for doc in doctors:
        patient_count = db.query(func.count(Admission.id)).filter(Admission.doctor_id == doc.id).scalar()
        utilization = round((patient_count / doc.max_patients_per_day) * 100, 2) if doc.max_patients_per_day > 0 else 0
        result.append({
            "doctor_id": doc.id,
            "specialization": doc.specialization,
            "shift": doc.shift,
            "assigned_patients": patient_count,
            "max_patients_per_day": doc.max_patients_per_day,
            "utilization_percent": utilization
        })
    return {"doctors": result}

@router.get("/icu-occupancy-trend")
def icu_occupancy_trend(days: int = 7, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total_icu_beds = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar()
    trend = []
    for i in range(days):
        day = datetime.utcnow().date() - timedelta(days=i)
        occupied_that_day = db.query(func.count(Admission.id)).filter(
            Admission.admission_date <= datetime.combine(day, datetime.max.time()),
            (Admission.discharge_date.is_(None)) | (Admission.discharge_date >= datetime.combine(day, datetime.min.time()))
        ).scalar()
        rate = round((occupied_that_day / total_icu_beds) * 100, 2) if total_icu_beds > 0 else 0
        trend.append({"date": str(day), "icu_occupancy_percent": rate})
    trend.reverse()
    return {"total_icu_beds": total_icu_beds, "trend": trend}

@router.get("/medicine-wastage")
def medicine_wastage(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    today = datetime.utcnow().date()
    inventories = db.query(Inventory).all()
    total_stock = sum(i.current_stock for i in inventories) or 1
    expired_stock = sum(i.current_stock for i in inventories if i.expiry_date and i.expiry_date < today)
    wastage_percent = round((expired_stock / total_stock) * 100, 2)
    return {
        "total_stock_units": total_stock,
        "expired_stock_units": expired_stock,
        "medicine_wastage_percent": wastage_percent
    }

@router.get("/stock-out-alerts")
def stock_out_alerts(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    low_stock = db.query(Inventory, Medicine).join(Medicine, Inventory.medicine_id == Medicine.id).filter(
        Inventory.current_stock <= Inventory.reorder_level
    ).all()
    alerts = [
        {
            "medicine_name": med.name,
            "current_stock": inv.current_stock,
            "reorder_level": inv.reorder_level,
            "status": "OUT OF STOCK" if inv.current_stock == 0 else "LOW STOCK"
        }
        for inv, med in low_stock
    ]
    return {"total_alerts": len(alerts), "alerts": alerts}

@router.get("/readmission-rate")
def readmission_rate(days: int = 30, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    since = datetime.utcnow() - timedelta(days=days)
    discharged = db.query(Admission).filter(Admission.discharge_date.isnot(None), Admission.discharge_date >= since).all()
    if not discharged:
        return {"readmission_rate_percent": 0, "total_discharges": 0, "readmissions": 0}

    readmit_count = 0
    for adm in discharged:
        future_admission = db.query(Admission).filter(
            Admission.patient_id == adm.patient_id,
            Admission.id != adm.id,
            Admission.admission_date > adm.discharge_date,
            Admission.admission_date <= adm.discharge_date + timedelta(days=30)
        ).first()
        if future_admission:
            readmit_count += 1

    rate = round((readmit_count / len(discharged)) * 100, 2)
    return {
        "period_days": days,
        "total_discharges": len(discharged),
        "readmissions": readmit_count,
        "readmission_rate_percent": rate
    }

@router.get("/ambulance-utilization")
def ambulance_utilization(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total = db.query(func.count(Ambulance.id)).scalar()
    on_trip = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "on_trip").scalar()
    avg_response_time = db.query(func.avg(Ambulance.last_response_time_minutes)).scalar()
    utilization = round((on_trip / total) * 100, 2) if total > 0 else 0
    return {
        "total_ambulances": total,
        "on_trip": on_trip,
        "utilization_percent": utilization,
        "avg_response_time_minutes": round(avg_response_time, 2) if avg_response_time else 0
    }

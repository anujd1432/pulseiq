from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.bed import Bed
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.admission import Admission
from app.models.ambulance import Ambulance
from app.models.inventory import Inventory
from app.models.bloodbank import BloodBank


def get_department_states(db: Session):
    departments = db.query(Department).all()
    states = []
    for dept in departments:
        beds = db.query(Bed).filter(Bed.department_id == dept.id).all()
        total_beds = len(beds)
        occupied = len([b for b in beds if b.status == "occupied"])
        occupancy_pct = round((occupied / total_beds) * 100, 1) if total_beds > 0 else 0

        doctors = db.query(Doctor).filter(Doctor.department_id == dept.id).all()
        doctor_count = len(doctors)

        active_admissions = db.query(func.count(Admission.id)).join(
            Doctor, Admission.doctor_id == Doctor.id
        ).filter(Doctor.department_id == dept.id, Admission.status == "admitted").scalar()

        states.append({
            "department_id": dept.id,
            "department_name": dept.name,
            "total_beds": total_beds,
            "occupied_beds": occupied,
            "occupancy_percent": occupancy_pct,
            "doctor_count": doctor_count,
            "active_admissions": active_admissions
        })
    return states


def get_resource_snapshot(db: Session):
    total_beds = db.query(func.count(Bed.id)).scalar()
    occupied_beds = db.query(func.count(Bed.id)).filter(Bed.status == "occupied").scalar()

    total_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar()
    occupied_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu", Bed.status == "occupied").scalar()

    total_ambulances = db.query(func.count(Ambulance.id)).scalar()
    available_ambulances = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "available").scalar()

    low_stock_medicines = db.query(func.count(Inventory.id)).filter(Inventory.current_stock <= Inventory.reorder_level).scalar()
    total_medicines = db.query(func.count(Inventory.id)).scalar()

    total_blood_units = db.query(func.sum(BloodBank.units_available)).scalar() or 0

    return {
        "beds": {"total": total_beds, "occupied": occupied_beds, "available": total_beds - occupied_beds},
        "icu": {"total": total_icu, "occupied": occupied_icu, "occupancy_percent": round((occupied_icu / total_icu) * 100, 1) if total_icu > 0 else 0},
        "ambulances": {"total": total_ambulances, "available": available_ambulances},
        "medicines": {"total_tracked": total_medicines, "low_stock_count": low_stock_medicines},
        "blood_bank": {"total_units_available": total_blood_units}
    }


def calculate_health_score(db: Session):
    """
    Composite score (0-100), weighted across 5 factors:
    - Bed availability (25%)
    - ICU headroom (25%)
    - Staffing adequacy (20%)
    - Medicine stock health (15%)
    - Ambulance availability (15%)
    Higher score = healthier operational state.
    """
    total_beds = db.query(func.count(Bed.id)).scalar() or 1
    available_beds = db.query(func.count(Bed.id)).filter(Bed.status == "available").scalar()
    bed_score = min(100, (available_beds / total_beds) * 100 * 1.5)

    total_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar() or 1
    occupied_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu", Bed.status == "occupied").scalar()
    icu_occupancy_pct = (occupied_icu / total_icu) * 100
    icu_score = max(0, 100 - icu_occupancy_pct)

    doctors = db.query(Doctor).all()
    if doctors:
        overloaded = 0
        for doc in doctors:
            active = db.query(func.count(Admission.id)).filter(Admission.doctor_id == doc.id, Admission.status == "admitted").scalar()
            util = (active / doc.max_patients_per_day) * 100 if doc.max_patients_per_day > 0 else 0
            if util >= 80:
                overloaded += 1
        staffing_score = max(0, 100 - (overloaded / len(doctors)) * 100)
    else:
        staffing_score = 50

    total_medicines = db.query(func.count(Inventory.id)).scalar() or 1
    low_stock = db.query(func.count(Inventory.id)).filter(Inventory.current_stock <= Inventory.reorder_level).scalar()
    medicine_score = max(0, 100 - (low_stock / total_medicines) * 100)

    total_ambulances = db.query(func.count(Ambulance.id)).scalar() or 1
    available_ambulances = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "available").scalar()
    ambulance_score = (available_ambulances / total_ambulances) * 100

    weighted_score = (
        bed_score * 0.25 +
        icu_score * 0.25 +
        staffing_score * 0.20 +
        medicine_score * 0.15 +
        ambulance_score * 0.15
    )

    if weighted_score >= 80:
        status = "Excellent"
    elif weighted_score >= 60:
        status = "Good"
    elif weighted_score >= 40:
        status = "Fair"
    else:
        status = "Critical"

    return {
        "overall_health_score": round(weighted_score, 1),
        "status": status,
        "breakdown": {
            "bed_availability_score": round(bed_score, 1),
            "icu_headroom_score": round(icu_score, 1),
            "staffing_adequacy_score": round(staffing_score, 1),
            "medicine_stock_score": round(medicine_score, 1),
            "ambulance_availability_score": round(ambulance_score, 1),
        },
        "weights": {
            "bed_availability": "25%",
            "icu_headroom": "25%",
            "staffing_adequacy": "20%",
            "medicine_stock": "15%",
            "ambulance_availability": "15%"
        }
    }

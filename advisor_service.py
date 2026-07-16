from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.bed import Bed
from app.models.admission import Admission
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.inventory import Inventory
from app.models.medicine import Medicine
from app.models.ambulance import Ambulance


def _detect_intent(question: str) -> str:
    q = question.lower()

    if any(kw in q for kw in ["crowded", "crowd", "busy", "occupancy", "occupied"]):
        return "occupancy_reason"
    if any(kw in q for kw in ["staff", "doctor", "workload", "understaffed"]):
        return "staffing_recommendation"
    if any(kw in q for kw in ["medicine", "stock", "inventory", "run out", "shortage"]):
        return "medicine_recommendation"
    if any(kw in q for kw in ["increase", "resources", "tomorrow", "prepare"]):
        return "resource_recommendation"
    if any(kw in q for kw in ["ambulance", "response time"]):
        return "ambulance_status"
    if any(kw in q for kw in ["icu"]):
        return "icu_status"
    return "general_summary"


def _occupancy_reason(db: Session) -> dict:
    total_beds = db.query(func.count(Bed.id)).scalar()
    occupied = db.query(func.count(Bed.id)).filter(Bed.status == "occupied").scalar()
    rate = round((occupied / total_beds) * 100, 1) if total_beds > 0 else 0

    dept_load = db.query(Department.name, func.count(Admission.id)).join(
        Doctor, Admission.doctor_id == Doctor.id
    ).join(Department, Doctor.department_id == Department.id).filter(
        Admission.status == "admitted"
    ).group_by(Department.name).order_by(func.count(Admission.id).desc()).all()

    top_dept = dept_load[0] if dept_load else None

    data = {"overall_occupancy_percent": rate, "occupied_beds": occupied, "total_beds": total_beds,
            "department_breakdown": [{"department": d[0], "active_admissions": d[1]} for d in dept_load]}

    if top_dept:
        answer = (f"Overall bed occupancy is at {rate}% ({occupied}/{total_beds} beds occupied). "
                   f"The {top_dept[0]} department has the highest active patient load with {top_dept[1]} admissions, "
                   f"which is likely the main driver of current crowding.")
    else:
        answer = f"Overall bed occupancy is at {rate}% ({occupied}/{total_beds} beds occupied). No active admissions data available to pinpoint a specific department."

    return {"answer": answer, "data": data}


def _staffing_recommendation(db: Session) -> dict:
    doctors = db.query(Doctor).all()
    overloaded = []
    for doc in doctors:
        patient_count = db.query(func.count(Admission.id)).filter(
            Admission.doctor_id == doc.id, Admission.status == "admitted"
        ).scalar()
        utilization = round((patient_count / doc.max_patients_per_day) * 100, 1) if doc.max_patients_per_day > 0 else 0
        if utilization >= 80:
            dept = db.query(Department).filter(Department.id == doc.department_id).first()
            overloaded.append({
                "doctor_id": doc.id,
                "specialization": doc.specialization,
                "department": dept.name if dept else "Unknown",
                "utilization_percent": utilization
            })

    overloaded.sort(key=lambda x: x["utilization_percent"], reverse=True)
    data = {"overloaded_doctors": overloaded, "count": len(overloaded)}

    if overloaded:
        top = overloaded[0]
        answer = (f"{len(overloaded)} doctor(s) are currently at or above 80% capacity. "
                   f"The {top['department']} department needs the most attention - Dr. (ID {top['doctor_id']}, "
                   f"{top['specialization']}) is at {top['utilization_percent']}% utilization. "
                   f"Consider reallocating staff or bringing in additional support for this department.")
    else:
        answer = "No doctors are currently overloaded (all below 80% utilization). Staffing levels look adequate right now."

    return {"answer": answer, "data": data}


def _medicine_recommendation(db: Session) -> dict:
    low_stock = db.query(Inventory, Medicine).join(Medicine, Inventory.medicine_id == Medicine.id).filter(
        Inventory.current_stock <= Inventory.reorder_level
    ).all()

    alerts = [{"medicine": med.name, "current_stock": inv.current_stock, "reorder_level": inv.reorder_level} for inv, med in low_stock]
    data = {"low_stock_medicines": alerts, "count": len(alerts)}

    if alerts:
        names = ", ".join(a["medicine"] for a in alerts[:5])
        answer = (f"{len(alerts)} medicine(s) are at or below reorder level, including: {names}. "
                   f"Procurement should prioritize these to avoid stock-outs.")
    else:
        answer = "All medicines are currently above their reorder levels. No immediate procurement action needed."

    return {"answer": answer, "data": data}


def _resource_recommendation(db: Session) -> dict:
    total_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar()
    occupied_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu", Bed.status == "occupied").scalar()
    icu_rate = round((occupied_icu / total_icu) * 100, 1) if total_icu > 0 else 0

    low_stock_count = db.query(Inventory).filter(Inventory.current_stock <= Inventory.reorder_level).count()

    available_ambulances = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "available").scalar()

    recommendations = []
    if icu_rate >= 80:
        recommendations.append(f"ICU occupancy is at {icu_rate}% - consider preparing additional ICU capacity.")
    if low_stock_count > 0:
        recommendations.append(f"{low_stock_count} medicine(s) are low on stock - prioritize procurement.")
    if available_ambulances <= 1:
        recommendations.append(f"Only {available_ambulances} ambulance(s) available - consider scheduling more for standby.")

    data = {"icu_occupancy_percent": icu_rate, "low_stock_medicine_count": low_stock_count, "available_ambulances": available_ambulances}

    if recommendations:
        answer = " ".join(recommendations)
    else:
        answer = "Current resource levels (ICU, medicine stock, ambulances) look stable. No urgent action needed for tomorrow."

    return {"answer": answer, "data": data}


def _ambulance_status(db: Session) -> dict:
    total = db.query(func.count(Ambulance.id)).scalar()
    available = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "available").scalar()
    on_trip = db.query(func.count(Ambulance.id)).filter(Ambulance.status == "on_trip").scalar()
    avg_response = db.query(func.avg(Ambulance.last_response_time_minutes)).scalar()

    data = {"total": total, "available": available, "on_trip": on_trip, "avg_response_time_minutes": round(avg_response, 1) if avg_response else 0}
    answer = (f"Out of {total} ambulances, {available} are available and {on_trip} are currently on trips. "
               f"Average response time is {data['avg_response_time_minutes']} minutes.")
    return {"answer": answer, "data": data}


def _icu_status(db: Session) -> dict:
    total_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar()
    occupied_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu", Bed.status == "occupied").scalar()
    rate = round((occupied_icu / total_icu) * 100, 1) if total_icu > 0 else 0

    data = {"total_icu_beds": total_icu, "occupied_icu_beds": occupied_icu, "occupancy_percent": rate}
    if rate >= 85:
        answer = f"ICU occupancy is critically high at {rate}% ({occupied_icu}/{total_icu} beds). Immediate attention recommended."
    elif rate >= 60:
        answer = f"ICU occupancy is at {rate}% ({occupied_icu}/{total_icu} beds) - moderate load, worth monitoring."
    else:
        answer = f"ICU occupancy is at {rate}% ({occupied_icu}/{total_icu} beds) - currently within safe capacity."
    return {"answer": answer, "data": data}


def _general_summary(db: Session) -> dict:
    total_patients = db.query(func.count(Admission.id)).filter(Admission.status == "admitted").scalar()
    total_beds = db.query(func.count(Bed.id)).scalar()
    available_beds = db.query(func.count(Bed.id)).filter(Bed.status == "available").scalar()
    data = {"active_admissions": total_patients, "total_beds": total_beds, "available_beds": available_beds}
    answer = (f"Currently there are {total_patients} active admissions, with {available_beds} of {total_beds} beds available. "
               f"Try asking about ICU occupancy, staffing, medicine stock, or ambulance status for more specific insights.")
    return {"answer": answer, "data": data}


def answer_question(db: Session, question: str) -> dict:
    intent = _detect_intent(question)

    handlers = {
        "occupancy_reason": _occupancy_reason,
        "staffing_recommendation": _staffing_recommendation,
        "medicine_recommendation": _medicine_recommendation,
        "resource_recommendation": _resource_recommendation,
        "ambulance_status": _ambulance_status,
        "icu_status": _icu_status,
        "general_summary": _general_summary,
    }

    result = handlers[intent](db)
    return {
        "question": question,
        "intent_detected": intent,
        "answer": result["answer"],
        "supporting_data": result["data"]
    }

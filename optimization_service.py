from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.bed import Bed
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.admission import Admission
from app.models.inventory import Inventory
from app.models.medicine import Medicine
from app.ml.forecast_medicine import forecast_medicine_demand
from app.ml.forecast_hospital import forecast_icu_demand


def recommend_staff_allocation(db: Session):
    departments = db.query(Department).all()
    recommendations = []

    for dept in departments:
        doctors = db.query(Doctor).filter(Doctor.department_id == dept.id).all()
        if not doctors:
            continue

        total_capacity = sum(d.max_patients_per_day for d in doctors)
        active_load = db.query(func.count(Admission.id)).join(
            Doctor, Admission.doctor_id == Doctor.id
        ).filter(Doctor.department_id == dept.id, Admission.status == "admitted").scalar()

        utilization = round((active_load / total_capacity) * 100, 1) if total_capacity > 0 else 0

        if utilization >= 85:
            action = "URGENT: Add more doctors or redistribute patients"
            priority = "HIGH"
        elif utilization >= 65:
            action = "Monitor closely, consider adding 1 doctor if trend continues"
            priority = "MEDIUM"
        else:
            action = "Staffing adequate"
            priority = "LOW"

        recommendations.append({
            "department": dept.name,
            "doctor_count": len(doctors),
            "active_admissions": active_load,
            "utilization_percent": utilization,
            "priority": priority,
            "recommendation": action
        })

    recommendations.sort(key=lambda x: x["utilization_percent"], reverse=True)
    return recommendations


def recommend_bed_allocation(db: Session):
    departments = db.query(Department).all()
    dept_stats = []

    for dept in departments:
        beds = db.query(Bed).filter(Bed.department_id == dept.id).all()
        if not beds:
            continue
        total = len(beds)
        occupied = len([b for b in beds if b.status == "occupied"])
        occupancy_pct = round((occupied / total) * 100, 1)
        dept_stats.append({
            "department": dept.name,
            "total_beds": total,
            "occupied_beds": occupied,
            "occupancy_percent": occupancy_pct
        })

    if not dept_stats:
        return {"recommendations": [], "message": "No bed data available"}

    overloaded = [d for d in dept_stats if d["occupancy_percent"] >= 85]
    underused = [d for d in dept_stats if d["occupancy_percent"] <= 40]

    recommendations = []
    for over in overloaded:
        if underused:
            best_source = min(underused, key=lambda x: x["occupancy_percent"])
            recommendations.append({
                "action": "REALLOCATE",
                "priority": "HIGH",
                "message": f"{over['department']} is at {over['occupancy_percent']}% occupancy. Consider reallocating beds from {best_source['department']} (only {best_source['occupancy_percent']}% occupied)."
            })
        else:
            recommendations.append({
                "action": "ADD_CAPACITY",
                "priority": "HIGH",
                "message": f"{over['department']} is at {over['occupancy_percent']}% occupancy with no underused department to reallocate from. Consider adding new beds."
            })

    return {"department_occupancy": dept_stats, "recommendations": recommendations}


def recommend_medicine_procurement(db: Session, horizon_days: int = 7):
    medicines = db.query(Medicine).all()
    recommendations = []

    for med in medicines:
        inventory = db.query(Inventory).filter(Inventory.medicine_id == med.id).first()
        if not inventory:
            continue

        forecast = forecast_medicine_demand(db, med.id, horizon_days)
        predicted_demand = forecast["total_predicted_demand"] if forecast else 0

        shortfall = round(predicted_demand - inventory.current_stock, 1)

        if shortfall > 0:
            suggested_order = max(round(shortfall * 1.2), inventory.reorder_level)
            recommendations.append({
                "medicine_name": med.name,
                "current_stock": inventory.current_stock,
                "predicted_demand_next_days": predicted_demand,
                "shortfall": shortfall,
                "suggested_order_quantity": suggested_order,
                "priority": "HIGH" if inventory.current_stock == 0 else "MEDIUM"
            })

    recommendations.sort(key=lambda x: x["shortfall"], reverse=True)
    return {"horizon_days": horizon_days, "procurement_recommendations": recommendations}


def emergency_preparedness_plan(db: Session):
    total_icu = db.query(func.count(Bed.id)).filter(Bed.bed_type == "icu").scalar()
    icu_forecast = forecast_icu_demand(db, horizon_days=7, total_icu_beds=total_icu)

    plan = []
    if icu_forecast:
        max_day = max(icu_forecast["daily_forecast"], key=lambda x: x["predicted_occupancy_percent"])
        if max_day["predicted_occupancy_percent"] >= 85:
            plan.append({
                "concern": "ICU capacity risk",
                "detail": f"ICU occupancy forecasted to reach {max_day['predicted_occupancy_percent']}% on {max_day['date']}.",
                "recommended_action": "Prepare additional ICU beds and put extra nursing staff on standby for this date."
            })

    low_stock_meds = db.query(Inventory).filter(Inventory.current_stock == 0).count()
    if low_stock_meds > 0:
        plan.append({
            "concern": "Medicine stock-outs",
            "detail": f"{low_stock_meds} medicine(s) are completely out of stock.",
            "recommended_action": "Emergency procurement needed to avoid care disruption."
        })

    if not plan:
        plan.append({
            "concern": "None",
            "detail": "No immediate emergency risks detected based on current forecasts and stock levels.",
            "recommended_action": "Continue standard monitoring."
        })

    return {"emergency_preparedness_plan": plan}

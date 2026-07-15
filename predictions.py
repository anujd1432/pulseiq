from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.ml.forecast_medicine import forecast_medicine_demand
from app.ml.forecast_hospital import forecast_patient_inflow, forecast_icu_demand
from app.models.bed import Bed

router = APIRouter(prefix="/predict", tags=["Predictions"])


@router.get("/medicine-demand/{medicine_id}")
def predict_medicine_demand(medicine_id: int, horizon_days: int = 7, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    result = forecast_medicine_demand(db, medicine_id, horizon_days)
    if result is None:
        raise HTTPException(status_code=400, detail="Not enough consumption history to forecast")

    inventory = db.query(Inventory).filter(Inventory.medicine_id == medicine_id).first()
    current_stock = inventory.current_stock if inventory else 0

    stock_out_risk = current_stock < result["total_predicted_demand"]

    result["medicine_name"] = medicine.name
    result["current_stock"] = current_stock
    result["stock_out_risk"] = stock_out_risk
    return result


@router.get("/medicine-demand-all")
def predict_all_medicines(horizon_days: int = 7, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    medicines = db.query(Medicine).all()
    results = []
    for med in medicines:
        forecast = forecast_medicine_demand(db, med.id, horizon_days)
        if forecast is None:
            continue
        inventory = db.query(Inventory).filter(Inventory.medicine_id == med.id).first()
        current_stock = inventory.current_stock if inventory else 0
        results.append({
            "medicine_id": med.id,
            "medicine_name": med.name,
            "current_stock": current_stock,
            "total_predicted_demand": forecast["total_predicted_demand"],
            "stock_out_risk": current_stock < forecast["total_predicted_demand"]
        })
    return {"horizon_days": horizon_days, "medicines": results}

@router.get("/patient-inflow")
def predict_patient_inflow(horizon_days: int = 7, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    result = forecast_patient_inflow(db, horizon_days)
    if result is None:
        raise HTTPException(status_code=400, detail="Not enough historical data to forecast")
    return result


@router.get("/icu-demand")
def predict_icu_demand(horizon_days: int = 7, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total_icu_beds = db.query(Bed).filter(Bed.bed_type == "icu").count()
    result = forecast_icu_demand(db, horizon_days, total_icu_beds)
    if result is None:
        raise HTTPException(status_code=400, detail="Not enough historical data to forecast")
    return result
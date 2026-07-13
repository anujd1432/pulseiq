from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ResourceActionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    metric_type: str  # icu_occupied_beds, patient_inflow, total_occupied_beds
    action_date: datetime

class ResourceActionOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    metric_type: str
    action_date: datetime

    class Config:
        from_attributes = True

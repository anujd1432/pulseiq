from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base

class ResourceAction(Base):
    __tablename__ = "resource_actions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    metric_type = Column(String(50), nullable=False)  # icu_occupied_beds, patient_inflow, total_occupied_beds
    action_date = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

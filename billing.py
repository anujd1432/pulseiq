from sqlalchemy import Column, Integer, Float, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base

class Billing(Base):
    __tablename__ = "billing"

    id = Column(Integer, primary_key=True, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    room_charges = Column(Float, default=0)
    doctor_fee = Column(Float, default=0)
    medicine_charges = Column(Float, default=0)
    other_charges = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    payment_status = Column(String(20), default="pending")
    billing_date = Column(TIMESTAMP(timezone=True), server_default=func.now())

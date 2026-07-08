from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150))
    age = Column(Integer)
    gender = Column(String(10))
    contact = Column(String(20))
    address = Column(String)
    blood_group = Column(String(5))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

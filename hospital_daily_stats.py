from sqlalchemy import Column, Integer, Date
from app.core.database import Base

class HospitalDailyStats(Base):
    __tablename__ = "hospital_daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    patient_inflow = Column(Integer, nullable=False)
    icu_occupied_beds = Column(Integer, nullable=False)
    total_occupied_beds = Column(Integer, nullable=False)

import random
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.hospital_daily_stats import HospitalDailyStats
from app.models.bed import Bed

db = SessionLocal()

total_icu_beds = db.query(Bed).filter(Bed.bed_type == "icu").count()
total_beds = db.query(Bed).count()

today = datetime.utcnow().date()

print(f"Seeding 90 days of hospital daily stats (ICU beds: {total_icu_beds}, Total beds: {total_beds})...")

base_inflow = 15
trend = 0.03

for i in range(90, 0, -1):
    day = today - timedelta(days=i)
    weekday_factor = 1.2 if day.weekday() in [0, 1] else (0.75 if day.weekday() in [5, 6] else 1.0)
    seasonal_factor = 1.15 if day.month in [12, 1, 7, 8] else 1.0
    noise = random.uniform(0.85, 1.15)
    trend_factor = 1 + (trend * (90 - i) / 90)

    inflow = max(0, round(base_inflow * weekday_factor * seasonal_factor * trend_factor * noise))

    icu_occupancy_ratio = min(0.95, random.uniform(0.4, 0.85) * trend_factor)
    icu_occupied = round(total_icu_beds * icu_occupancy_ratio) if total_icu_beds > 0 else 0

    total_occupancy_ratio = min(0.95, random.uniform(0.5, 0.9))
    total_occupied = round(total_beds * total_occupancy_ratio) if total_beds > 0 else 0

    record = HospitalDailyStats(
        date=day,
        patient_inflow=inflow,
        icu_occupied_beds=icu_occupied,
        total_occupied_beds=total_occupied
    )
    db.add(record)

db.commit()
db.close()
print("Hospital daily stats seeding complete!")

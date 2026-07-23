import random
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment

db = SessionLocal()

patients = db.query(Patient).all()
doctors = db.query(Doctor).all()

print(f"Seeding OPD appointments for last 30 days...")

count = 0
for day_offset in range(30, 0, -1):
    day = datetime.utcnow().date() - timedelta(days=day_offset)
    is_weekend = day.weekday() in [5, 6]
    num_appointments = random.randint(5, 12) if is_weekend else random.randint(15, 35)

    for _ in range(num_appointments):
        patient = random.choice(patients)
        doctor = random.choice(doctors)

        hour = random.choices(
            population=[9, 10, 11, 12, 14, 15, 16, 17, 18],
            weights=[10, 15, 15, 8, 10, 15, 15, 10, 5]
        )[0]
        minute = random.randint(0, 59)
        appointment_time = datetime.combine(day, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

        waiting_time = random.randint(5, 60)
        consultation_time = random.randint(8, 30)
        status = random.choices(["completed", "cancelled", "no_show"], weights=[80, 12, 8])[0]

        appt = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_time=appointment_time,
            status=status,
            waiting_time_minutes=waiting_time if status == "completed" else None,
            consultation_time_minutes=consultation_time if status == "completed" else None
        )
        db.add(appt)
        count += 1

db.commit()
db.close()
print(f"Seeded {count} appointments successfully!")

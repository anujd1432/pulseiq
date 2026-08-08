import random
from app.core.database import SessionLocal
from app.models.admission import Admission
from app.models.billing import Billing

db = SessionLocal()

admissions = db.query(Admission).all()
print(f"Seeding billing records for {len(admissions)} admissions...")

payment_statuses = ["paid", "pending", "partially_paid"]

for adm in admissions:
    room_charges = round(random.uniform(2000, 8000), 2)
    doctor_fee = round(random.uniform(500, 3000), 2)
    medicine_charges = round(random.uniform(300, 2500), 2)
    other_charges = round(random.uniform(100, 1000), 2)
    total = round(room_charges + doctor_fee + medicine_charges + other_charges, 2)

    status = "paid" if adm.status == "discharged" else random.choices(payment_statuses, weights=[30, 50, 20])[0]

    bill = Billing(
        admission_id=adm.id,
        patient_id=adm.patient_id,
        room_charges=room_charges,
        doctor_fee=doctor_fee,
        medicine_charges=medicine_charges,
        other_charges=other_charges,
        total_amount=total,
        payment_status=status
    )
    db.add(bill)

db.commit()
db.close()
print("Billing seeding complete!")

import random
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.user import User
from app.models.patient import Patient
from app.models.bed import Bed
from app.models.admission import Admission
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.bloodbank import BloodBank
from app.models.ambulance import Ambulance
from app.core.security import hash_password

db = SessionLocal()

print("Seeding departments...")
dept_names = ["General Medicine", "ICU", "Emergency", "Pediatrics", "Cardiology"]
departments = []
for name in dept_names:
    d = Department(name=name, floor=f"Floor {random.randint(1,5)}")
    db.add(d)
    departments.append(d)
db.commit()
for d in departments:
    db.refresh(d)

print("Seeding doctor user accounts + doctors...")
first_names = ["Amit", "Priya", "Rahul", "Sneha", "Vikram", "Anjali", "Karan", "Neha", "Rohan", "Divya"]
last_names = ["Sharma", "Verma", "Gupta", "Mehta", "Patel", "Nair", "Iyer", "Reddy", "Singh", "Kapoor"]
specializations = ["Cardiology", "Pediatrics", "General Medicine", "Emergency Medicine", "Orthopedics"]
doctors = []
for i in range(10):
    full_name = f"Dr. {first_names[i]} {last_names[i]}"
    email = f"doctor{i+1}@pulseiq.com"
    u = User(full_name=full_name, email=email, password_hash=hash_password("doctor1234"), role="doctor")
    db.add(u)
    db.commit()
    db.refresh(u)
    doc = Doctor(
        user_id=u.id,
        department_id=random.choice(departments).id,
        specialization=random.choice(specializations),
        shift=random.choice(["Morning", "Evening", "Night"]),
        max_patients_per_day=random.randint(15, 30)
    )
    db.add(doc)
    doctors.append(doc)
db.commit()
for d in doctors:
    db.refresh(d)

print("Seeding beds...")
bed_types = ["general", "icu", "emergency", "pediatric"]
beds = []
for dept in departments:
    for i in range(6):
        bed_type = random.choices(bed_types, weights=[50, 20, 15, 15])[0]
        status = random.choices(["available", "occupied", "maintenance"], weights=[55, 40, 5])[0]
        b = Bed(department_id=dept.id, bed_number=f"{dept.name[:3].upper()}-{i+1}", bed_type=bed_type, status=status)
        db.add(b)
        beds.append(b)
db.commit()
for b in beds:
    db.refresh(b)

print("Seeding patients...")
genders = ["Male", "Female"]
blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
patients = []
for i in range(50):
    p = Patient(
        full_name=f"Patient {first_names[i % 10]} {last_names[(i+3) % 10]}",
        age=random.randint(1, 90),
        gender=random.choice(genders),
        contact=f"9{random.randint(100000000, 999999999)}",
        address="Indore, MP",
        blood_group=random.choice(blood_groups)
    )
    db.add(p)
    patients.append(p)
db.commit()
for p in patients:
    db.refresh(p)

print("Seeding admissions...")
diagnoses = ["Fever", "Fracture", "Cardiac issue", "Respiratory infection", "Post-surgery recovery", "Diabetes management"]
for i in range(25):
    patient = random.choice(patients)
    doctor = random.choice(doctors)
    admission_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
    is_discharged = random.choice([True, False])
    discharge_date = admission_date + timedelta(days=random.randint(1, 10)) if is_discharged else None
    bed = random.choice(beds)
    a = Admission(
        patient_id=patient.id,
        bed_id=bed.id,
        doctor_id=doctor.id,
        admission_date=admission_date,
        discharge_date=discharge_date,
        diagnosis=random.choice(diagnoses),
        status="discharged" if is_discharged else "admitted"
    )
    db.add(a)
db.commit()

print("Seeding medicines + inventory...")
medicine_names = ["Paracetamol", "Amoxicillin", "Ibuprofen", "Cetirizine", "Azithromycin",
                   "Metformin", "Omeprazole", "Insulin", "Aspirin", "Atorvastatin",
                   "Losartan", "Salbutamol", "Diclofenac", "Ranitidine", "Ceftriaxone"]
for name in medicine_names:
    m = Medicine(name=name, category="General", unit="tablets/vials")
    db.add(m)
    db.commit()
    db.refresh(m)
    stock = random.randint(0, 500)
    reorder = random.randint(50, 150)
    inv = Inventory(
        medicine_id=m.id,
        current_stock=stock,
        reorder_level=reorder,
        expiry_date=(datetime.utcnow() + timedelta(days=random.randint(30, 400))).date()
    )
    db.add(inv)
db.commit()

print("Seeding blood bank...")
for bg in blood_groups:
    bb = BloodBank(
        blood_group=bg,
        units_available=random.randint(0, 40),
        expiry_date=(datetime.utcnow() + timedelta(days=random.randint(10, 60))).date()
    )
    db.add(bb)
db.commit()

print("Seeding ambulances...")
for i in range(6):
    amb = Ambulance(
        vehicle_number=f"MP09-AB-{1000+i}",
        status=random.choices(["available", "on_trip", "maintenance"], weights=[60, 30, 10])[0],
        driver_name=f"{random.choice(first_names)} {random.choice(last_names)}",
        last_response_time_minutes=round(random.uniform(4, 20), 1)
    )
    db.add(amb)
db.commit()

db.close()
print("Seeding complete!")

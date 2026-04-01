"""
setup_database.py
Creates the clinic SQLite database schema and inserts realistic dummy data.
Run this script first before starting the application.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta, date

DB_PATH = "clinic.db"

# ─────────────────────────────────────────────
# Reference data
# ─────────────────────────────────────────────
FIRST_NAMES = [
    "Aarav", "Priya", "Rohan", "Sneha", "Arjun", "Kavya", "Vikram", "Neha",
    "Aditya", "Pooja", "Rahul", "Anjali", "Karan", "Meera", "Siddharth",
    "Divya", "Amit", "Isha", "Nikhil", "Riya", "Suresh", "Nandita", "Rajesh",
    "Smita", "Akash", "Sonia", "Vivek", "Deepa", "Gaurav", "Swati",
    "Harish", "Pallavi", "Manish", "Rekha", "Tarun", "Usha", "Yogesh",
    "Vidya", "Pankaj", "Sunita", "Ashok", "Geeta", "Vinod", "Shweta",
    "Ramesh", "Rani", "Girish", "Lata", "Dinesh", "Sudha",
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Mehta", "Joshi", "Gupta", "Shah",
    "Yadav", "Verma", "Nair", "Iyer", "Reddy", "Pillai", "Rao",
    "Khanna", "Malhotra", "Bose", "Chatterjee", "Banerjee", "Das", "Ghosh",
    "Mishra", "Tiwari", "Pandey", "Tripathi", "Srivastava", "Dubey",
    "Agarwal", "Goel", "Saxena", "Kapoor", "Chopra", "Arora",
]

CITIES = [
    "Mumbai", "Pune", "Nashik", "Nagpur", "Aurangabad",
    "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
]

SPECIALIZATIONS = ["Dermatology", "Cardiology", "Orthopedics", "General", "Pediatrics"]

DEPARTMENTS = {
    "Dermatology": "Skin & Hair",
    "Cardiology": "Heart & Vascular",
    "Orthopedics": "Bone & Joint",
    "General": "General Medicine",
    "Pediatrics": "Child Health",
}

DOCTORS = [
    ("Dr. Rajiv Menon",      "Dermatology"),
    ("Dr. Anita Sharma",     "Dermatology"),
    ("Dr. Suresh Iyer",      "Dermatology"),
    ("Dr. Pradeep Nair",     "Cardiology"),
    ("Dr. Kavitha Reddy",    "Cardiology"),
    ("Dr. Mohan Pillai",     "Cardiology"),
    ("Dr. Sanjay Gupta",     "Orthopedics"),
    ("Dr. Leela Rao",        "Orthopedics"),
    ("Dr. Arun Verma",       "Orthopedics"),
    ("Dr. Sunita Patel",     "General"),
    ("Dr. Vijay Kumar",      "General"),
    ("Dr. Rekha Joshi",      "General"),
    ("Dr. Harish Mehta",     "Pediatrics"),
    ("Dr. Geetha Nambiar",   "Pediatrics"),
    ("Dr. Dinesh Shah",      "Pediatrics"),
]

TREATMENT_NAMES = {
    "Dermatology": ["Skin Biopsy", "Acne Treatment", "Laser Therapy", "Chemical Peel", "Phototherapy"],
    "Cardiology":  ["ECG", "Echocardiogram", "Stress Test", "Angiography", "Cardiac Catheterization"],
    "Orthopedics": ["X-Ray", "Physiotherapy", "Joint Injection", "Arthroscopy", "Bone Density Scan"],
    "General":     ["Blood Test", "Urine Analysis", "General Checkup", "Vaccination", "Wound Dressing"],
    "Pediatrics":  ["Growth Assessment", "Vaccination", "Allergy Test", "Nebulization", "Developmental Screening"],
}

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
INVOICE_STATUSES     = ["Paid", "Pending", "Overdue"]

NOTES_POOL = [
    "Follow-up required in 2 weeks",
    "Patient advised to rest",
    "Medication prescribed",
    "Lab reports awaited",
    "Referred to specialist",
    "Annual checkup",
    "Post-surgery follow-up",
    None, None, None,   # intentional NULLs
]


def random_date(start_days_ago: int, end_days_ago: int = 0) -> str:
    """Return a random date string between start_days_ago and end_days_ago."""
    start = datetime.now() - timedelta(days=start_days_ago)
    end   = datetime.now() - timedelta(days=end_days_ago)
    delta = (end - start).days
    if delta <= 0:
        return start.strftime("%Y-%m-%d")
    return (start + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def random_datetime(start_days_ago: int, end_days_ago: int = 0) -> str:
    base_date = random_date(start_days_ago, end_days_ago)
    hour   = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    return f"{base_date} {hour:02d}:{minute:02d}:00"


def random_phone() -> str:
    return f"+91-{random.randint(70000,99999)}{random.randint(10000,99999)}"


def random_email(first: str, last: str) -> str | None:
    if random.random() < 0.15:   # ~15 % NULL
        return None
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    return f"{first.lower()}.{last.lower()}{random.randint(1,99)}@{random.choice(domains)}"


# ─────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    date_of_birth   DATE,
    gender          TEXT,
    city            TEXT,
    registered_date DATE
);

CREATE TABLE IF NOT EXISTS doctors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    specialization   TEXT,
    department       TEXT,
    phone            TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER,
    doctor_id        INTEGER,
    appointment_date DATETIME,
    status           TEXT,
    notes            TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id)  REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS treatments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id     INTEGER,
    treatment_name     TEXT,
    cost               REAL,
    duration_minutes   INTEGER,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER,
    invoice_date  DATE,
    total_amount  REAL,
    paid_amount   REAL,
    status        TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
"""


def seed_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.executescript(SCHEMA_SQL)
    conn.commit()

    # ── Doctors (15) ──────────────────────────────────────────────────────────
    doctor_rows = []
    for name, spec in DOCTORS:
        phone = random_phone() if random.random() > 0.05 else None
        doctor_rows.append((name, spec, DEPARTMENTS[spec], phone))

    cur.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
        doctor_rows,
    )
    conn.commit()
    doctor_ids = [r[0] for r in cur.execute("SELECT id FROM doctors").fetchall()]

    # Build a map: doctor_id -> specialization
    doc_spec = {}
    for row in cur.execute("SELECT id, specialization FROM doctors").fetchall():
        doc_spec[row[0]] = row[1]

    # ── Patients (200) ────────────────────────────────────────────────────────
    patient_rows = []
    for _ in range(200):
        first   = random.choice(FIRST_NAMES)
        last    = random.choice(LAST_NAMES)
        email   = random_email(first, last)
        phone   = random_phone() if random.random() > 0.10 else None
        dob     = random_date(365 * 60, 365 * 5)    # 5–60 years old
        gender  = random.choice(["M", "F"])
        city    = random.choice(CITIES)
        reg_dt  = random_date(365, 0)
        patient_rows.append((first, last, email, phone, dob, gender, city, reg_dt))

    cur.executemany(
        """INSERT INTO patients
           (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
           VALUES (?,?,?,?,?,?,?,?)""",
        patient_rows,
    )
    conn.commit()
    patient_ids = [r[0] for r in cur.execute("SELECT id FROM patients").fetchall()]

    # ── Appointments (500) ────────────────────────────────────────────────────
    # Make some patients high-frequency (repeat visitors)
    heavy_patients = random.sample(patient_ids, 30)
    heavy_doctors  = random.sample(doctor_ids,   5)   # busier doctors

    appointment_rows = []
    for i in range(500):
        if random.random() < 0.25:
            pid = random.choice(heavy_patients)
        else:
            pid = random.choice(patient_ids)

        if random.random() < 0.30:
            did = random.choice(heavy_doctors)
        else:
            did = random.choice(doctor_ids)

        appt_dt = random_datetime(365, 0)

        # Future appointments get "Scheduled"
        appt_date_obj = datetime.strptime(appt_dt, "%Y-%m-%d %H:%M:%S")
        if appt_date_obj > datetime.now():
            status = "Scheduled"
        else:
            status = random.choices(
                APPOINTMENT_STATUSES,
                weights=[10, 55, 20, 15],
            )[0]

        notes = random.choice(NOTES_POOL)
        appointment_rows.append((pid, did, appt_dt, status, notes))

    cur.executemany(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes) VALUES (?,?,?,?,?)",
        appointment_rows,
    )
    conn.commit()

    # ── Treatments (350) – only for Completed appointments ───────────────────
    completed_appts = cur.execute(
        "SELECT id, doctor_id FROM appointments WHERE status = 'Completed'"
    ).fetchall()

    # Sample up to 350
    treatment_sample = random.sample(completed_appts, min(350, len(completed_appts)))

    treatment_rows = []
    for appt_id, did in treatment_sample:
        spec  = doc_spec.get(did, "General")
        tname = random.choice(TREATMENT_NAMES[spec])
        cost  = round(random.uniform(50, 5000), 2)
        dur   = random.randint(15, 120)
        treatment_rows.append((appt_id, tname, cost, dur))

    cur.executemany(
        "INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes) VALUES (?,?,?,?)",
        treatment_rows,
    )
    conn.commit()

    # ── Invoices (300) ────────────────────────────────────────────────────────
    invoice_sample_patients = random.choices(patient_ids, k=300)
    invoice_rows = []
    for pid in invoice_sample_patients:
        inv_date     = random_date(365, 0)
        total_amount = round(random.uniform(200, 15000), 2)
        status       = random.choices(
            INVOICE_STATUSES, weights=[55, 25, 20]
        )[0]
        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(random.uniform(0, total_amount * 0.5), 2)
        else:   # Overdue
            paid_amount = round(random.uniform(0, total_amount * 0.3), 2)

        invoice_rows.append((pid, inv_date, total_amount, paid_amount, status))

    cur.executemany(
        "INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status) VALUES (?,?,?,?,?)",
        invoice_rows,
    )
    conn.commit()

    # ── Summary ───────────────────────────────────────────────────────────────
    counts = {
        "patients":     cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        "doctors":      cur.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
        "appointments": cur.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
        "treatments":   cur.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
        "invoices":     cur.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
    }

    conn.close()

    print(
        f"✅ Database created: {DB_PATH}\n"
        f"   Created {counts['patients']} patients, "
        f"{counts['doctors']} doctors, "
        f"{counts['appointments']} appointments, "
        f"{counts['treatments']} treatments, "
        f"{counts['invoices']} invoices."
    )


if __name__ == "__main__":
    seed_database()

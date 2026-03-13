from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(30))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class TemporalMixin:
    valid_start_date = db.Column(db.Date, nullable=False, default=date.today)
    valid_end_date = db.Column(db.Date, nullable=False, default=date(9999, 12, 31))
    tx_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    record_status = db.Column(db.String(20), nullable=False, default="ACTIVE")


class Diagnosis(db.Model, TemporalMixin):
    __tablename__ = "diagnoses"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    diagnosis_code = db.Column(db.String(30), nullable=False)
    diagnosis_text_enc = db.Column(db.Text, nullable=False)
    diagnosed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Treatment(db.Model, TemporalMixin):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    treatment_plan_enc = db.Column(db.Text, nullable=False)
    treated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Consultation(db.Model, TemporalMixin):
    __tablename__ = "consultations"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes_enc = db.Column(db.Text, nullable=False)


class LabReport(db.Model, TemporalMixin):
    __tablename__ = "lab_reports"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    report_type = db.Column(db.String(120), nullable=False)
    result_enc = db.Column(db.Text, nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Prescription(db.Model, TemporalMixin):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    medication_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(80), nullable=False)
    notes_enc = db.Column(db.Text)
    prescribed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class AdmissionTimeline(db.Model, TemporalMixin):
    __tablename__ = "admissions"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    ward = db.Column(db.String(100), nullable=False)
    admission_reason_enc = db.Column(db.Text, nullable=False)
    discharge_date = db.Column(db.Date)
    managed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    entity_name = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"
    __table_args__ = (UniqueConstraint("token", name="uq_token_blocklist_token"),)

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

import os
from datetime import datetime, date

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, g
from sqlalchemy import text

from models import (
    db,
    User,
    Patient,
    Diagnosis,
    Treatment,
    Consultation,
    LabReport,
    Prescription,
    AdmissionTimeline,
    AuditLog,
)
from security import (
    security_manager,
    load_current_user,
    login_user,
    logout_user,
    require_permission,
    parse_json,
)
from temporal_queries import (
    TREATMENT_HISTORY_BETWEEN_DATES,
    REPEATED_DIAGNOSES,
    MEDICATION_CHANGES_BY_MONTH,
    DOCTOR_CONSULTATION_FREQUENCY,
    DISEASE_TREND_REPORT,
)


load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/healthcare"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "development-secret")

db.init_app(app)


@app.before_request
def _load_user():
    load_current_user()


@app.get("/")
def home():
    return render_template("index.html")


def log_action(actor_id: int, action: str, entity_name: str, entity_id: int, details: str = ""):
    db.session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            details=details,
        )
    )


def supersede_current_versions(model, patient_id: int, as_of: date):
    active_rows = model.query.filter_by(patient_id=patient_id, record_status="ACTIVE").all()
    for row in active_rows:
        row.valid_end_date = as_of
        row.record_status = "SUPERSEDED"


@app.post("/api/bootstrap-admin")
def bootstrap_admin():
    if User.query.count() > 0:
        return jsonify({"message": "Bootstrap disabled; users already exist"}), 400
    payload = parse_json(["username", "password"])
    admin = User(
        username=payload["username"],
        password_hash=security_manager.hash_password(payload["password"]),
        role="Admin",
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"message": "Admin created"}), 201


@app.post("/api/login")
def login():
    payload = parse_json(["username", "password"])
    user = User.query.filter_by(username=payload["username"]).first()
    if not user or not security_manager.verify_password(user.password_hash, payload["password"]):
        return jsonify({"message": "Invalid credentials"}), 401
    login_user(user)
    return jsonify({"message": "Login successful", "role": user.role})


@app.post("/api/logout")
def logout():
    logout_user()
    return jsonify({"message": "Logged out"})


@app.post("/api/users")
@require_permission("user:manage")
def create_user():
    payload = parse_json(["username", "password", "role"])
    user = User(
        username=payload["username"],
        password_hash=security_manager.hash_password(payload["password"]),
        role=payload["role"],
    )
    db.session.add(user)
    db.session.commit()
    log_action(g.current_user.id, "CREATE_USER", "User", user.id, f"Role={user.role}")
    db.session.commit()
    return jsonify({"id": user.id, "username": user.username, "role": user.role}), 201


@app.post("/api/patients")
@require_permission("patient:create")
def create_patient():
    payload = parse_json(["patient_code", "full_name", "dob", "gender"])
    patient = Patient(
        patient_code=payload["patient_code"],
        full_name=payload["full_name"],
        dob=datetime.strptime(payload["dob"], "%Y-%m-%d").date(),
        gender=payload["gender"],
        phone=payload.get("phone"),
        created_by=g.current_user.id,
    )
    db.session.add(patient)
    db.session.commit()
    log_action(g.current_user.id, "CREATE_PATIENT", "Patient", patient.id)
    db.session.commit()
    return jsonify({"id": patient.id, "patient_code": patient.patient_code}), 201


def _insert_temporal(model, patient_id: int, field_values: dict, permission: str, entity: str):
    require_permission(permission)(lambda: None)()
    payload = parse_json(["valid_start_date"])
    start = datetime.strptime(payload["valid_start_date"], "%Y-%m-%d").date()
    supersede_current_versions(model, patient_id, start)
    item = model(
        patient_id=patient_id,
        valid_start_date=start,
        valid_end_date=date(9999, 12, 31),
        tx_timestamp=datetime.utcnow(),
        record_status="ACTIVE",
        **field_values,
    )
    db.session.add(item)
    db.session.flush()
    log_action(g.current_user.id, f"UPSERT_{entity.upper()}", entity, item.id)
    db.session.commit()
    return jsonify({"id": item.id, "status": item.record_status}), 201


@app.post("/api/patients/<int:patient_id>/diagnosis")
def upsert_diagnosis(patient_id):
    payload = parse_json(["diagnosis_code", "diagnosis_text", "valid_start_date"])
    encrypted = security_manager.encrypt_text(payload["diagnosis_text"])
    return _insert_temporal(
        Diagnosis,
        patient_id,
        {
            "diagnosis_code": payload["diagnosis_code"],
            "diagnosis_text_enc": encrypted,
            "diagnosed_by": g.current_user.id,
        },
        "diagnosis:write",
        "Diagnosis",
    )


@app.post("/api/patients/<int:patient_id>/treatment")
def upsert_treatment(patient_id):
    payload = parse_json(["treatment_plan", "valid_start_date"])
    encrypted = security_manager.encrypt_text(payload["treatment_plan"])
    return _insert_temporal(
        Treatment,
        patient_id,
        {"treatment_plan_enc": encrypted, "treated_by": g.current_user.id},
        "treatment:write",
        "Treatment",
    )


@app.post("/api/patients/<int:patient_id>/consultation")
def upsert_consultation(patient_id):
    payload = parse_json(["notes", "valid_start_date"])
    encrypted = security_manager.encrypt_text(payload["notes"])
    return _insert_temporal(
        Consultation,
        patient_id,
        {"notes_enc": encrypted, "doctor_id": g.current_user.id},
        "consultation:write",
        "Consultation",
    )


@app.post("/api/patients/<int:patient_id>/lab")
def upsert_lab_report(patient_id):
    payload = parse_json(["report_type", "result", "valid_start_date"])
    encrypted = security_manager.encrypt_text(payload["result"])
    return _insert_temporal(
        LabReport,
        patient_id,
        {
            "report_type": payload["report_type"],
            "result_enc": encrypted,
            "technician_id": g.current_user.id,
        },
        "lab:write",
        "LabReport",
    )


@app.post("/api/patients/<int:patient_id>/prescription")
def upsert_prescription(patient_id):
    payload = parse_json(["medication_name", "dosage", "valid_start_date"])
    encrypted_notes = security_manager.encrypt_text(payload.get("notes", "")) if payload.get("notes") else None
    return _insert_temporal(
        Prescription,
        patient_id,
        {
            "medication_name": payload["medication_name"],
            "dosage": payload["dosage"],
            "notes_enc": encrypted_notes,
            "prescribed_by": g.current_user.id,
        },
        "prescription:write",
        "Prescription",
    )


@app.post("/api/patients/<int:patient_id>/admission")
def upsert_admission(patient_id):
    payload = parse_json(["ward", "admission_reason", "valid_start_date"])
    encrypted = security_manager.encrypt_text(payload["admission_reason"])
    discharge_date = (
        datetime.strptime(payload["discharge_date"], "%Y-%m-%d").date() if payload.get("discharge_date") else None
    )
    return _insert_temporal(
        AdmissionTimeline,
        patient_id,
        {
            "ward": payload["ward"],
            "admission_reason_enc": encrypted,
            "discharge_date": discharge_date,
            "managed_by": g.current_user.id,
        },
        "admission:write",
        "Admission",
    )


@app.get("/api/patients/<int:patient_id>/history")
@require_permission("patient:read")
def patient_history(patient_id):
    start = request.args.get("start_date", "1900-01-01")
    end = request.args.get("end_date", "9999-12-31")
    stmt = text(TREATMENT_HISTORY_BETWEEN_DATES)
    rows = db.session.execute(
        stmt,
        {"patient_id": patient_id, "start_date": start, "end_date": end},
    ).mappings()
    return jsonify([dict(row) for row in rows])


@app.get("/api/analytics/repeated-diagnoses")
@require_permission("analytics:read")
def repeated_diagnoses():
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    rows = db.session.execute(text(REPEATED_DIAGNOSES), {"start_date": start, "end_date": end}).mappings()
    return jsonify([dict(row) for row in rows])


@app.get("/api/analytics/medication-changes")
@require_permission("analytics:read")
def medication_changes():
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    rows = db.session.execute(
        text(MEDICATION_CHANGES_BY_MONTH),
        {"start_date": start, "end_date": end},
    ).mappings()
    return jsonify([dict(row) for row in rows])


@app.get("/api/analytics/doctor-consultations")
@require_permission("analytics:read")
def doctor_consultations():
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    rows = db.session.execute(
        text(DOCTOR_CONSULTATION_FREQUENCY),
        {"start_date": start, "end_date": end},
    ).mappings()
    return jsonify([dict(row) for row in rows])


@app.get("/api/analytics/disease-trends")
@require_permission("analytics:read")
def disease_trends():
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    rows = db.session.execute(text(DISEASE_TREND_REPORT), {"start_date": start, "end_date": end}).mappings()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)

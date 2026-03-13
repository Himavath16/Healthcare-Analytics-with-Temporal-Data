CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    patient_code VARCHAR(30) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    dob DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    phone VARCHAR(30),
    created_by INT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS diagnoses (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id),
    diagnosis_code VARCHAR(30) NOT NULL,
    diagnosis_text_enc TEXT NOT NULL,
    diagnosed_by INT NOT NULL REFERENCES users(id),
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    tx_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('ACTIVE','SUPERSEDED','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS treatments (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id),
    treatment_plan_enc TEXT NOT NULL,
    treated_by INT NOT NULL REFERENCES users(id),
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    tx_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('ACTIVE','SUPERSEDED','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS consultations (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id),
    doctor_id INT NOT NULL REFERENCES users(id),
    notes_enc TEXT NOT NULL,
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    tx_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('ACTIVE','SUPERSEDED','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id),
    report_type VARCHAR(120) NOT NULL,
    result_enc TEXT NOT NULL,
    technician_id INT NOT NULL REFERENCES users(id),
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    tx_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('ACTIVE','SUPERSEDED','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id),
    medication_name VARCHAR(120) NOT NULL,
    dosage VARCHAR(80) NOT NULL,
    notes_enc TEXT,
    prescribed_by INT NOT NULL REFERENCES users(id),
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    tx_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('ACTIVE','SUPERSEDED','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS admissions (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id),
    ward VARCHAR(100) NOT NULL,
    admission_reason_enc TEXT NOT NULL,
    discharge_date DATE,
    managed_by INT NOT NULL REFERENCES users(id),
    valid_start_date DATE NOT NULL,
    valid_end_date DATE NOT NULL,
    tx_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    record_status VARCHAR(20) NOT NULL CHECK (record_status IN ('ACTIVE','SUPERSEDED','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    actor_id INT NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_name VARCHAR(80) NOT NULL,
    entity_id INT NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diag_temporal ON diagnoses(patient_id, valid_start_date, valid_end_date);
CREATE INDEX IF NOT EXISTS idx_treat_temporal ON treatments(patient_id, valid_start_date, valid_end_date);
CREATE INDEX IF NOT EXISTS idx_pres_temporal ON prescriptions(patient_id, valid_start_date, valid_end_date);

CREATE OR REPLACE FUNCTION enforce_single_active()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.record_status = 'ACTIVE' THEN
        UPDATE ONLY diagnoses SET record_status = 'SUPERSEDED', valid_end_date = NEW.valid_start_date
        WHERE patient_id = NEW.patient_id AND record_status = 'ACTIVE' AND TG_TABLE_NAME = 'diagnoses';

        UPDATE ONLY treatments SET record_status = 'SUPERSEDED', valid_end_date = NEW.valid_start_date
        WHERE patient_id = NEW.patient_id AND record_status = 'ACTIVE' AND TG_TABLE_NAME = 'treatments';

        UPDATE ONLY prescriptions SET record_status = 'SUPERSEDED', valid_end_date = NEW.valid_start_date
        WHERE patient_id = NEW.patient_id AND record_status = 'ACTIVE' AND TG_TABLE_NAME = 'prescriptions';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_diagnosis_active_version ON diagnoses;
CREATE TRIGGER trg_diagnosis_active_version
BEFORE INSERT ON diagnoses
FOR EACH ROW EXECUTE FUNCTION enforce_single_active();

DROP TRIGGER IF EXISTS trg_treatment_active_version ON treatments;
CREATE TRIGGER trg_treatment_active_version
BEFORE INSERT ON treatments
FOR EACH ROW EXECUTE FUNCTION enforce_single_active();

DROP TRIGGER IF EXISTS trg_prescription_active_version ON prescriptions;
CREATE TRIGGER trg_prescription_active_version
BEFORE INSERT ON prescriptions
FOR EACH ROW EXECUTE FUNCTION enforce_single_active();

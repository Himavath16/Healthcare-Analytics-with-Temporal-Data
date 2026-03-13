TREATMENT_HISTORY_BETWEEN_DATES = """
SELECT
    p.patient_code,
    p.full_name,
    t.id AS treatment_version_id,
    t.valid_start_date,
    t.valid_end_date,
    t.tx_timestamp,
    t.record_status
FROM treatments t
JOIN patients p ON p.id = t.patient_id
WHERE t.patient_id = :patient_id
  AND t.valid_start_date <= :end_date
  AND t.valid_end_date >= :start_date
ORDER BY t.valid_start_date;
"""

REPEATED_DIAGNOSES = """
SELECT
    d.patient_id,
    p.full_name,
    d.diagnosis_code,
    COUNT(*) AS occurrence_count,
    MIN(d.valid_start_date) AS first_seen,
    MAX(d.valid_start_date) AS last_seen
FROM diagnoses d
JOIN patients p ON p.id = d.patient_id
WHERE d.valid_start_date BETWEEN :start_date AND :end_date
GROUP BY d.patient_id, p.full_name, d.diagnosis_code
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC, last_seen DESC;
"""

MEDICATION_CHANGES_BY_MONTH = """
WITH monthly_rx AS (
    SELECT
        patient_id,
        medication_name,
        DATE_TRUNC('month', valid_start_date)::date AS rx_month,
        COUNT(*) AS monthly_changes
    FROM prescriptions
    WHERE valid_start_date BETWEEN :start_date AND :end_date
    GROUP BY patient_id, medication_name, DATE_TRUNC('month', valid_start_date)
)
SELECT
    m1.patient_id,
    p.full_name,
    m1.medication_name,
    m1.rx_month,
    m1.monthly_changes,
    LAG(m1.monthly_changes) OVER (
      PARTITION BY m1.patient_id, m1.medication_name ORDER BY m1.rx_month
    ) AS prev_month_changes,
    m1.monthly_changes - COALESCE(
      LAG(m1.monthly_changes) OVER (
        PARTITION BY m1.patient_id, m1.medication_name ORDER BY m1.rx_month
      ), 0
    ) AS change_delta
FROM monthly_rx m1
JOIN patients p ON p.id = m1.patient_id
ORDER BY m1.patient_id, m1.medication_name, m1.rx_month;
"""

DOCTOR_CONSULTATION_FREQUENCY = """
SELECT
    c.doctor_id,
    u.username AS doctor_name,
    DATE_TRUNC('month', c.valid_start_date)::date AS consult_month,
    COUNT(*) AS consultations_count
FROM consultations c
JOIN users u ON u.id = c.doctor_id
WHERE c.valid_start_date BETWEEN :start_date AND :end_date
GROUP BY c.doctor_id, u.username, DATE_TRUNC('month', c.valid_start_date)
ORDER BY consult_month, consultations_count DESC;
"""

DISEASE_TREND_REPORT = """
SELECT
    d.diagnosis_code,
    DATE_TRUNC('month', d.valid_start_date)::date AS diagnosis_month,
    COUNT(DISTINCT d.patient_id) AS affected_patients,
    COUNT(*) AS diagnosis_events
FROM diagnoses d
WHERE d.valid_start_date BETWEEN :start_date AND :end_date
GROUP BY d.diagnosis_code, DATE_TRUNC('month', d.valid_start_date)
ORDER BY diagnosis_month, diagnosis_events DESC;
"""

TEMPORAL_JOIN_CLINICAL_VIEW = """
SELECT
    p.patient_code,
    p.full_name,
    d.diagnosis_code,
    t.valid_start_date AS treatment_start,
    t.valid_end_date AS treatment_end,
    pr.medication_name,
    pr.dosage
FROM patients p
JOIN diagnoses d ON d.patient_id = p.id
JOIN treatments t ON t.patient_id = p.id
JOIN prescriptions pr ON pr.patient_id = p.id
WHERE d.valid_start_date <= t.valid_end_date
  AND d.valid_end_date >= t.valid_start_date
  AND pr.valid_start_date <= t.valid_end_date
  AND pr.valid_end_date >= t.valid_start_date
  AND p.id = :patient_id;
"""

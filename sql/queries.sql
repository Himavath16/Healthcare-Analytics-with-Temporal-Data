-- 1) Patient treatment history between two dates (interval filtering)
SELECT
    p.patient_code,
    p.full_name,
    t.id AS treatment_version,
    t.valid_start_date,
    t.valid_end_date,
    t.record_status,
    t.tx_timestamp
FROM treatments t
JOIN patients p ON p.id = t.patient_id
WHERE p.id = :patient_id
  AND t.valid_start_date <= :end_date
  AND t.valid_end_date >= :start_date
ORDER BY t.valid_start_date;

-- 2) Repeated diagnoses over a period
SELECT
    d.patient_id,
    p.full_name,
    d.diagnosis_code,
    COUNT(*) AS diagnosis_count,
    MIN(d.valid_start_date) AS first_occurrence,
    MAX(d.valid_start_date) AS latest_occurrence
FROM diagnoses d
JOIN patients p ON p.id = d.patient_id
WHERE d.valid_start_date BETWEEN :start_date AND :end_date
GROUP BY d.patient_id, p.full_name, d.diagnosis_code
HAVING COUNT(*) > 1
ORDER BY diagnosis_count DESC;

-- 3) Medication changes across months (historical comparison)
WITH monthly_med_changes AS (
    SELECT
        patient_id,
        medication_name,
        DATE_TRUNC('month', valid_start_date)::date AS month_bucket,
        COUNT(*) AS updates_in_month
    FROM prescriptions
    WHERE valid_start_date BETWEEN :start_date AND :end_date
    GROUP BY patient_id, medication_name, DATE_TRUNC('month', valid_start_date)
)
SELECT
    mmc.patient_id,
    p.full_name,
    mmc.medication_name,
    mmc.month_bucket,
    mmc.updates_in_month,
    LAG(mmc.updates_in_month) OVER (
      PARTITION BY mmc.patient_id, mmc.medication_name ORDER BY mmc.month_bucket
    ) AS prev_updates,
    mmc.updates_in_month - COALESCE(
      LAG(mmc.updates_in_month) OVER (
        PARTITION BY mmc.patient_id, mmc.medication_name ORDER BY mmc.month_bucket
      ), 0
    ) AS change_delta
FROM monthly_med_changes mmc
JOIN patients p ON p.id = mmc.patient_id
ORDER BY mmc.patient_id, mmc.medication_name, mmc.month_bucket;

-- 4) Doctor consultation frequency by month
SELECT
    c.doctor_id,
    u.username AS doctor_name,
    DATE_TRUNC('month', c.valid_start_date)::date AS month_bucket,
    COUNT(*) AS consultation_count
FROM consultations c
JOIN users u ON u.id = c.doctor_id
WHERE c.valid_start_date BETWEEN :start_date AND :end_date
GROUP BY c.doctor_id, u.username, DATE_TRUNC('month', c.valid_start_date)
ORDER BY month_bucket, consultation_count DESC;

-- 5) Disease trend report over time
SELECT
    d.diagnosis_code,
    DATE_TRUNC('month', d.valid_start_date)::date AS month_bucket,
    COUNT(DISTINCT d.patient_id) AS affected_patients,
    COUNT(*) AS diagnosis_events
FROM diagnoses d
WHERE d.valid_start_date BETWEEN :start_date AND :end_date
GROUP BY d.diagnosis_code, DATE_TRUNC('month', d.valid_start_date)
ORDER BY month_bucket, diagnosis_events DESC;

-- 6) Temporal join across diagnosis, treatment, and prescription intervals
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
WHERE p.id = :patient_id
  AND d.valid_start_date <= t.valid_end_date
  AND d.valid_end_date >= t.valid_start_date
  AND pr.valid_start_date <= t.valid_end_date
  AND pr.valid_end_date >= t.valid_start_date;

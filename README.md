# Temporal Healthcare Analytics System

This project implements a secure healthcare analytics platform using a **temporal database model** so that patient data is never overwritten. Instead, each change creates a new version with validity windows and transaction timestamps.

## Features

- Patient registration
- Temporal diagnosis and treatment updates (versioned history)
- Doctor consultations, lab reports, prescriptions, and admission/discharge timeline tracking
- Historical record retrieval using temporal filters
- Time-based analytics dashboard queries
- Secure login and role-based access control (Admin, Doctor, Nurse, Lab Technician)
- Audit logging for all create/update actions

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python (Flask)
- **Database:** PostgreSQL (SQL scripts + SQLAlchemy models)
- **Security:** Password hashing + encrypted sensitive fields + RBAC

## Project Structure

- `app.py` - Flask application and API endpoints
- `models.py` - SQLAlchemy temporal entities
- `security.py` - Authentication, authorization, and encryption utilities
- `temporal_queries.py` - Advanced temporal analytics SQL
- `templates/index.html` - UI for login, patient creation, temporal updates, and analytics
- `static/style.css` - Dashboard styling
- `sql/schema.sql` - PostgreSQL temporal schema and audit trigger
- `sql/queries.sql` - Complex temporal SQL query examples

## Temporal Model

Temporal medical records include:

- `valid_start_date`: Date when version becomes medically valid
- `valid_end_date`: Date when version stops being valid (`9999-12-31` means active)
- `tx_timestamp`: Database transaction timestamp
- `record_status`: `ACTIVE`, `SUPERSEDED`, or `INACTIVE`

Any update to diagnosis, treatment, prescription, lab report, consultation, or admission/discharge timeline:

1. Marks currently active version as `SUPERSEDED`
2. Sets old version `valid_end_date` to update date
3. Inserts a new `ACTIVE` version

## Security Model

- Passwords are hashed using Werkzeug PBKDF2 hashing.
- Sensitive textual clinical fields are encrypted using Fernet symmetric encryption.
- Role-based endpoint checks:
  - `Admin`: full access
  - `Doctor`: diagnosis/treatment/prescription/consultation/history
  - `Nurse`: patient profile/history/admission-discharge
  - `Lab Technician`: lab reports only
- All changes are written to `AuditLog` with actor, action, entity, entity id, and timestamp.

## Running Locally

1. Create PostgreSQL database.
2. Apply schema:
   ```bash
   psql "$DATABASE_URL" -f sql/schema.sql
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/healthcare"
   export FLASK_SECRET_KEY="change-me"
   export APP_ENCRYPTION_KEY="<fernet-key>"
   ```
5. Start app:
   ```bash
   python app.py
   ```

## Temporal Analytics Examples

See `sql/queries.sql` and `/api/analytics/*` endpoints for:

- Treatment history between dates
- Repeated diagnoses detection
- Medication changes month-over-month
- Doctor consultation frequency
- Disease trend reports

## Notes

- The ORM model and raw SQL align to support both application workflows and direct analytics.
- The UI is intentionally lightweight for demonstration while backend enforces access control and auditing.

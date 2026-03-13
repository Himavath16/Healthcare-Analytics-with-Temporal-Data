import os
from functools import wraps

from cryptography.fernet import Fernet
from flask import abort, g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from models import User


ROLE_PERMISSIONS = {
    "Admin": {
        "patient:create",
        "patient:read",
        "diagnosis:write",
        "diagnosis:read",
        "treatment:write",
        "treatment:read",
        "consultation:write",
        "consultation:read",
        "lab:write",
        "lab:read",
        "prescription:write",
        "prescription:read",
        "admission:write",
        "admission:read",
        "analytics:read",
        "user:manage",
    },
    "Doctor": {
        "patient:read",
        "diagnosis:write",
        "diagnosis:read",
        "treatment:write",
        "treatment:read",
        "consultation:write",
        "consultation:read",
        "prescription:write",
        "prescription:read",
        "analytics:read",
    },
    "Nurse": {
        "patient:create",
        "patient:read",
        "treatment:read",
        "diagnosis:read",
        "admission:write",
        "admission:read",
    },
    "Lab Technician": {
        "patient:read",
        "lab:write",
        "lab:read",
    },
}


class SecurityManager:
    def __init__(self):
        key = os.getenv("APP_ENCRYPTION_KEY")
        self.fernet = Fernet(key.encode() if key else Fernet.generate_key())

    def hash_password(self, plain_password: str) -> str:
        return generate_password_hash(plain_password)

    def verify_password(self, password_hash: str, plain_password: str) -> bool:
        return check_password_hash(password_hash, plain_password)

    def encrypt_text(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt_text(self, value: str) -> str:
        return self.fernet.decrypt(value.encode()).decode()


security_manager = SecurityManager()


def load_current_user():
    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return
    g.current_user = User.query.get(user_id)


def login_user(user: User):
    session["user_id"] = user.id
    session["role"] = user.role


def logout_user():
    session.clear()


def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if g.get("current_user") is None:
                abort(401, description="Authentication required")
            role = g.current_user.role
            if permission not in ROLE_PERMISSIONS.get(role, set()):
                abort(403, description="Insufficient permissions")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def parse_json(required_fields=None):
    payload = request.get_json(silent=True) or {}
    required_fields = required_fields or []
    missing = [field for field in required_fields if field not in payload]
    if missing:
        abort(400, description=f"Missing required fields: {', '.join(missing)}")
    return payload

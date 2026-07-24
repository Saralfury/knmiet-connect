from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.core.totp_crypto import decrypt_totp_secret, encrypt_totp_secret
from app.main import app
from app.models.attendance import ClassSession
from app.models.users import Teacher, User, UserRole
from app.services.attendance import AttendanceService


class RecordingSession:
    def __init__(self, result: ClassSession | None):
        self.result = result
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return self.result


def test_self_registration_rejects_privileged_roles_before_database_access() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            headers={"Origin": "http://localhost:8000"},
            json={
                "email": "attacker@example.com",
                "name": "Attacker",
                "password": "StrongPassword123",
                "role": "admin",
            },
        )

    assert response.status_code == 403
    assert response.json()["code"] == "self_registration_forbidden"
    assert response.json()["message"] == "Only student accounts can be self-registered"


def test_admin_user_creation_requires_authentication() -> None:
    with TestClient(app) as client:
        client.cookies.set("csrf_token", "test-csrf-token")
        response = client.post(
            "/api/auth/admin/users",
            headers={
                "Origin": "http://localhost:8000",
                "X-CSRF-Token": "test-csrf-token",
            },
            json={
                "email": "new-admin@example.com",
                "name": "New Admin",
                "password": "StrongPassword123",
                "role": "admin",
            },
        )

    assert response.status_code == 401


def test_totp_secret_uses_authenticated_encryption() -> None:
    secret = "JBSWY3DPEHPK3PXP"
    encrypted = encrypt_totp_secret(secret)

    assert encrypted != secret.encode("ascii")
    assert decrypt_totp_secret(encrypted) == secret
    with pytest.raises(ValueError, match="could not be decrypted"):
        decrypt_totp_secret(encrypted[:-1] + b"x")


def test_settings_require_totp_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOTP_ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.asyncio
async def test_teacher_session_query_is_owner_scoped() -> None:
    teacher = Teacher(id=uuid4(), user_id=uuid4(), employee_code="T-1", department_id=uuid4())
    user = User(id=teacher.user_id, email="teacher@example.com", name="Teacher", password_hash="x", role=UserRole.teacher)
    expected = ClassSession(id=uuid4(), course_id=uuid4(), teacher_id=teacher.id, totp_secret_encrypted=b"x")
    db = RecordingSession(expected)

    result = await AttendanceService(db).authorized_session(user, teacher, expected.id)
    sql = str(db.statement.compile(dialect=postgresql.dialect()))

    assert result is expected
    assert "class_sessions.teacher_id" in sql


@pytest.mark.asyncio
async def test_hod_session_query_is_department_scoped() -> None:
    teacher = Teacher(id=uuid4(), user_id=uuid4(), employee_code="H-1", department_id=uuid4())
    user = User(id=teacher.user_id, email="hod@example.com", name="HOD", password_hash="x", role=UserRole.hod)
    expected = ClassSession(id=uuid4(), course_id=uuid4(), teacher_id=uuid4(), totp_secret_encrypted=b"x")
    db = RecordingSession(expected)

    result = await AttendanceService(db).authorized_session(user, teacher, expected.id)
    sql = str(db.statement.compile(dialect=postgresql.dialect()))

    assert result is expected
    assert "JOIN courses" in sql
    assert "JOIN hod_assignments" in sql
    assert "hod_assignments.department_id = courses.department_id" in sql
    assert "hod_assignments.teacher_id" in sql

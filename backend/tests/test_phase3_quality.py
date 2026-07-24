from unittest.mock import AsyncMock
from uuid import uuid4
from pathlib import Path

import pyotp
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.errors import AppError
from app.core.totp_crypto import encrypt_totp_secret
from app.models.attendance import ClassSession, DeviceRegistration
from app.models.users import Student, User, UserRole
from app.main import app
from app.services.admin import AdminService
from app.services.attendance import AttendanceService
from app.services.auth import AuthService


class ScalarSession:
    def __init__(self, *values):
        self.values = iter(values)
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return next(self.values)

    async def execute(self, statement):
        self.statement = statement
        return ResultRows([])

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class DuplicateCommitSession(ScalarSession):
    async def commit(self):
        self.commits += 1
        if self.commits == 1:
            raise IntegrityError("INSERT", {}, Exception("duplicate"))


class ResultRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


@pytest.mark.asyncio
async def test_invalid_device_token_is_rejected_and_recorded() -> None:
    user = User(id=uuid4(), email="s@example.com", name="Student", password_hash="x", role=UserRole.student)
    student = Student(id=uuid4(), user_id=user.id, roll_no="R1", department_id=uuid4(), semester=1, section="A")
    db = ScalarSession(student, None)

    with pytest.raises(AppError) as error:
        await AttendanceService(db).scan(user, uuid4(), "123456", "invalid-device")

    assert error.value.code == "device_mismatch"
    assert db.commits == 1
    assert db.added[0].event_type == "DEVICE_MISMATCH"


@pytest.mark.asyncio
async def test_duplicate_attendance_scan_returns_conflict() -> None:
    user = User(id=uuid4(), email="s@example.com", name="Student", password_hash="x", role=UserRole.student)
    student = Student(id=uuid4(), user_id=user.id, roll_no="R1", department_id=uuid4(), semester=1, section="A")
    device = DeviceRegistration(id=uuid4(), student_id=student.id, device_token_hash="hash")
    secret = pyotp.random_base32()
    session = ClassSession(id=uuid4(), course_id=uuid4(), teacher_id=uuid4(), totp_secret_encrypted=encrypt_totp_secret(secret), is_active=True)
    db = DuplicateCommitSession(student, device, session, uuid4())

    with pytest.raises(AppError) as error:
        await AttendanceService(db).scan(
            user,
            session.id,
            pyotp.TOTP(secret).now(),
            "device-token",
        )

    assert error.value.status_code == 409
    assert error.value.code == "attendance_duplicate"
    assert db.rollbacks == 1
    assert db.commits == 2


@pytest.mark.asyncio
async def test_fifth_failed_login_locks_account(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User(
        id=uuid4(),
        email="locked@example.com",
        name="Locked",
        password_hash="hash",
        role=UserRole.student,
        failed_login_count=4,
    )
    db = ScalarSession(user)
    monkeypatch.setattr("app.services.auth.verify_password", AsyncMock(return_value=False))

    with pytest.raises(AppError) as error:
        await AuthService(db).login(
            type("Login", (), {"email": "locked@example.com", "password": "wrong"})(),
            "127.0.0.1",
        )

    assert error.value.code == "invalid_credentials"
    assert user.failed_login_count == 5
    assert user.locked_until is not None


@pytest.mark.asyncio
async def test_student_summary_uses_one_grouped_query() -> None:
    user = User(id=uuid4(), email="s@example.com", name="Student", password_hash="x", role=UserRole.student)
    student = Student(id=uuid4(), user_id=user.id, roll_no="R1", department_id=uuid4(), semester=1, section="A")
    db = ScalarSession(student)
    db.execute = AsyncMock(return_value=ResultRows([("CS101", "Computer Science", 4, 3)]))

    rows = await AttendanceService(db).student_summary(user)
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert db.execute.await_count == 1
    assert "count(class_sessions.id)" in sql
    assert "count(attendance_logs.id)" in sql
    assert rows[0]["percentage"] == 75.0


def test_csv_is_fully_validated_before_database_use() -> None:
    content = (
        b"roll_no,name,email,department,semester,section\n"
        b"R1,Valid Student,valid@example.com,CSE,1,A\n"
        b"R2,X,not-an-email,CSE,99,A\n"
    )

    with pytest.raises(AppError) as error:
        AdminService._parse_and_validate_csv(content)

    assert error.value.code == "csv_validation_failed"
    assert error.value.details[0]["line"] == 3


def test_production_configuration_rejects_insecure_defaults() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            TOTP_ENCRYPTION_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
            environment="production",
        )


def test_production_configuration_accepts_secure_values() -> None:
    settings = Settings(
        _env_file=None,
        TOTP_ENCRYPTION_KEY="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        JWT_SECRET_KEY="a-secure-production-secret-that-is-long-enough",
        environment="production",
        secure_cookies=True,
        https_enabled=True,
    )

    assert settings.environment == "production"
    assert settings.secure_cookies is True


def test_admin_mutations_use_json_request_bodies() -> None:
    paths = app.openapi()["paths"]
    for path in ("/api/admin/departments", "/api/admin/courses", "/api/admin/teacher-course", "/api/admin/student-course"):
        operation = paths[path]["post"]
        assert "requestBody" in operation
        assert not [parameter for parameter in operation.get("parameters", []) if parameter["in"] == "query"]


def test_validation_errors_use_standard_envelope() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            headers={"Origin": "http://localhost:8000"},
            json={"role": "student"},
        )

    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "details"}
    assert response.json()["code"] == "validation_error"


def test_request_observability_adds_request_id_and_metrics() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "test-request-id"})
        metrics_response = client.get("/metrics")

    assert response.headers["X-Request-ID"] == "test-request-id"
    assert metrics_response.json()["request_count"] >= 1


def test_frontend_attendance_rendering_avoids_inner_html() -> None:
    source = (Path(__file__).resolve().parents[2] / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "attendanceRows.innerHTML" not in source
    assert "cell.textContent" in source

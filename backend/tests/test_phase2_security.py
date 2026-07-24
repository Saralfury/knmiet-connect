from uuid import uuid4

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy.dialects import postgresql

from app.api.reports import attendance_report_statement, authorize_course_report
from app.api.auth import (
    claim_refresh_token_statement,
    refresh_token,
    revoke_refresh_family_statement,
    revoke_refresh_token_statement,
)
from app.core.security import create_refresh_token, decode_token
from app.core.errors import AppError
from app.db.audit import set_audit_context
from app.main import app
from app.models.academics import Course
from app.models.audit import SecurityEvent
from app.models.auth import RefreshToken
from app.models.users import Teacher, User, UserRole
from app.schemas.auth import LoginResponse


class RecordingSession:
    def __init__(self):
        self.statement = None
        self.parameters = None

    async def execute(self, statement, parameters=None):
        self.statement = statement
        self.parameters = parameters


class EmptyUpdateResult:
    def first(self):
        return None


class RefreshReuseSession:
    def __init__(self, user, reused):
        self.scalar_results = iter([user, reused])
        self.statements = []
        self.added = []
        self.commits = 0

    async def scalar(self, statement):
        self.statements.append(statement)
        return next(self.scalar_results)

    async def execute(self, statement, parameters=None):
        self.statements.append(statement)
        if len([item for item in self.statements if item.__class__.__name__ == "Update"]) == 1:
            return EmptyUpdateResult()
        return None

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1


class ScalarSequenceSession:
    def __init__(self, *results):
        self.results = iter(results)
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return next(self.results)


def test_refresh_tokens_have_unique_jti_and_preserve_family() -> None:
    user_id = uuid4()
    first = create_refresh_token(str(user_id))
    rotated = create_refresh_token(str(user_id), family_id=first.family_id)
    first_payload = decode_token(first.token, "refresh")
    rotated_payload = decode_token(rotated.token, "refresh")

    assert first.jti != rotated.jti
    assert first_payload["jti"] == first.jti
    assert rotated_payload["family_id"] == str(first.family_id)
    assert rotated.family_id == first.family_id


def test_login_response_does_not_expose_access_token() -> None:
    assert "access_token" not in LoginResponse.model_fields


def test_refresh_claim_logout_and_family_revocation_are_database_updates() -> None:
    user_id = uuid4()
    family_id = uuid4()
    dialect = postgresql.dialect()

    logout_sql = str(revoke_refresh_token_statement("hash").compile(dialect=dialect))
    claim_sql = str(
        claim_refresh_token_statement(user_id, "hash", "jti", family_id).compile(
            dialect=dialect
        )
    )
    family_sql = str(revoke_refresh_family_statement(family_id).compile(dialect=dialect))

    assert logout_sql.startswith("UPDATE refresh_tokens")
    assert "refresh_tokens.revoked IS false" in logout_sql
    assert "RETURNING refresh_tokens.id" in claim_sql
    assert "refresh_tokens.jti" in claim_sql
    assert "refresh_tokens.family_id" in family_sql


@pytest.mark.asyncio
async def test_reused_refresh_token_revokes_its_family() -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        email="student@example.com",
        name="Student",
        password_hash="x",
        role=UserRole.student,
    )
    bundle = create_refresh_token(str(user_id))
    reused = RefreshToken(
        user_id=user_id,
        token_hash="unused-by-fake",
        jti=bundle.jti,
        family_id=bundle.family_id,
        expires_at=bundle.expires_at,
        revoked=True,
    )
    db = RefreshReuseSession(user, reused)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/refresh",
            "headers": [(b"cookie", f"refresh_token={bundle.token}".encode())],
        }
    )

    with pytest.raises(AppError, match="Refresh token revoked"):
        await refresh_token(request, Response(), db)

    update_sql = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in db.statements
        if statement.__class__.__name__ == "Update"
    ]
    assert any("refresh_tokens.family_id" in sql for sql in update_sql)
    assert any(
        isinstance(event, SecurityEvent) and event.event_type == "REFRESH_TOKEN_REUSE"
        for event in db.added
    )
    assert db.commits == 1


def test_csrf_rejects_untrusted_origin() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            headers={"Origin": "https://attacker.example"},
            json={"email": "student@example.com", "password": "password"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "untrusted_origin"
    assert response.json()["message"] == "Untrusted request origin"


def test_csrf_rejects_missing_double_submit_header() -> None:
    with TestClient(app) as client:
        client.cookies.set("csrf_token", "cookie-token")
        response = client.post(
            "/api/auth/admin/users",
            headers={"Origin": "http://localhost:8000"},
            json={
                "email": "admin@example.com",
                "name": "Admin",
                "password": "StrongPassword123",
                "role": "admin",
            },
        )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_validation_failed"
    assert response.json()["message"] == "CSRF validation failed"


@pytest.mark.asyncio
async def test_audit_context_sets_actor_and_reason_transaction_locally() -> None:
    db = RecordingSession()
    actor_id = uuid4()

    await set_audit_context(db, actor_id, "Corrected from signed register")

    sql = str(db.statement)
    assert "set_config('app.actor_id'" in sql
    assert "set_config('app.audit_reason'" in sql
    assert db.parameters == {
        "actor_id": str(actor_id),
        "reason": "Corrected from signed register",
    }


def test_attendance_report_is_anchored_to_enrollment() -> None:
    sql = str(
        attendance_report_statement(uuid4()).compile(dialect=postgresql.dialect())
    )

    assert "FROM student_course_enrollment" in sql
    assert "JOIN students" in sql
    assert "student_course_enrollment.course_id" in sql
    assert "class_sessions.course_id" in sql


@pytest.mark.asyncio
async def test_unassigned_teacher_cannot_export_course_report() -> None:
    user = User(
        id=uuid4(),
        email="teacher@example.com",
        name="Teacher",
        password_hash="x",
        role=UserRole.teacher,
    )
    course = Course(id=uuid4(), course_code="CS101", course_name="CS", department_id=uuid4(), semester=1)
    teacher = Teacher(id=uuid4(), user_id=user.id, employee_code="T1", department_id=course.department_id)
    db = ScalarSequenceSession(course, teacher, None)

    with pytest.raises(AppError, match="Not authorized"):
        await authorize_course_report(db, user, course.id)


@pytest.mark.asyncio
async def test_hod_report_check_uses_course_department() -> None:
    user = User(
        id=uuid4(),
        email="hod@example.com",
        name="HOD",
        password_hash="x",
        role=UserRole.hod,
    )
    course = Course(id=uuid4(), course_code="CS101", course_name="CS", department_id=uuid4(), semester=1)
    teacher = Teacher(id=uuid4(), user_id=user.id, employee_code="H1", department_id=course.department_id)
    db = ScalarSequenceSession(course, teacher, uuid4())

    result = await authorize_course_report(db, user, course.id)
    authorization_sql = str(db.statements[-1].compile(dialect=postgresql.dialect()))

    assert result is course
    assert "hod_assignments.department_id" in authorization_sql

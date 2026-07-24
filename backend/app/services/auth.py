from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.metrics import metrics
from app.core.security import (
    RefreshTokenBundle,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    sha256_hex,
    utcnow,
    verify_password,
)
from app.models.audit import AuthAudit, SecurityEvent
from app.models.auth import RefreshToken
from app.models.users import Department, HodAssignment, Student, Teacher, User, UserRole
from app.schemas.auth import CreatePrivilegedUserRequest, LoginRequest, RegisterUserRequest


@dataclass(frozen=True)
class AuthSessionResult:
    user: User
    access_token: str
    refresh_token: str


def password_policy_ok(role: UserRole, password: str) -> bool:
    if role == UserRole.student:
        return len(password) >= 8
    if role == UserRole.teacher:
        return len(password) >= 12 and any(c.isdigit() for c in password) and any(c.isalpha() for c in password)
    return (
        len(password) >= 14
        and any(c.isdigit() for c in password)
        and any(c.islower() for c in password)
        and any(c.isupper() for c in password)
    )


def refresh_token_record(user_id: UUID, bundle: RefreshTokenBundle) -> RefreshToken:
    return RefreshToken(
        user_id=user_id,
        token_hash=sha256_hex(bundle.token),
        jti=bundle.jti,
        family_id=bundle.family_id,
        expires_at=bundle.expires_at,
    )


def revoke_refresh_token_statement(token_hash: str):
    return (
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
        )
        .values(revoked=True, revoked_at=utcnow())
    )


def claim_refresh_token_statement(
    user_id: UUID,
    token_hash: str,
    jti: str,
    family_id: UUID,
):
    return (
        revoke_refresh_token_statement(token_hash)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.jti == jti,
            RefreshToken.family_id == family_id,
            RefreshToken.expires_at > utcnow(),
        )
        .returning(RefreshToken.id)
    )


def revoke_refresh_family_statement(family_id: UUID):
    return (
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id)
        .values(revoked=True, revoked_at=utcnow())
    )


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_student(self, payload: RegisterUserRequest) -> AuthSessionResult:
        if payload.role != UserRole.student:
            raise AppError(403, "self_registration_forbidden", "Only student accounts can be self-registered")
        if not password_policy_ok(payload.role, payload.password):
            raise AppError(400, "password_policy_failed", "Password does not meet role policy")
        if not all([payload.department_code, payload.roll_no, payload.semester, payload.section]):
            raise AppError(400, "student_profile_required", "Student profile fields are required")

        password_hash = await hash_password(payload.password)
        try:
            async with self.db.begin():
                if await self.db.scalar(select(User.id).where(User.email == str(payload.email).lower())):
                    raise AppError(409, "email_exists", "Email already registered")
                department = await self.db.scalar(
                    select(Department).where(Department.code == payload.department_code.upper())
                )
                if not department:
                    raise AppError(404, "department_not_found", "Department not found")
                user = User(
                    email=str(payload.email).lower(),
                    name=payload.name,
                    password_hash=password_hash,
                    role=payload.role,
                )
                self.db.add(user)
                await self.db.flush()
                self.db.add(
                    Student(
                        user_id=user.id,
                        roll_no=payload.roll_no,
                        phone=payload.phone,
                        department_id=department.id,
                        semester=payload.semester,
                        section=payload.section,
                    )
                )
                result = self._new_session(user)
                self.db.add(refresh_token_record(user.id, result[1]))
        except IntegrityError as exc:
            raise AppError(409, "account_conflict", "Account profile already exists") from exc
        return AuthSessionResult(user, result[0], result[1].token)

    async def create_privileged_user(self, payload: CreatePrivilegedUserRequest) -> User:
        allowed_roles = {UserRole.teacher, UserRole.hod, UserRole.director, UserRole.admin}
        if payload.role not in allowed_roles:
            raise AppError(400, "invalid_role", "Use self-registration for student accounts")
        if not password_policy_ok(payload.role, payload.password):
            raise AppError(400, "password_policy_failed", "Password does not meet role policy")
        password_hash = await hash_password(payload.password)
        if self.db.in_transaction():
            await self.db.commit()
        try:
            async with self.db.begin():
                if await self.db.scalar(select(User.id).where(User.email == str(payload.email).lower())):
                    raise AppError(409, "email_exists", "Email already registered")
                department = None
                if payload.role in {UserRole.teacher, UserRole.hod}:
                    if not payload.department_code or not payload.employee_code:
                        raise AppError(400, "teacher_profile_required", "Teacher profile fields are required")
                    department = await self.db.scalar(
                        select(Department).where(Department.code == payload.department_code.upper())
                    )
                    if not department:
                        raise AppError(404, "department_not_found", "Department not found")
                user = User(
                    email=str(payload.email).lower(),
                    name=payload.name,
                    password_hash=password_hash,
                    role=payload.role,
                )
                self.db.add(user)
                await self.db.flush()
                if department:
                    teacher = Teacher(
                        user_id=user.id,
                        employee_code=payload.employee_code,
                        department_id=department.id,
                    )
                    self.db.add(teacher)
                    await self.db.flush()
                    if payload.role == UserRole.hod:
                        self.db.add(HodAssignment(teacher_id=teacher.id, department_id=department.id))
        except IntegrityError as exc:
            raise AppError(409, "account_conflict", "Account profile already exists") from exc
        return user

    async def login(self, payload: LoginRequest, ip_address: str | None) -> AuthSessionResult:
        user = await self.db.scalar(select(User).where(User.email == str(payload.email).lower()))
        if not user:
            self.db.add(AuthAudit(action="LOGIN_FAILURE", ip_address=ip_address))
            await self.db.commit()
            metrics.record_security_event("FAILED_LOGIN")
            raise AppError(401, "invalid_credentials", "Invalid credentials")
        if user.locked_until and user.locked_until > utcnow():
            raise AppError(423, "account_locked", "Account temporarily locked")
        if not await verify_password(payload.password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= 20:
                user.locked_until = utcnow() + timedelta(days=3650)
            elif user.failed_login_count >= 10:
                user.locked_until = utcnow() + timedelta(minutes=30)
            elif user.failed_login_count >= 5:
                user.locked_until = utcnow() + timedelta(minutes=15)
            self.db.add(AuthAudit(actor_id=user.id, action="LOGIN_FAILURE", ip_address=ip_address))
            self.db.add(
                SecurityEvent(
                    event_type="FAILED_LOGIN",
                    actor_id=user.id,
                    severity="medium",
                    metadata_json={"email": user.email},
                )
            )
            await self.db.commit()
            metrics.record_security_event("FAILED_LOGIN")
            raise AppError(401, "invalid_credentials", "Invalid credentials")
        user.failed_login_count = 0
        user.locked_until = None
        access_token, refresh_bundle = self._new_session(user)
        self.db.add(refresh_token_record(user.id, refresh_bundle))
        self.db.add(AuthAudit(actor_id=user.id, action="LOGIN_SUCCESS", ip_address=ip_address))
        await self.db.commit()
        return AuthSessionResult(user, access_token, refresh_bundle.token)

    async def logout(self, token: str | None) -> None:
        if token:
            await self.db.execute(revoke_refresh_token_statement(sha256_hex(token)))
            await self.db.commit()

    async def refresh(self, token: str) -> AuthSessionResult:
        try:
            payload = decode_token(token, expected_type="refresh")
            user_id = UUID(payload["sub"])
            family_id = UUID(payload["family_id"])
            jti = payload["jti"]
        except (ValueError, KeyError) as exc:
            raise AppError(401, "invalid_refresh_token", "Invalid refresh token") from exc
        user = await self.db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
        if not user:
            raise AppError(401, "inactive_user", "Inactive user")
        claimed = await self.db.execute(
            claim_refresh_token_statement(user_id, sha256_hex(token), jti, family_id)
        )
        if claimed.first() is None:
            reused = await self.db.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == sha256_hex(token),
                    RefreshToken.jti == jti,
                    RefreshToken.family_id == family_id,
                )
            )
            if reused and reused.revoked:
                await self.db.execute(revoke_refresh_family_statement(reused.family_id))
                self.db.add(
                    SecurityEvent(
                        event_type="REFRESH_TOKEN_REUSE",
                        actor_id=user_id,
                        severity="high",
                        metadata_json={"family_id": str(reused.family_id)},
                    )
                )
                await self.db.commit()
                metrics.record_security_event("REFRESH_TOKEN_REUSE")
            raise AppError(401, "refresh_token_revoked", "Refresh token revoked")
        access_token = create_access_token(str(user.id), user.role.value)
        refresh_bundle = create_refresh_token(str(user.id), family_id=family_id)
        self.db.add(refresh_token_record(user.id, refresh_bundle))
        await self.db.commit()
        return AuthSessionResult(user, access_token, refresh_bundle.token)

    @staticmethod
    def _new_session(user: User) -> tuple[str, RefreshTokenBundle]:
        return (
            create_access_token(str(user.id), user.role.value),
            create_refresh_token(str(user.id)),
        )

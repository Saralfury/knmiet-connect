from uuid import UUID

import pyotp
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.metrics import metrics
from app.core.security import new_opaque_token, sha256_hex, utcnow
from app.core.totp_crypto import decrypt_totp_secret, encrypt_totp_secret
from app.models.academics import Course, StudentCourseEnrollment, TeacherCourseMapping
from app.models.attendance import AttendanceLog, ClassSession, DeviceRegistration
from app.models.audit import SecurityEvent
from app.models.users import HodAssignment, Student, Teacher, User, UserRole


class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def current_student(self, user: User) -> Student:
        student = await self.db.scalar(
            select(Student).where(Student.user_id == user.id, Student.is_active.is_(True))
        )
        if not student:
            raise AppError(404, "student_not_found", "Student profile not found")
        return student

    async def current_teacher(self, user: User) -> Teacher:
        teacher = await self.db.scalar(
            select(Teacher).where(Teacher.user_id == user.id, Teacher.is_active.is_(True))
        )
        if not teacher:
            raise AppError(404, "teacher_not_found", "Teacher profile not found")
        return teacher

    async def authorized_session(
        self,
        user: User,
        teacher: Teacher,
        session_id: UUID,
    ) -> ClassSession:
        statement = select(ClassSession).where(ClassSession.id == session_id)
        if user.role == UserRole.teacher:
            statement = statement.where(ClassSession.teacher_id == teacher.id)
        else:
            statement = statement.join(Course, Course.id == ClassSession.course_id).join(
                HodAssignment,
                and_(
                    HodAssignment.department_id == Course.department_id,
                    HodAssignment.teacher_id == teacher.id,
                ),
            )
        session = await self.db.scalar(statement)
        if not session:
            raise AppError(404, "session_not_found", "Session not found")
        return session

    async def register_device(self, user: User) -> str:
        student = await self.current_student(user)
        existing = await self.db.scalar(
            select(DeviceRegistration.id).where(
                DeviceRegistration.student_id == student.id,
                DeviceRegistration.is_active.is_(True),
            )
        )
        if existing:
            raise AppError(409, "device_exists", "A device is already registered")
        token = new_opaque_token()
        self.db.add(DeviceRegistration(student_id=student.id, device_token_hash=sha256_hex(token)))
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AppError(409, "device_exists", "A device is already registered") from exc
        return token

    async def create_session(self, user: User, course_id: UUID) -> tuple[ClassSession, str]:
        teacher = await self.current_teacher(user)
        if user.role == UserRole.teacher:
            authorized = await self.db.scalar(
                select(TeacherCourseMapping.id).where(
                    TeacherCourseMapping.teacher_id == teacher.id,
                    TeacherCourseMapping.course_id == course_id,
                )
            )
        else:
            authorized = await self.db.scalar(
                select(Course.id)
                .join(
                    HodAssignment,
                    and_(
                        HodAssignment.department_id == Course.department_id,
                        HodAssignment.teacher_id == teacher.id,
                    ),
                )
                .where(Course.id == course_id)
            )
        if not authorized:
            raise AppError(403, "course_permission_denied", "Not authorized for this course")
        secret = pyotp.random_base32()
        session = ClassSession(
            course_id=course_id,
            teacher_id=teacher.id,
            totp_secret_encrypted=encrypt_totp_secret(secret),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        token = pyotp.TOTP(secret, interval=get_settings().totp_interval_seconds).now()
        return session, token

    async def current_qr(self, user: User, session_id: UUID) -> tuple[ClassSession, str]:
        teacher = await self.current_teacher(user)
        session = await self.authorized_session(user, teacher, session_id)
        if not session.is_active:
            raise AppError(404, "active_session_not_found", "Active session not found")
        token = pyotp.TOTP(
            decrypt_totp_secret(session.totp_secret_encrypted),
            interval=get_settings().totp_interval_seconds,
        ).now()
        return session, token

    async def end_session(self, user: User, session_id: UUID) -> None:
        teacher = await self.current_teacher(user)
        session = await self.authorized_session(user, teacher, session_id)
        if not session.is_active:
            raise AppError(409, "session_already_ended", "Session is already ended")
        session.is_active = False
        session.end_time = utcnow()
        await self.db.commit()

    async def scan(self, user: User, session_id: UUID, token: str, device_token: str | None) -> None:
        if not device_token:
            raise AppError(403, "device_cookie_missing", "Registered device cookie missing")
        student = await self.current_student(user)
        device = await self.db.scalar(
            select(DeviceRegistration).where(
                DeviceRegistration.student_id == student.id,
                DeviceRegistration.device_token_hash == sha256_hex(device_token),
                DeviceRegistration.is_active.is_(True),
            )
        )
        if not device:
            self.db.add(
                SecurityEvent(
                    event_type="DEVICE_MISMATCH",
                    actor_id=user.id,
                    severity="high",
                    metadata_json={"student_id": str(student.id)},
                )
            )
            await self.db.commit()
            metrics.record_security_event("DEVICE_MISMATCH")
            raise AppError(403, "device_mismatch", "Device mismatch")
        session = await self.db.scalar(
            select(ClassSession).where(
                ClassSession.id == session_id,
                ClassSession.is_active.is_(True),
            )
        )
        if not session:
            raise AppError(404, "active_session_not_found", "Active session not found")
        enrollment = await self.db.scalar(
            select(StudentCourseEnrollment.id).where(
                StudentCourseEnrollment.student_id == student.id,
                StudentCourseEnrollment.course_id == session.course_id,
            )
        )
        if not enrollment:
            raise AppError(403, "course_enrollment_required", "Student is not enrolled in this course")
        totp = pyotp.TOTP(
            decrypt_totp_secret(session.totp_secret_encrypted),
            interval=get_settings().totp_interval_seconds,
        )
        if not totp.verify(token, valid_window=get_settings().totp_valid_window):
            metrics.record_security_event("INVALID_ATTENDANCE_TOKEN")
            raise AppError(400, "attendance_token_invalid", "Invalid or expired attendance token")
        device.last_seen_at = utcnow()
        self.db.add(AttendanceLog(student_id=student.id, session_id=session.id, device_id=device.id))
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            self.db.add(
                SecurityEvent(
                    event_type="DUPLICATE_SCAN_ATTEMPT",
                    actor_id=user.id,
                    severity="medium",
                )
            )
            await self.db.commit()
            metrics.record_security_event("DUPLICATE_SCAN_ATTEMPT")
            raise AppError(409, "attendance_duplicate", "Attendance already recorded for this session") from exc

    async def student_summary(self, user: User) -> list[dict[str, object]]:
        student = await self.current_student(user)
        result = await self.db.execute(
            select(
                Course.course_code,
                Course.course_name,
                func.count(ClassSession.id).label("total_sessions"),
                func.count(AttendanceLog.id).label("attended"),
            )
            .select_from(StudentCourseEnrollment)
            .join(Course, Course.id == StudentCourseEnrollment.course_id)
            .outerjoin(ClassSession, ClassSession.course_id == Course.id)
            .outerjoin(
                AttendanceLog,
                and_(
                    AttendanceLog.session_id == ClassSession.id,
                    AttendanceLog.student_id == student.id,
                ),
            )
            .where(StudentCourseEnrollment.student_id == student.id)
            .group_by(Course.id, Course.course_code, Course.course_name)
            .order_by(Course.course_code)
        )
        rows = []
        for code, name, total, attended in result.all():
            total_count = int(total or 0)
            attended_count = int(attended or 0)
            rows.append(
                {
                    "course_code": code,
                    "course_name": name,
                    "attended": attended_count,
                    "total_sessions": total_count,
                    "percentage": round((attended_count / total_count) * 100, 2) if total_count else 0,
                }
            )
        return rows

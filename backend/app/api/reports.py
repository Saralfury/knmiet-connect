import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.errors import AppError
from app.db.session import get_db
from app.models.academics import Course, StudentCourseEnrollment, TeacherCourseMapping
from app.models.attendance import AttendanceLog, ClassSession
from app.models.users import HodAssignment, Student, Teacher, User, UserRole

router = APIRouter(prefix="/reports", tags=["reports"])


async def authorize_course_report(
    db: AsyncSession,
    user: User,
    course_id: UUID,
) -> Course:
    course = await db.scalar(select(Course).where(Course.id == course_id))
    if not course:
        raise AppError(404, "course_not_found", "Course not found")
    if user.role in {UserRole.director, UserRole.admin}:
        return course

    teacher = await db.scalar(
        select(Teacher).where(Teacher.user_id == user.id, Teacher.is_active.is_(True))
    )
    if not teacher:
        raise AppError(403, "teacher_profile_required", "Teacher profile is required")
    if user.role == UserRole.teacher:
        authorized = await db.scalar(
            select(TeacherCourseMapping.id).where(
                TeacherCourseMapping.teacher_id == teacher.id,
                TeacherCourseMapping.course_id == course_id,
            )
        )
    else:
        authorized = await db.scalar(
            select(HodAssignment.id).where(
                HodAssignment.teacher_id == teacher.id,
                HodAssignment.department_id == course.department_id,
            )
        )
    if not authorized:
        raise AppError(403, "report_permission_denied", "Not authorized to export this course")
    return course


def attendance_report_statement(course_id: UUID):
    return (
        select(Student.roll_no, User.name, func.count(ClassSession.id).label("attended"))
        .select_from(StudentCourseEnrollment)
        .join(Student, Student.id == StudentCourseEnrollment.student_id)
        .join(User, User.id == Student.user_id)
        .outerjoin(AttendanceLog, AttendanceLog.student_id == Student.id)
        .outerjoin(
            ClassSession,
            and_(
                ClassSession.id == AttendanceLog.session_id,
                ClassSession.course_id == course_id,
            ),
        )
        .where(StudentCourseEnrollment.course_id == course_id)
        .group_by(Student.roll_no, User.name)
        .order_by(Student.roll_no)
    )


@router.get("/attendance/course/{course_id}.csv")
async def course_attendance_csv(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.teacher, UserRole.hod, UserRole.director, UserRole.admin)),
) -> Response:
    await authorize_course_report(db, user, course_id)
    total_sessions = await db.scalar(select(func.count()).select_from(ClassSession).where(ClassSession.course_id == course_id))
    result = await db.execute(attendance_report_statement(course_id))
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["roll_no", "name", "attended", "total_sessions", "percentage"])
    for roll_no, name, attended in result.all():
        total = int(total_sessions or 0)
        present = int(attended or 0)
        writer.writerow([roll_no, name, present, total, round((present / total) * 100, 2) if total else 0])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendance_report.csv"'},
    )

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("semester BETWEEN 1 AND 8", name="ck_courses_semester"),
        CheckConstraint("total_lectures >= 0", name="ck_courses_total_lectures"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    course_name: Mapped[str] = mapped_column(String(160), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"))
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    total_lectures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TeacherCourseMapping(Base):
    __tablename__ = "teacher_course_mapping"
    __table_args__ = (UniqueConstraint("teacher_id", "course_id", name="uix_teacher_course"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentCourseEnrollment(Base):
    __tablename__ = "student_course_enrollment"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uix_student_course"),
        CheckConstraint("semester BETWEEN 1 AND 8", name="ck_enrollment_semester"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Timetable(Base):
    __tablename__ = "timetable"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_timetable_day"),
        CheckConstraint("start_time < end_time", name="ck_timetable_time_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Marks(Base):
    __tablename__ = "marks"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uix_student_course_marks"),
        CheckConstraint("sessional1 BETWEEN 0 AND 100", name="ck_marks_sessional1"),
        CheckConstraint("sessional2 BETWEEN 0 AND 100", name="ck_marks_sessional2"),
        CheckConstraint("put_marks BETWEEN 0 AND 100", name="ck_marks_put"),
        CheckConstraint("total_marks BETWEEN 0 AND 300", name="ck_marks_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    sessional1: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sessional2: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    put_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

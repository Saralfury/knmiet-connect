import asyncio
import csv
from io import StringIO

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_password
from app.models.academics import Course, StudentCourseEnrollment, TeacherCourseMapping
from app.models.users import Department, Student, User, UserRole
from app.schemas.admin import (
    CourseCreateRequest,
    DepartmentCreateRequest,
    StudentCourseRequest,
    StudentImportRow,
    TeacherCourseRequest,
)


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _close_read_transaction(self) -> None:
        if self.db.in_transaction():
            await self.db.commit()

    async def create_department(self, payload: DepartmentCreateRequest) -> Department:
        await self._close_read_transaction()
        try:
            async with self.db.begin():
                department = Department(name=payload.name, code=payload.code.upper())
                self.db.add(department)
                await self.db.flush()
        except IntegrityError as exc:
            raise AppError(409, "department_conflict", "Department code already exists") from exc
        return department

    async def create_course(self, payload: CourseCreateRequest) -> Course:
        await self._close_read_transaction()
        try:
            async with self.db.begin():
                department = await self.db.scalar(
                    select(Department).where(Department.code == payload.department_code.upper())
                )
                if not department:
                    raise AppError(404, "department_not_found", "Department not found")
                course = Course(
                    course_code=payload.course_code.upper(),
                    course_name=payload.course_name,
                    department_id=department.id,
                    semester=payload.semester,
                )
                self.db.add(course)
                await self.db.flush()
        except IntegrityError as exc:
            raise AppError(409, "course_conflict", "Course code already exists") from exc
        return course

    async def assign_teacher(self, payload: TeacherCourseRequest) -> TeacherCourseMapping:
        await self._close_read_transaction()
        try:
            async with self.db.begin():
                mapping = TeacherCourseMapping(
                    teacher_id=payload.teacher_id,
                    course_id=payload.course_id,
                )
                self.db.add(mapping)
                await self.db.flush()
        except IntegrityError as exc:
            raise AppError(409, "teacher_course_conflict", "Teacher is already assigned or reference is invalid") from exc
        return mapping

    async def enroll_student(self, payload: StudentCourseRequest) -> StudentCourseEnrollment:
        await self._close_read_transaction()
        try:
            async with self.db.begin():
                enrollment = StudentCourseEnrollment(
                    student_id=payload.student_id,
                    course_id=payload.course_id,
                    semester=payload.semester,
                )
                self.db.add(enrollment)
                await self.db.flush()
        except IntegrityError as exc:
            raise AppError(409, "student_course_conflict", "Student is already enrolled or reference is invalid") from exc
        return enrollment

    async def import_students(self, content: bytes) -> tuple[int, int]:
        rows = self._parse_and_validate_csv(content)
        password_hashes = await asyncio.gather(
            *[
                hash_password(row.password or f"{row.roll_no}@KNMIET")
                for row in rows
            ]
        )
        await self._close_read_transaction()
        try:
            async with self.db.begin():
                department_codes = {row.department.upper() for row in rows}
                departments = {
                    department.code: department
                    for department in (
                        await self.db.scalars(
                            select(Department).where(Department.code.in_(department_codes))
                        )
                    ).all()
                }
                missing = sorted(department_codes - set(departments))
                if missing:
                    raise AppError(
                        400,
                        "unknown_departments",
                        "CSV contains unknown departments",
                        {"departments": missing},
                    )
                emails = {str(row.email).lower() for row in rows}
                roll_numbers = {row.roll_no for row in rows}
                existing_emails = set(
                    (
                        await self.db.scalars(select(User.email).where(User.email.in_(emails)))
                    ).all()
                )
                existing_rolls = set(
                    (
                        await self.db.scalars(
                            select(Student.roll_no).where(Student.roll_no.in_(roll_numbers))
                        )
                    ).all()
                )
                created = 0
                skipped = 0
                for row, password_hash in zip(rows, password_hashes):
                    email = str(row.email).lower()
                    if email in existing_emails or row.roll_no in existing_rolls:
                        skipped += 1
                        continue
                    user = User(
                        email=email,
                        name=row.name,
                        role=UserRole.student,
                        password_hash=password_hash,
                    )
                    self.db.add(user)
                    await self.db.flush()
                    self.db.add(
                        Student(
                            user_id=user.id,
                            roll_no=row.roll_no,
                            department_id=departments[row.department.upper()].id,
                            semester=row.semester,
                            section=row.section,
                            phone=row.phone,
                        )
                    )
                    created += 1
        except IntegrityError as exc:
            raise AppError(409, "student_import_conflict", "CSV import conflicts with existing data") from exc
        return created, skipped

    @staticmethod
    def _parse_and_validate_csv(content: bytes) -> list[StudentImportRow]:
        try:
            text_content = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise AppError(400, "csv_encoding_invalid", "CSV must use UTF-8 encoding") from exc
        reader = csv.DictReader(StringIO(text_content))
        required = {"roll_no", "name", "email", "department", "semester", "section"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise AppError(
                400,
                "csv_columns_missing",
                "CSV is missing required columns",
                {"required": sorted(required)},
            )
        rows = []
        validation_errors = []
        for line_number, raw_row in enumerate(reader, start=2):
            normalized = {key: (value.strip() if value else None) for key, value in raw_row.items()}
            try:
                rows.append(StudentImportRow.model_validate(normalized))
            except ValidationError as exc:
                validation_errors.append({"line": line_number, "errors": exc.errors()})
        if validation_errors:
            raise AppError(400, "csv_validation_failed", "CSV validation failed", validation_errors)
        if not rows:
            raise AppError(400, "csv_empty", "CSV contains no student rows")
        emails = [str(row.email).lower() for row in rows]
        rolls = [row.roll_no for row in rows]
        if len(emails) != len(set(emails)) or len(rolls) != len(set(rolls)):
            raise AppError(400, "csv_duplicates", "CSV contains duplicate email or roll number values")
        return rows

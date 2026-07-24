from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.users import User, UserRole
from app.schemas.admin import (
    CourseCreateRequest,
    DepartmentCreateRequest,
    ImportStudentsResponse,
    ResourceCreatedResponse,
    StudentCourseRequest,
    TeacherCourseRequest,
)
from app.schemas.common import MessageResponse
from app.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/departments", response_model=ResourceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.hod, UserRole.admin)),
) -> ResourceCreatedResponse:
    department = await AdminService(db).create_department(payload)
    return ResourceCreatedResponse(id=department.id, message="Department created")


@router.post("/courses", response_model=ResourceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.hod, UserRole.admin)),
) -> ResourceCreatedResponse:
    course = await AdminService(db).create_course(payload)
    return ResourceCreatedResponse(id=course.id, message="Course created")


@router.post("/teacher-course", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def assign_teacher_course(
    payload: TeacherCourseRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.hod, UserRole.admin)),
) -> MessageResponse:
    await AdminService(db).assign_teacher(payload)
    return MessageResponse(message="Teacher assigned")


@router.post("/student-course", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student_course(
    payload: StudentCourseRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.hod, UserRole.admin)),
) -> MessageResponse:
    await AdminService(db).enroll_student(payload)
    return MessageResponse(message="Student enrolled")


@router.post("/students/import-csv", response_model=ImportStudentsResponse)
async def import_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.hod, UserRole.admin)),
) -> ImportStudentsResponse:
    created, skipped = await AdminService(db).import_students(await file.read())
    return ImportStudentsResponse(created=created, skipped=skipped)

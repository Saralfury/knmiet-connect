from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=20)


class CourseCreateRequest(BaseModel):
    course_code: str = Field(min_length=2, max_length=40)
    course_name: str = Field(min_length=2, max_length=160)
    department_code: str = Field(min_length=2, max_length=20)
    semester: int = Field(ge=1, le=8)


class TeacherCourseRequest(BaseModel):
    teacher_id: UUID
    course_id: UUID


class StudentCourseRequest(BaseModel):
    student_id: UUID
    course_id: UUID
    semester: int = Field(ge=1, le=8)


class ResourceCreatedResponse(BaseModel):
    id: UUID
    message: str


class ImportStudentsResponse(BaseModel):
    created: int
    skipped: int


class StudentImportRow(BaseModel):
    roll_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    department: str = Field(min_length=2, max_length=20)
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=10)
    phone: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=128)

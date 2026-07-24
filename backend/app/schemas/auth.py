from pydantic import BaseModel, EmailStr, Field

from app.models.users import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8)
    role: UserRole
    department_code: str | None = None
    roll_no: str | None = None
    employee_code: str | None = None
    semester: int | None = None
    section: str | None = None
    phone: str | None = None


class CreatePrivilegedUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole
    department_code: str | None = None
    employee_code: str | None = None


class LoginResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole

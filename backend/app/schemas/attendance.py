from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    course_id: UUID


class CreateSessionResponse(BaseModel):
    session_id: UUID
    qr_payload: str


class CurrentQRResponse(CreateSessionResponse):
    token: str


class ScanRequest(BaseModel):
    session_id: UUID
    token: str = Field(min_length=4, max_length=12)


class CorrectAttendanceRequest(BaseModel):
    status: str
    reason: str = Field(min_length=5, max_length=500)


class AttendanceSummary(BaseModel):
    course_code: str
    course_name: str
    attended: int
    total_sessions: int
    percentage: float

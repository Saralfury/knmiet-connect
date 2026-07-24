from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.users import User, UserRole
from app.schemas.attendance import (
    AttendanceSummary,
    CreateSessionRequest,
    CreateSessionResponse,
    CurrentQRResponse,
    ScanRequest,
)
from app.schemas.common import MessageResponse
from app.services.attendance import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/devices/register", response_model=MessageResponse)
async def register_device(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
) -> MessageResponse:
    token = await AttendanceService(db).register_device(user)
    settings = get_settings()
    response.set_cookie(
        settings.device_cookie_name,
        token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=94608000,
    )
    return MessageResponse(message="Device registered")


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    payload: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.teacher, UserRole.hod)),
) -> CreateSessionResponse:
    session, token = await AttendanceService(db).create_session(user, payload.course_id)
    return CreateSessionResponse(
        session_id=session.id,
        qr_payload=f"knmiet://attendance/{session.id}?token={token}",
    )


@router.get("/sessions/{session_id}/qr", response_model=CurrentQRResponse)
async def current_qr(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.teacher, UserRole.hod)),
) -> CurrentQRResponse:
    session, token = await AttendanceService(db).current_qr(user, session_id)
    return CurrentQRResponse(
        session_id=session.id,
        token=token,
        qr_payload=f"knmiet://attendance/{session.id}?token={token}",
    )


@router.post("/sessions/{session_id}/end", response_model=MessageResponse)
async def end_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.teacher, UserRole.hod)),
) -> MessageResponse:
    await AttendanceService(db).end_session(user, session_id)
    return MessageResponse(message="Session ended")


@router.post("/scan", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def scan_attendance(
    payload: ScanRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
    device_token: str | None = Cookie(default=None, alias=get_settings().device_cookie_name),
) -> MessageResponse:
    await AttendanceService(db).scan(user, payload.session_id, payload.token, device_token)
    return MessageResponse(message="Attendance marked")


@router.get("/me", response_model=list[AttendanceSummary])
async def my_attendance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
) -> list[AttendanceSummary]:
    rows = await AttendanceService(db).student_summary(user)
    return [AttendanceSummary(**row) for row in rows]

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import new_opaque_token
from app.db.session import get_db
from app.models.users import User, UserRole
from app.schemas.auth import (
    CreatePrivilegedUserRequest,
    LoginRequest,
    LoginResponse,
    RegisterUserRequest,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth import (
    AuthService,
    claim_refresh_token_statement,
    revoke_refresh_family_statement,
    revoke_refresh_token_statement,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.access_cookie_name,
        access_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.refresh_token_days * 24 * 60 * 60,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        new_opaque_token(),
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.refresh_token_days * 24 * 60 * 60,
    )


def login_response(user: User) -> LoginResponse:
    return LoginResponse(id=str(user.id), name=user.name, email=user.email, role=user.role)


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterUserRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    result = await AuthService(db).register_student(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return login_response(result.user)


@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_privileged_user(
    payload: CreatePrivilegedUserRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
) -> UserResponse:
    user = await AuthService(db).create_privileged_user(payload)
    return UserResponse(id=str(user.id), name=user.name, email=user.email, role=user.role)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    ip_address = request.client.host if request.client else None
    result = await AuthService(db).login(payload, ip_address)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return login_response(result.user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    settings = get_settings()
    await AuthService(db).logout(request.cookies.get(settings.refresh_cookie_name))
    response.delete_cookie(settings.access_cookie_name)
    response.delete_cookie(settings.refresh_cookie_name)
    response.delete_cookie(settings.csrf_cookie_name)
    return MessageResponse(message="Logged out")


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise AppError(401, "refresh_token_missing", "Refresh token missing")
    result = await AuthService(db).refresh(token)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return login_response(result.user)

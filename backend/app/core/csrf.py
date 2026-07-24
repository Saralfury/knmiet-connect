import secrets
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings
from app.core.errors import error_payload


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
TOKEN_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/register"}


def _request_origin(request: Request) -> str | None:
    origin = request.headers.get("Origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("Referer")
    if not referer:
        return None
    parsed = urlsplit(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in SAFE_METHODS or not request.url.path.startswith("/api/"):
            return await call_next(request)

        settings = get_settings()
        allowed_origins = {origin.rstrip("/") for origin in settings.cors_origins}
        if _request_origin(request) not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content=error_payload("untrusted_origin", "Untrusted request origin"),
            )

        if request.url.path not in TOKEN_EXEMPT_PATHS:
            cookie_token = request.cookies.get(settings.csrf_cookie_name)
            header_token = request.headers.get(settings.csrf_header_name)
            if (
                not cookie_token
                or not header_token
                or not secrets.compare_digest(cookie_token, header_token)
            ):
                return JSONResponse(
                    status_code=403,
                    content=error_payload("csrf_validation_failed", "CSRF validation failed"),
                )

        return await call_next(request)

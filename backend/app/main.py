from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import admin, attendance, auth, reports
from app.core.config import get_settings
from app.core.csrf import CSRFMiddleware
from app.core.errors import AppError, error_payload
from app.core.metrics import metrics
from app.core.observability import RequestObservabilityMiddleware
from app.db.session import engine

settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RequestObservabilityMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.details),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {
        400: "bad_request",
        401: "authentication_required",
        403: "permission_denied",
        404: "not_found",
        409: "conflict",
        423: "account_locked",
    }.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = None if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, message, details),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload("validation_error", "Request validation failed", exc.errors()),
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_payload("internal_error", "Internal server error"),
    )

app.include_router(auth.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/health/live")
@app.get("/health")
async def health_live() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/health/ready")
async def health_ready() -> JSONResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )
    return JSONResponse(content={"status": "ready"})


@app.get("/metrics")
async def application_metrics() -> dict[str, object]:
    snapshot = metrics.snapshot()
    pool = engine.pool
    snapshot["database_pool"] = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": max(0, pool.overflow()),
    }
    return snapshot


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# System Audit Report: KNMIET Connect Attendance App

> [!IMPORTANT]
> This is a comprehensive, principal-level system engineering audit of the KNMIET Connect Attendance App. The application has been evaluated against production-grade security, scalability, and operational standards. Every claim references specific files and components in the repository.

---

## 1. Project Inventory
The application follows a standard three-tier architecture:
- **Frontend**: A minimal Progressive Web App (PWA) located in `frontend/`. It consists of static assets (`index.html`, `styles.css`, `app.js`, `manifest.json`, `service-worker.js`).
- **Backend**: A Python web service built with FastAPI (`backend/app/main.py`), utilizing SQLAlchemy 2.0 with the `asyncpg` driver for asynchronous database access. Database migrations are managed by Alembic (`backend/alembic/`).
- **Database**: PostgreSQL 16 (inferred from infrastructure and asyncpg usage).
- **Infrastructure**: Containerized using Docker (`docker-compose.yml`), with Nginx (`nginx/nginx.conf`) acting as a reverse proxy and static file server.

## 2. Architecture Audit
- **Topology**: The system uses a separated network topology defined in `docker-compose.yml`. Nginx is the public-facing entry point (ports 80/443), proxying API requests to the `backend` container and serving static files. The `db` (PostgreSQL) is isolated on an internal network (`knmiet-db`) accessible only by the backend.
- **Data Flow**: Client (PWA) `->` Nginx `->` FastAPI `->` PostgreSQL. The frontend communicates with the backend exclusively via REST APIs under the `/api/` prefix (verified in `frontend/service-worker.js` line 23 and `frontend/app.js` line 24).
- **Resilience**: The backend exposes `/health/live` and `/health/ready` (checking DB connectivity) in `backend/app/main.py` (lines 3025-3041) for container orchestration platforms.

## 3. Dependency Audit
- **Core Packages**: The backend relies on `fastapi`, `sqlalchemy`, `asyncpg`, `alembic`, `pyotp` (for TOTP), `cryptography` (for Fernet encryption), `jose` (for JWT), and `passlib[bcrypt]` (for password hashing).
- **Vulnerability Risk**: No explicitly declared version lock file (e.g., `requirements.txt` or `poetry.lock`) was found in the dumped output. *Unable to verify* exact dependency versions and associated CVEs.

## 4. Docker & Infrastructure Audit
- **Isolation**: Services are logically isolated via Docker networks (`knmiet-frontend`, `knmiet-backend`, `knmiet-db` per `docker-compose.yml`). The database is not exposed to the host machine (no port mapping).
- **Resource Limits**: Nginx (`nginx/nginx.conf`) implements rate limiting (`limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;` and a stricter auth limit of `5r/s`). 
- **Security Headers**: Nginx sets standard security headers (`X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, and strict CSP restricting scripts to `'self'`).

## 5. Configuration & Secret Management
- **Configuration**: Handled by `pydantic-settings` in `backend/app/core/config.py`.
- **Secrets**: `DATABASE_URL`, `JWT_SECRET_KEY`, and `TOTP_ENCRYPTION_KEY` are read from environment variables.
- **Validation**: Production settings are strictly validated in `Settings.validate_production_security` (`config.py` line 354). It asserts `environment == "production"` requires `secure_cookies = True`, `https_enabled = True`, and a strong non-default `jwt_secret_key`. `TOTP_ENCRYPTION_KEY` is validated as a legitimate Fernet key.
- **Leaks**: No hardcoded secrets were found in the codebase.

## 6. Database Schema Audit
- **Tables**: Mapped thoroughly in `backend/app/models/`. Covers `users`, `departments`, `students`, `teachers`, `courses`, `class_sessions`, `attendance_logs`, `refresh_tokens`, `device_registrations`, and several audit tables.
- **Constraints**: 
  - Domain constraints are actively enforced in PostgreSQL (added in `alembic/versions/0004_domain_constraints.py`), checking valid ranges (e.g., `semester BETWEEN 1 AND 8`, `ck_timetable_time_order`).
  - Referential integrity utilizes `ON DELETE CASCADE` and `RESTRICT` appropriately (e.g., `device_registrations.student_id` cascades, while `attendance_logs.device_id` restricts deletion in `models/attendance.py`).
- **Indexes**: Redundant indexes covered by unique constraints were pruned via `0005_remove_redundant_indexes.py`, demonstrating high-quality schema design.

## 7. Query & ORM Audit
- **ORM Patterns**: The backend uses SQLAlchemy 2.0 async sessions (`app/db/session.py`).
- **Performance**: Joins are constructed efficiently. E.g., `attendance_report_statement` (`api/reports.py` line 1261) leverages explicit `.join()` and `.outerjoin()` with `group_by` to prevent N+1 queries during CSV generation.
- **Locking**: *Unable to verify* explicit row-level locking (e.g., `FOR UPDATE`), which may be a risk if concurrent marking of attendance for the same student/session occurs, though a `UniqueConstraint("student_id", "session_id")` mitigates duplicate log creation (handled via `IntegrityError` in `services/attendance.py` line 2609).

## 8. Frontend Security & Logic
- **Storage**: The application does not store sensitive tokens in `localStorage`.
- **CSRF**: Mitigated via the Double-Submit Cookie pattern. `app.js` (line 18) reads the non-HttpOnly `csrf_token` cookie and sends it as the `X-CSRF-Token` header for state-changing requests.
- **XSS**: Safe DOM manipulation is used. `app.js` avoids `.innerHTML`, utilizing `document.createElement("tr")` and `.textContent` (line 120), preventing malicious script injection via DOM.

## 9. Backend API Audit
- **Validation**: All incoming payloads are validated using strict Pydantic schemas (`app/schemas/*.py`).
- **Verb Abuse**: Standard HTTP verbs are respected (`GET` for reads, `POST` for creations/mutations). `SAFE_METHODS` (`core/csrf.py` line 1385) correctly excludes `GET`/`HEAD`/`OPTIONS` from CSRF checks.
- **Business Logic Enforcement**: 
  - `AdminService.enroll_student` (`services/admin.py` line 2302) correctly traps `IntegrityError`.
  - Device token verification validates the exact hash provided by the client (`services/attendance.py` line 2559).

## 10. Authentication & Authorization
- **Hashing**: Passwords are hashed asynchronously using `bcrypt` via `asyncio.to_thread` (`core/security.py` line 1595), preventing event loop blocking.
- **JWT**: Access tokens have short lifetimes (default 15 minutes, `config.py` line 1329).
- **Refresh Tokens**: Opaque tokens are hashed (SHA256) before DB storage (`services/auth.py` line 2712). Implements token family tracking, revocation on reuse (`services/auth.py` line 2911), and rotation (`services/auth.py` line 2924).
- **TOTP**: Teacher session tokens are securely encrypted at rest using Fernet (`core/totp_crypto.py`). Time-window validation (`valid_window=1`) in `services/attendance.py` (line 2602) mitigates replay attacks.
- **Authorization**: Endpoint access is constrained by the `require_roles` dependency (`api/deps.py` line 1197), ensuring strict Role-Based Access Control (RBAC).

## 11. Middleware & Request Lifecycle
- **CORS**: `CORSMiddleware` (`main.py` line 2968) correctly restricts allowed origins per `settings.cors_origins`.
- **CSRF Middleware**: Evaluates origin/referer headers and validates the `X-CSRF-Token` against the cookie (`core/csrf.py`). Exempt paths are restricted to login/register endpoints.
- **Observability Middleware**: `RequestObservabilityMiddleware` injects an `X-Request-ID` and logs request timing/status to stdout (`core/observability.py`).

## 12. Error Handling & Information Disclosure
- **Standardization**: All exceptions subclass `AppError` (`core/errors.py`).
- **Information Leakage**: The global exception handler (`main.py` line 3012) intercepts generic `Exception` types and returns a generic 500 error (`{"code": "internal_error", "message": "Internal server error"}`), entirely preventing stack trace disclosure to end users.
- **Validation Errors**: Pydantic `RequestValidationError` instances are safely wrapped (`main.py` line 3004).

## 13. Concurrency & Performance
- **Event Loop Blocking**: Password hashing, the most intensive CPU-bound operation, is successfully offloaded to a thread pool via `asyncio.to_thread` in `core/security.py`.
- **Race Conditions**: Refresh token replacement (`services/auth.py` line 2899) uses an atomic `UPDATE ... RETURNING` via `claim_refresh_token_statement` to prevent race conditions during concurrent token refresh attempts.

## 14. Background Jobs & Worker Architecture
- No external message broker (RabbitMQ/Redis) or worker framework (Celery) is used.
- Background operations (such as sending emails or heavy report generation) are not explicitly present. CSV imports occur synchronously within the request lifecycle (`api/admin.py` line 923), which could lead to timeout vulnerabilities for massive datasets.

## 15. Compliance & Audit Logging
- **Triggers**: PostgreSQL triggers log attendance (`audit_attendance_changes`), timetable, and marks modifications into `_audit` tables (`alembic/versions/0003_phase2_security.py`).
- **Context Injection**: The application actor ID and reason are injected into PostgreSQL session config (`set_config('app.actor_id', ...)`) via `app/db/audit.py`, ensuring DB-level logs contain the identity of the user.
- **Security Events**: `SecurityEvent` model (`models/audit.py` line 1941) logs anomalies such as `FAILED_LOGIN`, `DEVICE_MISMATCH`, and `REFRESH_TOKEN_REUSE` for SIEM ingest.

## 16. Code Quality & SOLID Principles
- **DRY/SRP**: Excellent separation of concerns. Routes (`api/`), business logic (`services/`), DB models (`models/`), and schemas (`schemas/`) are decoupled.
- **Typing**: Strict Python type hints are employed universally (e.g., `async def get_current_user(...) -> User:`).
- **Constants/Enums**: `UserRole` and `AttendanceStatus` are explicitly mapped to PostgreSQL `ENUM` types.

## 17. Testing & Coverage
- **Integration Tests**: Extensive tests (`tests/integration/`) check real database behaviors. `verify_domain_constraints.py`, `verify_redundant_indexes.py`, and `verify_audit_permissions.py` assert that PostgreSQL schema mechanics and RBAC function as expected.
- **Security Tests**: `tests/test_phase1_security.py` and `tests/test_phase2_security.py` rigorously assert API access bounds (e.g., preventing privileged role self-registration, asserting token reuse revokes families).
- **Blind Spots**: *Unable to verify* the percentage of unit test coverage, as there are no test coverage reports or UI test suites included in the snapshot.

## 18. Incident Response & Observability
- **Metrics**: Exposes a `/metrics` endpoint (`main.py` line 3044) dumping a JSON snapshot of request counts, response time averages, error counts, DB pool states, and security event frequencies (tracked by `core/metrics.py`).
- **Structured Logging**: `core/observability.py` uses JSON logging to output structured data to `stdout`, which is ideal for ingestion by tools like Datadog, ELK, or Splunk.
- **Traceability**: `X-Request-ID` is correctly generated, attached to the request state, and reflected in the HTTP response headers.

# KNMIET Connect Attendance App

Self-hosted FastAPI + PostgreSQL + static PWA implementation for secure institutional attendance.

## What Is Implemented

- Async FastAPI backend with SQLAlchemy 2.0 and Alembic.
- Role-based JWT authentication using HttpOnly cookies.
- bcrypt password hashing offloaded from the async event loop.
- Server-issued HttpOnly device registration token, stored as SHA-256 in PostgreSQL.
- Persistent class sessions with TOTP attendance validation.
- Enrollment check before attendance can be marked.
- Database unique constraint for duplicate attendance protection.
- PostgreSQL trigger-backed audit tables for attendance, marks, and timetable updates.
- CSV student import and CSV attendance export without pandas.
- Static HTML/CSS/ES module PWA shell.
- Service worker cache-first for static assets and network-only for `/api/*`.
- Docker Compose with PostgreSQL, single-worker Uvicorn backend, and Nginx.
- Nginx rate limits for auth and scan endpoints.
- Service-layer authentication and attendance workflows with standardized API errors.
- Database readiness checks, structured JSON request logs, and lightweight metrics.
- PostgreSQL domain CHECK constraints and EXPLAIN-verified redundant-index cleanup.
- Service-worker cache version eviction and safe same-origin GET-only response caching.

## Run Locally With Docker

Generate a Fernet key and place it in `.env` as `TOTP_ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

Create the first administrator once, from the backend container:

```bash
docker compose exec backend python scripts/bootstrap_admin.py --email admin@example.edu --name "System Admin"
```

After that, privileged accounts are created through authenticated `POST /api/auth/admin/users` requests.

Browser clients use a double-submit `csrf_token` cookie. Every state-changing request
after login must return that value in the `X-CSRF-Token` header and use an Origin or
Referer matching `CORS_ORIGINS`.

Refresh tokens rotate in database-tracked families. Applying migration `0003` invalidates
refresh cookies issued by older application versions because those JWTs do not contain the
new `jti` and `family_id` claims; users must sign in again after deployment.

Verify the application database role cannot mutate audit history after deployment:

```bash
docker compose exec -T backend python tests/integration/verify_audit_permissions.py
```

Operational endpoints:

```text
GET /health/live   process liveness
GET /health/ready  PostgreSQL readiness
GET /metrics       request, latency, security-event, and DB-pool counters
```

Migration `0004_domain_constraints` enforces semester, timetable, lecture-count,
and marks ranges in PostgreSQL. Verify the complete migration chain with:

```bash
docker compose exec -T backend python tests/integration/verify_migration_roundtrip.py
docker compose exec -T backend python tests/integration/verify_domain_constraints.py
```

Migration `0005_remove_redundant_indexes` removes duplicate indexes for user email,
student roll number, course code, department code, and teacher employee code. Their
unique-constraint indexes serve the same lookup plans. `uix_student_device` is retained
because it is the sole index for device `student_id` lookups.

Verify index plans and service-worker lifecycle behavior with:

```bash
docker compose exec -T backend python tests/integration/verify_redundant_indexes.py
node frontend/tests/service-worker.test.js
```

## Security & Review Status

The original production review contained 22 findings. Twenty-one are addressed:

1. Public privileged registration is blocked; privileged creation is admin-only.
2. TOTP secrets use required Fernet authenticated encryption.
3. Teacher session ownership and HOD department scope are enforced.
4. Refresh tokens use unique JTIs, token families, atomic rotation, and reuse detection.
5. Logout revokes refresh tokens server-side.
6. Audit triggers capture actor/reason and the application role cannot update/delete audit rows.
7. Mutations use Origin/Referer validation and double-submit CSRF protection.
8. Course-report authorization is assignment/department scoped.
9. Attendance reports are anchored to course enrollment.
10. **Deferred:** mandatory 2FA for HOD/director/admin is not implemented.
11. Authentication and attendance business logic lives in service classes.
12. Admin writes are transactional; conflicts map to 409; CSV imports validate and batch-load first.
13. Student attendance summaries use one grouped query.
14. Academic ranges and timetable ordering are database CHECK constraints.
15. Production startup rejects default secrets, insecure cookies, or disabled HTTPS.
16. Liveness and database readiness are separate endpoints.
17. Security, authorization, migration, and regression tests are present.
18. Attendance rendering uses DOM APIs and `textContent`, not `innerHTML` interpolation.
19. Admin mutations use JSON models; responses and errors have consistent schemas.
20. Requests emit structured logs and expose request/security/DB-pool metrics.
21. Redundant indexes were removed only after live EXPLAIN comparison.
22. Service-worker activation evicts stale caches and caches only successful same-origin GET responses.

Privileged-account 2FA remains a known production-security gap and is tracked in
`docs/technical-debt.md`. Do not describe this application as having full privileged-account
security parity until that work is complete.

## Run Backend Directly

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --workers 1
```

## Important Production Notes

- Required configuration includes `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `APP_DB_ROLE`,
  `APP_DB_PASSWORD`, `JWT_SECRET_KEY`, `TOTP_ENCRYPTION_KEY`, `ENVIRONMENT`,
  `SECURE_COOKIES`, `HTTPS_ENABLED`, and JSON-formatted `CORS_ORIGINS`.
- Replace `JWT_SECRET_KEY` and all database passwords before deployment.
- Keep `TOTP_ENCRYPTION_KEY` stable and backed up; losing it makes active session secrets unreadable.
- Use separate migration-owner and application database URLs in production. The Phase 2
  migration creates `APP_DB_ROLE`, grants normal table access, and removes update/delete
  access from audit tables.
- Set `SECURE_COOKIES=true` behind HTTPS.
- Keep Uvicorn at `--workers 1` unless a Redis/pub-sub WebSocket layer or sticky Nginx strategy is added.
- Do not change the service worker to queue `/api/*` requests; TOTP scans must fail online-only.

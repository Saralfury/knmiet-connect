KNMIET Connect Attendance App - Extensive Documentation
=====================================================

1. Architecture Overview
------------------------
This is a robust, self-hosted institutional attendance application built using modern Web and Backend technologies. It uses a 3-tier architecture:

- Frontend: Progressive Web Application (PWA) using Vanilla HTML, CSS, and JavaScript. 
- Backend: Asynchronous Python REST API built with FastAPI.
- Database: PostgreSQL 16.
- Infrastructure: Docker Compose with Nginx acting as a reverse proxy and static file server.

2. System Components & Files
----------------------------

### Root Directory
- docker-compose.yml: Defines the containerized environment. Sets up Postgres, FastAPI backend, and Nginx. Orchestrates networking, volumes, and health checks.
- README.md: The original concise documentation.

### Frontend (PWA)
The frontend is deliberately kept lightweight, avoiding heavy frameworks like React or Angular, favoring fast load times and offline capabilities via Service Workers.
- index.html: The core application shell. Contains the login form, student scan form, teacher session generator, and attendance view.
- app.js: The main JavaScript logic. Handles DOM manipulation, API fetching, form submissions, state management, and service worker registration.
- styles.css: Defines the visual layout and responsive design.
- manifest.json: Web App Manifest for PWA installation (provides icons, theme color, etc.).
- service-worker.js: Handles caching of static assets and manages network requests for offline resilience.

### Backend (FastAPI)
The backend is a modern asynchronous Python application utilizing SQLAlchemy 2.0 for ORM and Alembic for database migrations.

- backend/Dockerfile: Uses python:3.12-slim. Installs dependencies and sets up the execution environment.
- backend/requirements.txt: Lists dependencies including fastapi, uvicorn, SQLAlchemy, asyncpg, alembic, passlib, pyotp, etc.
- backend/start.sh: Entrypoint script for the backend container.

#### backend/app/ Directory
- main.py: The FastAPI application entrypoint. Configures CORS, includes routers (auth, attendance, admin, reports), and mounts the static frontend directory.

- app/api/: Contains the routing logic for various endpoints.
  - auth.py: Handles login, logout, and token issuance.
  - attendance.py: Handles scanning, session creation, and fetching user attendance.
  - admin.py: Administrative endpoints for user management.
  - reports.py: Endpoints for generating CSV reports.
  - deps.py: FastAPI dependency injection (e.g., getting the current user, database sessions).

- app/core/: Core configuration and security logic.
  - config.py: Pydantic settings management, loading variables from environment.
  - security.py: Password hashing (bcrypt) and JWT token generation/validation.

- app/db/: Database configuration.
  - base.py: SQLAlchemy declarative base.
  - session.py: Async engine and session maker setup.

- app/models/: SQLAlchemy ORM models.
  - users.py: User accounts (Teachers, Students, Admins).
  - academics.py: Courses and enrollments.
  - attendance.py: Sessions and attendance records.
  - audit.py: Audit logging for tracking changes.

- app/schemas/: Pydantic models for data validation and serialization (request/response schemas).
  - auth.py: Login and token schemas.
  - attendance.py: Scan and session schemas.

### Nginx Configuration
- nginx/nginx.conf: Configures Nginx to serve the static frontend files and proxy API requests (`/api/*`) to the backend container. It implements rate limiting for authentication and scanning endpoints to prevent brute-force and abuse. Includes security headers.

3. Key Features
---------------
- Role-Based Access Control (RBAC): Distinguishes between Students, Teachers, and Admins.
- Secure Authentication: Uses HttpOnly cookies for JWTs to mitigate XSS attacks.
- Device Registration: Secures attendance by binding it to registered devices.
- TOTP Validation: Uses Time-based One-Time Passwords (TOTP) to validate attendance scans securely.
- Asynchronous Database Operations: Utilizes `asyncpg` for non-blocking high-performance database interactions.
- Rate Limiting: Nginx protects critical endpoints from abuse.

4. Deployment Instructions
--------------------------
1. Ensure Docker and Docker Compose are installed.
2. Clone the repository.
3. Configure environment variables (replace `JWT_SECRET_KEY` in production).
4. Run `docker compose up --build -d`.
5. Access the application at http://localhost:8080.

# Repository Deep Dive

## Folder Analysis

### Folder: .
Purpose: Root directory of the repository. Contains configuration for Docker, the root level documentation, and the application's top-level structural folders.
Contained Components:
- `docker-compose.yml`: Orchestration file.
- `.env.example`: Environment template.
- `README.md`: Short description.
- `readme.txt`: Extended documentation.
- `.dockerignore`, `.gitignore`: Git and Docker ignoring rules.
Architectural Role: The entry point for developers and deployment tools. Orchestrates the frontend, backend, and database via Docker Compose.
Dependency Relationships: Depends on Docker to run `docker-compose.yml`.

### Folder: /frontend
Purpose: Contains the vanilla HTML/JS/CSS Progressive Web App (PWA).
Contained Components:
- `index.html`: Main UI shell.
- `app.js`: Client-side logic.
- `styles.css`: CSS styling.
- `manifest.json`: Web app manifest.
- `service-worker.js`: Offline caching worker.
Architectural Role: Represents the client-tier. Interacts with the backend via REST API calls. Served statically by Nginx.
Dependency Relationships: Depends on the `/api` endpoints provided by the backend.

### Folder: /nginx
Purpose: Stores Nginx configuration files.
Contained Components:
- `nginx.conf`: Rate limiting and reverse proxy rules.
Architectural Role: Acts as the Edge/Gateway. Serves static files, enforces rate limits, adds security headers, and proxies `/api/*` to the backend.
Dependency Relationships: Depends on the `backend` container being resolvable by DNS.

### Folder: /backend
Purpose: Houses the Python FastAPI application and its Dockerfile.
Contained Components:
- `Dockerfile`: Container build instructions.
- `requirements.txt`: Python packages.
- `start.sh`: Entrypoint.
- `alembic.ini`: Migration config.
Architectural Role: The main business logic and API layer.
Dependency Relationships: Depends on PostgreSQL. Serves requests from Nginx.

### Folder: /backend/alembic & /backend/alembic/versions
Purpose: Database migration files managed by Alembic.
Contained Components:
- `env.py`: Alembic environment setup for async migrations.
Architectural Role: Translates SQLAlchemy models into PostgreSQL schema changes.
Dependency Relationships: Depends on `app.models` and `app.core.config`.

### Folder: /backend/app
Purpose: The main Python module for the backend API.
Contained Components:
- `main.py`: Application entrypoint.
- subfolders: `api`, `core`, `db`, `models`, `schemas`.
Architectural Role: Orchestrates the entire backend processing logic.

### Folder: /backend/app/api
Purpose: FastAPI routing controllers.
Contained Components:
- `auth.py`, `attendance.py`, `admin.py`, `reports.py`, `deps.py`.
Architectural Role: Exposes HTTP endpoints. Validates input schemas and triggers business logic.
Dependency Relationships: Depends on `schemas`, `models`, and `core`.

### Folder: /backend/app/core
Purpose: Security, configuration, and fundamental utilities.
Contained Components:
- `config.py`: Pydantic settings.
- `security.py`: JWT and bcrypt logic.
Architectural Role: Provides cross-cutting concerns (crypto, environment configs).

### Folder: /backend/app/db
Purpose: Database connectivity setup.
Contained Components:
- `base.py`: DeclarativeBase.
- `session.py`: Async engine and session maker.
Architectural Role: Establishes the link between the Python async loop and PostgreSQL.

### Folder: /backend/app/models
Purpose: SQLAlchemy ORM models.
Contained Components:
- `users.py`, `academics.py`, `attendance.py`, `audit.py`, `auth.py`.
Architectural Role: Represents the database schema in Python. Used for ORM operations.
Dependency Relationships: Depends on `db.base.Base`.

### Folder: /backend/app/schemas
Purpose: Pydantic schemas for data validation.
Contained Components:
- `auth.py`, `attendance.py`.
Architectural Role: Defines the shapes of incoming requests and outgoing responses.

## File Analysis

### File: docker-compose.yml
Purpose: Defines the multi-container Docker applications.
Responsibilities: Sets up `postgres`, `backend`, and `nginx` services. Wires networks, ports, and volumes. Provides healthchecks to ensure services boot in the right order.
Dependencies: Docker engine.
Detailed Walkthrough:
- `postgres`: Uses `postgres:16-alpine`. Sets credentials, mounts `postgres_data` volume, implements `pg_isready` healthcheck.
- `backend`: Builds from `./backend/Dockerfile`. Passes `DATABASE_URL` and `JWT_SECRET_KEY`. Waits for postgres health. Implements python-based healthcheck.
- `nginx`: Uses `nginx:1.27-alpine`. Mounts `nginx.conf` and `/frontend`. Waits for backend health. Exposes port 8080.
Security Notes: Exposes port 8080. Internal DB port 5432 is not exposed to host. Passwords should be injected via .env in production, not hardcoded.
Potential Risks: Hardcoded `JWT_SECRET_KEY` in the file. Should be an external env var.
Improvement Opportunities: Use `.env` file instead of hardcoded environment variables.

### File: frontend/index.html
Purpose: The entry point for the frontend PWA.
Responsibilities: Renders the layout, imports `styles.css` and `app.js`. Contains all views (Login, Scan, Teacher Session, Attendance Table).
Detailed Walkthrough:
- `<head>`: Sets theme color and links `manifest.json`.
- `<body>`: Contains `.app-shell`.
  - `#loginForm`: Email/password form.
  - `.workspace`: Main authenticated area. Contains Student Scan, Teacher Session, and My Attendance sections.
Security Notes: Uses standard forms. Relies on `app.js` to handle tokens securely.

### File: frontend/app.js
Purpose: Frontend JavaScript logic.
Responsibilities: Handles DOM events, API fetches, State management (currentUser).
Detailed Walkthrough:
- `api(path, options)`: Wrapper around `fetch`. Automatically includes credentials (cookies) and parses JSON.
- `#loginForm`: POSTs to `/api/auth/login`. Updates UI with user info.
- `#logoutBtn`: POSTs to `/api/auth/logout`. Clears state.
- `#registerDeviceBtn`: POSTs to `/api/attendance/devices/register`.
- `#scanForm`: POSTs session ID and TOTP token to mark attendance.
- `#sessionForm`: POSTs to create a session. Displays UUID and QR payload.
- `loadAttendance()`: Fetches `/api/attendance/me` and populates the table.
- Registers `service-worker.js`.
Security Notes: `credentials: "include"` ensures HttpOnly cookies are sent. No tokens are stored in `localStorage` (mitigating XSS).

### File: frontend/styles.css
Purpose: Provides visual styling.
Responsibilities: Defines color variables, typography, flexbox/grid layouts, and component classes (`.panel`, `.status`, `.stack`).
Detailed Walkthrough: Uses modern CSS features (custom properties, `gap`, `border-radius`). Responsive grid using `auto-fit`.

### File: frontend/manifest.json
Purpose: PWA Manifest.
Responsibilities: Defines app name, colors, and display mode (`standalone`) so it can be installed on mobile devices.

### File: frontend/service-worker.js
Purpose: Offline caching and network interception.
Responsibilities: Caches static assets (`/`, `/index.html`, etc.) during `install`. Intercepts `fetch` events.
Detailed Walkthrough:
- `install`: Opens cache and adds `STATIC_ASSETS`.
- `fetch`: If URL starts with `/api/`, it bypasses cache (Network Only). Otherwise, it uses Cache-First strategy, falling back to Network and caching the result.
Security Notes: Bypassing `/api/` is critical to prevent caching sensitive user data or breaking TOTP validation.

### File: nginx/nginx.conf
Purpose: Configure the Nginx web server and reverse proxy.
Responsibilities: Serves the static PWA files. Proxies API requests to the Python backend. Implements security headers and rate limiting.
Detailed Walkthrough:
- `limit_req_zone`: Defines `auth_limit` (5 req/min) and `scan_limit` (20 req/min) based on `$binary_remote_addr` (client IP).
- `add_header`: Injects anti-clickjacking (`X-Frame-Options`), MIME sniffing protection (`X-Content-Type-Options`), and a strict Content Security Policy (`CSP`).
- `location = /api/auth/login`, `/api/auth/register`: Proxies to backend with `auth_limit` applied.
- `location = /api/attendance/scan`: Proxies to backend with `scan_limit` applied.
- `location /api/`: Proxies everything else to backend.
- `location /`: Tries to serve static files. Falls back to `/index.html` (for SPA/PWA routing, though this app is mostly single-page).
Security Notes: The rate limit zones are crucial for mitigating brute-force password attacks and brute-force TOTP guessing. CSP prevents inline scripts from executing, mitigating XSS.
Improvement Opportunities: Could add SSL/TLS termination here for HTTPS instead of relying on an external load balancer.

### File: backend/Dockerfile
Purpose: Docker image definition for the Python backend.
Responsibilities: Installs dependencies, copies source code, and sets the entry command.
Detailed Walkthrough: Uses `python:3.12-slim`. Sets environment variables to prevent bytecode generation and buffering. Installs from `requirements.txt`. Copies `backend` and `frontend`. Runs `start.sh`.

### File: backend/requirements.txt
Purpose: Python dependencies.
Contained Packages: `fastapi`, `uvicorn`, `SQLAlchemy`, `asyncpg`, `alembic`, `pydantic-settings`, `email-validator`, `python-jose`, `passlib[bcrypt]`, `pyotp`, `python-multipart`, `xlsxwriter`.

### File: backend/start.sh
Purpose: Container entrypoint script.
Responsibilities: Runs database migrations using Alembic, then starts the Uvicorn ASGI server.
Detailed Walkthrough: `alembic upgrade head` ensures DB schema is up to date before app start. `uvicorn app.main:app` runs the server with 1 worker.

### File: backend/alembic.ini
Purpose: Alembic configuration.
Responsibilities: Tells Alembic where the migration scripts are and how to connect to the DB.

### File: backend/alembic/env.py
Purpose: Alembic environment setup.
Responsibilities: Loads models, configures the async SQLAlchemy engine, and runs migrations asynchronously.
Detailed Walkthrough: Uses `async_engine_from_config` to create an async engine. Runs `do_run_migrations` inside `connection.run_sync()`. This is necessary because Alembic is synchronously designed but the app uses `asyncpg`.

### File: backend/app/main.py
Purpose: FastAPI Application Setup.
Responsibilities: Initializes the FastAPI app, adds CORS middleware, mounts routers, and mounts the static frontend.
Detailed Walkthrough:
- `CORSMiddleware`: Allows credentials and specific origins based on settings.
- `app.include_router()`: Mounts `auth`, `attendance`, `admin`, and `reports` routers under `/api`.
- `@app.get("/health")`: Simple health check endpoint.
- `app.mount("/", StaticFiles...)`: Serves the frontend folder if a route isn't caught by `/api`.

### File: backend/app/api/auth.py
Purpose: Authentication Endpoints.
Responsibilities: Registration, Login, Logout, and Token Refresh.
Detailed Walkthrough:
- `register_user`: Validates password policy. Hashes password. Creates User, and associated Student/Teacher profiles. Generates JWT and Refresh token. Stores refresh token in DB. Sets HttpOnly cookies.
- `login`: Fetches user by email. Checks `locked_until`. Verifies password using `verify_password`. If failed, increments `failed_login_count` and triggers `SecurityEvent`. If success, resets counters, issues tokens, and sets cookies. Logs `AuthAudit`.
- `refresh_token`: Reads refresh token from cookie. Decodes it. Checks if it exists and is not revoked in the DB. Issues a new access and refresh token pair, revoking the old one (Refresh Token Rotation).
Security Notes: Implements account lockout (e.g. 5 fails = 15m lockout) mitigating brute force. Uses HttpOnly, Secure, SameSite=Lax cookies to prevent XSS exfiltration of tokens.

### File: backend/app/api/attendance.py
Purpose: Attendance Management Endpoints.
Responsibilities: Device registration, starting sessions (teachers), scanning attendance (students).
Detailed Walkthrough:
- `register_device`: Generates a random opaque token, hashes it, saves the hash to the DB, and gives the plaintext token to the student via a long-lived HttpOnly cookie.
- `create_session`: Creates a `ClassSession`. Generates a random TOTP secret (encrypted at rest). Returns the session ID and a QR payload (`knmiet://...`).
- `scan_attendance`: 
  1. Checks if `device_token` cookie exists.
  2. Verifies the device hash matches the DB.
  3. Checks if the student is enrolled in the course.
  4. Validates the provided TOTP token against the session's decrypted secret using `pyotp`.
  5. Records `AttendanceLog`. Catches `IntegrityError` to prevent duplicate scans.
Security Notes: The `device_token` acts as a "something you have" factor, binding attendance to the student's physical device. The TOTP prevents QR code sharing (it changes every 30s). The secret is encrypted in the DB.

### File: backend/app/api/admin.py
Purpose: Administrative Endpoints.
Responsibilities: Creating departments, courses, assigning teachers, enrolling students, and bulk importing students via CSV.
Detailed Walkthrough:
- `import_students`: Parses a CSV. For each row, checks if user exists. Hashes password (defaulting to RollNo@KNMIET). Creates User and Student records.
Security Notes: Protected by `require_roles(UserRole.hod, UserRole.admin)`. CSV import must carefully sanitize inputs.

### File: backend/app/api/reports.py
Purpose: Reporting Endpoints.
Responsibilities: Generates CSV exports of attendance data.
Detailed Walkthrough:
- `course_attendance_csv`: Calculates total sessions for a course. Uses an Outer Join to aggregate attendance counts for all enrolled students. Writes directly to a `StringIO` buffer using Python's `csv` module and returns it as a downloadable response.
Improvement Opportunities: For huge courses, `StreamingResponse` could be used instead of building the entire CSV in memory.

### File: backend/app/api/deps.py
Purpose: FastAPI Dependency Injection.
Responsibilities: Provides the current authenticated user and enforces RBAC.
Detailed Walkthrough:
- `get_current_user`: Looks for `access_token` in cookies, falling back to Authorization header. Decodes JWT. Fetches User from DB. Raises 401 if invalid.
- `require_roles`: A dependency factory that wraps `get_current_user` and asserts the user's role is in the allowed list, raising 403 otherwise.

### File: backend/app/core/config.py
Purpose: Configuration Management.
Responsibilities: Loads and validates environment variables using `pydantic_settings`.
Detailed Walkthrough: Defines the `Settings` class. Defaults are provided but variables like `DATABASE_URL` and `JWT_SECRET_KEY` should be overridden via `.env`.

### File: backend/app/core/security.py
Purpose: Cryptographic and Security Utilities.
Responsibilities: Password hashing, JWT creation, JWT decoding, and opaque token generation.
Detailed Walkthrough:
- `hash_password`, `verify_password`: Uses `passlib` with `bcrypt`. Wraps them in `asyncio.to_thread` to prevent CPU-bound hashing from blocking the async event loop.
- `create_access_token`, `create_refresh_token`: Uses `python-jose` to sign tokens using `HS256`.
- `decode_token`: Verifies the signature and the `exp` claim, and asserts the token `type` matches the expected type.
- `new_opaque_token`: Uses `secrets.token_urlsafe(48)` to generate cryptographically strong random strings (used for device tokens).

### File: backend/app/db/base.py
Purpose: SQLAlchemy Declarative Base.
Responsibilities: Defines `Base(DeclarativeBase)` which all ORM models inherit from.

### File: backend/app/db/session.py
Purpose: Database Session Management.
Responsibilities: Configures the async engine and provides the `get_db` dependency.
Detailed Walkthrough: Uses `create_async_engine` and `async_sessionmaker`. The `get_db` function yields a session and automatically closes it when the request completes.

### File: backend/app/models/users.py
Purpose: Core Identity Models.
Responsibilities: Defines `User`, `Department`, `Student`, and `Teacher` tables.
Detailed Walkthrough:
- `User`: Stores credentials, role enum (`student`, `teacher`, `hod`, `admin`), and lockout fields (`failed_login_count`, `locked_until`).
- `Student`: Links to User, stores `roll_no`, `semester`, etc.
- `Teacher`: Links to User, stores `employee_code`.

### File: backend/app/models/academics.py
Purpose: Academic Structure Models.
Responsibilities: Defines `Course`, `TeacherCourseMapping`, `StudentCourseEnrollment`, `Timetable`, and `Marks`.
Detailed Walkthrough: Establishes Many-to-Many relationships via mapping tables (e.g. students to courses). Includes UniqueConstraints to prevent double enrollment.

### File: backend/app/models/attendance.py
Purpose: Attendance Tracking Models.
Responsibilities: Defines `ClassSession`, `AttendanceLog`, and `DeviceRegistration`.
Detailed Walkthrough:
- `ClassSession`: Holds `totp_secret_encrypted` as a `LargeBinary`. Tracks start/end times.
- `AttendanceLog`: Maps a student to a session. Has a `UniqueConstraint("student_id", "session_id")` to prevent double scanning.
- `DeviceRegistration`: Stores `device_token_hash`. Has `UniqueConstraint("student_id")` enforcing one device per student.

### File: backend/app/models/audit.py
Purpose: Audit Logging Models.
Responsibilities: Defines tables intended to be populated (often via DB triggers or app logic) when sensitive records change. Includes `AuthAudit` and `SecurityEvent`.

### File: backend/app/models/auth.py
Purpose: Token Storage Models.
Responsibilities: Defines `RefreshToken` to track issued refresh tokens, enabling server-side revocation. Stores tokens as hashes to prevent leaks if DB is compromised.

### File: backend/app/schemas/auth.py
Purpose: Authentication Request/Response Schemas.
Responsibilities: Pydantic models for Login/Registration validation.
Detailed Walkthrough: Validates string lengths and ensures `email` is a valid EmailStr.

### File: backend/app/schemas/attendance.py
Purpose: Attendance Request/Response Schemas.
Responsibilities: Defines `CreateSessionRequest`, `ScanRequest`, etc. `ScanRequest` requires a 6-digit TOTP string.

## System Architecture

### High-Level Architecture
The system employs a classic 3-Tier containerized microservice approach:
1. **Presentation Layer**: Static HTML/JS Progressive Web App served by Nginx.
2. **Application Layer**: Python FastAPI REST application running on Uvicorn.
3. **Data Layer**: PostgreSQL 16 relational database.

### Component Relationships
- **Client (Browser/PWA)** <---> **Nginx (Reverse Proxy)**
- **Nginx** <---> **FastAPI Backend (Port 8000)**
- **FastAPI Backend** <---> **PostgreSQL (Port 5432)**

### Request Lifecycle
1. User interacts with UI (e.g. clicks "Mark Attendance").
2. `app.js` issues a `fetch` POST to `/api/attendance/scan` including cookies.
3. Nginx receives the request, evaluates the `limit_req_zone`. If within limits, proxies to backend.
4. FastAPI routes to `scan_attendance`.
5. Dependency `get_current_user` decodes the JWT cookie, validating the user.
6. The route logic retrieves the session and device data from Postgres via `asyncpg`.
7. Business logic (TOTP validation) executes.
8. Attendance log is committed to the database.
9. FastAPI returns a JSON response.
10. `app.js` updates the DOM based on the result.

### Authentication Flow
- **Login**: User submits Email/Password. Backend hashes input, compares with DB. On success, generates an Access Token JWT (short-lived, 15m) and a Refresh Token (long-lived, 7d). Both are returned as `HttpOnly`, `Secure`, `SameSite=Lax` cookies.
- **Subsequent Requests**: Browser automatically includes cookies. Backend validates the Access Token signature statelessly.
- **Refresh**: When Access Token expires, UI calls `/api/auth/refresh`. Backend validates Refresh Token against DB (checking revocation status), and issues a new pair.

### Database Flow
Uses Asynchronous SQLAlchemy 2.0. Queries are constructed using the new 2.0 style (`select(Model).where(...)`) and executed via `await db.execute(...)`. This prevents the event loop from blocking during IO waits. Connection pooling is managed by `asyncpg`.

### Frontend Flow
PWA is a Single Page App (SPA) fundamentally, though it doesn't use a router. All views are injected/hidden via CSS or DOM manipulation in `app.js`.
Service Worker caches static assets aggressively but explicitly passes `/api/*` requests to the network.

## Database Design Overview

### Table: users
- Fields: `id` (UUID), `email` (String, unique), `name` (String), `password_hash` (String), `role` (Enum), `is_active` (Bool), `failed_login_count` (Int), `locked_until` (DateTime), `created_at` (DateTime).
- Usage: The central authentication table.

### Table: departments
- Fields: `id` (UUID), `name` (String), `code` (String, unique).

### Table: students
- Fields: `id` (UUID), `user_id` (FK to users), `roll_no` (String, unique), `phone` (String), `department_id` (FK), `semester` (Int), `section` (String).
- Relationships: One-to-One with `users`.

### Table: teachers
- Fields: `id` (UUID), `user_id` (FK to users), `employee_code` (String, unique), `department_id` (FK).
- Relationships: One-to-One with `users`.

### Table: courses
- Fields: `id` (UUID), `course_code` (String, unique), `course_name` (String), `department_id` (FK), `semester` (Int), `total_lectures` (Int).

### Table: class_sessions
- Fields: `id` (UUID), `course_id` (FK), `teacher_id` (FK), `totp_secret_encrypted` (LargeBinary), `start_time` (DateTime), `end_time` (DateTime), `is_active` (Bool).
- Usage: Represents a single lecture occurrence. Stores the encrypted TOTP seed.

### Table: attendance_logs
- Fields: `id` (UUID), `student_id` (FK), `session_id` (FK), `attendance_status` (Enum), `scan_timestamp` (DateTime), `device_id` (FK).
- Constraints: `uix_student_session` (Unique constraint on student_id + session_id).

### Table: device_registrations
- Fields: `id` (UUID), `student_id` (FK, unique), `device_token_hash` (String), `registered_at`, `last_seen_at`.
- Constraints: One device per student. Stores a SHA-256 hash.

### Table: refresh_tokens
- Fields: `id`, `user_id`, `token_hash`, `expires_at`, `revoked`.

### Tables: audit (`auth_audit`, `security_events`, etc.)
- Fields: Capture historical events for compliance. Store `actor_id`, `event_type`, and `metadata_json`.

## API Reference

### Auth Endpoints
- **POST /api/auth/register**
  - Requires: None (Public).
  - Body: `RegisterUserRequest` (email, name, password, role, profile details).
  - Response: `LoginResponse` (Sets cookies).
  - Execution: Validates password complexity per role. Creates User + Profile.
- **POST /api/auth/login**
  - Requires: None (Public).
  - Body: `LoginRequest`.
  - Execution: Checks lockout, verifies bcrypt hash. Implements exponential lockout on failure. Generates JWTs.
- **POST /api/auth/refresh**
  - Requires: `refresh_token` Cookie.
  - Execution: Rotates the refresh token and issues a new access token.

### Attendance Endpoints
- **POST /api/attendance/devices/register**
  - Requires: `Student` role.
  - Execution: Generates opaque token, stores hash, sets `device_registration_token` cookie for 3 years. Fails if device already registered.
- **POST /api/attendance/sessions**
  - Requires: `Teacher` or `HOD` role.
  - Body: `CreateSessionRequest` (course_id).
  - Execution: Generates pyotp secret, encrypts it. Returns QR payload.
- **GET /api/attendance/sessions/{id}/qr**
  - Requires: `Teacher`.
  - Execution: Generates the current live 6-digit TOTP for the session.
- **POST /api/attendance/scan**
  - Requires: `Student` role, `device_registration_token` Cookie.
  - Body: `ScanRequest` (session_id, token).
  - Execution: Verifies device hash. Checks course enrollment. Validates TOTP within 30s window. Inserts AttendanceLog.
- **GET /api/attendance/me**
  - Requires: `Student` role.
  - Execution: Aggregates total sessions and attended sessions per course.

### Admin & Report Endpoints
- **POST /api/admin/students/import-csv**
  - Requires: `Admin/HOD`.
  - Execution: Reads CSV upload. Creates Users/Students in bulk.
- **GET /api/reports/attendance/course/{id}.csv**
  - Requires: `Teacher/Admin`.
  - Execution: Generates tabular CSV string in memory and returns `text/csv`.

## Configuration Analysis

### Environment Variables
Managed via `pydantic-settings` in `app/core/config.py`.
- `DATABASE_URL`: Connection string for asyncpg. Default points to localhost.
- `JWT_SECRET_KEY`: Used to sign JWTs. **Critical Security Boundary**. Default "change-me-in-production" MUST be overridden.
- `SECURE_COOKIES`: Boolean. Must be True in production to ensure cookies are only sent over HTTPS.
- `CORS_ORIGINS`: Allowed origins for API requests.

### Consequences of Incorrect Configuration
- Exposing `JWT_SECRET_KEY` allows attackers to forge Admin tokens.
- Setting `SECURE_COOKIES=False` in production allows tokens to be intercepted over HTTP.
- Connecting to a non-async driver in `DATABASE_URL` (like standard `psycopg2`) will crash `asyncpg`.

## Security Assessment

### Strengths
- **Session Handling**: Uses HttpOnly, SameSite=Lax cookies, completely removing JWTs from the reach of XSS via `document.cookie`.
- **Brute Force Protection**: Implements both Edge-level rate limiting via Nginx and Application-level lockout (5 fails = 15m lockout) in `auth.py`.
- **Token Rotation**: Refresh tokens are stored as hashes in the DB and revoked upon use.
- **Hardware Binding**: Attendance scanning requires a `device_token` stored as a 3-year cookie. The plaintext token is never stored on the server (only the SHA256 hash).
- **Physical Proximity Verification**: Time-based One Time Passwords (TOTP) ensure the student scanning the code is physically looking at the teacher's screen, as the code changes every 30 seconds.

### Attack Surfaces & Recommendations
1. **QR Code Snapping**: A student could take a photo of the QR code and send it to a WhatsApp group. The 30s TOTP window heavily mitigates this, but a dedicated student could still scan within that window.
2. **Device Token Stealing**: If a student's laptop is stolen, the `device_registration_token` cookie could be extracted. Recommendation: Add a way for students/admins to revoke device tokens.
3. **Admin CSV Injection**: Uploading a malicious CSV could lead to CSV Injection if the reports are opened in Excel. Recommendation: Sanitize CSV exports (e.g., prefixing fields starting with `=` or `@` with a single quote).

## Operational Characteristics

### Startup Sequence
1. Docker Compose provisions Postgres.
2. Nginx waits for backend healthcheck.
3. Backend container executes `start.sh`.
4. Alembic connects to Postgres and runs migrations (`upgrade head`).
5. Uvicorn starts the FastAPI ASGI application on port 8000.

### Scalability Characteristics
- The backend is entirely asynchronous (`asyncio`, `asyncpg`, `httpx`). It can handle thousands of concurrent requests efficiently on a single worker.
- Current config uses `--workers 1`. To scale horizontally across multiple CPU cores, Uvicorn workers can be increased. However, if state (like rate limits) is stored in memory, workers might need a Redis backend. Currently, Nginx handles rate limiting, so scaling workers is safe.

### Performance Bottlenecks
- Password hashing using `bcrypt` is CPU intensive. While offloaded to `asyncio.to_thread` to prevent event loop blocking, a huge spike in simultaneous logins will spike CPU usage.

## Dependency Audit

- **FastAPI / Uvicorn**: Core web framework. Highly performant. Necessary.
- **SQLAlchemy 2.0 & asyncpg**: Database ORM and driver. The 2.0 version natively supports async, which is critical for performance. Necessary.
- **Alembic**: Database migrations. Standard tool in the SQLAlchemy ecosystem. Necessary.
- **passlib[bcrypt] & python-jose**: Cryptography. Note: `python-jose` has seen lack of maintenance recently; migrating to `PyJWT` could be a future consideration.
- **pyotp**: Generates standard TOTP codes. Necessary for the core feature.

## Engineering Assessment

- **Maintainability Score: 9/10**. Code is highly modular. Clear separation of routing (`api/`), logic/security (`core/`), database structure (`db/`), and schemas (`schemas/`).
- **Scalability Score: 8/10**. Async PostgreSQL handles high connection concurrency beautifully. Horizontal scaling is trivialized by stateless JWTs.
- **Security Score: 9/10**. Adheres to strict OWASP recommendations (HttpOnly cookies, hashed refresh tokens, hashed device tokens, rate limiting, progressive lockouts).
- **Production Readiness Score: 8/10**. Needs actual environment variables injected via CI/CD, and HTTPS configuration at the Nginx edge.

## Final Summary
The KNMIET Connect Attendance application represents a well-architected, highly secure solution. It avoids the bloat of massive frontend frameworks while delivering a progressive, offline-capable experience. The backend utilizes the latest async Python paradigms to ensure high throughput, making it perfectly suited for the bursty traffic typical of attendance marking at the end of a university lecture.

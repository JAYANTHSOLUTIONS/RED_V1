# Real-Estate Consultant System — Backend

## 1. Project Purpose

Backend API for a single-operator real-estate brokerage and consultancy
business: property inventory, client/lead management, requirement
matching, site-visit scheduling, secure document handling, and deal/
commission tracking.

This repository currently contains **Phase 1 — Backend Architecture &
Project Foundation** only. Business modules (Auth, Properties, Clients,
Leads, Documents, Verification, Site Visits, Deals, Commissions,
Notifications) are implemented in later phases on top of this foundation.
See `docs/backend_specification.pdf` (the master specification) for full
product scope.

## 2. Technology Stack

| Layer          | Choice                                          |
|-----------------|--------------------------------------------------|
| Language        | Python 3.11+                                     |
| API framework   | FastAPI                                          |
| Validation      | Pydantic v2 / pydantic-settings                  |
| Database        | PostgreSQL 15+                                   |
| ORM             | SQLAlchemy 2.x (async, declarative)              |
| Migrations      | Alembic                                          |
| Auth (future)   | Argon2id, JWT (PyJWT), refresh-token rotation    |
| Testing         | pytest, pytest-asyncio, httpx                    |
| Containerization| Docker / Docker Compose                          |

## 3. Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Docker, see below)
- Docker & Docker Compose (recommended for local development)

## 4. Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env with real local values (never commit this file)
```

`.env` must define, at minimum: `DATABASE_URL` and `JWT_SECRET_KEY`. The
app fails fast at startup if either is missing — this is intentional.

## 5. PostgreSQL Setup (without Docker)

```bash
createdb realestate
# then set in .env:
# DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/realestate
```

## 6. Docker Setup (recommended)

```bash
docker compose up --build
```

This starts the API on `http://localhost:8000` and a PostgreSQL 16
container with a persisted volume. The API container waits for the
database's healthcheck before starting.

## 7. Migration Commands

Migrations are managed with Alembic. The database URL is read from
`app.core.config.get_settings()` (i.e. from `.env`) — never duplicated in
`alembic.ini`.

```bash
# Generate a new migration after adding/changing SQLAlchemy models
alembic revision --autogenerate -m "add properties table"

# Apply all pending migrations
alembic upgrade head

# Roll back the most recent migration
alembic downgrade -1
```

No business tables exist yet in this phase — `migrations/versions/` is
intentionally empty until Phase 2 adds the first models.

## 8. Development Server Command

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs (non-production only): `http://localhost:8000/docs`

## 9. Testing Command

```bash
pytest
# with coverage:
pytest --cov=app --cov-report=term-missing
```

Tests are organized as:

- `tests/unit/` — pure logic: config validation, exception hierarchy,
  security primitives. No network or DB required.
- `tests/integration/` — full ASGI request/response cycles (health
  endpoints, middleware, CORS). The database dependency is faked via
  FastAPI `dependency_overrides`, so no live PostgreSQL is required to run
  this suite.
- `tests/failure/` — fault-tolerance and error-sanitization checks: every
  exception path must return the standard error envelope and must never
  leak stack traces, driver errors, or internal details.

## 10. Health Endpoints

| Endpoint                  | Purpose                                                        |
|-----------------------------|-----------------------------------------------------------------|
| `GET /api/v1/health/live`  | Process heartbeat. Always 200 if the ASGI server is running.   |
| `GET /api/v1/health/ready` | Verifies dependencies (currently: database). 200 if all pass, 503 otherwise. Never exposes connection strings or credentials. |

## 11. Project Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py            # shared FastAPI dependencies
│   │   └── v1/
│   │       ├── health.py      # /health/live, /health/ready
│   │       └── router.py      # aggregates all v1 routers
│   ├── core/
│   │   ├── config.py          # Settings (env-var driven)
│   │   ├── exceptions.py      # AppException hierarchy
│   │   ├── logging.py         # structured logging + request-id context
│   │   └── security.py        # Argon2id + JWT primitives (not yet wired)
│   ├── db/
│   │   ├── base.py            # SQLAlchemy declarative Base
│   │   └── session.py         # async engine, get_db, transaction()
│   ├── models/                # SQLAlchemy models (empty — Phase 2+)
│   ├── schemas/
│   │   └── common.py          # success/error response envelopes
│   ├── repositories/          # data-access layer (empty — Phase 2+)
│   ├── services/              # business logic layer (empty — Phase 2+)
│   ├── middleware/
│   │   ├── request_id.py
│   │   ├── logging.py
│   │   └── security_headers.py
│   └── main.py                # application factory
├── migrations/                 # Alembic (env.py reads DATABASE_URL from Settings)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── failure/
├── scripts/                     # reserved for future operational scripts
├── .env.example
├── .gitignore
├── requirements.txt
├── alembic.ini
├── pyproject.toml              # pytest configuration
├── Dockerfile
└── docker-compose.yml
```

## 12. Development Conventions

- **Layering is strict**: `Router → Schema → Service → Repository →
  SQLAlchemy`. Routers contain no business logic. Repositories contain no
  HTTP concerns. This phase only builds the shared infrastructure; Phase 2
  introduces the first `services/` and `repositories/` modules.
- **No hard-coded single-user assumptions.** Even though V1 has one
  operator, nothing in this foundation assumes a fixed `user_id` or a
  single administrator — RBAC and multi-user support are designed to slot
  in during the Auth phase without rework.
- **Never use bare `except Exception: pass`.** Catch specific exceptions;
  let genuinely unexpected ones propagate to the centralized handler in
  `app.main`, which logs them and returns a sanitized `INTERNAL_ERROR`.
- **All responses use the standard envelope** (`{"success": ..., "data"
  | "error": ...}`). Never serialize SQLAlchemy models directly.
- **All monetary values must use `Decimal`/`NUMERIC`, never floats** —
  enforced starting in the Deals module (Phase 2+ concern; noted here for
  visibility).
- **Never commit `.env`, credentials, or tokens.** `.env.example`
  documents every variable with safe placeholder values only.
- **Every schema change goes through an Alembic migration.** No manual
  production database edits.

## Known Limitations (Phase 1)

- No business tables/models exist yet — only the SQLAlchemy/Alembic
  infrastructure they will build on.
- Authentication is not wired to any route; `app/core/security.py`
  provides the primitives only.
- The readiness check currently verifies PostgreSQL only. Object-storage
  connectivity will be added to `READINESS_CHECKS` in `app/api/v1/health.py`
  once the Documents module (Phase 2+) introduces real storage config.

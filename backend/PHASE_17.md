# PHASE 17 — PRODUCTION HARDENING TECHNICAL SPECIFICATION

## 1. Phase Objective & Architectural Scope

Phase 17 hardens the **RED_V1** real-estate consultant backend for production readiness, operational resilience, and secure deployment across Tamil Nadu real-estate operations.

### Architectural Constraints Maintained
* **Strict Monolith Preservation**: Zero external distributed dependencies introduced (no Redis, Kafka, Celery, RabbitMQ, or Kubernetes).
* **Fail-Fast Secret & Environment Validation**: Rejection of weak/insecure keys, debug mode, and wildcards at startup.
* **OpenAPI Documentation Protection**: Swagger UI (`/docs`), ReDoc (`/redoc`), and schema (`/openapi.json`) disabled by default in production.
* **Correlation ID Sanitization**: Strict input validation on `X-Request-ID` to prevent log injection and header buffer attacks.
* **Log Volume & Sensitivity Controls**: Routine health-check noise suppression and automatic masking of secrets, bearer tokens, and credentials.
* **Bounded Rate Limiter Memory**: Automatic pruning of stale client IPs and ceiling bounds to eliminate memory exhaustion under scanning.
* **Zero Warnings & High Test Coverage**: Resolved pytest-asyncio fixture warnings and maintained >= 93% test coverage.

---

## 2. Hardened Architecture & Components

```text
┌───────────────────────────────────────────────────────────────────────┐
│                           Client / Gateway                            │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │ X-Request-ID (Sanitized: ^[a-zA-Z0-9_\-\.:]{1,64}$)
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                            │
│                                                                       │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────┐  │
│  │ Security Headers     │  │ Request Logging      │  │ RequestId   │  │
│  │ (HSTS, CSP, nosniff) │  │ (Health suppressed)  │  │ Middleware  │  │
│  └──────────────────────┘  └──────────────────────┘  └─────────────┘  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Settings Validation (@model_validator)                          │  │
│  │ • JWT_SECRET_KEY >= 32 chars & not in weak list                 │  │
│  │ • DEBUG == False                                                │  │
│  │ • CORS_ALLOWED_ORIGINS != '*'                                   │  │
│  │ • S3 credentials required if STORAGE_BACKEND=s3                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────┐              ┌─────────────────────────┐  │
│  │ OpenAPI Docs Control   │              │ SlidingWindowRateLimiter│  │
│  │ • /docs (404 in prod)  │              │ • max_tracked_clients   │  │
│  │ • /redoc (404 in prod) │              │ • stale client pruning  │  │
│  │ • /openapi.json (404)  │              │ • zero external deps    │  │
│  └────────────────────────┘              └─────────────────────────┘  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Lifespan & Engine Management                                    │  │
│  │ • Startup banner (environment, docs status, DB pool)            │  │
│  │ • Bounded shutdown: asyncio.wait_for(dispose_engine(), 5.0s)    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details & Implementation Summary

### 3.1 Fail-Fast Production Configuration ([`app/core/config.py`](app/core/config.py))
- Validates that when `APP_ENV="production"`:
  - `JWT_SECRET_KEY` is not empty, not from a known insecure list (`test-only-...`, `secret`, `changeme`, etc.), and at least 32 characters long.
  - `DEBUG` is strictly `False`.
  - `CORS_ALLOWED_ORIGINS` contains explicit domains and does not allow wildcard `*`.
  - If `STORAGE_BACKEND == "s3"`, bucket name, access key, and secret key must be set.
  - If `SMTP_HOST` is configured, valid port and sender email must be set.
- Allows flexibility in local/test environments so automated test suites continue running without friction.

### 3.2 Documentation Access Control ([`app/main.py`](app/main.py))
- Introduced `OPENAPI_DOCS_ENABLED: Optional[bool] = None`.
- In production, `/docs`, `/redoc`, and `/openapi.json` are disabled (404 NOT_FOUND) unless `OPENAPI_DOCS_ENABLED=True` is explicitly specified.
- Enabled by default in local/staging environments for developer convenience.

### 3.3 Correlation ID Sanitization ([`app/middleware/request_id.py`](app/middleware/request_id.py))
- Validates `X-Request-ID` against regex pattern `^[a-zA-Z0-9_\-\.:]{1,64}$`.
- Missing, empty, oversized (> 64 characters), or malformed tokens (containing `<script>`, spaces, SQL quotes, or newlines) are automatically replaced with a clean `uuid.uuid4()`.
- The correlation ID is propagated to `request.state.request_id`, response header `X-Request-ID`, and all structured log records.

### 3.4 Operational Logging & Spam Suppression ([`app/middleware/logging.py`](app/middleware/logging.py), [`app/core/logging.py`](app/core/logging.py))
- **Spam Suppression**: Requests to `/health`, `/ready`, `/api/v1/health/live`, `/api/v1/health/ready` that return status < 400 are logged at `DEBUG` level rather than `INFO`. Failures (>= 400) continue logging at `WARNING`/`ERROR`.
- **Sensitive Data Masking**: `SensitiveDataFilter` masks `Bearer <token>`, `password`, and JWT patterns from application log records to prevent accidental token leakage.

### 3.5 Bounded Sliding-Window Rate Limiting ([`app/core/rate_limiter.py`](app/core/rate_limiter.py))
- Added `MAX_TRACKED_CLIENTS = 50_000` ceiling and automatic stale client pruning (`_prune_stale_locked`).
- Added public `prune_stale(window_seconds)` method.
- Completely contained within the process memory space without Redis or distributed caches.

### 3.6 Clean Asyncio Pytest Scope Configuration ([`pyproject.toml`](pyproject.toml))
- Configured `asyncio_default_fixture_loop_scope = "function"` to clear the `pytest-asyncio` deprecation warning.

---

## 4. Test Suite Execution & Coverage

- Total Tests: **486 passing tests** (470 Phase 1–16 + 16 new Phase 17 tests).
- Failures: **0**
- Errors: **0**
- Warnings: **0**
- Overall Application Coverage: **>= 93%**

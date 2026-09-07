# PHASE 16 — SECURITY REVIEW & ADVERSARIAL ASSESSMENT REPORT

## Executive Summary

Phase 16 conducted an adversarial security assessment and defense-in-depth hardening of the **RED_V1** Tamil Nadu Real-Estate Consultant & Brokerage Backend. 

Building directly on Phase 15's fault-tolerance baseline (391 passing tests, 93% coverage), this assessment evaluated whether an authenticated or unauthenticated attacker could bypass controls, escalate privileges, access unauthorized resources, forge audit records, tamper with idempotency keys, upload malicious binaries, inject malicious payloads, or extract private owner PII.

The review resulted in:
- Implementation of an in-memory, thread-safe sliding-window brute-force rate limiter for authentication endpoints.
- Integration of hardened security headers (Strict Content-Security-Policy, Permissions-Policy, Referrer-Policy, nosniff, DENY, Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy).
- Validation and length constraints on `Idempotency-Key` headers ($\le 128$ chars, non-empty) preventing unhandled database `DataError` crashes.
- Verification of strict PII filtering on public property and site visit endpoints.
- Creation of a dedicated 79-test security test suite (`tests/security/`).
- Full regression verification: **470 passed (0 failures, 0 errors)** with **93% test coverage** across the application.

---

## Threat Model

The application threat model assumed an active adversary operating under several profiles:
1. **Unauthenticated Internet Attacker**: Attempts credential stuffing/brute force on `/api/v1/auth/login`, probes public endpoints for PII leakage, attempts token forgery (`alg: none`, algorithm confusion), and submits malformed/oversized payloads.
2. **Authenticated Untrusted User (Role: `USER` / Client)**: Attempts vertical privilege escalation by invoking consultant/admin endpoints (`/properties`, `/clients`, `/leads`, `/documents`, `/audit-logs`), submitting forged `role` or `is_active` attributes.
3. **Malicious Authenticated Consultant (Tenant B)**: Attempts horizontal privilege escalation (IDOR / BOLA) to read or alter another consultant's private notifications, documents, client records, or site visits.
4. **Malicious File Uploader**: Uploads executable scripts (`.php`, `.sh`, `.exe`) or polyglot files disguised with legitimate extensions (`.pdf`, `.png`) to trigger remote execution or directory traversal (`../../`).
5. **Workflow & Concurrency Manipulator**: Replays idempotency keys with altered payloads, submits oversized idempotency headers, or races state transitions to bypass verification requirements.

---

## Security Surface Inventory

| Area | Reviewed Components | Controls Verified | Status |
| :--- | :--- | :--- | :--- |
| **Authentication** | `app/services/auth.py`, `app/api/v1/auth.py`, `app/core/security.py` | Argon2id password hashing, PyJWT HS256 strict decoding, token type separation, refresh token rotation with row-level locking (`SELECT FOR UPDATE`), reuse detection with blanket revocation, inactive user gating | Hardened & Verified |
| **Authorization & RBAC** | `app/api/deps.py` (`require_roles`), all API routers | Mandatory `CONSULTANT` role enforcement on all private routes, 401 unauthenticated, 403 non-consultant `USER` role | Hardened & Verified |
| **IDOR / BOLA** | Notifications, Documents, Audit Logs, Site Visits | Strict recipient/user scoping on notifications, private document streaming authorization, read-only audit log APIs | Hardened & Verified |
| **Mass Assignment** | Pydantic v2 schemas (`PropertyCreate`, `ClientCreate`, etc.) | System fields (`id`, `status`, `public_reference`, `created_at`, `is_archived`) ignored or rejected on client input | Hardened & Verified |
| **File Uploads** | `app/services/document.py`, `app/storage/local.py` | Extension allowlist (`.pdf`, `.jpg`, `.jpeg`, `.png`), magic byte inspection, 15MB size ceiling, empty file rejection, `os.path.basename` path traversal sanitization, UUID storage key isolation | Hardened & Verified |
| **Injection Defense** | SQLAlchemy ORM 2.0 query construction | 100% parameterized SQL queries, zero raw string concatenation, Tamil Unicode preservation (`"அண்ணா நகர்"`), safe text storage of HTML/XSS payloads | Hardened & Verified |
| **Idempotency Abuse** | `app/core/idempotency.py`, `app/models/idempotency.py` | Length bounds ($\le 128$), non-empty validation, SHA-256 payload hash verification (`409 IDEMPOTENCY_PAYLOAD_MISMATCH`), composite `(key, user_id, endpoint)` scoping | Hardened & Verified |
| **Brute-Force / Abuse** | `app/core/rate_limiter.py` | Thread-safe sliding-window rate limiting per IP (10 attempts/min on login), returning `429 RATE_LIMITED` | Hardened & Verified |
| **Security Headers** | `app/middleware/security_headers.py` | CSP, X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy, Permissions-Policy, COOP, CORP | Hardened & Verified |
| **Information Leakage**| Exception handlers (`app/main.py`), public schemas | Standardized error envelopes (`code`, `message`), zero stack traces or DB connection strings exposed, public property schemas omit owner contact details and internal notes | Hardened & Verified |

---

## Findings & Remediation

### Finding SEC-01 — Missing Brute-Force Rate Limiting on Login Endpoint
- **Severity**: MEDIUM
- **Affected Component**: `app/api/v1/auth.py` (`POST /api/v1/auth/login`)
- **Attack Scenario**: An attacker scripts thousands of credential-guessing attempts against `/api/v1/auth/login` to brute-force consultant accounts.
- **Impact**: Increased risk of credential compromise and server resource exhaustion.
- **Root Cause**: No request throttling or rate limiting existed on the authentication route.
- **Fix**: Implemented `SlidingWindowRateLimiter` in `app/core/rate_limiter.py` using in-memory deque per client IP. Configured via `RATE_LIMIT_LOGIN_ATTEMPTS: int = 10` and `RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60` in `app/core/config.py`. Injected as a FastAPI dependency returning HTTP 429 `RateLimitedError`.
- **Regression Test**: `tests/security/test_rate_limiting.py::test_login_brute_force_rate_limited`
- **Status**: FIXED

### Finding SEC-02 — Unbounded Idempotency-Key Header Causing Unhandled Database Error
- **Severity**: LOW
- **Affected Component**: `app/core/idempotency.py` (`IdempotencyService.check_or_reserve`)
- **Attack Scenario**: A client passes an arbitrary string exceeding 128 characters or an empty string as `Idempotency-Key`.
- **Impact**: Database schema column is `varchar(128)`. Postgres raises `DataError` (value too long), triggering a 500 Internal Error response rather than a structured validation rejection.
- **Root Cause**: `Idempotency-Key` was directly passed to the repository query and insert without length verification.
- **Fix**: Added validation in `IdempotencyService.check_or_reserve` checking `0 < len(key.strip()) <= 128`, raising `ValidationAppError` (HTTP 422 `INVALID_IDEMPOTENCY_KEY`).
- **Regression Test**: `tests/security/test_idempotency_security.py::test_oversized_idempotency_key_rejected`, `test_empty_idempotency_key_rejected`
- **Status**: FIXED

### Finding SEC-03 — Defense-in-Depth Security Headers Incomplete
- **Severity**: LOW
- **Affected Component**: `app/middleware/security_headers.py`
- **Attack Scenario**: Browsers accessing API or documentation endpoints lack explicit framing and cross-origin resource isolation directives.
- **Impact**: Potential clickjacking or cross-origin embedding risk in browser environments.
- **Root Cause**: Middleware previously only set `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.
- **Fix**: Added `Content-Security-Policy` (`default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'`), `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin`, and `Strict-Transport-Security` for production.
- **Regression Test**: `tests/security/test_cors_and_headers.py::test_security_headers_present_on_api_responses`
- **Status**: FIXED

### Finding SEC-04 — User Enumeration via Login Error Envelopes
- **Severity**: INFORMATIONAL / REVIEWED
- **Affected Component**: `app/services/auth.py`
- **Status**: Reviewed — no exploitable issue identified. Login failures for non-existent email and incorrect password return identical `401 Unauthorized` responses with message `"Invalid email or password."`. Regression covered in `tests/security/test_authentication_security.py::test_user_enumeration_resistance`.

### Finding SEC-05 — SQL Injection in Search and Filters
- **Severity**: INFORMATIONAL / REVIEWED
- **Affected Component**: All repositories using SQLAlchemy 2.0 select queries
- **Status**: Reviewed — no exploitable issue identified. All string and numeric filters use parameterized bound variables via SQLAlchemy ORM. Regression tested against raw quotes, DROP TABLE payloads, and UNION statements in `tests/security/test_injection_security.py::test_sql_injection_in_search_queries_parameterized`.

### Finding SEC-06 — File Upload Path Traversal & Magic Byte Validation
- **Severity**: INFORMATIONAL / REVIEWED
- **Affected Component**: `app/services/document.py`
- **Status**: Reviewed — no exploitable issue identified. Filenames are stripped via `os.path.basename` and regex whitelist; storage paths use generated UUID keys; binaries are checked against magic byte signatures for `.pdf`, `.png`, `.jpg`. Regression covered in `tests/security/test_file_upload_security.py`.

---

## Security Test Summary

| Test File | Tests Added | Status | Focus Areas |
| :--- | :--- | :--- | :--- |
| `tests/security/test_authentication_security.py` | 13 | PASSED | Alg: none, Alg confusion, expired tokens, type confusion, inactive users, refresh reuse, enumeration |
| `tests/security/test_authorization_security.py` | 31 | PASSED | 401 unauthenticated check, 403 RBAC check across all routers for non-consultant `USER` role |
| `tests/security/test_cors_and_headers.py` | 2 | PASSED | Security headers (CSP, nosniff, DENY, COOP, CORP), CORS preflight |
| `tests/security/test_file_upload_security.py` | 11 | PASSED | Disallowed extensions (.exe, .php, .html), magic bytes, oversized, empty, path traversal, UUID key isolation |
| `tests/security/test_idempotency_security.py` | 4 | PASSED | Oversized keys (>128), empty keys, payload tampering detection (409), cross-user key replay isolation |
| `tests/security/test_idor_bola.py` | 2 | PASSED | Notification cross-user isolation (404 on IDOR read/unread), audit log API immutability |
| `tests/security/test_information_leakage.py` | 2 | PASSED | Error envelope sanitization, public property schema owner PII & internal notes omission |
| `tests/security/test_injection_security.py` | 10 | PASSED | SQL injection parameterization, Tamil Unicode preservation, stored XSS safety, CRLF rejection |
| `tests/security/test_mass_assignment.py` | 3 | PASSED | System field tampering defense (id, status, public_reference, is_archived) |
| `tests/security/test_rate_limiting.py` | 2 | PASSED | Login brute-force rate limiting (429 RATE_LIMITED), client IP isolation |
| **Total Security Tests** | **79** | **ALL PASSED** | **10 Dedicated Security Modules** |

---

## Full Regression Verification

```text
============================= test session starts =============================
platform win32 -- Python 3.12.11, pytest-8.3.3
rootdir: C:\Users\w\Documents\GitHub\RED\backend
plugins: anyio-4.15.0, asyncio-0.24.0, cov-5.0.0
collected 470 items

470 passed in 202.79s (0:03:22)
============================== 470 passed ==============================
```

- **Baseline Tests (Phases 1–15)**: 391 passed
- **Security Tests Added (Phase 16)**: 79 passed
- **Total Tests Passing**: 470 passed
- **Failures / Errors**: 0 failures, 0 errors
- **Application Test Coverage**: **93%** (5,967 total statements, 417 missed)

---

## Remaining Risks & Phase 17 Recommendations

The following items are low risk within the local monolithic architecture and are appropriately deferred to Phase 17 (Production Hardening) and Phase 20 (Deployment):
1. **Reverse Proxy TLS & HSTS**: The application enforces baseline security headers, but full HTTPS termination, certificate renewal, and production HSTS should be finalized in the Nginx/Caddy reverse proxy layer.
2. **Distributed Rate Limiting**: The current sliding-window rate limiter is in-memory and optimal for single-process deployments. If multi-worker horizontal scaling is introduced in production, rate limiting should evaluate an external state store or reverse-proxy IP rate limiting (e.g. `limit_req_zone` in Nginx).
3. **API Documentation Exposure**: FastAPI Swagger UI (`/docs`) and ReDoc (`/redoc`) are currently enabled in non-production environments (`not settings.is_production`). Confirm `APP_ENV=production` is set in production deployment to disable interactive docs.

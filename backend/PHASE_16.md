# PHASE 16 — SECURITY REVIEW & HARDENING TECHNICAL SPECIFICATION

## 1. Phase Objective & Architecture Principles

Phase 16 executes a comprehensive adversarial security review, threat modeling, and defense-in-depth hardening of the **RED_V1** Tamil Nadu Real-Estate Consultant & Brokerage Backend.

### Architectural Constraints
* **Strict Monolith Preservation**: Zero external distributed dependencies introduced (no Redis, Kafka, Celery, RabbitMQ, or microservices).
* **Defensive Depth**: Every trust boundary validates inputs, rejects unauthorized actions server-side, and guarantees that client-controlled fields cannot escalate privileges or leak tenant data.
* **Preserving Legitimate Functionality**: Hardening preserves all legitimate Tamil Nadu real-estate data (Tamil script, Tamil measurements, local addresses) and developer tooling.
* **Non-Leaking Error Envelopes**: All client errors return sanitized, standardized JSON error envelopes without exposing stack traces, filesystem roots, or database connection strings.

---

## 2. Threat Model & Security Controls

```text
                               ┌─────────────────────────┐
                               │   Adversarial Threat    │
                               └────────────┬────────────┘
                                            │
        ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
        │                   │                               │                   │
        ▼                   ▼                               ▼                   ▼
┌───────────────┐   ┌───────────────┐               ┌───────────────┐   ┌───────────────┐
│ Authentication│   │ Authorization │               │ File Storage  │   │  Idempotency  │
│  & Token Flow │   │    & RBAC     │               │   & Uploads   │   │  & Workflows  │
└───────┬───────┘   └───────┬───────┘               └───────┬───────┘   └───────┬───────┘
        │                   │                               │                   │
  Sliding-Window      Server-Side                   Extension Whitelist         Length Bound
   Rate Limiting     require_roles                     + Magic Bytes           Hash Integrity
    (429 Error)       (403 Error)                    + UUID Key Isol.          User Isolation
```

---

## 3. Hardened Components & Implementations

### 3.1 In-Memory Sliding-Window Rate Limiter ([`app/core/rate_limiter.py`](app/core/rate_limiter.py))
- Zero-dependency, thread-safe rate limiter implemented via `asyncio.Lock` and in-memory timestamp deques per client IP.
- Enforced on `POST /api/v1/auth/login` (configurable via `RATE_LIMIT_LOGIN_ATTEMPTS = 10` and `RATE_LIMIT_LOGIN_WINDOW_SECONDS = 60`).
- Raises `RateLimitedError` (HTTP 429) upon threshold breach.

### 3.2 Enhanced Security Headers ([`app/middleware/security_headers.py`](app/middleware/security_headers.py))
- Injected on all API responses:
  - `Content-Security-Policy`: `"default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; ..."`
  - `X-Content-Type-Options`: `"nosniff"`
  - `X-Frame-Options`: `"DENY"`
  - `Referrer-Policy`: `"strict-origin-when-cross-origin"`
  - `Permissions-Policy`: `"geolocation=(), microphone=(), camera=()"`
  - `Cross-Origin-Opener-Policy`: `"same-origin"`
  - `Cross-Origin-Resource-Policy`: `"same-origin"`
  - `Strict-Transport-Security`: `"max-age=31536000; includeSubDomains"` (in production)

### 3.3 Idempotency Key Validation ([`app/core/idempotency.py`](app/core/idempotency.py))
- Enforces strict input validation on `Idempotency-Key` headers:
  - Rejects empty or whitespace-only keys with `ValidationAppError` (HTTP 422).
  - Rejects keys exceeding 128 characters with `ValidationAppError` (HTTP 422), avoiding unhandled PostgreSQL `varchar(128)` `DataError` exceptions.

---

## 4. Security Test Suite (`tests/security/`)

The dedicated Phase 16 security test suite contains 79 adversarial test cases:

1. **`test_authentication_security.py`** (13 tests): Missing token, malformed token, tampered signature, `alg: none`, algorithm confusion, expired token, token type confusion, inactive user rejection, refresh token reuse detection, user enumeration resistance.
2. **`test_authorization_security.py`** (31 tests): 401 unauthenticated access rejection, 403 Forbidden enforcement across all routers for non-consultant `USER` role.
3. **`test_idor_bola.py`** (2 tests): Notification IDOR isolation (404 on cross-user read/unread), audit log API immutability.
4. **`test_mass_assignment.py`** (3 tests): Rejection/neutralization of client-controlled `role`, `id`, `status`, `public_reference`, and `is_archived`.
5. **`test_file_upload_security.py`** (11 tests): Extension whitelist, magic byte verification, oversized file rejection, empty file rejection, path traversal sanitization, UUID storage key isolation.
6. **`test_injection_security.py`** (10 tests): SQL injection parameterization, Tamil Unicode preservation (`"அண்ணா நகர்"`), stored XSS safety, CRLF injection defense.
7. **`test_cors_and_headers.py`** (2 tests): Baseline security headers verification, CORS preflight and origin isolation.
8. **`test_rate_limiting.py`** (2 tests): Login brute-force rate limit enforcement (429), client IP bucket isolation.
9. **`test_information_leakage.py`** (2 tests): Error envelope sanitization without stack traces, public property PII redaction.
10. **`test_idempotency_security.py`** (4 tests): Oversized key rejection, empty key rejection, payload tampering conflict, cross-user key isolation.

---

## 5. Verification Results

```text
Total Tests: 470 passed (391 baseline + 79 security)
Failures: 0
Errors: 0
Coverage: 93% application coverage
```

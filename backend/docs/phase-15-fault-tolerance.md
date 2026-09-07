# Phase 15 — Fault Tolerance & Reliability Specification

## 1. Scope

Phase 15 defines and implements fault-tolerance, bounded timeouts, transient error recovery, transaction atomicity, idempotency, concurrency conflict guards, and graceful degradation for the monolithic `RED_V1` real-estate backend.

---

## 2. Dependency Inventory & Architecture

```text
                               ┌─────────────────────────┐
                               │   FastAPI Application   │
                               └────────────┬────────────┘
                                            │
        ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
        │                   │                               │                   │
        ▼                   ▼                               ▼                   ▼
┌───────────────┐   ┌───────────────┐               ┌───────────────┐   ┌───────────────┐
│  PostgreSQL   │   │  File Storage │               │  SMTP / Email │   │   External    │
│  (SQLAlchemy  │   │  (Local/S3)   │               │   Provider    │   │  Authorities  │
│   AsyncEngine)│   │               │               │               │   │ (Rev/TNRERA)  │
└───────┬───────┘   └───────┬───────┘               └───────┬───────┘   └───────┬───────┘
        │                   │                               │                   │
  Transactions         Compensation                      Bounded              Bounded
  Pool Bounds            Cleanup                         Timeouts             Retries
```

---

## 3. Failure Matrix

| Dependency / Scenario | Failure Mode | Impact | Handling Strategy | HTTP Code | Severity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | Connection refused at boot / request | DB queries fail | Controlled `ServiceUnavailableError`, connection reset, no stack trace | `503` | Critical |
| **PostgreSQL** | Connection dropped mid-request | In-flight transaction fails | Session rollback, pool disconnect eviction, transaction aborted | `503` | Critical |
| **PostgreSQL** | Connection pool exhausted | No available connection in pool | Bounded timeout (`DB_POOL_TIMEOUT = 10s`), raises 503 rather than indefinite hang | `503` | Critical |
| **PostgreSQL** | Transaction query error | Constraint violation or bad SQL | Automatic transaction rollback, session cleanup, sanitized error envelope | `409` / `422` / `500` | High |
| **PostgreSQL** | `session.commit()` fails | Commit aborted by DB engine | Full rollback, session cleanup, no phantom writes | `500` / `503` | Critical |
| **File Storage** | Storage write failure | File cannot be written to disk/S3 | Abort DB transaction, raise `StorageError`, zero orphan metadata | `503` / `500` | Critical |
| **File Storage** | DB fails after storage write | File written, but DB metadata fails | **Compensation Cleanup**: delete newly written file, rollback DB, zero orphan files | `500` | High |
| **File Storage** | Storage read failure | File missing from disk / corrupted | Returns clean 404 / 503, no internal filesystem paths exposed | `404` / `503` | Medium |
| **SMTP / Email** | Connection refused | Email cannot be dispatched | Non-crashing delivery failure (`DeliveryStatus.FAILED`), business mutation succeeds | `200` (Degraded) | Non-Critical |
| **SMTP / Email** | SMTP server hang / timeout | Socket read blocks | Bounded timeout (`SMTP_TIMEOUT_SECONDS = 10s`), thread isolation, non-crashing | `200` (Degraded) | Non-Critical |
| **SMTP / Email** | Temporary failure | Network glitch | Single attempt policy: no blind automatic retry to prevent duplicate sends | `200` (Degraded) | Non-Critical |
| **External API** | 5xx Server Error | Authority service down | Bounded exponential retry (max 3), then fallback / degraded offline response | `200` / `503` | Dependency |
| **External API** | Timeout / Connection reset | Network drop | Bounded request timeout (`EXTERNAL_REQUEST_TIMEOUT = 10s`), retryable | `504` / `503` | Dependency |
| **External API** | 4xx Client Error | Invalid input / unauthorized | Non-retryable, immediately surface client error or offline status | `400` / `422` | Client Error |
| **Concurrency** | Double booking site visit | Two requests book same slot | Advisory lock + `SELECT ... FOR UPDATE`, second request rejected with conflict | `409` | High |
| **Concurrency** | Concurrent state mutation | Two requests update status | Row-level locking (`SELECT ... FOR UPDATE`), idempotent return if state matches | `200` / `409` | High |
| **Network Retry** | Client retries duplicate POST | Client disconnected before ACK | `Idempotency-Key` header: replay cached result without duplicate side-effects | `200` / `201` | High |
| **Readiness Probe**| DB unreachable | Kubernetes / Load Balancer probe | `/ready` probe returns 503 `{"status": "unavailable"}` | `503` | Critical |

---

## 4. Failure Classifications (Retryable vs. Non-Retryable)

### Retryable Failures:
- Transient I/O network timeouts (`TimeoutError`, `asyncio.TimeoutError`).
- Connection resets / transient drops (`ConnectionResetError`, `ConnectionRefusedError` during external calls).
- Temporary upstream server errors (`HTTP 502 Bad Gateway`, `HTTP 503 Service Unavailable`, `HTTP 504 Gateway Timeout`).
- Rate limiting when `Retry-After` header is supplied.

### Non-Retryable Failures:
- Validation errors (`422 Unprocessable Entity`).
- Authentication and authorization rejections (`401 Unauthorized`, `403 Forbidden`).
- Resource conflicts and domain invariants (`409 Conflict`, unique constraint violations).
- Non-idempotent operations where delivery status is ambiguous (e.g. SMTP email sending).

---

## 5. Timeout Policy

All network-bound and external operations have strict bounded timeouts:
- **Database Pool Acquisition**: `DB_POOL_TIMEOUT = 10` seconds (default 30s lowered to fail fast under exhaustion).
- **Database Connection Recycle**: `DB_POOL_RECYCLE = 1800` seconds (30 minutes to recycle idle/stale connections).
- **SMTP Network Operations**: `SMTP_TIMEOUT_SECONDS = 10` seconds.
- **External Provider Requests**: `EXTERNAL_REQUEST_TIMEOUT = 10` seconds.
- **Readiness Probe Database Query**: `READINESS_TIMEOUT = 2.0` seconds.

---

## 6. Transaction & Commit Policy

- All multi-record mutations (Entity + Audit + Notification) execute inside `app.db.session.transaction(session)`.
- If any statement raises an error before or during `session.commit()`, the session rolls back immediately (`await session.rollback()`).
- No partial writes: zero orphan records, zero phantom success audit entries.

---

## 7. Storage Consistency & Compensation Cleanup

When uploading documents:
1. File binary is stored via storage backend.
2. Metadata record and audit event are inserted in a database transaction.
3. If step 2 fails (DB error, constraint violation, connection drop):
   - The catch block executes **Compensation Cleanup**: `await self.storage.delete(storage_key)`.
   - The database transaction rolls back.
   - Result: No database record points to a missing file; no orphaned files consume disk space.

---

## 8. Email Failure & Duplicate Prevention Policy

- Email dispatch is executed in an isolated worker thread (`asyncio.to_thread`) with a 10s socket timeout.
- A failed or timed-out email transmission updates the notification delivery status to `DeliveryStatus.FAILED` without rolling back the parent business mutation (e.g. site visit confirmation).
- **Anti-Duplication**: Automatic retries are intentionally **NOT** executed for SMTP dispatch because timeouts leave delivery state ambiguous; blind retries cause duplicate client spam.

---

## 9. Idempotency Policy

Clients executing mutating operations (`POST /properties`, `POST /leads`, `POST /site-visits/request`, `POST /follow-ups`) may provide an `Idempotency-Key: <unique-uuid>` header.
- **Same Key + Same Payload**: Returns cached response immediately with `Idempotent-Replay: true` header.
- **Same Key + Different Payload**: Rejects with `409 Conflict` ("Idempotency key reused with different request payload").
- **Concurrent In-Flight Key**: Rejects with `409 Conflict` ("A request with this idempotency key is currently processing").
- **Failed Request**: Records status `FAILED` or deletes key so client can retry without permanent blockage.
- **TTL**: Idempotency records expire after 24 hours.

---

## 10. Concurrency Policy

- **Advisory Locks**: `SiteVisitService` acquires PostgreSQL transaction-scoped advisory lock `pg_advisory_xact_lock(...)` during visit confirmation to prevent conflicting double bookings.
- **Row-Level Locks**: `PropertyService`, `SiteVisitService`, and `FollowUpService` acquire `SELECT ... FOR UPDATE` row locks before evaluating and applying status transitions.
- **Idempotent Transitions**: Status mutation endpoints return the existing entity gracefully if already in the target state.

---

## 11. Health vs. Readiness Policy

- `GET /health` and `GET /api/v1/health/live`: Process liveness probe. Returns HTTP 200 `{"status": "alive"}` if ASGI server process is responding.
- `GET /ready` and `GET /api/v1/health/ready`: Dependency readiness probe. Runs bounded `SELECT 1` against PostgreSQL with 2.0s timeout. Returns HTTP 200 if connected; returns HTTP 503 `Service Unavailable` if database is disconnected.

---

## 12. Graceful Degradation

- **Critical Dependencies**: PostgreSQL database, authentication, and transaction persistence. If unavailable, request fails fast with 503.
- **Non-Critical Dependencies**: SMTP email dispatch and live external government scraping lookups. If unavailable, core business operations complete successfully while recording failure status in logs and delivery metadata.

---

## 13. Known Limitations

- Real government land record APIs (TNREGINET, CMDA, e-Services) are not officially licensed; the backend operates via `DefaultOfflineProvider` which accurately returns `NOT_AVAILABLE` status.
- S3 cloud storage is architected as an interface; local development uses `LocalStorageBackend`. Production S3 deployment is scheduled for Phase 17/20.

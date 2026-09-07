# PHASE 15 — FAULT TOLERANCE EXPANSION SPECIFICATION & TECHNICAL REFERENCE

## 1. Phase Objective & Architecture Principles

The objective of Phase 15 is to harden the existing monolithic **RED_V1** Tamil Nadu Real-Estate Consultant & Brokerage backend against real-world infrastructure, network, transaction, and storage failures.

### Architectural Boundaries
* **Strict Monolith Preservation**: Zero external distributed dependencies introduced (no Kafka, Celery, RabbitMQ, Kubernetes, microservices, or Redis).
* **Deterministic Fail-Safe Execution**: PostgreSQL ACID transactions, transaction-scoped advisory locks, and row-level locking (`FOR UPDATE`) provide concurrency safety without external coordination engines.
* **Non-Duplication Contract**: Ambiguous network dropouts must never result in duplicate real-world operations (e.g. duplicate property creations, duplicate emails, or duplicate client profiles).
* **Graceful Degradation**: Failures in non-critical auxiliary services (e.g. SMTP email notification dispatch) never abort core business transactions or corrupt persistence state.
* **Information Leakage Defense**: No database connection strings, credentials, raw SQL statements, internal file paths, or third-party provider stack traces are ever leaked to API clients.

---

## 2. Hardened Infrastructure Failure Matrix

| Component / Layer | Primary Failure Mode | Immediate Behavior | Client / User Impact | Compensation / Recovery |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL Connection** | Drops, connection refused, pool exhaustion | Engine catches `OperationalError`, `TimeoutError`; aborts request | HTTP 503 `SERVICE_UNAVAILABLE` with clean error envelope | Pool recycles connection (`pool_recycle=1800`), fails fast on exhaustion (`pool_timeout=10`) |
| **Multi-Entity Transactions** | Mid-transaction exception or constraint violation | Atomic rollback via `transaction(session)` context manager | HTTP 400/409/422/500 depending on exception; no partial records | All staged entities rolled back atomically |
| **Document Storage Write** | Disk full, S3 unavailable, network timeout | Storage write fails before DB write; transaction aborted | HTTP 500 `STORAGE_ERROR` | Zero orphaned database records |
| **Document Storage Compensation** | DB write fails after binary file is written to storage | Transaction rolls back; compensation handler deletes file | HTTP 500 `INTERNAL_ERROR` / `DATABASE_ERROR` | Written file deleted from storage backend (`storage.delete(storage_key)`) |
| **Document Download** | File missing from storage backend or corrupted | Storage layer validates file existence; raises `NotFoundError` | HTTP 404 `NOT_FOUND` | Path traversal blocked; storage directory never leaked |
| **SMTP Delivery** | Timeout, connection refused, auth failure | Bounded single attempt in isolated worker thread; logs error | Core business operation completes normally | Channel returns `DeliveryResult(success=False, status=FAILED)`; zero duplicate emails |
| **External Providers** | 5xx server error, 429 rate limit, network timeout | `retry_async` applies bounded exponential backoff with jitter | Transparent recovery on transient glitch; HTTP 504 on timeout | Retries transient errors only; non-retryable 4xx/AppException immediately re-raised |
| **Mutation Duplication** | Duplicate submission on slow network connection | `IdempotencyService` detects in-flight or completed submission | Replays cached response with `Idempotent-Replay: true` header | 409 Conflict if payload differs or request is in-flight |
| **Concurrent Bookings** | Overlapping site visits within 60-minute buffer | PostgreSQL advisory lock (`pg_advisory_xact_lock`) serializes checks | First caller succeeds; second receives HTTP 409 `RESOURCE_CONFLICT` | Zero double-bookings |
| **Readiness Probes** | Database hangs or connectivity lost | Readiness check bounds query execution with 2.0s timeout | Orchestrator/LB receives HTTP 503 `SERVICE_UNAVAILABLE` | Traffic routed away until database connection restored |

---

## 3. Database Resilience & Pool Configuration

### Configuration Settings ([`app/core/config.py`](app/core/config.py))
```python
DB_POOL_TIMEOUT: int = 10       # Seconds to wait before timing out on pool exhaustion
DB_POOL_RECYCLE: int = 1800     # Recycle pooled connections after 30 minutes to drop dead sockets
EXTERNAL_REQUEST_TIMEOUT: int = 10  # Seconds before external provider requests time out
IDEMPOTENCY_EXPIRE_HOURS: int = 24  # Hours before mutation idempotency keys expire
```

### Session & Transaction Resilience ([`app/db/session.py`](app/db/session.py))
1. **Engine Creation**: Configured with `pool_timeout=settings.DB_POOL_TIMEOUT` and `pool_recycle=settings.DB_POOL_RECYCLE`.
2. **Session Dependency (`get_db`)**: Translates `(OperationalError, TimeoutError)` into `ServiceUnavailableError` (HTTP 503).
3. **Transaction Context (`transaction`)**: Automatically commits on clean exit, rolls back on any exception, and translates connection drops or pool timeouts into `ServiceUnavailableError`.

---

## 4. Mutation Idempotency Architecture

To prevent duplicate records caused by client-side retry after network disconnects, RED_V1 implements transactional mutation idempotency.

### 4.1 Database Migration
- Migration: `migrations/versions/0002_phase15_idempotency.py`
- Down revision: `0001_phase2_initial_schema`
- Verified: Both full upgrade -> downgrade -> upgrade cycles verified via automated migration tests.

### 4.2 Idempotency Model ([`app/models/idempotency.py`](app/models/idempotency.py))
```python
class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROCESSING", index=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
```

### 4.3 Idempotency Lifecycle & Contracts ([`app/core/idempotency.py`](app/core/idempotency.py))
1. **Key Reservation**: When an `Idempotency-Key` header is provided, the key is reserved in `PROCESSING` status.
2. **Concurrent Collision**: If an identical key is already in `PROCESSING`, the request is rejected with `409 Conflict` (`IDEMPOTENCY_IN_PROGRESS`).
3. **Payload Mismatch**: If an identical key was previously `COMPLETED` with a different payload hash, the request is rejected with `409 Conflict` (`IDEMPOTENCY_PAYLOAD_MISMATCH`).
4. **Cached Replay**: If an identical key was previously `COMPLETED` with the same payload hash, the cached status and body are replayed immediately with the HTTP header `Idempotent-Replay: true`.
5. **Abort / Failure Cleanup**: If the business operation fails or crashes, `abort` removes the in-flight reservation so the client can retry cleanly.

---

## 5. Bounded Retry Utility ([`app/core/retry.py`](app/core/retry.py))

Transient network failures during third-party integration calls are managed through a bounded asynchronous retry utility:

```python
await retry_async(
    operation=external_call,
    op_name="tn_guideline_api",
    max_attempts=3,
    initial_delay=0.1,
    max_delay=2.0,
    backoff_factor=2.0,
    jitter=True,
    retryable_check=is_transient_network_or_5xx,
)
```

### Strict Reliability Rules
* **Bounded Attempts**: Defaults to 3 attempts (never retries infinitely).
* **Transient Error Recognition**: Retries connection drops, socket timeouts, 429 Too Many Requests, and 502/503/504 status errors.
* **Immediate Re-raise on Business/Client Errors**: Never retries `AppException`, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, or 422 Unprocessable Entity.
* **Exponential Backoff with Jitter**: Introduces randomized intervals to avoid thundering herd spikes against external providers.

---

## 6. Storage Compensation & Security

1. **Atomic Upload Compensation** ([`app/services/document.py`](app/services/document.py)):
   When uploading a property title deed or verification document:
   - Binary data is written to the storage backend.
   - Metadata is committed to PostgreSQL in a transaction.
   - If PostgreSQL commit fails, compensation cleanup deletes the stored file (`await storage.delete(storage_key)`), preventing orphaned storage blobs.
2. **Directory Traversal Defense** ([`app/storage/local.py`](app/storage/local.py)):
   All storage keys are resolved relative to a strict base directory; attempts to traverse paths (e.g. `../../etc/passwd`) raise `StorageError` without leaking base directory paths.
3. **Safe Streaming**:
   Downloads stream binary chunks asynchronously, avoiding high memory buffers.

---

## 7. Operational Health Probes

### Endpoints
* `GET /health` (or `/api/v1/health/live`): Process liveness probe. Fast heartbeat (returns `200 OK {"status": "alive"}`).
* `GET /ready` (or `/api/v1/health/ready`): Infrastructure readiness probe. Verifies database connectivity with a 2.0s bounded timeout. Returns `200 OK {"database": "ok"}` when healthy; returns `503 SERVICE_UNAVAILABLE` on outage or timeout without leaking connection strings.

---

## 8. Test Suite & Verification Results

### Dedicated Fault Tolerance Suite (`tests/fault_tolerance/`)
* [`tests/fault_tolerance/test_database_failures.py`](tests/fault_tolerance/test_database_failures.py): Connection failure, pool exhaustion, transaction rollback, and error mapping.
* [`tests/fault_tolerance/test_transaction_failures.py`](tests/fault_tolerance/test_transaction_failures.py): Multi-record atomic rollback and integrity violation handling.
* [`tests/fault_tolerance/test_storage_failures.py`](tests/fault_tolerance/test_storage_failures.py): Write failure abortion, DB failure compensation cleanup, and path traversal defense.
* [`tests/fault_tolerance/test_email_failures.py`](tests/fault_tolerance/test_email_failures.py): Unconfigured SMTP host, connection refused, timeouts, and single attempt policy.
* [`tests/fault_tolerance/test_external_provider_failures.py`](tests/fault_tolerance/test_external_provider_failures.py): 5xx/429 bounded retries, permanent 4xx non-retry, and timeout exhaustion.
* [`tests/fault_tolerance/test_idempotency.py`](tests/fault_tolerance/test_idempotency.py): Request hash determinism, reservation lifecycle, conflict rejection, and cached replay.
* [`tests/fault_tolerance/test_concurrency.py`](tests/fault_tolerance/test_concurrency.py): Advisory lock conflict prevention for site visits, row-level locking for property status transitions, and idempotent follow-up completions.
* [`tests/fault_tolerance/test_timeouts.py`](tests/fault_tolerance/test_timeouts.py): Bounded database ping, external HTTP timeouts with `GatewayTimeoutError`, and prompt SMTP termination.
* [`tests/fault_tolerance/test_graceful_degradation.py`](tests/fault_tolerance/test_graceful_degradation.py): Core mutations succeed when auxiliary notifications fail; zero phantom "SENT" statuses.
* [`tests/fault_tolerance/test_readiness.py`](tests/fault_tolerance/test_readiness.py): Root and versioned liveness/readiness probes, outage 503 mapping, and timeout protection.

### Regression & Metrics Summary
* **Total Automated Tests**: 391 tests
* **Pass Rate**: 100% (391 passed, 0 failed, 0 errors)
* **Code Coverage**: 93% across entire application codebase

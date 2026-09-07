# PHASE 13 — AUDIT EXPANSION SPECIFICATION & TECHNICAL REFERENCE

## 1. Phase Objective

The objective of Phase 13 is to expand the existing audit system into a consistent, secure, append-only audit trail covering critical business and security events across RED_V1 without disrupting existing business workflows.

The audit system answers:
- **WHO** performed the action (`actor_id`)
- **WHAT** action occurred (`action`)
- **WHAT** entity was affected (`entity_type`, `entity_id`)
- **WHEN** did it occur (`created_at`)
- **WHAT** changed (`change_diff`, stored as structured, sanitized JSON)
- **FROM WHICH** IP/request context (`ip_address`)
- **WHICH** correlation/request ID was involved (`correlation_id`)
- **WAS** the action successful or rejected where appropriate

---

## 2. Existing Audit Architecture Discovered

During repository inspection, we verified:
- The base `audit_logs` table was established in Phase 2 via migration `0001_phase2_initial_schema.py`.
- The SQLAlchemy model `AuditLog` in [`app/models/audit.py`](app/models/audit.py) already defined all necessary columns:
  - `id` (UUID, PK)
  - `actor_id` (UUID, nullable, FK to `users.id` with `ON DELETE SET NULL`)
  - `action` (VARCHAR, indexed)
  - `entity_type` (VARCHAR, indexed)
  - `entity_id` (UUID, indexed)
  - `change_diff` (TEXT, nullable)
  - `ip_address` (VARCHAR, nullable)
  - `correlation_id` (VARCHAR, indexed, nullable)
  - `created_at` (TIMESTAMP WITH TIME ZONE, indexed)
- Previous phases (Authentication, Properties, Clients/Leads, Documents, Verification, Site Visits, Follow-ups, Notifications) already integrated with `AuditRepository.record(...)`.
- **Zero schema migration was required** because the existing database table perfectly satisfies all Master Backend Specification requirements.

---

## 3. Audit Schema & Model

The persisted audit log model ([`app/models/audit.py`](app/models/audit.py)) represents immutable system events:

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    change_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
```

---

## 4. Audit Event Model & Action Catalog

Deterministic, machine-readable action identifiers are codified in [`app/schemas/audit.py`](app/schemas/audit.py) under `AuditAction`:

- **Authentication & Security**:
  - `LOGIN_SUCCESS`
  - `LOGIN_FAILURE`
  - `REFRESH_TOKEN_ROTATED`
  - `REFRESH_TOKEN_REUSE_DETECTED`
  - `REFRESH_TOKEN_EXPIRED`
  - `LOGOUT`
  - `SECURITY_FORBIDDEN_ACCESS`
  - `SECURITY_UNAUTHORIZED_ACCESS`
- **Properties**:
  - `PROPERTY_CREATED`, `PROPERTY_UPDATED`, `PROPERTY_PUBLISHED`, `PROPERTY_PAUSED`, `PROPERTY_ARCHIVED`, `PROPERTY_STATUS_CHANGED`
- **Clients & Leads**:
  - `CLIENT_CREATED`, `CLIENT_UPDATED`, `CLIENT_ARCHIVED`
  - `LEAD_CREATED`, `LEAD_UPDATED`, `LEAD_STATUS_CHANGED`, `LEAD_ARCHIVED`
- **Requirements**:
  - `REQUIREMENT_CREATED`, `REQUIREMENT_UPDATED`, `REQUIREMENT_MATCHED`
- **Documents**:
  - `DOCUMENT_UPLOADED`, `DOCUMENT_UPDATED`, `DOCUMENT_ARCHIVED`, `DOCUMENT_STATUS_CHANGED`, `DOCUMENT_ACCESSED`
- **Verification**:
  - `VERIFICATION_REQUESTED`, `VERIFICATION_COMPLETED`, `VERIFICATION_NEEDS_REVIEW`, `VERIFICATION_REVIEWED`
- **Site Visits**:
  - `SITE_VISIT_CREATED`, `SITE_VISIT_CONFIRMED`, `SITE_VISIT_COMPLETED`, `SITE_VISIT_CANCELLED`, `SITE_VISIT_RESCHEDULED`, `SITE_VISIT_UPDATED`
- **Follow-ups**:
  - `FOLLOW_UP_CREATED`, `FOLLOW_UP_UPDATED`, `FOLLOW_UP_COMPLETED`, `FOLLOW_UP_MISSED`
- **Notifications**:
  - `NOTIFICATION_CREATED`, `NOTIFICATION_READ`, `NOTIFICATION_UNREAD`

---

## 5. Secret & PII Sanitization Engine

Centralized sanitization is implemented in [`app/core/sanitizer.py`](app/core/sanitizer.py):
- **Target Patterns**: Passwords (`password`, `password_hash`, `hashed_password`), tokens (`token`, `access_token`, `refresh_token`, `captcha_token`), keys (`api_key`, `apikey`, `secret_key`, `storage_secret_key`), and credentials (`authorization`, `smtp_password`, `private_key`, `presigned_url`).
- **Container Recognition**: Distinguishes containers and descriptors (e.g. `token_list`, `token_count`, `token_type`) from actual secret fields to prevent improper structural truncation.
- **Inline Masking**: Regex detection for raw JWT strings (`eyJ...`) and HTTP Bearer tokens embedded within log messages or serialized string diffs.
- **Redaction Marker**: Masks sensitive values with `"[REDACTED]"`.
- **Automatic Enforcement**: Sanitization is invoked automatically by `AuditRepository.record(...)` before any audit log is added to the session.

---

## 6. Request Context, Correlation IDs, and IP Handling

- **Correlation ID**: Captured from the incoming request header `X-Request-ID` or `X-Correlation-ID` via middleware [`app/middleware/request_id.py`](app/middleware/request_id.py). Defaults to an auto-generated UUID when omitted. Passed down to service and repository calls and persisted in `AuditLog.correlation_id`.
- **Request IP**: Extracted from direct client socket information via FastAPI's `Request.client.host`. Does not blindly trust arbitrary unverified proxy headers until Phase 17 production hardening. Persisted in `AuditLog.ip_address`.

---

## 7. Append-Only Immutability Guarantees

- **No Mutation Endpoints**: The API router exposes ONLY `GET /api/v1/audit-logs` and `GET /api/v1/audit-logs/{id}`. `POST`, `PUT`, `PATCH`, and `DELETE` requests return `405 Method Not Allowed`.
- **Repository Architecture**: [`app/repositories/audit.py`](app/repositories/audit.py) exposes exclusively `record(...)`, `get_by_id(...)`, and `list_audit_logs(...)`. There are zero update or delete methods in the data access layer.
- **No Soft Deletion**: Audit logs do not have `is_deleted` or `archived_at` columns and cannot be soft-deleted by application logic.

---

## 8. Private Consultant Audit Read API

Endpoints are mounted under `/api/v1/audit-logs`:

### `GET /api/v1/audit-logs`
- **Role Required**: `CONSULTANT`
- **Query Parameters**:
  - `actor_id` (UUID, optional)
  - `action` (string, optional)
  - `entity_type` (string, optional)
  - `entity_id` (UUID, optional)
  - `correlation_id` (string, optional)
  - `from_date` (ISO datetime, optional)
  - `to_date` (ISO datetime, optional)
  - `limit` (integer, bounded between 1 and 100, default 50)
  - `offset` (integer, >= 0, default 0)
- **Response**: `SuccessEnvelope[PaginatedResponse[AuditLogResponse]]` with total count aggregation.
- **Ordering**: Deterministic newest-first (`created_at DESC, id DESC`).

### `GET /api/v1/audit-logs/{id}`
- **Role Required**: `CONSULTANT`
- **Response**: `SuccessEnvelope[AuditLogResponse]`
- **Errors**: `404 Not Found` if the log entry does not exist; `422 Unprocessable Entity` on invalid UUID.

---

## 9. RBAC & Security

1. **Role Enforcement**: Both read endpoints strictly enforce `current_user: User = Depends(require_roles("CONSULTANT"))`. Anonymous and non-consultant users receive `401 Unauthorized` or `403 Forbidden`.
2. **Anti-IDOR & Scrubbing**: Audit read responses return sanitized diff payloads (`AuditLogResponse`). Raw SQLAlchemy internal models and sensitive database engine attributes are never leaked.
3. **Bounded Pagination**: Page size is hard-capped at 100 to prevent denial-of-service via unbounded database queries.

---

## 10. Transactional Behavior

Audit record creation is integrated with the business transaction:
```text
Business Service
      ↓
Business Repository Mutation
      +
Audit Repository Persistence
      ↓
Atomic Session Commit / Rollback
```
- If a business transaction fails and rolls back, the corresponding uncommitted audit entry is rolled back with it, preventing phantom audit entries for failed operations.
- Dedicated authentication failures and security events record audit logs within their own explicit transaction block to ensure security logs persist even when access is denied.

---

## 11. Database Indexing & Migration Analysis

- The `audit_logs` table already possesses B-Tree indexes on:
  - `action`
  - `entity_type`
  - `entity_id`
  - `actor_id`
  - `correlation_id`
  - `created_at`
- Because the existing indexes directly match the filter and sort patterns utilized by `list_audit_logs`, **no database migration was required**.

---

## 12. Testing Verification

All 331 tests across the RED_V1 test suite pass completely:
- Pre-existing baseline tests: 315 passed.
- New Phase 13 tests: 16 passed:
  - `tests/unit/test_audit_unit.py` (4 unit tests): secret key redaction, JWT/Bearer inline scrubbing, diff JSON handling, action enum catalog.
  - `tests/integration/test_audit_integration.py` (4 integration tests): business mutation audit logging, multi-field filtering, bounded pagination, detail queries.
  - `tests/integration/test_audit_security.py` (3 security tests): 401 unauthenticated rejection, 405 mutation rejection, credential sanitization verification.
  - `tests/failure/test_audit_failures.py` (4 failure tests): 404 on nonexistent log, 422 on invalid UUID, 422 on invalid pagination limits, 422 on invalid date format.
  - `tests/integration/test_audit_concurrency.py` (1 concurrency test): 20 concurrent audit events recorded without lock contention or data loss.

**Total**: **331 passed, 0 failed, 0 errors**.
**Overall Application Coverage**: **93%**.
**Audit Module Coverage**:
- `app/schemas/audit.py`: 100%
- `app/api/v1/audit.py`: 100%
- `app/services/audit.py`: 96%
- `app/core/sanitizer.py`: 92%
- `app/repositories/audit.py`: 91%
- `app/models/audit.py`: 95%

---

## 13. Tamil Nadu Domain & Consultant Context

Audit logs trace key activities across Tamil Nadu real-estate brokerage operations (e.g. TNREGINET evidence capture, EC review notes, survey/subdivision data changes, site visit logs, follow-up coordination).

**Legal Non-Certification Disclaimer**:
Audit records in RED_V1 represent internal consultant operational traceability only. Audit logging does NOT constitute government certification, statutory clearance, or legal title guarantee.

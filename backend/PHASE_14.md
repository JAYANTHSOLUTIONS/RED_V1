# PHASE 14 — INTEGRATION TESTING EXPANSION TECHNICAL REFERENCE

## 1. Phase Objective

The objective of Phase 14 is to comprehensively verify cross-module interaction across all completed backend systems (Phases 4 through 13).
Rather than evaluating units or isolated routers in isolation, Phase 14 models realistic Tamil Nadu real-estate consultant journeys and cross-cutting architectural invariants:
- Authentication & RBAC boundaries
- Property inventory & lifecycle state machines
- Client profiles, leads, and requirements
- Rule-based deterministic property matching
- Document management & secure object storage abstraction
- Tamil Nadu documentary preliminary verification
- Site visit scheduling and conflict prevention
- Consultant follow-up task progression
- Notification dispatch and delivery (in-app, email, WhatsApp link generation)
- Append-only immutable audit trail chains
- Transaction atomicity & rollback integrity
- Data isolation & anti-IDOR protections
- Timezone correctness (`Asia/Kolkata` UTC+05:30)

---

## 2. Existing Test Architecture Reviewed

Prior to Phase 14, the repository maintained:
- **Baseline Test Suite**: 331 tests passing across `tests/database/`, `tests/failure/`, `tests/integration/`, and `tests/unit/`.
- **Database Architecture**: PostgreSQL 16+ running on local port 5432 using SQLAlchemy 2.0 async with `asyncpg` driver and Alembic migrations.
- **Fixtures & Dependency Injection**: Clean separation in `tests/conftest.py`, using `create_app()` with async `httpx.AsyncClient` ASGI transport, per-test connection pool disposal, and domain fixtures.
- **Storage & External Stubs**: `LocalStorageEngine` for secure local blob streaming with SHA-256 integrity, mocked SMTP dispatch, and deterministic URI query-encoded WhatsApp deep links.

---

## 3. Integration Strategy & Test Organization

Phase 14 integration tests were added in dedicated test suites under [`tests/integration/`](file:///c:/Users/w/Documents/GitHub/RED/backend/tests/integration/):

| Test File | Scenarios Covered | Primary Invariants Verified |
| :--- | :--- | :--- |
| `test_phase14_property_client_lead_flow.py` | Scenarios 1 & 2 | Consultant Property CRUD, Client profiles, Lead association, Foreign Key integrity, Inactive/Archived entity protection |
| `test_phase14_requirement_matching_flow.py` | Scenario 3 | Buyer requirements, deterministic rule-based matching, filtering of non-published/archived properties, exact scoring |
| `test_phase14_document_verification_flow.py` | Scenarios 4 & 5 | Multipart document upload, SHA-256 deduplication, stream download, preliminary verification case review, non-title disclaimer |
| `test_phase14_site_visit_followup_flow.py` | Scenarios 6 & 7 | Site visit lifecycle (REQUESTED -> CONFIRMED -> COMPLETED), Follow-up scheduling and MISSED status transition |
| `test_phase14_notification_audit_flow.py` | Scenarios 8, 9, 24, 25 | Follow-up & site visit in-app alerts, unread counts, read/unread transitions, WhatsApp link generation, cross-consultant isolation |
| `test_phase14_cross_module_security.py` | Scenarios 11, 12, 14 | Unauthenticated 401 rejections, Non-consultant 403 blocks, Public property discovery shielding private seller data |
| `test_phase14_transaction_rollbacks.py` | Scenario 13 | Atomic transaction rollback on downstream failure, zero orphan business entities, zero phantom audit logs |
| `test_phase14_end_to_end_workflow.py` | Scenarios 10, 15, 21, 22, 23 | Complete 18-step consultant workflow, full property lifecycle (DRAFT -> PUBLISHED -> PAUSED -> SOLD -> ARCHIVED), Asia/Kolkata timezone verification |

---

## 4. Workflows Tested

### 4.1 Consultant -> Property -> Audit (Scenario 1)
- Consultant creates property in `DRAFT`.
- Verifies property persistence with sequence-generated public reference (e.g. `PR-2026-XXXXXX`).
- Verifies `PROPERTY_CREATED` audit log recorded with actor ID, entity ID, and sanitized attributes.
- Consultant applies partial update; verifies `PROPERTY_UPDATED` audit log reflects field diff without secret leakage.

### 4.2 Property -> Client -> Lead Flow (Scenario 2)
- Consultant creates property and buyer client profile.
- Creates lead linking client to property.
- Verifies relational foreign keys and eager loading of lead details.
- Validates rejection when attempting to associate leads with non-existent or archived entities.

### 4.3 Client -> Requirement -> Matching -> Property (Scenario 3)
- Client buyer requirement registered (budget, area, locality, bedrooms, transaction type).
- Multiple properties evaluated: exact match, locality mismatch, transaction mismatch (Rent vs Sale), and non-published status.
- Validates deterministic scoring algorithm: exact match achieves score 100 with `"EXACT_MATCH"` grade, while non-published properties are strictly excluded.

### 4.4 Property -> Document -> Secure Storage -> Verification (Scenarios 4 & 5)
- Multipart document upload (Sale Deed, Patta Passbook) with SHA-256 checksum and MIME validation.
- Validates rejection of disallowed file types (`.exe`, `.sh`).
- Verifies binary download streaming without exposing internal storage filesystem paths.
- Initiates preliminary property documentary verification case; updates consultant review observations with statutory disclaimer preserved.

### 4.5 Site Visit -> Follow-Up Coordination (Scenarios 6 & 7)
- Site visit requested on published property; consultant confirms visit with PostgreSQL advisory conflict check; site visit completed with feedback.
- Associated follow-up scheduled with target client and property; transitions from `SCHEDULED` to `COMPLETED` or `MISSED`.
- Verifies rejection when attempting to schedule visits for archived properties.

### 4.6 Follow-Up / Site Visit -> Notification -> Audit (Scenarios 8 & 9)
- Creation of follow-up alerts consultant in-app notification queue.
- Unread count aggregates increment accurately.
- Marking notification as read updates status and records `NOTIFICATION_READ` audit event.
- Validates cross-consultant notification isolation (Consultant B cannot read or view Consultant A's notifications).
- Safe, deterministic WhatsApp deep-link generation without external network calls.

### 4.7 Complete End-to-End Workflow (Scenario 10)
Full 18-step consultant lifecycle:
```text
Consultant Login
  ↓ Create Property (DRAFT)
  ↓ Publish Property (PUBLISHED)
  ↓ Create Client (BUYER)
  ↓ Create Lead (DIRECT_CALL)
  ↓ Create Requirement
  ↓ Match Requirement (Score 100)
  ↓ Upload Document (Patta PDF)
  ↓ Create Verification Case
  ↓ Consultant Review Verification
  ↓ Request Site Visit
  ↓ Confirm Site Visit
  ↓ Complete Site Visit
  ↓ Create Follow-Up
  ↓ Complete Follow-Up
  ↓ Receive In-App Notification
  ↓ Mark Notification Read
  ↓ Verify Complete Chronological Audit Trail
```

### 4.8 Authentication, RBAC, and Anti-IDOR Security (Scenarios 11, 12, 14)
- Unauthenticated requests to protected endpoints across all modules return HTTP 401.
- Non-consultant users (e.g. `BUYER` role) attempting access return HTTP 403 Forbidden.
- Public property endpoint returns public view while shielding internal notes and owner contact details.
- Consultant data isolation prevents cross-tenant access to private resources.

### 4.9 Failure & Transaction Rollbacks (Scenario 13)
- Simulated failure during property creation rolls back both property record and audit event.
- Simulated failure during site visit confirmation retains original `REQUESTED` state without leaving phantom `SITE_VISIT_CONFIRMED` audit records.
- Explicit `app.db.session.transaction` multi-model rollback leaves no orphaned dependent records.

### 4.10 Timezone Correctness (Scenario 22)
- Input timestamps supplied with `Asia/Kolkata` offset (`+05:30`) (e.g. `2026-10-15T15:30:00+05:30`).
- Validates response serialization maintains valid timezone-aware ISO 8601 strings.
- Direct PostgreSQL inspection confirms stored UTC timestamp matches exact normalized UTC time (`2026-10-15 10:00:00 UTC`).

---

## 5. External Service Mocking

All tests run in total network isolation:
- **Object Storage**: Local private storage engine / in-memory BytesIO buffers.
- **Email**: Mocked SMTP transport.
- **WhatsApp**: Deterministic query-string URI encoding (`https://wa.me/{phone}?text={encoded_msg}`).
- **Zero external network calls** were executed.

---

## 6. Regression Baseline & Test Metrics

- **Previous Baseline (Phase 13)**: 331 passed, 0 failed, 0 errors, 93% coverage.
- **Phase 14 New Integration Tests**: 22 passed.
- **Total Test Count**: **353 passed**, 0 failed, 0 errors.
- **Overall Code Coverage**: **93%** (5,721 statements evaluated, 409 missed).

---

## 7. Known Warnings

The existing benign warning remains:
```text
PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
```
As instructed by the Master Specification, this cleanup is scheduled for **Phase 17 — Production Hardening**.

---

## 8. Database Migrations

- **Migration required**: **NO**
The existing PostgreSQL schema and Alembic migrations fully support all cross-module foreign key constraints, indexes, and transactional boundaries.

---

## 9. Scope Boundaries

The following boundaries were strictly respected:
- Phase 15 (Fault Tolerance Expansion) — NOT implemented.
- Phase 16 (Dedicated Security Review) — NOT implemented.
- Phase 17 (Production Hardening) — NOT implemented.
- Phase 18 (API Freeze) — NOT implemented.
- Phase 19 (Frontend) — NOT implemented.
- Phase 20 (Deployment) — NOT implemented.
- No new business modules (Deals, Commissions, Payments) or speculative features (AI matching, Redis, Celery) were introduced.

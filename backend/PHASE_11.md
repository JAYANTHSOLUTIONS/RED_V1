# PHASE 11 — FOLLOW-UP MANAGEMENT DOCUMENTATION

## 1. Scope & Business Objective

Phase 11 implements **Follow-up Management** for `RED_V1`, a production backend system tailored for a solo Tamil Nadu real-estate consultant and property brokerage business.

Follow-ups are operational tracking tasks that ensure no buyer enquiry, owner check-in, missing property document, preliminary verification clarification, site visit arrangement, or registration coordination step is dropped.

The module provides:
1. Follow-up creation targeting a `Client` OR a `Lead`, with optional associated `Property`.
2. Action classification into 5 distinct operational real-estate categories (`CALL`, `SEND_DOCS`, `ARRANGE_VISIT`, `OWNER_FOLLOW_UP`, `MISSING_PAPERWORK`).
3. Lifecycle state machine: `SCHEDULED -> COMPLETED` or `SCHEDULED -> MISSED` with terminal state protection.
4. Concurrency protection via PostgreSQL row-level locking (`SELECT ... FOR UPDATE`).
5. Timezone-safe scheduling with `Asia/Kolkata` (`UTC+05:30`) normalization.
6. Comprehensive filtering (status, action_type, client, lead, property, date ranges) and pagination.
7. Audit trail integration recording `FOLLOW_UP_CREATED`, `FOLLOW_UP_UPDATED`, `FOLLOW_UP_COMPLETED`, and `FOLLOW_UP_MISSED`.
8. Centralized RBAC protection (`CONSULTANT` role).

> [!NOTE]
> Phase 11 maintains strict boundaries:
> - Automated notifications (WhatsApp / SMS / Email reminders) are deferred to Phase 12.
> - Deal closing and commission management are deferred to Phase 14.
> - No frontend UI or background cron workers were introduced in this phase.

---

## 2. Architecture & Layered Design

Adheres strictly to the established `RED_V1` layered repository pattern:

```text
API Router (/api/v1/follow-ups)
       ↓
Pydantic Schemas (app/schemas/follow_up.py)
       ↓
Domain Service (app/services/follow_up.py)
       ↓
Repository (app/repositories/follow_up.py)
       ↓
SQLAlchemy 2.x Async Engine & Models (app/models/follow_up.py)
       ↓
PostgreSQL 15+ (follow_ups table)
```

- **Routes**: Thin FastAPI route handlers enforcing RBAC and standard response envelopes (`SuccessEnvelope`).
- **Schemas**: Validates action types, ensures at least one target (`client_id` or `lead_id`) is present, and serializes responses.
- **Domain Service**: Enforces relationship constraints, verifies target non-archived status, enforces state machine transitions, manages transaction boundaries, and triggers audit logs.
- **Repository**: Executes optimized queries with eager-loading (`selectinload` for `client`, `lead`, `property`), row-level locking (`with_for_update()`), and paginated ordering.

---

## 3. Database & Data Model

The `follow_ups` table was established in Phase 2 (`0001_phase2_initial_schema.py`) and is mapped via `FollowUp` in `app/models/follow_up.py`:

| Column | Type | Constraints & Notes |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key, default `uuid.uuid4` |
| `client_id` | UUID | Foreign Key $\rightarrow$ `clients.id` (`ondelete="CASCADE"`), Nullable, Indexed |
| `lead_id` | UUID | Foreign Key $\rightarrow$ `leads.id` (`ondelete="CASCADE"`), Nullable, Indexed |
| `property_id` | UUID | Foreign Key $\rightarrow$ `properties.id` (`ondelete="SET NULL"`), Nullable |
| `scheduled_at` | TIMESTAMPTZ | Scheduled execution timestamp, Indexed, NOT NULL |
| `action_type` | VARCHAR(50) | Action category, NOT NULL |
| `status` | VARCHAR(30) | Default `"SCHEDULED"`, Indexed, NOT NULL |
| `notes` | TEXT | Consultant operational instructions / task details, Nullable |
| `completion_notes` | TEXT | Task execution outcome, Nullable |
| `completed_at` | TIMESTAMPTZ | Server timestamp upon completion, Nullable |
| `created_at` | TIMESTAMPTZ | Server default `func.now()`, NOT NULL |
| `updated_at` | TIMESTAMPTZ | Server default `func.now()`, onupdate, NOT NULL |

Constraints:
- `CheckConstraint("client_id IS NOT NULL OR lead_id IS NOT NULL", name="ck_follow_ups_target_present")`

Indexes:
- `ix_follow_ups_client_id`
- `ix_follow_ups_lead_id`
- `ix_follow_ups_scheduled_at`
- `ix_follow_ups_status`

**Database migration required**: **NO** (pre-existing schema reused without duplicate tables).

---

## 4. Action Categories & Business Meaning

| Action Type | Operational Meaning in Tamil Nadu Context |
| :--- | :--- |
| `CALL` | Direct phone call to buyer, tenant, seller, or landlord regarding requirements, availability, or pricing. |
| `SEND_DOCS` | Sharing draft sale agreements, EC copies, Patta extracts, or preliminary verification summaries. |
| `ARRANGE_VISIT` | Coordinating physical site visits with property owners or prospective buyers/tenants. |
| `OWNER_FOLLOW_UP` | Checking in with property owner on negotiation readiness, key handover, or pricing decisions. |
| `MISSING_PAPERWORK` | Chasing pending documentation (parent deeds, subdivision sketch, tax receipts, legal heir certificates). |

---

## 5. State Machine & Transitions

```text
       SCHEDULED
      /         \
     ↓           ↓
COMPLETED      MISSED
```

- **Initial Status**: `SCHEDULED`.
- **Allowed Transitions**:
  - `SCHEDULED -> COMPLETED` (records `completed_at = now()` server-side and optional `completion_notes`).
  - `SCHEDULED -> MISSED` (records transition and optional notes).
- **Terminal States**: `COMPLETED` and `MISSED` cannot transition to any other status. Attempting to mutate a terminal task is rejected with `422 INVALID_FOLLOW_UP_STATE`.
- **Idempotency**: Repeatedly completing an already `COMPLETED` follow-up, or marking an already `MISSED` follow-up as missed, returns the current entity cleanly.

---

## 6. Concurrency Protection

Operations that mutate follow-up status or metadata run inside `async with transaction(session):` and acquire a row-level lock:
```sql
SELECT * FROM follow_ups WHERE id = :follow_up_id FOR UPDATE;
```
If two requests attempt conflicting state transitions (e.g. `complete` vs `miss`) concurrently:
- Exactly one transaction acquires the row lock, executes the transition, and commits.
- The competing transaction waits for the lock, observes that the status is now terminal, and is rejected with `422 INVALID_FOLLOW_UP_STATE`.
- No row corruption or inconsistent state can occur.

---

## 7. API Endpoints Reference

All endpoints are mounted under `/api/v1/follow-ups` and require `require_roles("CONSULTANT")`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/follow-ups` | Schedule a new follow-up task targeting a Client or Lead |
| `GET` | `/api/v1/follow-ups` | List follow-ups with filtering (`status`, `action_type`, `client_id`, `lead_id`, `property_id`, date range) and pagination |
| `GET` | `/api/v1/follow-ups/{id}` | Retrieve full details of a follow-up task |
| `PATCH`| `/api/v1/follow-ups/{id}` | Update metadata (`action_type`, `scheduled_at`, `notes`, `property_id`) |
| `POST` | `/api/v1/follow-ups/{id}/complete` | Mark a scheduled follow-up as completed |
| `POST` | `/api/v1/follow-ups/{id}/miss` | Mark a scheduled follow-up as missed |

---

## 8. Security & RBAC

- **Role-Based Access Control**: Private consultant endpoints require valid JWT authentication and `require_roles("CONSULTANT")`. Users with non-consultant roles (e.g. `ASSISTANT`) receive `403 FORBIDDEN`. Unauthenticated requests receive `401 UNAUTHORIZED`.
- **Target & Relationship Consistency**: Validates that target entities exist and are active. If both `client_id` and `lead_id` are provided, enforces that the lead belongs to that client.
- **Data Protection**: Responses include only operational fields and exclude internal credentials, authentication tokens, and private database metadata.

---

## 9. Verification & Test Summary

- **Unit Tests** (`tests/unit/test_follow_up_unit.py`): 5 passed.
  - State machine transitions and terminal rules.
  - Target validation (Client OR Lead required; neither rejected).
  - Action type enum validations.
  - Timezone normalization (`Asia/Kolkata` to UTC).
  - Filter parameter parsing.
- **Integration Tests** (`tests/integration/test_follow_up_integration.py`): 3 passed.
  - Full lifecycle: Create $\rightarrow$ Get $\rightarrow$ Update $\rightarrow$ Complete $\rightarrow$ Audit.
  - Lead target auto-association with client and miss lifecycle.
  - Filtering by action_type, client_id, and pagination.
- **Security Tests** (`tests/integration/test_follow_up_security.py`): 3 passed.
  - Unauthenticated requests rejected with 401.
  - Non-consultant roles (`ASSISTANT`) rejected with 403.
  - Malformed UUID handling (422).
- **Failure Tests** (`tests/failure/test_follow_up_failures.py`): 5 passed.
  - Nonexistent client, lead, property, or follow-up returns 404.
  - Missing target returns 422.
  - Archived client rejected with 422.
  - Terminal state mutations rejected with 422.
  - Cross-client lead mismatch rejected with 422.
- **Concurrency Test** (`tests/integration/test_follow_up_concurrency.py`): 1 passed.
  - Concurrent competing `complete` vs `miss`: exactly one succeeds (200), other fails (422).
- **Regression Suite**:
  - Baseline: 275 passed.
  - Phase 11: 17 new tests.
  - Total: **292 passed**, 0 failures, 0 errors.

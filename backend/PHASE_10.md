# PHASE 10 — SITE VISIT COORDINATION DOCUMENTATION

## 1. Scope & Business Objective

Phase 10 implements **Site Visit Coordination** for `RED_V1`, a production backend system tailored for a solo Tamil Nadu real-estate consultant and property brokerage business.

The system coordinates physical property inspections between clients (buyers, tenants, investors) and the consultant, facilitating:
1. Customer / public property visit requests (always initialized in `REQUESTED` status, never automatically confirmed).
2. Consultant review, direct creation, and schedule management.
3. Conflict-checked confirmation preventing double booking.
4. Concurrency safety using PostgreSQL transactional row-locking and advisory locking.
5. Visit completion tracking with outcomes and feedback.
6. Controlled rescheduling preserving complete historical immutability via `rescheduled_from_id`.
7. Explicit cancellation requiring a cancellation reason.
8. Audit logging for all site visit state mutations (`SITE_VISIT_CREATED`, `SITE_VISIT_CONFIRMED`, `SITE_VISIT_COMPLETED`, `SITE_VISIT_CANCELLED`, `SITE_VISIT_RESCHEDULED`, `SITE_VISIT_UPDATED`).
9. Public vs. private data isolation (consultant notes, confidential pricing strategies, and client PII are strictly excluded from public responses).
10. Explicit separation between operational site visits and legal/documentary title verification.

> [!NOTE]
> Phase 10 maintains strict boundaries:
> - Follow-ups are deferred to Phase 11.
> - Notifications (WhatsApp / SMS / Email) are deferred to Phase 12.
> - Deals and Commissions are deferred to Phase 14.
> - No frontend UI or speculative features were introduced.

---

## 2. Architecture & Layered Design

Adheres strictly to the established `RED_V1` repository pattern:

```text
API Route (/api/v1/site-visits)
       ↓
Pydantic Schemas (app/schemas/site_visit.py)
       ↓
Domain Service (app/services/site_visit.py)
       ↓
Repository (app/repositories/site_visit.py)
       ↓
SQLAlchemy 2.x Async Engine & Models (app/models/site_visit.py)
       ↓
PostgreSQL 15+ (site_visits table)
```

- **Routes**: Thin HTTP adapters extracting headers, dependency injection, and mapping responses to `SuccessEnvelope`.
- **Schemas**: Separate `SiteVisitPublicRequest`, `SiteVisitPublicResponse`, `SiteVisitCreate`, `SiteVisitPrivateResponse`, `SiteVisitConfirm`, `SiteVisitComplete`, `SiteVisitCancel`, and `SiteVisitReschedule`.
- **Domain Service**: Enforces lifecycle state machine transitions, entity relationship validations (property, client, lead), timezone normalization, advisory locks, and atomic audit logging.
- **Repository**: Encapsulates database queries, eager loading (`selectinload` for client, property, lead, and rescheduled_from), row locks (`with_for_update`), and interval overlap queries.

---

## 3. Database & Data Model

The `site_visits` table was already created in Phase 2 (`0001_phase2_initial_schema.py`) and is mapped via `SiteVisit` in `app/models/site_visit.py`:

| Column | Type | Constraints & Notes |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key, default `uuid.uuid4` |
| `client_id` | UUID | Foreign Key $\rightarrow$ `clients.id` (`ondelete="RESTRICT"`), NOT NULL |
| `property_id` | UUID | Foreign Key $\rightarrow$ `properties.id` (`ondelete="RESTRICT"`), NOT NULL |
| `lead_id` | UUID | Foreign Key $\rightarrow$ `leads.id` (`ondelete="SET NULL"`), Nullable |
| `scheduled_at` | TIMESTAMPTZ | Scheduled timestamp, indexed, NOT NULL |
| `status` | VARCHAR(30) | Default `"REQUESTED"`, indexed, NOT NULL |
| `notes` | TEXT | Consultant operational notes / customer requests, Nullable |
| `cancellation_reason`| TEXT | Reason for cancellation, Nullable |
| `rescheduled_from_id`| UUID | Foreign Key $\rightarrow$ `site_visits.id` (`ondelete="SET NULL"`), Nullable |
| `feedback` | TEXT | Post-visit inspection outcome / feedback, Nullable |
| `created_at` | TIMESTAMPTZ | Server default `func.now()`, NOT NULL |
| `updated_at` | TIMESTAMPTZ | Server default `func.now()`, onupdate, NOT NULL |

Indexes:
- `ix_site_visits_property_schedule` (`property_id`, `scheduled_at`)
- `ix_site_visits_scheduled_at`
- `ix_site_visits_status`
- Foreign key indexes on `client_id`, `property_id`, `lead_id`

**Database migration required**: **NO** (pre-existing schema preserved without duplicate tables).

---

## 4. State Machine & Transitions

```text
       REQUESTED
      /    |    \
     /     |     \
    ↓      |      ↓
CANCELLED  |   RESCHEDULED (creates new linked record)
           ↓
       CONFIRMED
      /    |    \
     /     |     \
    ↓      |      ↓
COMPLETED  |   CANCELLED
           ↓
      RESCHEDULED (creates new linked record)
```

### Transition Enforcement Rules
- `REQUESTED` $\rightarrow$ `CONFIRMED`: Consultant reviews and confirms slot. Conflict checking enforced.
- `REQUESTED` $\rightarrow$ `CANCELLED`: Explicit cancellation before confirmation. Requires `cancellation_reason`.
- `REQUESTED` $\rightarrow$ `RESCHEDULED`: Reschedules directly from requested state.
- `CONFIRMED` $\rightarrow$ `COMPLETED`: Visit concluded. Notes outcome and feedback.
- `CONFIRMED` $\rightarrow$ `CANCELLED`: Explicit cancellation after confirmation.
- `CONFIRMED` $\rightarrow$ `RESCHEDULED`: Old visit marked `RESCHEDULED`; new visit created with `status="CONFIRMED"` and `rescheduled_from_id=old.id`.
- `REQUESTED` $\rightarrow$ `COMPLETED`: Strictly **rejected** (`422 INVALID_SITE_VISIT_TRANSITION`).
- `COMPLETED` and `CANCELLED`: Terminal states; no further transitions allowed.

---

## 5. Scheduling Semantics & Interval Conflict Protection

- **Timezone**: Tamil Nadu operates under Indian Standard Time (`Asia/Kolkata`, `UTC+05:30`). Naive datetimes are localized to `Asia/Kolkata` and normalized to UTC for database storage.
- **Default Buffer**: 60 minutes (`CONFLICT_BUFFER_MINUTES = 60`).
- **Interval Overlap Condition**: Two confirmed visits conflict if:
  $$|T_1 - T_2| < 60\text{ minutes}$$
- **Touching Boundaries**: Touching boundaries ($|T_1 - T_2| \ge 60\text{ minutes}$) do **not** conflict. For example, a visit from 10:00 to 11:00 and another from 11:00 to 12:00 are both permitted.
- **Status Scope**: Only visits with `status == "CONFIRMED"` occupy time slots. Visits in `REQUESTED`, `CANCELLED`, `RESCHEDULED`, or `COMPLETED` do not block calendar booking.

---

## 6. Concurrency Safety & PostgreSQL Transaction Isolation

To protect against race conditions when concurrent requests attempt to confirm overlapping visits:
1. Operations run inside `async with transaction(session):`.
2. A PostgreSQL transaction-scoped advisory lock is acquired:
   ```sql
   SELECT pg_advisory_xact_lock(8829910);
   ```
   This lock automatically releases on commit or rollback and serializes competing booking confirmations at the database level across multiple processes or workers.
3. The target site visit row is locked with `SELECT ... FOR UPDATE`:
   ```sql
   SELECT * FROM site_visits WHERE id = :visit_id FOR UPDATE;
   ```
4. Existing confirmed visits are queried within the 60-minute window.
5. If an overlap is found, `ConflictError` (`409 RESOURCE_CONFLICT`) is raised, rolling back the transaction.
6. If no conflict exists, the status is updated to `CONFIRMED`, an audit log entry is flushed, and the transaction commits atomically.

---

## 7. Public vs. Private API Separation & RBAC

### Role-Based Access Control (RBAC)
- Private endpoints require valid Bearer token authentication and the `CONSULTANT` role (`require_roles("CONSULTANT")`). Non-consultant roles (e.g. `ASSISTANT`) receive `403 FORBIDDEN`.
- Unauthenticated requests receive `401 UNAUTHORIZED`.

### Data Isolation
- **Public Request** (`POST /api/v1/site-visits/request`): Allows customers to request visits. Initialized only to `REQUESTED`. Returns `SiteVisitPublicResponse`.
- **Public View** (`GET /api/v1/site-visits/{id}/public`): Exposes only public safe fields (`id`, `property_id`, `scheduled_at`, `status`, `created_at`, `disclaimer`). Confidential consultant notes, pricing limits, client PII, and internal IDs are strictly stripped.
- **Private View** (`GET /api/v1/site-visits/{id}`): Full details with eager-loaded `client`, `property`, and `lead` summaries.

---

## 8. API Endpoint Reference

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/site-visits/request` | Public | Submit customer visit request (`REQUESTED`) |
| `GET` | `/api/v1/site-visits/{id}/public` | Public | View sanitized visit status |
| `POST` | `/api/v1/site-visits` | Consultant | Create visit (`REQUESTED` or `CONFIRMED`) |
| `GET` | `/api/v1/site-visits` | Consultant | List visits with filters & pagination |
| `GET` | `/api/v1/site-visits/{id}` | Consultant | Full visit detail |
| `PATCH`| `/api/v1/site-visits/{id}` | Consultant | Update editable notes / feedback |
| `POST` | `/api/v1/site-visits/{id}/confirm` | Consultant | Confirm visit with conflict checks |
| `POST` | `/api/v1/site-visits/{id}/complete`| Consultant | Mark confirmed visit as completed |
| `POST` | `/api/v1/site-visits/{id}/cancel` | Consultant | Cancel visit with mandatory reason |
| `POST` | `/api/v1/site-visits/{id}/reschedule` | Consultant | Reschedule visit (creates linked record) |

---

## 9. Tamil Nadu Real-Estate Context & Legal Safety

Site visits reflect practical Tamil Nadu property brokerage operations across:
- **Residential**: Apartments, independent houses, villas, residential plots in approved/unapproved layouts.
- **Land**: Plots, agricultural land, farm land, commercial layouts.
- **Locations**: District, Taluk, Village, Locality, Pincode context.

### Required Legal Disclaimer
Every site visit response envelope embeds the standard preliminary property assessment disclaimer:
> "This is a preliminary property verification assessment based on the information and documentary evidence available to RED_V1. It does not constitute legal title verification, certification of ownership, confirmation of document authenticity, or a guarantee that the property is free from encumbrances, disputes, planning violations, or other legal issues. Independent verification by the appropriate authorities and qualified legal professionals may be required."

A physical site visit never implies title clearance, government approval, or legal ownership.

---

## 10. Verification & Test Suite Summary

- **Unit Tests** (`tests/unit/test_site_visit_unit.py`): 5 passed.
  - State machine transition rules.
  - Indian Standard Time (`Asia/Kolkata`) normalization.
  - Conflict math (60-minute window, touching boundaries allowed).
  - Schema validations (mandatory cancellation reason, invalid statuses).
  - Filter parameters parsing.
- **Integration Tests** (`tests/integration/test_site_visit_integration.py`): 6 passed.
  - Full lifecycle: Create $\rightarrow$ Confirm $\rightarrow$ Complete.
  - Public visit request flow and sanitized response.
  - Explicit cancellation with mandatory reason.
  - Rescheduling preserving historical link (`rescheduled_from_id`).
  - List filtering and pagination.
  - Metadata patch updates.
- **Security Tests** (`tests/integration/test_site_visit_security.py`): 4 passed.
  - Unauthenticated access returns 401.
  - Non-consultant role (`ASSISTANT`) returns 403.
  - Public endpoint does not leak consultant notes or client PII.
  - Malformed UUID path handling (422).
- **Failure Tests** (`tests/failure/test_site_visit_failures.py`): 5 passed.
  - Nonexistent property (404 `PROPERTY_NOT_FOUND`).
  - Nonexistent client (404 `CLIENT_NOT_FOUND`).
  - Nonexistent lead (404 `LEAD_NOT_FOUND`).
  - Nonexistent site visit (404 `SITE_VISIT_NOT_FOUND`).
  - Attempting to complete unconfirmed visit rejected (422 `INVALID_SITE_VISIT_TRANSITION`).
  - Attempting to mutate terminal visit rejected (422).
  - Overlapping confirmation rejected (409 `RESOURCE_CONFLICT`).
  - Cross-client lead mismatch rejected (422).
- **Concurrency Test** (`tests/integration/test_site_visit_concurrency.py`): 1 passed.
  - Concurrent requests to confirm overlapping visits: exactly one returns 200, competing request receives 409 `RESOURCE_CONFLICT`.
- **Regression Suite**:
  - Baseline: 254 passed.
  - Phase 10: 21 passed.
  - Total: **275 passed**, 0 failures, 0 errors.

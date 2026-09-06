# PHASE 12 — NOTIFICATION MANAGEMENT DOCUMENTATION

## 1. Scope & Business Objective

Phase 12 implements the **Decoupled Notification System** for `RED_V1`, a production backend system tailored for a solo Tamil Nadu real-estate consultant and property brokerage business.

Notifications provide operational visibility across the consultant's daily workflows without coupling business logic to delivery infrastructure. The system supports:
1. **In-App Dashboard Alerts**: Persistent notification records queried, filtered, and marked read/unread by the consultant.
2. **Decoupled Email Dispatch**: Asynchronous, thread-isolated SMTP delivery with bounded timeouts, environment-driven configuration, and non-crashing failure modes.
3. **WhatsApp Deep-Link Generation**: Deterministic, URL-encoded `https://wa.me` links with Indian phone number sanitization (prefixing `91` for 10-digit mobile numbers) for consultant-triggered external messaging.
4. **Domain Event Integration**: Operational notification helpers for Follow-ups (`FOLLOW_UP_DUE`, `FOLLOW_UP_COMPLETED`, `FOLLOW_UP_MISSED`) and Site Visits (`SITE_VISIT_REQUESTED`, `SITE_VISIT_CONFIRMED`, `SITE_VISIT_RESCHEDULED`, `SITE_VISIT_CANCELLED`).
5. **Anti-IDOR Security**: Strict recipient scoping ensuring consultants only ever access their own notifications.
6. **Audit Trail**: Tracking key notification events (`NOTIFICATION_CREATED`, `NOTIFICATION_READ`, `NOTIFICATION_UNREAD`).

> [!NOTE]
> Phase 12 maintains strict architectural boundaries:
> - No external bot, scraper, or unofficial WhatsApp API was implemented; WhatsApp is strictly a secure deep-link generator.
> - No distributed task queue or message broker (Celery / Redis / RabbitMQ / Kafka) was introduced.
> - No deals or commission management (deferred to Phase 14).
> - No frontend UI components (backend REST API only).

---

## 2. Architecture & Layered Design

Adheres strictly to the established `RED_V1` layered repository and decoupled channel provider pattern:

```text
FastAPI Router (/api/v1/notifications)
       ↓
Pydantic Schemas (app/schemas/notification.py)
       ↓
Domain Service (app/services/notification.py)
       ↓
Notification Dispatcher (app/services/notifications/dispatcher.py)
 ┌─────┼─────────────────────────┐
 ↓     ↓                         ↓
In-App Email                  WhatsApp
Provider Provider              Provider
       ↓                         ↓
NotificationRepository     https://wa.me/...
       ↓
SQLAlchemy 2.x Async (app/models/notification.py)
       ↓
PostgreSQL 15+ (notifications table)
```

- **Routes**: Thin FastAPI endpoints enforcing RBAC (`CONSULTANT` role) and standard response envelopes (`SuccessEnvelope`).
- **Schemas**: Validates notification types, channels, query filter bounds, and ensures phone formatting.
- **Service**: Enforces recipient ownership, manages transaction boundaries with row-level locks (`SELECT ... FOR UPDATE`), coordinates audit logging, and drives channel dispatch.
- **Channel Providers**: Implements `BaseNotificationChannel` for `IN_APP`, `EMAIL`, and `WHATSAPP`.
- **Repository**: Executes optimized queries with anti-IDOR filtering, bounded pagination (1–100), and direct SQL aggregation for unread counts.

---

## 3. Database & Data Model

The `notifications` table was established in Phase 2 (`migrations/versions/0001_phase2_initial_schema.py`) and is mapped via `Notification` in `app/models/notification.py`:

| Column | Type | Constraints & Notes |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key, default `uuid.uuid4` |
| `user_id` | UUID | Foreign Key $\rightarrow$ `users.id` (`ondelete="CASCADE"`), Nullable, Indexed |
| `title` | VARCHAR(255) | Notification title, NOT NULL |
| `message` | TEXT | Notification body, NOT NULL |
| `channel` | VARCHAR(30) | Default `"DASHBOARD"` (normalized to `"IN_APP"` in domain layer), NOT NULL |
| `notification_type` | VARCHAR(50) | Operational event category, NOT NULL |
| `entity_type` | VARCHAR(50) | Referenced domain entity (`FOLLOW_UP`, `SITE_VISIT`, etc.), Nullable |
| `entity_id` | UUID | Referenced domain entity primary key, Nullable |
| `is_read` | BOOLEAN | Read flag, default `false`, Indexed, NOT NULL |
| `read_at` | TIMESTAMPTZ | Server timestamp when marked read, Nullable |
| `created_at` | TIMESTAMPTZ | Server default `func.now()`, NOT NULL |

Indexes:
- `ix_notifications_user_id`
- `ix_notifications_is_read`

**Database migration required**: **NO** (pre-existing schema fully supports all Phase 12 requirements).

---

## 4. Channel Providers & Abstraction

### 1. In-App Provider (`app/services/notifications/in_app.py`)
- Channel name: `IN_APP` (with `DASHBOARD` supported as a legacy alias).
- Stores alerts in the `notifications` table via `NotificationRepository`.
- Returns `DeliveryResult(success=True, status="DELIVERED", notification_id=...)`.

### 2. Email Provider (`app/services/notifications/email.py`)
- Channel name: `EMAIL`.
- Uses Python's standard library `smtplib` and `email.message.EmailMessage`.
- Isolated from the async event loop using `asyncio.to_thread`.
- Environment-driven configuration via `Settings` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `SMTP_TIMEOUT_SECONDS`).
- Bounded timeout prevents hanging operations.
- Graceful degradation: if `SMTP_HOST` is unset, returns `DeliveryResult(status="NOT_CONFIGURED")` without error.
- Non-crashing error handling: network or SMTP exceptions return `DeliveryResult(status="FAILED", message=str(exc))` without aborting business transactions.

### 3. WhatsApp Deep-Link Provider (`app/services/notifications/whatsapp.py`)
- Channel name: `WHATSAPP`.
- Formats encoded URL: `https://wa.me/{sanitized_digits}?text={urlencoded_message}`.
- Sanitizes Indian phone numbers: strips non-digits and automatically prepends country code `91` for standard 10-digit mobile numbers.
- Validates phone digit length (between 7 and 15 digits).
- Returns `DeliveryResult(success=True, status="READY", deep_link=...)`. Never claims delivery success because opening a link is not an automated delivery.

---

## 5. API Reference

All endpoints are grouped under `/api/v1/notifications` and require `CONSULTANT` role authentication.

| Method | Path | Summary | Success Status | Enforces Anti-IDOR |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/notifications` | List notifications for authenticated consultant with filtering & pagination | `200 OK` | Yes (`user_id = current_user.id`) |
| `GET` | `/api/v1/notifications/unread-count` | Aggregate count of unread notifications | `200 OK` | Yes (`user_id = current_user.id`) |
| `GET` | `/api/v1/notifications/{id}` | Get single notification details | `200 OK` | Yes (404 on ownership mismatch) |
| `POST` | `/api/v1/notifications/{id}/read` | Mark notification as read (idempotent) | `200 OK` | Yes (404 on ownership mismatch) |
| `POST` | `/api/v1/notifications/{id}/unread` | Mark notification as unread (idempotent) | `200 OK` | Yes (404 on ownership mismatch) |
| `POST` | `/api/v1/notifications/whatsapp-link` | Generate safe WhatsApp deep link for client message | `200 OK` | Yes (Consultant only) |

---

## 6. Audit Trail Integration

The notification system records the following audit events via `AuditRepository`:

| Action | Entity Type | Trigger | Sanitized Change Diff Captured |
| :--- | :--- | :--- | :--- |
| `NOTIFICATION_CREATED` | `NOTIFICATION` | When an in-app notification is created | `title`, `channel`, `notification_type`, `user_id`, `entity_type`, `entity_id` |
| `NOTIFICATION_READ` | `NOTIFICATION` | When marked read by recipient | `is_read: true`, `read_at: <timestamp>` |
| `NOTIFICATION_UNREAD` | `NOTIFICATION` | When marked unread by recipient | `is_read: false`, `read_at: null` |

---

## 7. Security & Privacy Guarantees

1. **Anti-IDOR Protection**: All notification lookups and state mutations filter strictly by `Notification.user_id == current_user.id`. Requesting another consultant's notification UUID returns `404 Not Found`.
2. **Credential Safety**: No email passwords, SMTP credentials, API keys, or JWT tokens are embedded in notification titles, bodies, audit diffs, or API response envelopes.
3. **No Legal Overreach**: Operational messages strictly avoid certifying legal facts (e.g. avoiding "Title cleared" or "Government approved").
4. **URL Encoding**: All WhatsApp pre-filled text is safely URL-encoded to prevent query parameter injection.

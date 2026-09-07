# RED_V1 FRONTEND CANONICAL SPEC

*This document is the final, reconciled source of truth for the Phase 19 Frontend design and implementation. It relies strictly on the Phase 18 frozen backend API contract.*

## 1. Product & Theme
- **Identity:** Operational Real Estate Brokerage Platform.
- **Theme:** `EXISTING` Light Mode Only (No dark mode).
- **Style:** Minimal, premium, professional, trustworthy, non-AI aesthetic.

## 2. Users & Roles
- **Consultant:** `EXISTING` Authenticated, has full operational control over private properties, clients, leads, and requirements.
- **Public:** `EXISTING` Unauthenticated, can view published properties and request site visits.

## 3. Navigation
- **Primary:** `DERIVED` Left Sidebar (Dashboard, Properties, Clients, Leads, Requirements, Site Visits, Follow-ups, Documents).
- **Secondary:** `DERIVED` Top Bar (Global Search, Notifications, Profile).

## 4. Workflows & API Support

### Authentication
- `EXISTING` Login (POST `/api/v1/auth/login`)
- `EXISTING` Token Refresh (POST `/api/v1/auth/refresh`)
- `EXISTING` Logout (POST `/api/v1/auth/logout`)
- `EXISTING` Load Context (GET `/api/v1/auth/me`)

### Properties
- `EXISTING` List (GET `/api/v1/properties`)
- `EXISTING` Create (POST `/api/v1/properties`) *[Idempotent]*
- `EXISTING` Edit (PATCH `/api/v1/properties/{id}`)
- `EXISTING` Status Mutations (Publish, Pause, Archive, Mark Sold/Rented)
- `EXISTING` Image Management (Upload, Reorder, Delete)

### Clients
- `EXISTING` List/Create/Edit/Archive.

### Leads
- `EXISTING` List/Create/Edit.
- `EXISTING` Status Mutations (Contact, Convert, Lost).

### Requirements & Matching
- `EXISTING` List/Create/Edit/Archive/Fulfill/Cancel.
- `EXISTING` Find Matches (GET `/api/v1/property-requirements/{id}/matches`) - Synchronous, returns scored candidates and explanations.

### Site Visits
- `EXISTING` List/Create/Update.
- `EXISTING` Status Mutations (Confirm, Complete, Cancel, Reschedule).
- `EXISTING` Public Request Flow.

### Verification (Property Intelligence)
- `EXISTING` Run check, view summary, view detailed evidence, view actions.

### Documents
- `EXISTING` List, Upload, Review, Archive.
- `EXISTING` Download binary stream.
- `VISUAL` Secure Previewer (Frontend wraps the binary stream rendering; backend doesn't serve a separate "viewer" HTML page).

### Follow-ups
- `EXISTING` List, Create, Edit.
- `EXISTING` Complete, Miss.

### Notifications
- `EXISTING` List, Mark Read/Unread, WhatsApp Link Generation.

### Dashboard
- `DERIVED` Metrics derived from list endpoints (using `total` count).
- `BLOCKED` Explicit aggregation/statistics APIs (do not exist, so complex historical charts are unsupported).

## 5. Idempotency
- `EXISTING` Requires `Idempotency-Key` header on all entity creation endpoints to safely handle network retries.

## 6. Error Handling
- `EXISTING` 422 for field validation.
- `EXISTING` 401 for unauthorized (redirect/refresh).
- `EXISTING` 403 for forbidden (modal/page).
- `EXISTING` 409 for conflicts / idempotency mismatch.

## 7. Unsupported Features
- `UNSUPPORTED` Analytics / Complex Charts (No aggregation endpoints).
- `UNSUPPORTED` "Dark Mode" (Explicitly forbidden by design requirements).
- `UNSUPPORTED` AI Chatbot / Generative UI (Intelligence is strictly tabular/structured evidence).

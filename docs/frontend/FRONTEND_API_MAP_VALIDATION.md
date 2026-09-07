# FRONTEND API MAP VALIDATION

This document reconciles the previously proposed `FRONTEND_API_MAP.md` against the frozen Phase 18 API contract to ensure 100% accuracy.

| Endpoint | Discovery Claim | Actual Contract | Status | Correction |
| -------- | --------------- | --------------- | ------ | ---------- |
| `/api/v1/auth/login` (POST) | `login` | Exists, returns JWTs | VERIFIED | |
| `/api/v1/auth/refresh` (POST) | `refresh` | Exists | VERIFIED | |
| `/api/v1/auth/me` (GET) | `me` | Exists | VERIFIED | |
| `/api/v1/auth/logout` (POST) | `logout` | Exists | VERIFIED | |
| `/api/v1/properties` (GET) | `list_properties` | Exists | VERIFIED | |
| `/api/v1/properties` (POST) | `create_property` | Exists | VERIFIED | |
| `/api/v1/properties/{id}` (GET) | `get_property` | Exists | VERIFIED | |
| `/api/v1/properties/{id}` (PATCH) | `update_property` | Exists | VERIFIED | |
| `/api/v1/properties/{id}/publish` (POST) | Publish | Exists | VERIFIED | |
| `/api/v1/properties/{id}/pause` (POST) | Pause | Exists | VERIFIED | |
| `/api/v1/properties/{id}/archive` (POST) | Archive | Exists | VERIFIED | |
| `/api/v1/properties/{id}/mark-sold` (POST) | Mark Sold | Exists | VERIFIED | |
| `/api/v1/properties/{id}/mark-rented` (POST)| Mark Rented | Exists | VERIFIED | |
| `/api/v1/public/properties` (GET) | Public list | Exists | VERIFIED | |
| `/api/v1/clients` (GET/POST) | List/Create | Exists | VERIFIED | |
| `/api/v1/clients/{id}` (GET) | Details | Exists | VERIFIED | |
| `/api/v1/leads` (GET/POST) | List/Create | Exists | VERIFIED | |
| `/api/v1/leads/{id}/contact` (POST) | Contacted | Exists | VERIFIED | |
| `/api/v1/leads/{id}/convert` (POST) | Converted | Exists | VERIFIED | |
| `/api/v1/documents` (GET/POST) | List/Upload | Exists | VERIFIED | |
| `/api/v1/documents/{id}/download` (GET)| Download | Exists | VERIFIED | Secure Viewer requires browser rendering of the binary stream. |
| `/api/v1/properties/{id}/verification` (POST/GET)| Verification | Exists | VERIFIED | |
| `/api/v1/properties/{id}/verification/evidence` (GET)| Evidence | Exists | VERIFIED | |
| `/api/v1/site-visits` (GET/POST) | List/Create | Exists | VERIFIED | |
| `/api/v1/site-visits/{id}/confirm` (POST) | Confirm | Exists | VERIFIED | |
| `/api/v1/site-visits/request` (POST) | Public Request | Exists | VERIFIED | |
| `/api/v1/notifications` (GET) | List | Exists | VERIFIED | |
| `/api/v1/notifications/unread-count` (GET)| Badge count | Exists | VERIFIED | |
| `/api/v1/notifications/{id}/read` (POST) | Mark read | Exists | VERIFIED | |
| *Dashboard Metrics* | Not explicitly listed in old map | No dedicated `/dashboard` API | INCORRECT | Frontend must derive stats from list APIs (e.g. `total` field) or it's an API CONTRACT BLOCKER for heavy aggregations. |
| *Matching* | Missed in previous map | `/api/v1/property-requirements/{id}/matches` | INCOMPLETE | Added matching to Canonical Spec. |
| *Follow-ups* | Missed in previous map | `/api/v1/follow-ups` | INCOMPLETE | Added follow-ups to Canonical Spec. |

# FRONTEND API MAP

This document maps the frozen Phase 18 API endpoints to the required frontend screens and actions.

## Authentication
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/auth/login` | POST | `/login` | Submit credentials | Public | Generates JWTs. |
| `/api/v1/auth/refresh` | POST | Global (Background) | Token expiry handling | Public | Uses refresh token. |
| `/api/v1/auth/me` | GET | Global / Dashboard | Load user context | Auth | - |
| `/api/v1/auth/logout` | POST | Global Header | "Log Out" click | Auth | - |

## Properties
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/properties` | GET | `/properties` | Load list / Search | CONSULTANT | - |
| `/api/v1/properties` | POST | `/properties/new` | Save new property | CONSULTANT | Idempotent |
| `/api/v1/properties/{id}` | GET | `/properties/{id}` | Load details | CONSULTANT | - |
| `/api/v1/properties/{id}` | PATCH | `/properties/{id}` | Save edits | CONSULTANT | - |
| `/api/v1/properties/{id}/publish` | POST | `/properties/{id}` | Click "Publish" | CONSULTANT | - |
| `/api/v1/properties/{id}/pause` | POST | `/properties/{id}` | Click "Pause" | CONSULTANT | - |
| `/api/v1/properties/{id}/archive` | POST | `/properties/{id}` | Click "Archive" | CONSULTANT | Requires Modal |
| `/api/v1/properties/{id}/mark-sold` | POST | `/properties/{id}` | Click "Mark Sold" | CONSULTANT | - |
| `/api/v1/properties/{id}/mark-rented`| POST | `/properties/{id}` | Click "Mark Rented"| CONSULTANT | - |
| `/api/v1/public/properties` | GET | `/public/properties` | Load list | Public | Safe subset of data. |

## Clients & Leads
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/clients` | GET | `/clients` | Load list | CONSULTANT | - |
| `/api/v1/clients` | POST | `/clients/new` | Save new client | CONSULTANT | Idempotent |
| `/api/v1/clients/{id}` | GET | `/clients/{id}` | Load details | CONSULTANT | Includes related leads |
| `/api/v1/leads` | GET | `/leads` | Load list | CONSULTANT | - |
| `/api/v1/leads` | POST | `/leads/new` | Create lead | CONSULTANT | Idempotent |
| `/api/v1/leads/{id}/contact` | POST | `/leads/{id}` | Move to Contacted | CONSULTANT | Pipeline transition |
| `/api/v1/leads/{id}/convert` | POST | `/leads/{id}` | Mark Converted | CONSULTANT | Terminal state |

## Documents
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/documents` | GET | `/documents` | Load list | CONSULTANT | - |
| `/api/v1/documents` | POST | `/documents/upload` | Upload file | CONSULTANT | multipart/form-data |
| `/api/v1/documents/{id}/download`| GET | `/documents/{id}` | Click Download | CONSULTANT | Streams binary |

## Verification
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/properties/{id}/verification`| POST | `/properties/{id}/verification`| Run Intelligence | CONSULTANT | Triggers backend AI |
| `/api/v1/properties/{id}/verification/evidence`| GET | `/properties/{id}/verification`| Load Evidence | CONSULTANT | Detailed view |

## Site Visits
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/site-visits` | GET | `/site-visits` | Load list | CONSULTANT | - |
| `/api/v1/site-visits` | POST | `/site-visits/new` | Schedule Visit | CONSULTANT | Idempotent |
| `/api/v1/site-visits/{id}/confirm`| POST | `/site-visits/{id}` | Confirm Request | CONSULTANT | - |
| `/api/v1/site-visits/request` | POST | `/public/properties/{id}`| Public Request | Public | - |

## Notifications
| Endpoint | Method | Screen | Action | Role | Note |
|----------|--------|--------|--------|------|------|
| `/api/v1/notifications` | GET | `/notifications` | Load list | CONSULTANT | - |
| `/api/v1/notifications/unread-count`| GET | Global Header | Show badge count | CONSULTANT | Poll or load on init |
| `/api/v1/notifications/{id}/read` | POST | `/notifications` | Click notification | CONSULTANT | - |

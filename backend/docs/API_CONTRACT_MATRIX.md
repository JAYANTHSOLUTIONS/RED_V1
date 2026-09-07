# API CONTRACT MATRIX

This document provides a high-level overview of the API contracts grouped by domain. For exhaustive endpoint definitions (including Request/Response schemas, precise Error Codes, and Idempotency flags), frontend developers MUST refer to the generated `openapi.json` or the Swagger UI documentation.

## General Conventions

- **Success Responses**: Wraps data in a `{"success": true, "data": {...}, "message": "..."}` envelope.
- **Error Responses**: Wraps errors in a `{"success": false, "error": {"code": "...", "message": "..."}}` envelope.
- **Idempotency**: Mutation endpoints marked with `(Idempotent)` support the `Idempotency-Key` header.
- **Pagination**: List endpoints return `{"items": [...], "total": N, "limit": L, "offset": O}` inside the data payload.

## Authentication & Identity

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/auth/login` | POST | No | - | `200 OK` (Tokens) | `401` | Issues access/refresh tokens. Rate limited. |
| `/api/v1/auth/refresh` | POST | No | - | `200 OK` (Tokens) | `401` | Requires valid refresh token in body. |
| `/api/v1/auth/me` | GET | Yes | - | `200 OK` (User) | `401` | Retrieves current user context. |
| `/api/v1/auth/logout` | POST | No | - | `200 OK` | `401` | Revokes the current refresh token. |

## Properties

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/properties` | POST | Yes | CONSULTANT | `201 Created` | `422` | Create property. (Idempotent) |
| `/api/v1/properties` | GET | Yes | CONSULTANT | `200 OK` (Paginated) | `401` | List private properties (filters supported). |
| `/api/v1/public/properties` | GET | No | - | `200 OK` (Paginated) | `400` | List public properties (omits sensitive data). |
| `/api/v1/properties/{id}` | GET | Yes | CONSULTANT | `200 OK` | `404` | Retrieve private property details. |
| `/api/v1/properties/{id}` | PATCH | Yes | CONSULTANT | `200 OK` | `404`, `422` | Partial update property fields. |

## Clients & Leads

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/clients` | POST | Yes | CONSULTANT | `201 Created` | `422` | Create client. (Idempotent) |
| `/api/v1/clients/{id}` | GET | Yes | CONSULTANT | `200 OK` | `404` | Retrieve client details. |
| `/api/v1/leads` | POST | Yes | CONSULTANT | `201 Created` | `422`, `404` | Create lead tied to client/property. (Idempotent) |
| `/api/v1/leads/{id}/contact`| POST | Yes | CONSULTANT | `200 OK` | `404`, `409` | Transition lead status to CONTACTED. |

## Documents

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/documents` | POST | Yes | CONSULTANT | `201 Created` | `422`, `400` | Upload file (multipart/form-data). Max 15MB. |
| `/api/v1/documents/{id}/download` | GET | Yes | CONSULTANT | `200 OK` (Binary) | `404`, `403` | Stream document content. |
| `/api/v1/documents/{id}` | PATCH | Yes | CONSULTANT | `200 OK` | `404` | Update metadata. |

## Verification

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/properties/{id}/verification` | POST | Yes | CONSULTANT | `200 OK` | `404`, `409` | Run property intelligence checks. (Idempotent) |
| `/api/v1/properties/{id}/verification/summary`| GET | Yes | CONSULTANT | `200 OK` | `404` | Get high-level check results. |

## Site Visits & Follow-ups

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/site-visits` | POST | Yes | CONSULTANT | `201 Created` | `409`, `422` | Schedule a site visit. (Idempotent) |
| `/api/v1/site-visits/{id}/confirm`| POST | Yes | CONSULTANT | `200 OK` | `404`, `409` | Confirm requested visit. |
| `/api/v1/follow-ups` | POST | Yes | CONSULTANT | `201 Created` | `422` | Create task. (Idempotent) |
| `/api/v1/follow-ups/{id}/complete`| POST | Yes | CONSULTANT | `200 OK` | `404`, `409` | Mark task completed. |

## Notifications & Audit

| Endpoint | Method | Auth | Role | Typical Success | Common Errors | Notes |
|----------|--------|------|------|-----------------|---------------|-------|
| `/api/v1/notifications` | GET | Yes | CONSULTANT | `200 OK` (Paginated) | `401` | List inbox alerts. |
| `/api/v1/audit-logs` | GET | Yes | CONSULTANT | `200 OK` (Paginated) | `401` | View immutable system actions. |

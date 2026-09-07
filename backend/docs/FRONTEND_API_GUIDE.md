# RED_V1 FRONTEND API GUIDE

Welcome to the frontend integration guide for the RED_V1 Real-Estate Backend. The API contract is now frozen (Phase 18). This guide explains how to interact with the API correctly.

## 1. Base URL & Environments
- **Local Development:** `http://localhost:8000`
- The API is versioned. All business routes are prefixed with `/api/v1`.

## 2. Authentication
RED_V1 uses JSON Web Tokens (JWT) for authentication.
- **Login:** Send `POST /api/v1/auth/login` with `{"email": "...", "password": "..."}`. You will receive an `access_token` and `refresh_token`.
- **Authorization Header:** For all private endpoints, include the header:
  `Authorization: Bearer <access_token>`
- **Refresh:** Before the access token expires (20 minutes), call `POST /api/v1/auth/refresh` with `{"refresh_token": "..."}` to get a new pair.
- **Logout:** Send `POST /api/v1/auth/logout` with your refresh token to revoke it.

## 3. Standard Request & Response Format
All requests and responses use `application/json` (except file uploads).

### Success Envelope
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Example Property"
  },
  "message": "Property retrieved successfully."
}
```

### Error Envelope
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The provided data failed validation."
  }
}
```
*Note: Always use the `error.code` string (e.g., `VALIDATION_ERROR`, `NOT_FOUND`) for programmed logic in the frontend, rather than relying on HTTP status codes alone or parsing the human-readable `message`.*

## 4. Pagination
List endpoints are paginated using `limit` and `offset` query parameters.

**Request:** `GET /api/v1/properties?limit=20&offset=0`

**Response `data` payload:**
```json
{
  "items": [...],
  "total": 145,
  "limit": 20,
  "offset": 0
}
```

## 5. Dates & Timestamps
- All date and datetime fields returned by the API are strictly in **ISO 8601 UTC format** (e.g., `2026-09-07T10:00:00Z`).
- When submitting dates to the API, send them in ISO 8601 format. 

## 6. Enums
Enum values are strictly validated. See the `openapi.json` for exact values.
- Examples of Property Status: `DRAFT`, `PUBLISHED`, `PAUSED`, `ARCHIVED`, `SOLD`, `RENTED`.
- Examples of Lead Status: `NEW`, `CONTACTED`, `INTERESTED`, `SITE_VISIT`, `NEGOTIATION`, `CONVERTED`, `LOST`.
Do not send lowercase or localized equivalents.

## 7. File Uploads (Documents/Images)
Endpoints accepting files (like `POST /api/v1/documents`) require `multipart/form-data`.
- Field name: `file`
- Max size: 15MB
- Allowed Types: `.pdf`, `.png`, `.jpg`, `.jpeg`

## 8. Idempotency
Certain mutation endpoints (like `POST /api/v1/properties`) support idempotency to prevent duplicate creations on network retries.
- **Header:** Include `Idempotency-Key: <unique-uuid4-or-string>` in your POST requests.
- If a request is retried with the exact same key and payload, the backend will return the original successful response without duplicating the record.
- If the payload differs for the same key, you will receive a `409 Conflict` (`IDEMPOTENCY_PAYLOAD_MISMATCH`).

## 9. Roles & RBAC
- The application currently enforces the `CONSULTANT` role for all private endpoints.
- Unauthenticated requests receive `401 Unauthorized`.
- Authenticated requests lacking the role receive `403 Forbidden`.

## 10. OpenAPI / Swagger
For exact schemas, request fields, required properties, and nullability, refer to the generated `openapi.json` file in the backend repository (`backend/docs/openapi.json`).

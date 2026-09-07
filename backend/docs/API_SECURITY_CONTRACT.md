# API SECURITY CONTRACT

This document outlines the security controls, requirements, and behaviors expected by the RED_V1 API. The frontend MUST adhere to these contracts.

## 1. Authentication
- **Mechanism:** JWT (JSON Web Tokens) with HS256 signature algorithm.
- **Access Tokens:** Short-lived (default 20 minutes). Must be sent in the `Authorization` header as `Bearer <token>`.
- **Refresh Tokens:** Long-lived (default 14 days). Used strictly at the `/api/v1/auth/refresh` endpoint to obtain a new access token.
- **Token Storage (Frontend):** 
  - Do NOT store access tokens in `localStorage` if possible (in-memory preferred).
  - Refresh tokens must be stored securely.

## 2. Authorization (RBAC)
- **Role Requirement:** Almost all private API endpoints require the `CONSULTANT` role.
- **Enforcement:** The backend strictly enforces this. An authenticated user without the `CONSULTANT` role will receive a `403 Forbidden` (`FORBIDDEN`).
- **Inactive Users:** If a user account is deactivated, all tokens are immediately rejected with `401 Unauthorized`.

## 3. Rate Limiting
- **Login Endpoint:** Restricted to 10 attempts per minute per IP address.
- **Response:** Exceeding this limit yields a `429 Too Many Requests` (`RATE_LIMITED`).

## 4. Cross-Origin Resource Sharing (CORS)
- **Production Configuration:** Allowed origins are strictly explicitly whitelisted via `CORS_ALLOWED_ORIGINS`.
- **Wildcards:** `*` is not permitted in production.

## 5. Security Headers
The API responses include hardened security headers:
- `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (in production)

## 6. Mass Assignment Protection
- **Immutable Fields:** Fields like `id`, `status`, `public_reference`, and `created_at` cannot be altered by passing them in the request body for Create/Update payloads. The backend simply ignores or rejects them.

## 7. File Upload Restrictions
- **Allowed Extensions:** `.pdf`, `.png`, `.jpg`, `.jpeg` only.
- **Magic Bytes:** File content is strictly verified against its stated MIME type and extension using magic byte inspection.
- **Size Limit:** Max upload size is 15MB.
- **Malicious Filenames:** Directory traversal (`../../`) is prevented server-side.

## 8. Idempotency Security
- **Header:** `Idempotency-Key` must be a non-empty string $\le 128$ characters.
- **Payload Hash Verification:** Replayed requests are checked for payload drift. A changed payload with the same key yields a `409 Conflict` (`IDEMPOTENCY_PAYLOAD_MISMATCH`).

## 9. Error Sanitization
- The backend will NEVER expose internal database connection strings, stack traces, or framework exceptions to the API. All unhandled errors are genericized to `INTERNAL_ERROR`.

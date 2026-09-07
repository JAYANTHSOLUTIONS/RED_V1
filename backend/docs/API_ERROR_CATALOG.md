# API ERROR CATALOG

This document lists all canonical error codes returned by the RED_V1 API.

All API errors follow a standard envelope format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

The frontend should rely on the `error.code` string and HTTP Status code for programmatic handling, rather than parsing the `message`, which may change or be localized.

## Canonical Error Codes

| Code | HTTP Status | Meaning | Frontend Action |
|------|-------------|---------|-----------------|
| `VALIDATION_ERROR` | 422 | The provided data failed domain or schema validation. | Highlight specific form fields if possible, or show the message to the user. |
| `UNAUTHORIZED` | 401 | Authentication is missing, invalid, or expired. | Redirect to the login screen or attempt to refresh the session token. |
| `FORBIDDEN` | 403 | The authenticated user lacks the required role (e.g. CONSULTANT). | Show a "permission denied" message. |
| `NOT_FOUND` | 404 | The requested resource (property, client, etc.) does not exist. | Navigate back or show a 404 page/message. |
| `RESOURCE_CONFLICT` | 409 | The request conflicts with current state (e.g., double booking). | Inform the user of the conflict and refresh the current data view. |
| `RATE_LIMITED` | 429 | The client has exceeded the permitted request rate. | Prompt the user to wait before trying again. |
| `DATABASE_ERROR` | 500 | An internal database failure occurred. | Generic "Try again later" message. |
| `STORAGE_ERROR` | 500 | An object-storage failure occurred. | Generic "Try again later" message. |
| `SERVICE_UNAVAILABLE` | 503 | A required upstream service or database is unreachable. | Generic "Service is down" message; retry later. |
| `GATEWAY_TIMEOUT` | 504 | An external service (e.g. TN Intelligence) timed out. | Inform the user the external integration is slow/unavailable. |
| `INTERNAL_ERROR` | 500 | An unexpected, unhandled exception occurred. | Generic "Try again later" message. |

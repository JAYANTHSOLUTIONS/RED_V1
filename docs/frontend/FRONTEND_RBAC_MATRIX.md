# FRONTEND RBAC MATRIX

This matrix confirms role-based access control (RBAC) frontend behavior against the actual frozen backend.

| Screen | Public | Authenticated | Role Requirement | View | Create | Edit | Delete / Archive | Special Actions |
| ------ | -----: | ------------: | ---- | ---: | -----: | ---: | -----: | --------------: |
| Login | Yes | No | None | Yes | N/A | N/A | N/A | - |
| Dashboard | No | Yes | `CONSULTANT` | Yes | N/A | N/A | N/A | - |
| Properties | No | Yes | `CONSULTANT` | Yes | Yes | Yes | Yes (Archive) | Publish, Pause, Sold, Rented |
| Public Directory | Yes | Optional | None | Yes | No | No | No | Request Site Visit |
| Clients | No | Yes | `CONSULTANT` | Yes | Yes | Yes | Yes (Archive) | - |
| Leads | No | Yes | `CONSULTANT` | Yes | Yes | Yes | No | Contact, Convert, Lost |
| Requirements | No | Yes | `CONSULTANT` | Yes | Yes | Yes | Yes (Archive) | Fulfill, Match |
| Site Visits | No | Yes | `CONSULTANT` | Yes | Yes | Yes | No | Confirm, Complete, Reschedule, Cancel |
| Follow-ups | No | Yes | `CONSULTANT` | Yes | Yes | Yes | No | Complete, Miss |
| Documents | No | Yes | `CONSULTANT` | Yes | Yes | Yes | Yes (Archive) | Download, Review |
| Verification | No | Yes | `CONSULTANT` | Yes | Yes | No | No | - |
| Notifications | No | Yes | `CONSULTANT` | Yes | No | No | No | Mark Read/Unread |
| Audit Logs | No | Yes | `CONSULTANT` | Yes | No | No | No | - |

## Notes
- **Frontend Check:** Frontend router must redirect non-consultants to `403` or `/login`.
- **Backend Check:** The API will return `403 FORBIDDEN` for any `CONSULTANT` route accessed by a user missing that role.

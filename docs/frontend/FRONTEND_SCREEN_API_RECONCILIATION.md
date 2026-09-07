# FRONTEND SCREEN → API RECONCILIATION

| Screen | Route | Required API | Available API | Actions Supported | Missing/Conflict |
| ------ | ----- | ------------ | ------------- | ----------------- | ---------------- |
| Dashboard | `/dashboard` | Metrics APIs | None explicitly | Basic stats | Must derive stats from `GET` lists `total`. No explicit aggregation APIs. |
| Properties List | `/properties` | `GET /properties` | `GET /properties` | Filter, Sort, Paginate | None |
| Property Detail | `/properties/:id` | `GET /properties/{id}` | `GET /properties/{id}` | Edit, Publish, Pause, Archive | None |
| Property Images | `/properties/:id/images` | `GET`, `POST`, `PATCH`, `DELETE` on images | Supported in Phase 18 | Upload, Reorder, Primary | None |
| Client List | `/clients` | `GET /clients` | `GET /clients` | List, Search | None |
| Client Detail | `/clients/:id` | `GET /clients/{id}` | `GET /clients/{id}` | View, Edit, Archive | None |
| Leads List | `/leads` | `GET /leads` | `GET /leads` | List, Filter | None |
| Leads Detail | `/leads/:id` | `GET /leads/{id}` | `GET /leads/{id}` | Transition Status | None |
| Requirements | `/requirements` | `GET /property-requirements`| `GET /property-requirements`| List, Filter | None |
| Req. Details | `/requirements/:id` | `GET /property-requirements/{id}` | `GET /property-requirements/{id}` | View, Match | None |
| Matching | `/requirements/:id/matches`| `GET .../matches` | `GET .../matches` | View scores/explanations | None |
| Follow-ups | `/follow-ups` | `GET /follow-ups` | `GET /follow-ups` | List | None |
| Follow-up Detail| `/follow-ups/:id` | `GET /follow-ups/{id}` | `GET /follow-ups/{id}` | Complete, Miss | None |
| Verification | `/properties/:id/verification`| `POST` / `GET` | Supported | Run, Summary, Evidence, Actions | None |
| Site Visits | `/site-visits` | `GET /site-visits` | `GET /site-visits` | List | None |
| Visit Detail | `/site-visits/:id` | `GET /site-visits/{id}`| Supported | Confirm, Complete, Reschedule, Cancel | None |
| Documents | `/documents` | `GET /documents` | `GET /documents` | List | None |
| Document Detail | `/documents/:id` | `GET /documents/{id}` | `GET /documents/{id}` | View metadata, Download | Browser must render binary stream. Secure viewer is just a wrapped browser preview. |
| Notifications | `/notifications` | `GET /notifications` | `GET /notifications` | Read/Unread | None |
| Audit Logs | `/audit-logs` | `GET /audit-logs` | `GET /audit-logs` | List, Filter | None |

# FRONTEND ORPHAN API REPORT

This document identifies APIs that exist in the frozen Phase 18 contract but lack clear screen representation in earlier discovery drafts.

| Orphan API Endpoint | Likely Screen/Action | Frontend Inclusion Status | Notes |
|---------------------|----------------------|---------------------------|-------|
| `GET /api/v1/auth/me` | Profile / Settings / Global State | REQUIRED | The frontend must use this to bootstrap the user session and verify the consultant role on page load. |
| `POST /api/v1/notifications/whatsapp-link` | Leads / Clients / Follow-ups | REQUIRED | Allows generating a secure WhatsApp deep link for client communication without exposing direct raw links in the UI. Should be a button on Lead and Client cards. |
| `GET /api/v1/health/live` & `ready` | None (System) | IGNORED | These are for load balancers and Kubernetes/Docker orchestration. The frontend does not need to poll them. |
| `GET /api/v1/properties/{id}/verification/summary` | Property Verification | REQUIRED | The summary view should be part of the initial verification screen before digging into detailed evidence. |

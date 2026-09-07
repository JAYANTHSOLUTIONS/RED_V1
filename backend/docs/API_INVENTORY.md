# API INVENTORY

This document is automatically generated from the FastAPI application routes.

| Method | Path | Summary | Operation ID | Auth | Roles |
|--------|------|---------|--------------|------|-------|
| GET | `/api/v1/health/live` |  | `liveness` | No | - |
| GET | `/api/v1/health/ready` |  | `readiness` | No | - |
| POST | `/api/v1/auth/login` | Authenticate consultant and issue tokens | `login` | No | - |
| POST | `/api/v1/auth/refresh` | Rotate refresh token and issue new access token | `refresh` | No | - |
| POST | `/api/v1/auth/logout` | Revoke refresh token and terminate session | `logout` | No | - |
| GET | `/api/v1/auth/me` | Get current authenticated user profile | `me` | Yes | - |
| GET | `/api/v1/audit-logs` | List audit logs with filtering and pagination | `list_audit_logs` | Yes | CONSULTANT |
| GET | `/api/v1/audit-logs/{log_id}` | Get details of a specific audit log | `get_audit_log` | Yes | CONSULTANT |
| POST | `/api/v1/properties` | Create a new property listing | `create_property` | Yes | CONSULTANT |
| GET | `/api/v1/properties` | List properties with filters and pagination | `list_properties` | Yes | CONSULTANT |
| GET | `/api/v1/properties/{property_id}` | Get property detail for consultant workspace | `get_property` | Yes | CONSULTANT |
| PATCH | `/api/v1/properties/{property_id}` | Update property fields | `update_property` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/publish` | Publish property to public discovery | `publish_property` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/pause` | Pause property listing from public discovery | `pause_property` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/archive` | Soft-delete / archive property | `archive_property` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/mark-sold` | Mark published property as sold | `mark_sold` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/mark-rented` | Mark published property as rented | `mark_rented` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/images` | Add image metadata for a property | `add_image` | Yes | CONSULTANT |
| GET | `/api/v1/properties/{property_id}/images` | List image metadata for a property | `list_images` | Yes | CONSULTANT |
| PATCH | `/api/v1/properties/{property_id}/images/{image_id}` | Update property image metadata (order, primary) | `update_image` | Yes | CONSULTANT |
| DELETE | `/api/v1/properties/{property_id}/images/{image_id}` | Remove property image metadata | `delete_image` | Yes | CONSULTANT |
| GET | `/api/v1/public/properties` | Search and filter published properties | `list_public_properties` | No | - |
| GET | `/api/v1/public/properties/{public_reference}` | View public property details by public reference | `get_public_property` | No | - |
| POST | `/api/v1/clients` | Create a new client profile | `create_client` | Yes | CONSULTANT |
| GET | `/api/v1/clients` | List clients with filters and pagination | `list_clients` | Yes | CONSULTANT |
| GET | `/api/v1/clients/{client_id}` | Get client details with associated leads | `get_client` | Yes | CONSULTANT |
| PATCH | `/api/v1/clients/{client_id}` | Update client details | `update_client` | Yes | CONSULTANT |
| POST | `/api/v1/clients/{client_id}/archive` | Archive client profile (soft-delete) | `archive_client` | Yes | CONSULTANT |
| POST | `/api/v1/leads` | Create a new sales lead | `create_lead` | Yes | CONSULTANT |
| GET | `/api/v1/leads` | List leads with filters and pagination | `list_leads` | Yes | CONSULTANT |
| GET | `/api/v1/leads/{lead_id}` | Get lead details | `get_lead` | Yes | CONSULTANT |
| PATCH | `/api/v1/leads/{lead_id}` | Update non-lifecycle lead fields | `update_lead` | Yes | CONSULTANT |
| POST | `/api/v1/leads/{lead_id}/contact` | Transition lead to CONTACTED | `contact_lead` | Yes | CONSULTANT |
| POST | `/api/v1/leads/{lead_id}/mark-interested` | Transition lead to INTERESTED | `mark_interested` | Yes | CONSULTANT |
| POST | `/api/v1/leads/{lead_id}/site-visit-stage` | Transition lead to SITE_VISIT stage | `schedule_site_visit_stage` | Yes | CONSULTANT |
| POST | `/api/v1/leads/{lead_id}/negotiation` | Transition lead to NEGOTIATION stage | `move_to_negotiation` | Yes | CONSULTANT |
| POST | `/api/v1/leads/{lead_id}/convert` | Transition lead to CONVERTED (terminal) | `convert_lead` | Yes | CONSULTANT |
| POST | `/api/v1/leads/{lead_id}/lost` | Transition lead to LOST with mandatory reason (terminal) | `mark_lost` | Yes | CONSULTANT |
| POST | `/api/v1/property-requirements` | Create a customer property requirement | `create_requirement` | Yes | CONSULTANT |
| GET | `/api/v1/property-requirements` | List property requirements with filters and pagination | `list_requirements` | Yes | CONSULTANT |
| GET | `/api/v1/property-requirements/{requirement_id}` | Get property requirement details | `get_requirement` | Yes | CONSULTANT |
| PATCH | `/api/v1/property-requirements/{requirement_id}` | Update property requirement fields | `update_requirement` | Yes | CONSULTANT |
| POST | `/api/v1/property-requirements/{requirement_id}/fulfill` | Transition requirement to FULFILLED | `fulfill_requirement` | Yes | CONSULTANT |
| POST | `/api/v1/property-requirements/{requirement_id}/cancel` | Transition requirement to CANCELLED | `cancel_requirement` | Yes | CONSULTANT |
| POST | `/api/v1/property-requirements/{requirement_id}/archive` | Soft-archive requirement | `archive_requirement` | Yes | CONSULTANT |
| GET | `/api/v1/property-requirements/{requirement_id}/matches` | Evaluate and return matching properties with explainability | `find_matches` | Yes | CONSULTANT |
| POST | `/api/v1/documents` | Upload a new private document | `upload_document` | Yes | CONSULTANT |
| GET | `/api/v1/documents` | List documents with filtering and pagination | `list_documents` | Yes | CONSULTANT |
| GET | `/api/v1/documents/{document_id}` | Get document metadata | `get_document` | Yes | CONSULTANT |
| GET | `/api/v1/documents/{document_id}/download` | Download private document file | `download_document` | Yes | CONSULTANT |
| PATCH | `/api/v1/documents/{document_id}` | Update document metadata | `update_document` | Yes | CONSULTANT |
| POST | `/api/v1/documents/{document_id}/review` | Transition document status to UNDER_REVIEW | `review_document` | Yes | CONSULTANT |
| POST | `/api/v1/documents/{document_id}/archive` | Soft-archive a document | `archive_document` | Yes | CONSULTANT |
| POST | `/api/v1/properties/{property_id}/verification` | Execute preliminary Tamil Nadu property verification | `run_property_verification` | Yes | CONSULTANT |
| GET | `/api/v1/properties/{property_id}/verification` | Get latest preliminary verification assessment for a property | `get_latest_property_verification` | Yes | CONSULTANT |
| GET | `/api/v1/properties/{property_id}/verification/summary` | Get machine-readable summary metrics for property verification | `get_property_verification_summary` | Yes | CONSULTANT |
| GET | `/api/v1/properties/{property_id}/verification/evidence` | Get detailed documentary evidence intelligence report | `get_property_verification_evidence` | Yes | CONSULTANT |
| GET | `/api/v1/properties/{property_id}/verification/actions` | Get prioritized consultant action recommendations | `get_property_verification_actions` | Yes | CONSULTANT |
| GET | `/api/v1/verification/{verification_id}` |  | `get_verification_by_id` | Yes | CONSULTANT |
| GET | `/api/v1/verifications/{verification_id}` | Get specific verification case by ID | `get_verification_by_id` | Yes | CONSULTANT |
| GET | `/api/v1/verifications` | List verification cases with filtering and pagination | `list_verifications` | Yes | CONSULTANT |
| PATCH | `/api/v1/verifications/{verification_id}` | Update verification case observations or disclaimer acknowledgement | `update_verification` | Yes | CONSULTANT |
| POST | `/api/v1/site-visits/request` | Public / Customer request for a property visit | `request_site_visit` | No | - |
| GET | `/api/v1/site-visits/{visit_id}/public` | Public view of a site visit status | `get_public_site_visit` | No | - |
| POST | `/api/v1/site-visits` | Create a new site visit (Consultant) | `create_site_visit` | Yes | CONSULTANT |
| GET | `/api/v1/site-visits` | List site visits with filters and pagination (Consultant) | `list_site_visits` | Yes | CONSULTANT |
| GET | `/api/v1/site-visits/{visit_id}` | Get full site visit details (Consultant) | `get_site_visit` | Yes | CONSULTANT |
| PATCH | `/api/v1/site-visits/{visit_id}` | Update editable site visit fields (Consultant) | `update_site_visit` | Yes | CONSULTANT |
| POST | `/api/v1/site-visits/{visit_id}/confirm` | Confirm a requested site visit (Consultant) | `confirm_site_visit` | Yes | CONSULTANT |
| POST | `/api/v1/site-visits/{visit_id}/complete` | Mark a confirmed site visit as completed (Consultant) | `complete_site_visit` | Yes | CONSULTANT |
| POST | `/api/v1/site-visits/{visit_id}/cancel` | Cancel a site visit with mandatory reason (Consultant) | `cancel_site_visit` | Yes | CONSULTANT |
| POST | `/api/v1/site-visits/{visit_id}/reschedule` | Reschedule a site visit to a new date/time (Consultant) | `reschedule_site_visit` | Yes | CONSULTANT |
| POST | `/api/v1/follow-ups` | Create a new follow-up task (Consultant) | `create_follow_up` | Yes | CONSULTANT |
| GET | `/api/v1/follow-ups` | List follow-up tasks with filters and pagination (Consultant) | `list_follow_ups` | Yes | CONSULTANT |
| GET | `/api/v1/follow-ups/{follow_up_id}` | Get follow-up task details (Consultant) | `get_follow_up` | Yes | CONSULTANT |
| PATCH | `/api/v1/follow-ups/{follow_up_id}` | Update editable follow-up fields (Consultant) | `update_follow_up` | Yes | CONSULTANT |
| POST | `/api/v1/follow-ups/{follow_up_id}/complete` | Mark follow-up as completed (Consultant) | `complete_follow_up` | Yes | CONSULTANT |
| POST | `/api/v1/follow-ups/{follow_up_id}/miss` | Mark follow-up as missed (Consultant) | `mark_missed_follow_up` | Yes | CONSULTANT |
| GET | `/api/v1/notifications` | List notifications for the current consultant | `list_notifications` | Yes | CONSULTANT |
| GET | `/api/v1/notifications/unread-count` | Get count of unread notifications | `get_unread_count` | Yes | CONSULTANT |
| GET | `/api/v1/notifications/{notification_id}` | Get details of a specific notification | `get_notification` | Yes | CONSULTANT |
| POST | `/api/v1/notifications/{notification_id}/read` | Mark notification as read | `mark_as_read` | Yes | CONSULTANT |
| POST | `/api/v1/notifications/{notification_id}/unread` | Mark notification as unread | `mark_as_unread` | Yes | CONSULTANT |
| POST | `/api/v1/notifications/whatsapp-link` | Generate safe WhatsApp deep link for client communication | `generate_whatsapp_link` | Yes | CONSULTANT |
| GET | `/health` |  | `liveness` | No | - |
| GET | `/ready` |  | `readiness` | No | - |
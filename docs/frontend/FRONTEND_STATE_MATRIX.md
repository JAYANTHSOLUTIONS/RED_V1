# FRONTEND STATE MATRIX

This document defines how the frontend must handle various system and API states.

## General Component States

| State | Visual Representation | Interaction |
|-------|-----------------------|-------------|
| **Normal** | Fully opaque, default colors. | Fully interactive. |
| **Loading (Initial)** | Skeleton placeholders for content areas. | Disabled interactions. |
| **Loading (Mutation)**| Spinner on the primary action button, reduced opacity on form. | Inputs disabled to prevent double submission. |
| **Empty** | Illustration/Icon + "No [Entity] Found" message + CTA to create. | Specific CTA button active. |
| **Success** | Green checkmark, Toast notification ("Saved successfully"). | Auto-dismissal or navigation. |
| **Disabled** | 50% opacity, greyed out, `cursor: not-allowed`. | Clicks ignored. Optional tooltip explaining why. |

## HTTP Error State UX Mapping

| API Status Code | Code String | Frontend UX Strategy | Resolution Path |
|----------------|-------------|----------------------|-----------------|
| **400** | `BAD_REQUEST` | Inline error on specific fields, or general form error banner. | User corrects input. |
| **401** | `UNAUTHORIZED` | Full-screen intercept / Redirect to `/login`. | User logs in or refreshes token transparently in background. |
| **403** | `FORBIDDEN` | Modal or full-page "Access Denied". | Suggest returning to Dashboard. |
| **404** | `NOT_FOUND` | Full-page 404 state with "Resource not found". | Button to return to list view. |
| **409** | `RESOURCE_CONFLICT` | Modal warning ("The record was changed by someone else" or "Double booking"). | Refresh data / discard changes CTA. |
| **409** | `IDEMPOTENCY_PAYLOAD_MISMATCH` | Toast/Banner error indicating the action was already attempted differently. | Retry with correct data. |
| **422** | `VALIDATION_ERROR` | Inline red text under offending form inputs. | User corrects specific fields. |
| **429** | `RATE_LIMITED` | Toast warning: "Too many requests. Please wait." | Wait 1 minute. |
| **500** | `INTERNAL_ERROR` | Toast error: "An unexpected error occurred." (Avoid exposing stack trace). | Retry later. |
| **503** | `SERVICE_UNAVAILABLE`| Full-page maintenance state or Toast. | Retry later. |
| **504** | `GATEWAY_TIMEOUT` | Toast warning: "The service took too long to respond." | Retry operation. |
| **Network Failure** | N/A (Offline) | Global banner "You are currently offline." | Auto-retry when connection restored. |

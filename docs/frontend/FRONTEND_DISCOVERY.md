# RED_V1 FRONTEND DESIGN DISCOVERY & REQUIREMENTS AUDIT

## Executive Summary
This document is the result of a comprehensive frontend-oriented audit of the RED_V1 repository, performed after the API was frozen in Phase 18. The backend provides a robust, fault-tolerant, and secure foundation for a Tamil Nadu Real Estate Consultant Brokerage. The frontend must be designed to match this operational rigor while maintaining a premium, trustworthy visual identity.

## Product Understanding
RED_V1 is not a generic CRM. It is a highly specialized, operational tool for real estate consultants. It handles the entire lifecycle: from property ingestion and TN-specific legal verification, to client matching, secure document handling, site-visit scheduling, and final conversion.

## User Roles
1. **Consultant (Primary):** Authenticated via JWT, holds the `CONSULTANT` role. Needs dense, high-efficiency operational UI.
2. **Public / Client (Secondary):** Unauthenticated. Needs a read-only, sanitized view of published properties and the ability to request site visits.

## Complete Feature Inventory
- Authentication & Session Management
- Dashboard & KPI Tracking
- Property CRUD, Publishing, & Image Metadata
- Client & Lead Pipeline Management
- Property Requirements & AI Matching
- Secure Document Upload & Streaming
- TN Property Verification & Intelligence Reporting
- Site Visit Scheduling & Lifecycle
- Task Follow-ups
- Notification Inbox
- Immutable Audit Logging

## Complete Screen Inventory
*(See `FRONTEND_SCREEN_INVENTORY.md` for full details)*
Total Screens Identified: **26** across 10 domains.

## Navigation Recommendation
**Global Layout:**
- **Left Sidebar (Collapsible):** Dashboard, Properties, Clients, Leads, Requirements, Site Visits, Follow-ups, Documents, Verification Cases.
- **Top Bar:** Global Search, Notifications Badge, Profile/Logout.
- **Mobile:** Bottom Tab Bar for core items (Dashboard, Properties, Visits), Hamburger menu for the rest.

## Design System Requirements
- **Theme:** LIGHT MODE ONLY.
- **Vibe:** Light Editorial Operational Design. Professional, trustworthy, calm.
- **Anti-AI:** Strictly no glowing gradients, glassmorphism, or neon aesthetics despite the backend intelligence features.

## Typography Requirements
- Needs a highly legible sans-serif for operational data density (e.g., Inter, Roboto).
- Consider a refined serif for editorial property headers to convey a premium real estate feel.
- Balanced weights; avoid ultra-thin or ultra-bold extremes.

## Color System Requirements
- Clean whites and cool grays for structure.
- Deep, trustworthy primary brand color (e.g., Slate, Forest Green, or Burgundy).
- Muted semantic colors (Success=Calm Green, Error=Brick Red).

## Component Requirements
*(See `FRONTEND_COMPONENT_INVENTORY.md` for full details)*
Total Core Components: 20+
Total Domain-Specific Components: 8+

## Interaction Requirements
- Optimistic UI updates where safe, but respect the backend's strict validation.
- Clear loading states (spinners on buttons, skeletons for pages) to prevent double-submission.

## State Requirements
*(See `FRONTEND_STATE_MATRIX.md` for full details)*
Every major workflow must account for Initial Loading, Mutation Loading, Empty, Success, Error, and Validation states.

## Error / Status Code UX
- **422 Validation:** Inline field errors.
- **401 Unauthorized:** Transparent refresh or redirect to login.
- **403 Forbidden:** Access Denied modal.
- **409 Conflict:** Idempotency mismatch or concurrency warnings via Toast/Modal.

## Modal / Drawer / Toast Strategy
- **Modals:** Use strictly for destructive/critical confirmations (Archive Property, Mark Lead Lost).
- **Drawers:** Use for complex, non-destructive interactions (Filters, Quick Edit).
- **Toasts:** Non-blocking success/failure feedback.

## Responsive Requirements
- **Desktop:** Maximize data density in tables.
- **Tablet:** Collapse sidebar.
- **Mobile:** Convert tables to cards. Move filters to bottom-sheet drawers. Full functional parity required.

## Accessibility Requirements
- Strict WCAG AA contrast.
- Explicit form labels (no placeholder-only forms).
- Keyboard navigable focus rings.

## Motion / GSAP Opportunities
- **General:** Keep instantaneous or subtle (150ms fade).
- **GSAP:** Reserve for high-value data visualizations: TN Verification Timeline or AI Match Score Gauge. Avoid bouncy spring physics.

## Photography / Static Asset Requirements
- High-quality property photography is central to the editorial feel.
- Need branded empty-state illustrations for "No leads found" or "No documents uploaded." (Professional, not childish).
- High-quality placeholder image required for properties lacking photos.

## API → UI Mapping
*(See `FRONTEND_API_MAP.md` for full details)*
Total Mappings: **30+ endpoints** mapped to specific actions and screens.

## API Contract Blockers
**NO API CONTRACT BLOCKERS FOUND.**
The Phase 18 backend contract is comprehensive, standard-compliant, and fully supports the required frontend workflows.

## Design Risks
- **Data Density vs. Aesthetics:** Balancing the need for dense operational tables with the desire for a clean, premium look.
- **Verification Complexity:** Clearly communicating the nuance between "Preliminary Intelligence" and "Verified Facts" without overwhelming the user.
- **Mobile Parity:** Ensuring complex filters and large property forms remain usable on small screens.

## Recommended Frontend Phase Breakdown
1. **Phase 19a:** Design System & Figma Specification (Colors, Typography, Core Components).
2. **Phase 19b:** Static UI Implementation (React/Vue/Framework of choice) for core flows (Auth, Properties, Clients).
3. **Phase 19c:** API Integration (Wiring up the frozen Phase 18 endpoints).
4. **Phase 19d:** Advanced Workflows (Verification, Matching, File Uploads).
5. **Phase 19e:** Visual Polish, Responsive Audit, & QA.

## Final Recommendations
The frontend design should proceed immediately into Figma/Stitch using the `FRONTEND_FIGMA_STITCH_BRIEF.md`. The design must strictly adhere to the "Light Editorial Operational" constraint and actively resist generic "AI" visual tropes.

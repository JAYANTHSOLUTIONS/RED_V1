# FRONTEND DESIGN BRIEF (FIGMA & STITCH)

**DO NOT START DESIGNING IMMEDIATELY. THIS IS A REQUIREMENTS BRIEF TO GUIDE THE DESIGN PROCESS.**

## 1. Project Context
**Product:** RED_V1 Backend Interface
**Users:** Internal Tamil Nadu Real Estate Consultants (Primary) & Public Buyers (Secondary view-only).
**Backend Status:** API Contract is FROZEN (Phase 18). Do not design features that the API does not support.

## 2. Design Philosophy
**LIGHT EDITORIAL OPERATIONAL DESIGN**
- **Strictly Light Mode.** No dark theme variants.
- Combine the dense, structured usability of high-end operational software (like Linear or Stripe) with the visual elegance of editorial real estate presentations (like Architectural Digest).

## 3. Anti-AI Directives
Although the backend uses advanced algorithms (Matching, TN Verification), the UI must explicitly **hide** the "AI" aesthetic.
- NO purple/blue gradients.
- NO glowing borders or glassmorphism.
- NO sparkle icons.
- Communicate intelligence through extreme clarity, data density, and confident typography, not visual gimmicks.

## 4. Typography Requirements
**Action Required:** Propose a typeface pairing.
- **Criteria:** Needs a highly legible, data-friendly sans-serif for operational UI (tables, forms) and optionally a refined serif for property editorial headers.
- Weights must be balanced; avoid overly thin or overly bold extremes.

## 5. Color Direction
**Action Required:** Define the exact hex codes.
- **Backgrounds:** Clean white and structural cool-grays.
- **Primary:** Needs a trustworthy, premium anchor color (e.g., Slate, Forest, or Wine).
- **Semantic:** Define success/error/warning that are muted and professional, not neon.

## 6. Layout & Navigation
- **Architecture:** Left sidebar for main sections (Dashboard, Properties, Clients, Leads, Site Visits, Documents). Top bar for global actions (Search, Notifications, Profile).
- **Density:** High density for tables and lists.
- **Drawers vs Modals:** Use right-side sliding drawers for complex filters or contextual edits. Reserve centered modals strictly for destructive actions (Delete/Archive).

## 7. Core Deliverables Needed from Design Phase
1. **Design System:** Colors, Typography, Spacing grid, Elevation/Shadows.
2. **Component Library:** Buttons, Inputs, Tables, Badges, Tabs, Property Cards, Verification Timelines, Match Score Indicators.
3. **Key Screens (Desktop & Mobile):**
   - Authentication (Login)
   - Consultant Dashboard
   - Property List (Table/Grid toggle)
   - Property Detail (Editorial view + Operational data + Image Gallery)
   - Lead Kanban / Pipeline
   - TN Verification Report View
   - Document Secure Viewer

## 8. State Requirements
Design must explicitly account for:
- Skeletons / Loading states.
- Empty states (with professional, non-childish illustrations).
- Error states (Inline form validation & global Toasts).

## 9. Imagery
- **Properties:** Assume high-quality, wide-aspect ratio photography.
- **Placeholders:** Design elegant, branded fallback states for properties missing images, rather than generic grey boxes.

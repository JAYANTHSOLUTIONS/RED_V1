# FRONTEND COMPONENT INVENTORY

This document categorizes all reusable UI elements required for the RED_V1 frontend.

## 1. Design-System Primitives
These are the foundational atoms of the application. They are entirely agnostic of the real estate domain.
- **Button:** Primary, Secondary, Ghost, Danger, Icon-only. Includes loading (spinner) state.
- **Input:** Text, Number, Password. Includes validation states (success/error).
- **Textarea:** Multi-line text input for descriptions/notes.
- **Select / Dropdown:** Single-select and multi-select for enums.
- **Checkbox / Radio / Switch:** Boolean toggles.
- **Date/Time Picker:** For site visits and follow-ups.
- **Badge / Tag:** For status indicators (e.g. `PUBLISHED`, `CONTACTED`).
- **Avatar:** User profile representation.
- **Card:** Container for properties, clients, or dashboard widgets.
- **Table:** Data grids with sorting, filtering, and pagination support.
- **Tabs:** View switching (e.g. Property Details vs Images vs Verification).
- **Tooltip & Popover:** Contextual help and secondary actions.
- **Modal:** Destructive actions (Delete, Archive) and critical forms.
- **Drawer / Sheet:** Slide-out panels for filters or quick creation forms.
- **Toast / Alert:** Global feedback for success/failure.
- **Breadcrumb:** Hierarchical navigation.
- **Pagination:** Controls for navigating lists.
- **Skeleton Loader:** Placeholder for loading states.
- **Empty State:** Graphic + text for zero-results.
- **File Uploader:** Drag-and-drop zone with progress tracking.

## 2. Shared Application Components
Reusable compositions that appear across multiple domains but aren't strictly domain entities.
- **Page Header:** Title, breadcrumbs, and primary page actions (e.g., "Create Property").
- **Stat Widget:** Dashboard numeric summary (e.g., "Unread Notifications: 5").
- **Status Timeline:** Vertical steps showing lifecycle (used in Leads, Verification, Site Visits).
- **Data Detail Pair:** Label-Value pairing for read-only details (e.g., `Price: ₹1.5 Cr`).
- **Search & Filter Bar:** Integrated search input with filter dropdowns.
- **Activity Feed List:** For displaying audit logs or recent notifications.

## 3. RED-Specific Domain Components
Highly specialized components tied to specific API domains.
- **Property Card:** Displays thumbnail, title, price, configuration (BHK), and status badge.
- **Property Image Gallery:** Grid/Carousel for viewing property photos, with "make primary" controls.
- **Client Summary Card:** Shows client name, contact info, and active lead count.
- **Lead Kanban Board / Status Pipeline:** Visual representation of lead progression (NEW -> CONVERTED).
- **Match Score Indicator:** Visual ring/gauge showing matching percentage (e.g., 85% match).
- **Verification Evidence Card:** Displays TN property intelligence check results, highlighting discrepancies.
- **Site Visit Calendar/Schedule:** Specialized view of upcoming visits.
- **Document Previewer:** Component for viewing PDFs/Images securely.

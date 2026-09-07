# FRONTEND DESIGN DIRECTION

This document establishes the absolute visual and experiential requirements for the RED_V1 frontend interface. 

## 1. Core Identity & Vibe
**"Light Editorial Operational Design"**
- **Theme:** Strict **Light Theme Only**. No dark mode.
- **Personality:** Trustworthy, professional, calm, information-efficient, premium.
- **Inspiration:** Traditional high-end real estate meets modern Bootstrap-level operational discipline. 
- **What it is NOT:** It is NOT a generic SaaS dashboard. It is NOT a consumer app. It is NOT a sci-fi AI tool.

## 2. Anti-AI Visual Rules
The backend includes advanced AI/Intelligence (TN Verification, Matching), but the frontend must **conceal** this behind a professional facade.
**STRICTLY FORBIDDEN:**
- Purple/Blue "AI" gradients.
- Neon colors or glowing borders on "intelligent" elements.
- "Magic Sparkle" (✨) icons.
- Glassmorphism or excessive background blurring.
- Floating decorative blobs.
- Oversized rounded corners (keep border-radii professional, e.g., 4px - 8px max).
- Heavy drop shadows (use subtle elevation only where functionally necessary, like modals/popovers).

## 3. Typography Philosophy
Typography must carry the UI. 
- **Requirement:** Highly readable, balanced weights, professional.
- **Hierarchy:** Strong contrast between headings (e.g., Property Titles) and dense operational data (e.g., Table rows).
- **Recommendation:** Avoid overly geometric/trendy fonts (like Syne) or overly thin weights. Look towards robust workhorse families (e.g., Inter, Roboto, SF Pro) paired with a high-quality serif for editorial property highlights if appropriate.

## 4. Color Philosophy
- **Backgrounds:** Clean whites (`#FFFFFF`) and very subtle cool grays (`#F8F9FA` or similar) for contrast.
- **Primary Action:** A strong, grounded brand color (e.g., deep slate blue, refined forest green, or authoritative crimson/burgundy depending on brand finalization).
- **Status Colors:** Semantic and subdued. 
  - Success: Calm green (not neon).
  - Warning: Amber/Mustard (not bright yellow).
  - Error: Brick red (not alarm-bell red).
- **Text:** High contrast. Almost-black for primary text (`#1A1A1A`), dark gray for secondary (`#666666`).

## 5. Layout & Information Architecture
- **Operational UI (Tables, Lists, Forms):** Maximize information density. Avoid excessive whitespace that forces unnecessary scrolling. Use strict grid alignments.
- **Editorial UI (Property Detail, Gallery):** Allow photography to breathe. Use asymmetric layouts or magazine-style grids for presenting luxury or high-value properties.
- **Navigation:** Left sidebar for main operational sections (Dashboard, Properties, Clients). Top bar for global search, notifications, and profile.

## 6. Interaction & Motion Philosophy
- **Goal:** Motion should feel invisible but high-quality.
- **Usage:**
  - Micro-interactions on buttons/links (subtle color shifts, no bouncing).
  - Smooth expansion of accordions/drawers.
  - Page transitions should be instantaneous or a very fast fade (150ms).
- **Forbidden:** Spring physics that bounce, slow staggered list reveals, heavy parallax. 
- **GSAP Opportunities:** Retain GSAP strictly for complex, high-value data visualizations (e.g., rendering the Verification Timeline or Match Score gauge).

## 7. Responsive Philosophy
- **Desktop:** Optimized for widescreen operational work (data entry, table scanning).
- **Tablet:** Sidebars collapse to icons.
- **Mobile:** Tables convert to stacked cards. Complex filters move into bottom-sheet drawers. Full operational parity is required (a consultant must be able to do everything on mobile).

## 8. Accessibility Philosophy
- **Contrast:** WCAG AA minimum for all text and interactive elements.
- **Forms:** Explicit labels required for all inputs. No relying solely on placeholders.
- **Focus:** Clear, high-contrast focus rings for keyboard navigation.
- **Error States:** Color must not be the only indicator of an error (use icons and explicit text).

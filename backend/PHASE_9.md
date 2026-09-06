# PHASE 9 — TAMIL NADU PROPERTY INTELLIGENCE & VERIFICATION ENHANCEMENT

## Executive Summary

Phase 9 upgrades the **RED_V1** Preliminary Property Verification system into a production-grade **Tamil Nadu Property Intelligence Engine (v2.0)**. Built specifically for a one-person real-estate brokerage/consultancy in Tamil Nadu, this phase enriches preliminary property verification with deep regional domain knowledge, explainable check outputs, prioritized consultant action steps, document chronology graphing, and machine-readable intelligence summaries.

All additions preserve complete backward compatibility with frozen Phases 1 through 8:
* **Zero Database Schema Changes**: All rich Phase 9 structures are serialized into `verification_cases.consultant_observations`, ensuring zero migration risk.
* **Non-Breaking API Evolution**: All Phase 8 verification endpoints and response envelopes continue to function with enriched metadata, while three new high-performance endpoints provide dedicated views into summary metrics, documentary evidence intelligence, and consultant actions.
* **Statutory Guardrails**: The non-negotiable legal boundary (`PATTA != TITLE`, `EC != ZERO ENCUMBRANCE`, `PLANNING != OWNERSHIP`, `RERA != CLEAR TITLE`) is preserved across every check, explanation, and response envelope.

---

## 1. Architecture Overview

Phase 9 introduces a dedicated domain package `app/domain/tamil_nadu/` and elevates `DeterministicTNVerificationEngine` to version `TN-VERIFICATION-2.0`:

```
backend/
├── app/
│   ├── domain/
│   │   └── tamil_nadu/
│   │       ├── __init__.py
│   │       ├── planning.py       # CMDA vs DTCP jurisdiction rules, basis, & confidence
│   │       ├── measurements.py   # Decimal conversions (cents, grounds, acres, hectares)
│   │       ├── names.py          # Initials ordering, token permutation, Tamil Unicode
│   │       ├── survey.py         # S.No. prefixes, sub-division & parent parcel comparison
│   │       ├── chronology.py     # Document relationship graph, cycle & anomaly detection
│   │       └── actions.py        # Prioritized consultant recommendation generator
│   ├── schemas/
│   │   ├── document.py           # Extended VALID_DOCUMENT_TYPES (FMB, RERA, TAX, etc.)
│   │   └── verification.py       # Phase 9 intelligence models & envelope schemas
│   ├── services/
│   │   ├── tn_verification_engine.py   # Engine v2.0 with 100-point completeness scoring
│   │   ├── verification_providers.py  # TamilNaduVerificationProvider interfaces
│   │   └── verification.py            # Orchestrator with summary/evidence/action getters
│   └── api/v1/
│       └── verification.py       # REST endpoints (/summary, /evidence, /actions)
```

---

## 2. 100-Point Documentary Completeness Scoring Model

Completeness measures **documentary evidence availability**, strictly distinct from legal title certainty.

### Category Weight Allocations (100 Total Base Points)
1. **Property Identity Core (15 pts)**: District, Taluk/Locality, Survey number formatting.
2. **Primary Title Deed (15 pts)**: Uploaded registered deed, registration number, execution date.
3. **Parent Document Chain (15 pts)**: Minimum 30-year lineage, prior link documents provided.
4. **Encumbrance Certificate (15 pts)**: 30+ year search window, verified SRO nil/charge entries.
5. **Patta / Land Records (10 pts)**: Computerized Patta/Chitta matching current survey parcel.
6. **Planning & Layout Approval (10 pts)**: CMDA/DTCP layout approval order or regularization.
7. **TNRERA Registration (5 pts)**: RERA registration for promoter/marketed projects.
8. **Municipal Property Tax (5 pts)**: Recent assessment number and tax payment receipts.
9. **Owner Name Consistency (5 pts)**: Name matching between listing, deed, and Patta.
10. **Survey & Sub-Division Consistency (5 pts)**: Revenue parcel consistency across records.

### Dynamic Non-Applicable Category Scaling
When specific checks are non-applicable (e.g. TNRERA for individual secondary resale, building permission for agricultural land, layout approval for ancestral rural holdings):
$$\text{Final Score} = \text{round}\left(\frac{\text{Earned Points}}{\text{Total Applicable Points}} \times 100\right)$$
Properties are never unfairly penalized for missing permits or registrations that are legally non-applicable.

---

## 3. Planning Jurisdiction Rules (CMDA vs DTCP)

Tamil Nadu planning jurisdiction is resolved deterministically with explicit confidence and statutory basis tracking:
* **CMDA (Chennai Metropolitan Development Authority)**:
  * **Core**: Chennai District (100% CMDA statutory jurisdiction, `HIGH` confidence).
  * **CMA Expanded Localities**: Identified urban clusters (Tambaram, Avadi, Sholinganallur, Porur, Ambattur, Pallavaram, etc., `MEDIUM` confidence).
* **DTCP (Directorate of Town and Country Planning)**:
  * **Statewide**: Coimbatore, Madurai, Salem, Tiruchirappalli, Tirunelveli, Erode, Tiruppur, Vellore, and remaining 33+ Tamil Nadu districts (`HIGH` confidence).
  * **Peripheral CMA Overlap**: Non-core Chengalpattu, Kanchipuram, and Tiruvallur default to DTCP with flag `requires_consultant_confirmation = True`.
* **Fallback**: Unrecognized or missing location returns `UNKNOWN` with `LOW` confidence.

---

## 4. Land Measurement Conversion & Tolerance

All land extent arithmetic is computed using Python's `Decimal` type to avoid floating-point drift:
* **1 Cent** = $435.60\text{ sq.ft}$
* **1 Ground** = $2,400.00\text{ sq.ft}$
* **1 Acre** = $100\text{ cents} = 43,560.00\text{ sq.ft}$
* **1 Hectare** = $2.47105\text{ acres} = 107,639.10\text{ sq.ft}$
* **1 Square Metre** = $10.7639\text{ sq.ft}$
* **Non-Tamil Nadu Units** (marla, bigha, kanal): Evaluated as `UNKNOWN_UNIT` without guessing.

### Tolerance Thresholds
* **Difference $\le 2.0\%$**: `MATCH` (within allowable survey variation).
* **$2.0\% < \text{Difference} \le 10.0\%$**: `REVIEW` (minor discrepancy requiring boundary reconciliation).
* **Difference $> 10.0\%$**: `SIGNIFICANT_MISMATCH` (exceeds legal survey tolerance; flags elevated risk).

---

## 5. Tamil Nadu Naming & Script Handling

* **Initials Normalization**: Handles permutations such as `R. Kumar`, `R Kumar`, `Kumar R`, and `R.KUMAR`.
* **Conflicting Initials Detection**: Accurately flags conflicts (e.g. `R. Kumar` vs `S. Kumar` = `MISMATCH`).
* **Name Expansion**: Distinguishes probable expansions (e.g. `Rajesh Kumar` vs `R. Kumar` = `POSSIBLE_MATCH`).
* **Native Tamil Unicode Preservation**: Full NFC Unicode preservation supports native Tamil script matching (e.g. `'ராமசாமி' == 'ராமசாமி'`), and detects cross-script transliteration requiring verification.

---

## 6. Document Chronology Graph

Constructs a directed acyclic graph (DAG) representing the property's title devolution:
* **Nodes**: Represent Current Title Deed, Parent Documents, and Prior Link Deeds with execution dates.
* **Edges**: Directed relationships (`PARENT_OF`, `DERIVED_FROM`, `REFERENCED_BY`).
* **Cycle Detection**: Immediate detection of self-referencing or circular deed loops (`has_circular_dependency = True`), categorized as `CRITICAL` risk.
* **Future Parent Deed Detection**: Flags anomalies where a parent deed date is recorded after a descendant title deed (`has_future_parent_deed = True`).
* **Devolution Gaps**: Flags unlinked chronological gaps exceeding 30 to 50 years without intermediary link documents.

---

## 7. Evidence Intelligence Layer

Tracks every piece of documentary evidence through 7 discrete lifecycle states:
1. `NOT_PROVIDED`: Required document missing from the property dossier.
2. `PROVIDED`: Uploaded file present in storage.
3. `PARSED`: Metadata (dates, survey numbers, extent, parties) successfully parsed.
4. `CONSISTENT`: Parsed data completely aligns with listing and revenue records.
5. `INCONSISTENT`: Discrepancy identified against listing or other records.
6. `REQUIRES_REVIEW`: Ambiguous finding requiring consultant or advocate scrutiny.
7. `NOT_APPLICABLE`: Document type exempt for the specific property class.

Processing confidence is explicitly tracked as `HIGH`, `MEDIUM`, `LOW`, or `NOT_ASSESSED`.

---

## 8. Provider Interfaces & Offline Defaults

Architectural interfaces in `app/services/verification_providers.py` define the contract for prospective authoritative integrations:
* `TamilNaduVerificationProvider`:
  * `verify_ec(sro_name, survey_number)`
  * `verify_patta(district, taluk, village, survey_number)`
  * `verify_registration(sro_name, document_number, year)`
  * `verify_planning_approval(authority, approval_number)`
  * `verify_rera(rera_registration_number)`
* `DefaultTamilNaduVerificationProvider`:
  * Returns `{"status": "PROVIDER_NOT_CONFIGURED", "message": "..."}` without simulated or fake scraped responses.

---

## 9. API Endpoints Reference

All verification endpoints require JWT authentication and consultant role (`require_roles("CONSULTANT")`).

### 1. Execute Verification
* **`POST /api/v1/properties/{property_id}/verification`**
  * Status: `201 Created`
  * Response: Complete `VerificationCaseResponse` including `checks`, `explanations`, `actions`, `chronology`, `evidence_report`, and `summary`.
  * Audit: Records `action="VERIFICATION_COMPLETED"` with `"engine_version": "TN-VERIFICATION-2.0"`.

### 2. Get Latest Verification Case
* **`GET /api/v1/properties/{property_id}/verification`**
  * Status: `200 OK`
  * Response: Latest `VerificationCaseResponse`.

### 3. Machine-Readable Summary
* **`GET /api/v1/properties/{property_id}/verification/summary`**
  * Status: `200 OK`
  * Response: `VerificationSummaryResponse` containing `overall_risk`, `documentary_completeness_score`, `critical_issue_count`, `high_risk_issue_count`, `missing_document_count`, `review_required_count`, and mandatory legal disclaimer.

### 4. Documentary Evidence Intelligence Report
* **`GET /api/v1/properties/{property_id}/verification/evidence`**
  * Status: `200 OK`
  * Response: `EvidenceIntelligenceReport` detailing `evidence_completeness`, `evidence_quality`, `chronology_integrity`, and item-by-item `evidence_items`.

### 5. Prioritized Consultant Actions
* **`GET /api/v1/properties/{property_id}/verification/actions`**
  * Status: `200 OK`
  * Response: `List[ConsultantActionItemSchema]` ordered by priority (`CRITICAL` $\rightarrow$ `HIGH` $\rightarrow$ `MEDIUM` $\rightarrow$ `LOW`).

### 6. Historical Retrieval & Case Management
* **`GET /api/v1/verifications/{verification_id}`**: Retrieve specific verification case.
* **`GET /api/v1/verifications`**: List historical verification assessments with pagination and filters.
* **`PATCH /api/v1/verifications/{verification_id}`**: Update consultant observations, notes, or status.

---

## 10. Test Suite & Quality Metrics

Phase 9 expanded the test suite to **254 automated tests** with **0 failures** and **0 errors**:

| Test Module | Tests | Focus Area |
|:---|:---:|:---|
| `tests/unit/test_tn_property_intelligence.py` | 24 | Planning rules, measurements, names, survey parcel comparison, chronology graph, actions, providers |
| `tests/unit/test_tn_verification_engine.py` | 10 | Core deterministic evaluation rules and scoring baselines |
| `tests/integration/test_verification_intelligence_api.py` | 6 | Endpoints (`/summary`, `/evidence`, `/actions`), RBAC security, audit logging |
| `tests/integration/test_verification_integration.py` | 5 | Phase 8 baseline execution, property linking, historical queries |
| `tests/integration/test_verification_security.py` | 4 | Security boundaries and role enforcement |
| `tests/failure/test_verification_intelligence_failures.py` | 9 | Circular chain, future parent deed, survey subdivision mismatch, unit fallback, 404 handlers |
| `tests/failure/test_verification_failures.py` | 6 | Phase 8 boundary and 404 failure handling |
| Other Unit, Integration, & Database Tests | 190 | Existing frozen Phase 1–7 test coverage |
| **Total Test Suite** | **254** | **100% Passing (0 failures, 0 errors)** |

### Coverage Metrics
* **Total Application Coverage**: **93%**
* `app/api/v1/verification.py`: **100%**
* `app/schemas/verification.py`: **100%**
* `app/domain/tamil_nadu/actions.py`: **95%**
* `app/domain/tamil_nadu/chronology.py`: **94%**
* `app/domain/tamil_nadu/measurements.py`: **91%**
* `app/domain/tamil_nadu/survey.py`: **95%**
* `app/domain/tamil_nadu/names.py`: **89%**
* `app/domain/tamil_nadu/planning.py`: **86%**

---

## 11. Future Integration Roadmap

When official government credentials or APIs are procured:
1. **AnyTN / e-Services Land Records API**: Plug into `LandRecordProvider.fetch_patta_record` for live computerized Patta verification.
2. **TNREGINET SRO Portal**: Plug into `RegistrationProvider.search_encumbrance` for automated 30-year EC retrieval.
3. **TNRERA Public Register**: Plug into `RERAProvider.verify_rera_registration` for automated promoter project status verification.
4. **CMDA / DTCP Web Portals**: Plug into `PlanningApprovalProvider.verify_layout_approval` for layout regularization status lookups.

All future providers can be injected via dependency injection in `VerificationService` without breaking domain models or API contracts.

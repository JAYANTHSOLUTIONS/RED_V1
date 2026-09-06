# PHASE 8 — TAMIL NADU PRELIMINARY PROPERTY VERIFICATION

## 1. Status
**COMPLETE** — All deterministic preliminary verification checks, Tamil Nadu domain rules, risk calculation engine, completeness scoring, audit logging, and private consultant endpoints have been implemented and verified with 215 passing tests and 93% test coverage across the backend.

---

## 2. Tamil Nadu Domain Coverage
Phase 8 is designed specifically for the Tamil Nadu, India real-estate ecosystem:
- **Registration Department & SRO Ecosystem**: Sub-Registrar Offices (SRO), registered Sale Deeds, Settlement Deeds, Gift Deeds, Partition Deeds, Release Deeds, Power of Attorney (PoA), Encumbrance Certificates (EC), SRO document numbers, registration years, and registered charges/mortgages.
- **Revenue Land Records**: Patta, Chitta, A-Register, Town Survey Land Register (TSLR), Survey Numbers, Sub-Division Numbers, Taluk, Village, District, Land Classification, Extents, and Pattadar Name records.
- **Planning Authorities**:
  - **CMDA** (Chennai Metropolitan Development Authority) for the Chennai Metropolitan Area (Chennai district + specified taluks/localities in Chengalpattu, Kanchipuram, and Tiruvallur).
  - **DTCP** (Directorate of Town and Country Planning) for Tamil Nadu areas outside CMDA jurisdiction.
  - **Local Planning Authorities & Local Bodies** (Greater Chennai Corporation, Municipalities, Town Panchayats, Village Panchayats).
- **Tamil Nadu Real Estate Regulatory Authority (TNRERA)**: Project registrations (`TN/...`), promoter layouts, and multi-unit developments.

---

## 3. Verification Checks
The engine executes 12 deterministic, explainable preliminary verification checks:
1. `PROPERTY_IDENTITY_CORE`: Validates presence and hierarchy of District, Taluk, Village, and Survey identifiers.
2. `SURVEY_NUMBER_CONSISTENCY`: Compares normalized survey and subdivision identifiers across listing, deeds, EC, and land records.
3. `EXTENT_AREA_CHECK`: Converts Tamil Nadu units (cents, grounds, acres, sq.ft) and evaluates measurement discrepancies against legal/survey tolerances.
4. `OWNER_NAME_CONSISTENCY`: Normalizes name tokens and Tamil Nadu initial formatting, matching order variants while strictly flagging distinct initials.
5. `ADDRESS_LOCALITY_CONSISTENCY`: Compares municipal location hierarchy (District, Taluk, Locality, Pincode).
6. `EC_DOCUMENT_AVAILABILITY`: Evaluates Encumbrance Certificate availability, verifies search date range against the standard 13–30 year baseline, and flags adverse mortgage/charge entries.
7. `PATTA_LAND_RECORD_CHECK`: Validates revenue possession records (Patta, Chitta, A-Register, TSLR) and links survey/taluk/owner details.
8. `PLANNING_APPROVAL_CHECK`: Identifies CMDA vs DTCP jurisdiction and validates layout approval or building permission numbers.
9. `TNRERA_REGISTRATION_CHECK`: Evaluates project type applicability and verifies TNRERA registration reference.
10. `PRIMARY_TITLE_DEED_CHECK`: Evaluates presence of foundational registered title instrument (Sale Deed, Settlement, Gift).
11. `PARENT_DOCUMENT_CHAIN_CHECK`: Evaluates presence of prior link documents required for 30-year title tracing.
12. `DOCUMENT_SEQUENCE_CHRONOLOGY`: Validates chronological date sanity (parent document date must precede current title deed date).
13. `MUNICIPAL_TAX_EVIDENCE`: Evaluates municipal property tax assessment receipts as supporting possession evidence.

---

## 4. RERA
### Applicability Engine
- **RERA_APPLICABLE**:
  - Plotted developments / layout projects marketed by promoters/developers.
  - New apartment developments ($\le 3$ years old or under construction).
  - Explicit flag `is_new_project_or_promoter_sale = True`.
- **RERA_NOT_APPLICABLE**:
  - Secondary market resales of individual houses/villas ($> 10$ years old).
  - Agricultural / farmland parcels.
  - Resale individual plots not part of a developer marketing scheme.
- **RERA_UNKNOWN**: Ambiguous listings flagged for consultant review.

### States & Domain Rule
- `RERA_APPLICABLE`, `RERA_NOT_APPLICABLE`, `RERA_INFORMATION_AVAILABLE`, `RERA_INFORMATION_MISSING`, `RERA_REVIEW_REQUIRED`.
- **CRITICAL GUARDRAIL**: `RERA_REGISTERED != TITLE_VERIFIED`. RERA registration certifies promoter regulatory disclosure, not legal ownership.

---

## 5. EC (Encumbrance Certificate)
- Distinguishes:
  - `EC_DOCUMENT_AVAILABLE`
  - `EC_REVIEWED`
  - `NO_RELEVANT_ENTRY_OBSERVED_IN_PROVIDED_EC`
  - `REGISTERED_ENTRY_REQUIRES_REVIEW`
- Checks whether EC covers $\ge 13$ to 30 years. Search spans under 13 years flag `INCOMPLETE_EC_INFORMATION` (MEDIUM risk).
- Active charges, mortgages, or adverse entries flag `REGISTERED_ENTRY_REQUIRES_REVIEW` (HIGH risk).
- **CRITICAL GUARDRAIL**: `EC_AVAILABLE != ZERO_ENCUMBRANCES`. An uploaded EC is evidence supplied; it does not guarantee freedom from unregistered or court-ordered encumbrances.

---

## 6. Patta / Land Records
- Supported records: Patta, Chitta, A-Register, TSLR (Town Survey Land Register).
- For landed properties (`PLOT`, `LAND`, `AGRICULTURAL`), missing Patta flags `CRITICAL_REQUIRED_EVIDENCE_MISSING` (HIGH risk).
- **CRITICAL GUARDRAIL**: `PATTA_AVAILABLE != TITLE_CONFIRMED`. Under Tamil Nadu law, Patta is an administrative record of possession and revenue liability, not conclusive proof of legal title.

---

## 7. Survey / Subdivision
- Prefix normalization: removes `S.No.`, `S.F.No.`, `R.S.No.`, `T.S.No.`, `Survey No:`.
- Whitespace and delimiter normalization: `124 / 3 A` $\rightarrow$ `124/3A`.
- Sub-division precision:
  - `124/3A` vs `124/3A` $\rightarrow$ `MATCH`.
  - `124/3` vs `124/3A` $\rightarrow$ `REVIEW` (parent parcel vs subdivided parcel).
  - `124/3A` vs `124/3B` $\rightarrow$ `MISMATCH` (`PROPERTY_IDENTIFIER_MISMATCH`, HIGH risk).

---

## 8. Ownership / Parent Documents
- Evaluates primary title deed (Sale Deed, Settlement Deed, Gift Deed, Partition Deed, Release Deed).
- Evaluates prior link / parent documents: checks if parent deed date precedes current deed date. If parent deed date is later than current deed date, flags `DOCUMENT_SEQUENCE_REVIEW` (MEDIUM risk).
- Missing parent documents flag `MISSING_SUPPORTING_DOCUMENT` (MEDIUM risk).

---

## 9. CMDA / DTCP / Planning Authorities
- **Jurisdiction Detection**:
  - Chennai district + CMA expanded localities (Tambaram, Avadi, Pallavaram, Porur, Ambattur, Poonamallee, Sholinganallur, etc.) $\rightarrow$ `CMDA`.
  - Other Tamil Nadu districts (Coimbatore, Madurai, Salem, Trichy, Tirunelveli, Erode, Vellore, etc.) $\rightarrow$ `DTCP`.
- **Layout Checking**: Plotted properties without layout approval flag `INCOMPLETE_APPROVAL_INFORMATION` (MEDIUM risk) due to Tamil Nadu Section 22A registration curbs on unapproved plots.
- **CRITICAL GUARDRAIL**: `PLANNING_APPROVAL != OWNERSHIP_CONFIRMED`.

---

## 10. Risk Engine Rules
### HIGH Risk
- `OWNER_INFORMATION_MISMATCH`: Conflicting owner name or distinct initials (`R. Kumar` vs `S. Kumar`).
- `PROPERTY_IDENTIFIER_MISMATCH`: Different survey sub-divisions (`124/3A` vs `124/3B`).
- `SIGNIFICANT_EXTENT_MISMATCH`: Area discrepancy $> 10\%$.
- `REGISTERED_ENTRY_REQUIRES_REVIEW`: Visible registered mortgage, charge, or adverse entry in EC.
- `CRITICAL_REQUIRED_EVIDENCE_MISSING`: Missing title deed or missing survey number on landed parcel.

### MEDIUM Risk
- `MISSING_SUPPORTING_DOCUMENT`: Missing parent document or unuploaded EC.
- `ADDRESS_MISMATCH`: Inconsistent district, locality, or pincode.
- `INCOMPLETE_EC_INFORMATION`: EC search duration $< 13$ years or dates unspecified.
- `INCOMPLETE_APPROVAL_INFORMATION`: Missing layout approval on plotted property.
- `RERA_INFORMATION_MISSING_WHERE_APPLICABLE`: Promoter project missing TNRERA registration.
- `DOCUMENT_SEQUENCE_REVIEW`: Chronological anomaly between parent and current title deeds.

### LOW / INFO Risk
- `NO_OBVIOUS_INCONSISTENCY`: Expected documents present without conflicting identifiers.
- `EXPECTED_EVIDENCE_AVAILABLE`: High documentary completeness.

---

## 11. API Endpoints
All endpoints are gated by `require_roles("CONSULTANT")`:
- `POST /api/v1/properties/{property_id}/verification`: Trigger deterministic preliminary verification.
- `GET /api/v1/properties/{property_id}/verification`: Get latest verification assessment for property.
- `GET /api/v1/verifications/{verification_id}`: Get specific verification assessment by UUID.
- `GET /api/v1/verifications`: List historical verification assessments with pagination and filters.
- `PATCH /api/v1/verifications/{verification_id}`: Update consultant observations or acknowledge disclaimer.

---

## 12. Database Schema
- Utilizes existing `verification_cases` and `verification_items` tables from Phase 2.
- `verification_cases`:
  - `id`: UUID (PK)
  - `property_id`: UUID (FK `properties.id`, RESTRICT, indexed)
  - `status`: String(30), default "INCOMPLETE" (indexed)
  - `consultant_observations`: Text (stores structured evaluation metadata: risk level, completeness, risk flags, missing info)
  - `missing_documents_notes`: Text
  - `disclaimer_acknowledged`: Boolean
  - `reviewed_by`: UUID (FK `users.id`, nullable)
  - `completed_at`: DateTime(timezone=True), nullable
- `verification_items`:
  - `id`: UUID (PK)
  - `case_id`: UUID (FK `verification_cases.id`, CASCADE, indexed)
  - `checklist_code`: String(50)
  - `item_name`: String(255)
  - `is_present`: Boolean
  - `status`: String(30)
  - `notes`: Text
  - `document_id`: UUID (FK `documents.id`, SET NULL, nullable, indexed)
- **Zero migration drift**: 100% backward compatible with `0001_phase2_initial_schema (head)`.

---

## 13. Security
- **Authentication & RBAC**: All verification routes strictly require `CONSULTANT` role.
- **Tamper Resistance**: The client cannot submit `verified=true` or force `risk_level="LOW"`. All statuses and risk scores are computed server-side.
- **Document Leakage Protection**: Evidence items return secure document UUIDs and filenames; raw storage paths (`storage_key`, `C:\`, `s3://`) are never exposed.
- **IDOR Protection**: Property existence and soft-archival status are validated before execution.

---

## 14. Testing Results
- **Phase 8 Unit Tests**: 10 passed (`test_tn_verification_engine.py`).
- **Phase 8 Integration Tests**: 5 passed (`test_verification_integration.py`).
- **Phase 8 Security Tests**: 4 passed (`test_verification_security.py`).
- **Phase 8 Failure Tests**: 6 passed (`test_verification_failures.py`).
- **Total Test Suite**: **215 passed**, 0 failed, 0 errors in 129.29s.
- **Test Coverage**: **93% overall coverage** across the backend codebase.

---

## 15. Regression Confirmation
- **Phase 1 (Foundation)**: All middleware, configuration, and exception handling tests pass.
- **Phase 2 (Database & Alembic)**: `test_alembic_upgrade_downgrade_cycle` passed without error.
- **Phase 3 (Auth & Security)**: JWT token generation, password hashing, and role checks pass.
- **Phase 4 (Property Management)**: Property lifecycle, public references, and search pass.
- **Phase 5 (Clients & Leads)**: Client management, leads, enquiries, and site visits pass.
- **Phase 6 (Requirements & Matching)**: Property requirements and deterministic matching pass.
- **Phase 7 (Document Management)**: Document upload, validation, streaming download, and archival pass.

---

## 16. Files Changed & Created
- `app/schemas/document.py` (Modified: added `TSLR`, `CMDA_APPROVAL`, `DTCP_APPROVAL`, `ENCUMBRANCE_CERTIFICATE`).
- `app/schemas/verification.py` (New: verification schemas, enums, input models, response envelopes).
- `app/services/verification_providers.py` (New: abstract provider interfaces and offline provider).
- `app/services/tn_verification_engine.py` (New: deterministic Tamil Nadu verification rules engine).
- `app/repositories/verification.py` (New: verification database repository with eager loading).
- `app/services/verification.py` (New: verification service with transactional audit logging).
- `app/api/v1/verification.py` (New: verification API endpoints).
- `app/api/v1/router.py` (Modified: registered verification router).
- `tests/unit/test_tn_verification_engine.py` (New: unit tests for engine).
- `tests/integration/test_verification_integration.py` (New: integration tests for API).
- `tests/integration/test_verification_security.py` (New: security and RBAC tests).
- `tests/failure/test_verification_failures.py` (New: failure mode and boundary tests).
- `PHASE_8.md` (New: documentation).

---

## 17. Dependencies
- Zero new third-party dependencies added. Uses existing standard library (`re`, `datetime`, `decimal`, `json`) and existing project dependencies (FastAPI, SQLAlchemy 2, Pydantic v2).

---

## 18. Limitations
- **Documentary Evidence Only**: The preliminary assessment is based solely on documents and metadata supplied to RED_V1.
- **No Live Government Verification**: Does not query live TNREGINET or AnyTN portals directly (offline provider pattern in place for future phase integration).
- **Not a Title Opinion**: Does not substitute for an advocate's legal opinion or encumbrance search conducted directly at the relevant Sub-Registrar Office.

---

## 19. Mandatory Legal Disclaimer
Included in every verification assessment response and documentation:
> *"This is a preliminary property verification assessment based on the information and documentary evidence available to RED_V1. It does not constitute legal title verification, certification of ownership, confirmation of document authenticity, or a guarantee that the property is free from encumbrances, disputes, planning violations, or other legal issues. Independent verification by the appropriate authorities and qualified legal professionals may be required."*

---

## 20. Future Work
- **OCR & Tamil Document Extraction**: Extract survey numbers, document numbers, and schedules from Tamil script sale deeds and Patta copies.
- **Authoritative Provider Integrations**: Implement live TNREGINET EC verification and AnyTN e-Services Patta verification when official API credentials become available.
- **GIS / FMB Mapping**: Match Field Measurement Book (FMB) sketch coordinates with survey boundary maps.
- **Legal Advocate Review Workflow**: Enable empanelled legal counsels to append formal title certificates to verified cases.

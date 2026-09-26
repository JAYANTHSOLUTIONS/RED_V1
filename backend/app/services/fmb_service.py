"""FMB Map Generation Service.

Provides:
- GIS code construction from property district/taluk/village
- CollabLand government API integration (server-side only)
- Base64 PDF decoding and PDF magic byte validation
- Duplicate FMB detection within the Document Vault
- Save-to-vault integration using existing DocumentService

No raw government API details, credentials, or response data are
ever forwarded to the frontend in raw form.
"""
import base64
import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    GatewayTimeoutError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationAppError,
)
from app.db.session import transaction
from app.models.document import Document
from app.repositories.audit import AuditRepository
from app.repositories.document import DocumentRepository
from app.repositories.property import PropertyRepository
from app.storage import get_storage_backend

# ---------------------------------------------------------------------------
# CollabLand endpoint (server-side only — never exposed to frontend)
# ---------------------------------------------------------------------------
_COLLABLAND_URL = "https://collabland-tn.gov.in/rest/Collabland/FMBMapServicePDF"
_REQUEST_TIMEOUT_SECONDS = 30
_TN_STATE_CODE = "33"

# ---------------------------------------------------------------------------
# Tamil Nadu district → 2-digit code mapping
# Source: Government of Tamil Nadu revenue district codes (ISO 3166-2:IN-TN)
# ---------------------------------------------------------------------------
_DISTRICT_CODES: Dict[str, str] = {
    "ariyalur": "01",
    "chengalpattu": "02",
    "chennai": "03",
    "coimbatore": "04",
    "cuddalore": "05",
    "dharmapuri": "06",
    "dindigul": "07",
    "erode": "08",
    "kallakurichi": "09",
    "kanchipuram": "10",
    "kanyakumari": "11",
    "karur": "12",
    "krishnagiri": "13",
    "madurai": "14",
    "mayiladuthurai": "15",
    "nagapattinam": "16",
    "namakkal": "17",
    "nilgiris": "18",
    "perambalur": "19",
    "pudukkottai": "20",
    "ramanathapuram": "21",
    "ranipet": "22",
    "salem": "23",
    "sivaganga": "24",
    "tenkasi": "25",
    "thanjavur": "26",
    "theni": "27",
    "thoothukudi": "28",
    "thirunelveli": "29",
    "tirupathur": "30",
    "tiruppur": "31",
    "tiruvallur": "32",
    "tiruvannamalai": "33",
    "tiruvarur": "34",
    "trichy": "35",
    "tiruchirappalli": "35",
    "vellore": "36",
    "viluppuram": "37",
    "virudhunagar": "38",
    # Common abbreviations / alternate spellings
    "kancheepuram": "10",
    "thiruvalur": "32",
    "tanjore": "26",
    "tirunelveli": "29",
    "thiruchirapalli": "35",
    "thiruvarur": "34",
}


def _normalize(text: str) -> str:
    """Lowercase + strip for fuzzy lookup."""
    return (text or "").strip().lower()


def resolve_district_code(district: str) -> Optional[str]:
    """Map a district name to its 2-digit TN revenue code.

    Tries exact match first, then substring containment.
    """
    norm = _normalize(district)
    if not norm:
        return None
    if norm in _DISTRICT_CODES:
        return _DISTRICT_CODES[norm]
    # Substring fallback
    for key, code in _DISTRICT_CODES.items():
        if key in norm or norm in key:
            return code
    return None


def build_gis_code(
    district: str,
    taluk: str,
    village: str,
    survey_number: str,
) -> str:
    """Construct the CollabLand GIS code.

    Format (per CollabLand): {state(2)}{district(2)}{taluk(3)}{village(3)}{survey}
    When numeric taluk/village codes are unavailable, a best-effort
    padded representation of the names is used.

    Raises ValidationAppError if the district cannot be resolved.
    """
    district_code = resolve_district_code(district)
    if not district_code:
        raise ValidationAppError(
            f"FMB map could not be generated. The district '{district}' "
            "is not recognized. Please verify the property's location details."
        )

    # Taluk code: use first 3 characters of normalized name, zero-padded
    taluk_code = _normalize(taluk)[:3].ljust(3, "0")
    # Village code: use first 3 characters of normalized name, zero-padded
    village_code = _normalize(village)[:3].ljust(3, "0")
    # Clean survey number (digits and slashes only, strip leading zeros)
    survey_clean = survey_number.strip().lstrip("0") or survey_number.strip()

    return f"{_TN_STATE_CODE}{district_code}{taluk_code}{village_code}{survey_clean}"


def _validate_pdf_bytes(data: bytes) -> None:
    """Verify magic bytes confirm this is a PDF file."""
    if not data.startswith(b"%PDF-"):
        raise ValidationAppError(
            "FMB map could not be generated. The generated file was not a valid PDF."
        )


def _decode_pdf_base64(encoded: str) -> bytes:
    """Decode Base64 PDF content, raising a clean error on failure."""
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except Exception:
        raise ValidationAppError(
            "FMB map could not be generated. The service returned an invalid response."
        )
    return decoded


# ---------------------------------------------------------------------------
# CollabLand API Integration
# ---------------------------------------------------------------------------

async def call_collabland_fmb(
    gis_code: str,
    subdivision_number: Optional[str] = None,
    scale: int = 0,
    width: int = 500,
    height: int = 500,
) -> Dict[str, Any]:
    """POST to CollabLand FMB Map Service and return the parsed JSON response.

    Raises:
        GatewayTimeoutError: if the upstream service times out
        ServiceUnavailableError: on HTTP errors
        ValidationAppError: on empty/invalid JSON or missing 'success' field
    """
    payload = {
        "state": "33",
        "giscode": gis_code,
        "plotno": subdivision_number or "",
        "scale": scale,
        "width": width,
        "height": height,
    }

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS, verify=False) as client:
            response = await client.post(_COLLABLAND_URL, data=payload)
    except httpx.TimeoutException:
        raise GatewayTimeoutError(
            "FMB map service is temporarily unavailable. Please try again shortly."
        )
    except Exception:
        raise ServiceUnavailableError(
            "FMB map could not be generated. Please verify the property's survey and location details."
        )

    if not response.is_success:
        raise ServiceUnavailableError(
            "FMB map could not be generated. Please verify the property's survey and location details."
        )

    try:
        result = response.json()
    except Exception:
        raise ValidationAppError(
            "FMB map could not be generated. The service returned an unexpected response."
        )

    if not isinstance(result, dict):
        raise ValidationAppError(
            "FMB map could not be generated. The service returned an unexpected response format."
        )

    # CollabLand returns {"success": True, "data": "<base64>"} or {"success": False, "message": "..."}
    if not result.get("success", False):
        msg = result.get("message") or result.get("msg") or "No records found."
        raise ValidationAppError(
            f"FMB map could not be generated. The government service responded: {msg}"
        )

    return result


# ---------------------------------------------------------------------------
# Duplicate Detection
# ---------------------------------------------------------------------------

async def find_existing_fmb_doc(
    session: AsyncSession,
    property_id: uuid.UUID,
    survey_number: str,
    subdivision_number: Optional[str],
) -> Optional[Document]:
    """Check if an active FMB document with the same survey/subdivision already exists
    in the vault for this property.

    We store a fingerprint in the `notes` field:
      fmb_map:{survey_no}:{subdivision_no}
    """
    fingerprint = _make_fingerprint(survey_number, subdivision_number)
    stmt = select(Document).where(
        Document.property_id == property_id,
        Document.document_type == "FMB",
        Document.notes.ilike(f"%{fingerprint}%"),
        Document.is_archived.is_(False),
    )
    result = await session.execute(stmt)
    return result.scalars().first()


def _make_fingerprint(survey_number: str, subdivision_number: Optional[str]) -> str:
    """Stable fingerprint string embedded in the document's notes field."""
    subdiv = (subdivision_number or "").strip()
    return f"fmb_map:{survey_number.strip()}:{subdiv}"


# ---------------------------------------------------------------------------
# Main service functions
# ---------------------------------------------------------------------------

async def generate_fmb_map(
    session: AsyncSession,
    property_id: uuid.UUID,
    survey_number: str,
    subdivision_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch property location, build GIS code, call CollabLand, decode and validate PDF.

    Returns a dict containing `pdf_base64`, `filename`, `file_size`, `gis_code`,
    and echoed location/survey metadata.

    Raises appropriate AppException subclasses on all failure paths.
    """
    prop_repo = PropertyRepository()
    prop = await prop_repo.get_by_id(session, property_id)
    if prop is None:
        raise NotFoundError("Property not found.")
    if prop.is_archived:
        raise ValidationAppError("Cannot generate FMB map for an archived property.")

    district = (prop.district or "").strip()
    taluk = (prop.taluk or "").strip()
    locality = (prop.locality or "").strip()  # fallback village name

    if not district:
        raise ValidationAppError(
            "FMB map could not be generated. The property's district is missing. "
            "Please update the property's location details."
        )

    # Use taluk as the village if locality looks like a survey village
    village = locality or taluk

    # Build GIS code (raises ValidationAppError on unmapped district)
    gis_code = build_gis_code(district, taluk, village, survey_number)

    # Call CollabLand
    result = await call_collabland_fmb(
        gis_code=gis_code,
        subdivision_number=subdivision_number,
    )

    # The PDF data may be under "data", "pdf", or "pdfdata" keys
    raw_b64 = (
        result.get("data")
        or result.get("pdf")
        or result.get("pdfdata")
        or ""
    )
    if not raw_b64:
        raise ValidationAppError(
            "FMB map could not be generated. The service returned an empty document."
        )

    pdf_bytes = _decode_pdf_base64(raw_b64)
    _validate_pdf_bytes(pdf_bytes)

    subdiv_part = f"-{subdivision_number}" if subdivision_number else ""
    filename = f"FMB-{survey_number}{subdiv_part}-{district}.pdf"

    return {
        "pdf_base64": raw_b64,
        "filename": filename,
        "file_size": len(pdf_bytes),
        "district": district,
        "taluk": taluk or None,
        "village": village or None,
        "survey_number": survey_number,
        "subdivision_number": subdivision_number or None,
        "gis_code": gis_code,
        "scale": 0,
        "source": "CollabLand",
    }


async def save_fmb_to_vault(
    session: AsyncSession,
    property_id: uuid.UUID,
    survey_number: str,
    subdivision_number: Optional[str],
    pdf_base64: str,
    filename: str,
    actor_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
    force_duplicate: bool = False,
) -> Tuple[Document, bool]:
    """Decode, validate, and persist a generated FMB map PDF to the Document Vault.

    Returns (Document, duplicate_existed).

    Raises:
        ConflictError: if a duplicate exists and force_duplicate is False
    """
    from app.core.exceptions import ConflictError

    # Duplicate check
    existing = await find_existing_fmb_doc(session, property_id, survey_number, subdivision_number)
    duplicate_existed = existing is not None

    if duplicate_existed and not force_duplicate:
        raise ConflictError(
            "An FMB map already exists for this survey number. "
            "Use force_duplicate=true to save a new copy."
        )

    # Decode + validate PDF
    pdf_bytes = _decode_pdf_base64(pdf_base64)
    _validate_pdf_bytes(pdf_bytes)

    # Generate storage key
    doc_uuid = uuid.uuid4().hex
    storage_key = f"properties/{property_id}/documents/{doc_uuid}.pdf"

    # Persist binary to storage backend
    from app.core.config import get_settings
    storage = get_storage_backend(get_settings())
    try:
        await storage.store(storage_key, pdf_bytes, "application/pdf")
    except Exception as exc:
        from app.core.exceptions import StorageError
        raise StorageError(
            "FMB document storage is temporarily unavailable. Please try again later."
        ) from exc

    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    fingerprint = _make_fingerprint(survey_number, subdivision_number)
    notes = (
        f"{fingerprint} | Generated from CollabLand FMB Map Service | "
        f"Survey: {survey_number} | Subdivision: {subdivision_number or 'N/A'}"
    )

    doc_repo = DocumentRepository()
    audit_repo = AuditRepository()

    try:
        async with transaction(session):
            doc = Document(
                property_id=property_id,
                document_type="FMB",
                storage_key=storage_key,
                original_filename=filename,
                mime_type="application/pdf",
                file_size=len(pdf_bytes),
                checksum=checksum,
                status="UPLOADED",
                notes=notes,
                is_archived=False,
                uploaded_by=actor_id,
            )
            await doc_repo.create(session, doc)

            await audit_repo.record(
                session,
                action="FMB_MAP_GENERATED",
                entity_type="DOCUMENT",
                entity_id=doc.id,
                actor_id=actor_id,
                change_diff={
                    "property_id": str(property_id),
                    "document_type": "FMB",
                    "original_filename": filename,
                    "file_size": len(pdf_bytes),
                    "survey_number": survey_number,
                    "subdivision_number": subdivision_number or "",
                    "source": "CollabLand",
                    "duplicate_existed": duplicate_existed,
                    "result": "success",
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
    except Exception:
        try:
            await storage.delete(storage_key)
        except Exception:
            pass
        raise

    return doc, duplicate_existed

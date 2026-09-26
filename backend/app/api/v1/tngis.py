"""API endpoints for TNGIS Land & Survey Data Extraction, Verification, and Persistence.

Provides lookup mapping against the TNGIS scraper dataset, structured table normalization,
and selective saving to new or existing property records in the database.
"""
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.db.session import transaction
from app.models.property import Property
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.property import PropertyRepository
from app.schemas.common import SuccessEnvelope, success_envelope
from app.schemas.tngis import (
    TngisContinueRequest,
    TngisLookupRequest,
    TngisLookupResponse,
    TngisSaveRequest,
    TngisScrapeStartRequest,
    TngisScrapeStatusResponse,
)
from app.services.tngis_parser import (
    continue_interactive_scrape,
    get_interactive_scrape_status,
    load_tngis_results,
    run_live_tngis_scraper,
    start_interactive_scrape,
)

router = APIRouter(prefix="/tngis", tags=["TNGIS Land & Survey Records"])
property_repo = PropertyRepository()
audit_repo = AuditRepository()


@router.post(
    "/lookup",
    response_model=SuccessEnvelope[TngisLookupResponse],
    summary="Search & extract TNGIS land, owner, and guideline details",
)
async def lookup_tngis_records(
    payload: TngisLookupRequest,
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[TngisLookupResponse]:
    """Retrieve structured revenue records, owners, guideline valuation, and GPS vertices.

    Maps input parameters (District, Taluk, Village, Survey No, Subdivision) to TNGIS extraction.
    If live_scrape is True, runs tngis_scraper.py live against the TNGIS portal.
    """
    if payload.live_scrape:
        results = await run_live_tngis_scraper(
            district=payload.district,
            taluk=payload.taluk,
            village=payload.village,
            survey_number=payload.survey_number,
            subdivision=payload.subdivision,
            area_type=payload.area_type,
        )
    else:
        search_overrides = {
            "district": payload.district,
            "taluk": payload.taluk,
            "village": payload.village,
            "survey_number": payload.survey_number,
            "subdivision": payload.subdivision or "",
            "area_type": payload.area_type,
        }
        results = load_tngis_results(search_params=search_overrides)

    return success_envelope(
        data=results,
        message=results.message or f"TNGIS survey details extracted for Survey {payload.survey_number}/{payload.subdivision or ''} in {payload.village}.",
    )


@router.get(
    "/sample",
    response_model=SuccessEnvelope[TngisLookupResponse],
    summary="Get current extracted sample results from tngis_map_results.txt",
)
async def get_tngis_sample(
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[TngisLookupResponse]:
    """Return the raw and normalized dataset currently stored in tngis_map_results.txt."""
    results = load_tngis_results()
    return success_envelope(data=results)


@router.post(
    "/scrape/start",
    response_model=SuccessEnvelope[TngisScrapeStatusResponse],
    summary="Start interactive TNGIS live scraper session",
)
async def start_tngis_scrape(
    payload: TngisScrapeStartRequest,
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[TngisScrapeStatusResponse]:
    """Launch tngis_scraper.py and return tracking session ID."""
    session_id = start_interactive_scrape(
        district=payload.district,
        taluk=payload.taluk,
        village=payload.village,
        survey_number=payload.survey_number,
        subdivision=payload.subdivision,
        area_type=payload.area_type,
        headless=payload.headless,
    )
    status_resp = get_interactive_scrape_status(session_id)
    return success_envelope(data=status_resp, message="TNGIS scraper session initialized.")


@router.get(
    "/scrape/status/{session_id}",
    response_model=SuccessEnvelope[TngisScrapeStatusResponse],
    summary="Get status of an active TNGIS scraper session",
)
async def get_tngis_scrape_status(
    session_id: str,
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[TngisScrapeStatusResponse]:
    """Check live status of the scraper process (waiting for pin, extracting, completed, etc.)."""
    status_resp = get_interactive_scrape_status(session_id)
    return success_envelope(data=status_resp)


@router.post(
    "/scrape/continue/{session_id}",
    response_model=SuccessEnvelope[Dict[str, Any]],
    summary="Signal scraper to proceed with extraction after map pin",
)
async def continue_tngis_scrape(
    session_id: str,
    payload: Optional[TngisContinueRequest] = None,
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[Dict[str, Any]]:
    """Signal the waiting scraper process that the user has pinned the parcel point."""
    x_ratio = payload.x_ratio if payload else 0.5
    y_ratio = payload.y_ratio if payload else 0.5
    success = continue_interactive_scrape(session_id, x_ratio=x_ratio, y_ratio=y_ratio)
    return success_envelope(
        data={"session_id": session_id, "resumed": success, "x_ratio": x_ratio, "y_ratio": y_ratio},
        message="Scraper extraction signal sent.",
    )


@router.post(
    "/save",
    response_model=SuccessEnvelope[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Save verified/edited TNGIS records to database",
)
async def save_tngis_records(
    payload: TngisSaveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[Dict[str, Any]]:
    """Persist verified TNGIS land records into the database.

    Either updates an existing property with survey coordinates, patta number, and owner details,
    or creates a new property listing draft.
    """
    actor_id = current_user.id
    ip_address = get_ip_address(request)
    correlation_id = get_request_id(request)

    owner_str = ", ".join([f"{o.owner} ({o.relation or 'Owner'} of {o.relative or 'Self'})" for o in payload.owners]) if payload.owners else None
    primary_owner_name = payload.owners[0].owner if payload.owners else None

    # Format structured note
    revenue_notes = (
        f"[TNGIS Verified Revenue Record]\n"
        f"District: {payload.district} | Taluk: {payload.taluk} | Village: {payload.village}\n"
        f"Survey No: {payload.survey_number} | Subdivision: {payload.subdivision or '-'}\n"
        f"Patta No: {payload.patta_number or '-'} | Land Type: {payload.land_type or '-'} ({payload.land_type_detail or '-'})\n"
        f"Extent: {payload.extent_hectares or '0'} Hectares, {payload.extent_ares or '0'} Ares\n"
        f"Assessment Tax: ₹{payload.total_tax or '0.00'} | Guideline Valuation: {payload.guideline_rate or '-'}\n"
        f"Registered Owners: {owner_str or 'None'}\n"
        f"Pinned GPS: {payload.latitude or '-'}, {payload.longitude or '-'}\n"
    )
    if payload.vertices:
        revenue_notes += f"Boundary Vertices ({len(payload.vertices)}):\nVertex | Latitude | Longitude\n"
        for v in payload.vertices:
            revenue_notes += f"{v.vertex_number} | {v.latitude} | {v.longitude}\n"
    if payload.consultant_notes:
        revenue_notes += f"Consultant Remarks: {payload.consultant_notes}\n"

    # Case 1: Update Existing Property
    if payload.property_id:
        async with transaction(session):
            prop = await property_repo.get_by_id(session, payload.property_id)
            if not prop:
                return success_envelope(
                    data={"saved": False, "error": "Target property not found"},
                    message="Property not found.",
                )

            # Update property fields with verified revenue information
            prop.district = payload.district
            prop.taluk = payload.taluk
            prop.locality = payload.village
            if payload.latitude is not None:
                prop.latitude = Decimal(str(payload.latitude))
            if payload.longitude is not None:
                prop.longitude = Decimal(str(payload.longitude))
            if payload.google_maps_url:
                prop.google_maps_url = payload.google_maps_url
            if primary_owner_name and not prop.owner_name:
                prop.owner_name = primary_owner_name

            # Append to internal notes
            existing_notes = prop.internal_notes or ""
            if "[TNGIS Verified Revenue Record]" not in existing_notes:
                prop.internal_notes = f"{existing_notes}\n\n{revenue_notes}".strip()
            else:
                # Replace existing TNGIS section
                prop.internal_notes = revenue_notes

            await audit_repo.record(
                session,
                action="PROPERTY_UPDATED",
                entity_type="PROPERTY",
                entity_id=prop.id,
                actor_id=actor_id,
                change_diff={
                    "survey_verified": f"{payload.survey_number}/{payload.subdivision or ''}",
                    "patta_number": payload.patta_number,
                    "locality": payload.village,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return success_envelope(
            data={
                "saved": True,
                "property_id": str(payload.property_id),
                "action": "UPDATED",
                "message": f"Property {prop.public_reference} updated with verified TNGIS land record.",
            },
            message="Property updated successfully.",
        )

    # Case 2: Create New Property
    elif payload.create_new_property:
        async with transaction(session):
            public_ref = await property_repo.generate_public_reference(session)
            title = f"Survey {payload.survey_number}/{payload.subdivision or ''} - {payload.village}"

            # Calculate rough plot area in sq.ft from Ares if available (1 Are = 1076.39 sq ft)
            plot_sqft = None
            try:
                ares = float(payload.extent_ares or 0)
                hectares = float(payload.extent_hectares or 0)
                total_ares = (hectares * 100) + ares
                if total_ares > 0:
                    plot_sqft = Decimal(str(round(total_ares * 1076.391, 2)))
            except Exception:
                pass

            new_prop = Property(
                public_reference=public_ref,
                title=title,
                description=f"Verified Tamil Nadu land parcel under Patta No. {payload.patta_number or '-'}. Classification: {payload.land_type or 'Rayathuvari'} {payload.land_type_detail or ''}.",
                property_type="Plot",
                transaction_type="SALE",
                status="DRAFT",
                price=Decimal("1000000"),  # Default placeholder price
                price_negotiable=True,
                plot_area=plot_sqft,
                area_unit="sq.ft",
                district=payload.district,
                city=payload.taluk,
                taluk=payload.taluk,
                locality=payload.village,
                pincode="600001",
                address=f"Survey No. {payload.survey_number}/{payload.subdivision or ''}, {payload.village} Village, {payload.taluk} Taluk, {payload.district} District",
                latitude=Decimal(str(payload.latitude)) if payload.latitude is not None else None,
                longitude=Decimal(str(payload.longitude)) if payload.longitude is not None else None,
                google_maps_url=payload.google_maps_url,
                owner_name=primary_owner_name or "TNGIS Verified Owner",
                internal_notes=revenue_notes,
                is_archived=False,
            )
            await property_repo.create(session, new_prop)

            await audit_repo.record(
                session,
                action="PROPERTY_CREATED",
                entity_type="PROPERTY",
                entity_id=new_prop.id,
                actor_id=actor_id,
                change_diff={
                    "public_reference": public_ref,
                    "title": title,
                    "source": "TNGIS_SCRAPER",
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return success_envelope(
            data={
                "saved": True,
                "property_id": str(new_prop.id),
                "public_reference": new_prop.public_reference,
                "action": "CREATED",
                "message": f"New property draft {new_prop.public_reference} created from verified TNGIS record.",
            },
            message="New property registered successfully from TNGIS record.",
        )

    return success_envelope(
        data={"saved": False, "message": "No property ID provided and create_new_property was false."},
        message="No changes saved.",
    )

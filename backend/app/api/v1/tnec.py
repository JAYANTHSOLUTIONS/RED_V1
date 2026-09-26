import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.common import SuccessEnvelope, success_envelope
from app.schemas.tnec import (
    HierarchyItem,
    TnecScrapeRequest,
    TnecCaptchaSubmit,
    TnecJobStatus,
)
from app.services import tnec_service

router = APIRouter(prefix="/tnec", tags=["TNREGINET Encumbrance Certificate (EC)"])


@router.get("/hierarchy/zones", response_model=SuccessEnvelope[List[HierarchyItem]])
def get_zones():
    """Fetch all available TNREGINET Registration Zones."""
    return success_envelope(tnec_service.get_zones())


@router.get("/hierarchy/districts", response_model=SuccessEnvelope[List[HierarchyItem]])
def get_districts(zone_id: str = Query(...)):
    """Fetch all Registration Districts under a given Zone."""
    return success_envelope(tnec_service.get_districts(zone_id))


@router.get("/hierarchy/sros", response_model=SuccessEnvelope[List[HierarchyItem]])
def get_sros(
    district_id: str = Query(...),
    zone_id: Optional[str] = Query(None),
):
    """Fetch all Sub-Registrar Offices (SROs) under a District."""
    return success_envelope(tnec_service.get_sros(zone_id, district_id))


@router.get("/hierarchy/villages", response_model=SuccessEnvelope[List[HierarchyItem]])
def get_villages(sro_id: str = Query(...)):
    """Fetch all Villages under a Sub-Registrar Office (SRO)."""
    return success_envelope(tnec_service.get_villages(sro_id))


@router.post("/match-location", response_model=SuccessEnvelope[Optional[Dict[str, Any]]])
def match_location(
    payload: Dict[str, Any],
):
    """Automatically maps property district/taluk/village to TNREGINET Zone, District, SRO, and Village."""
    res = tnec_service.match_property_location(
        district=payload.get("district", ""),
        taluk=payload.get("taluk", ""),
        village=payload.get("village", "")
    )
    return success_envelope(res)


@router.post("/scrape/start", response_model=SuccessEnvelope[Dict[str, Any]])
def start_ec_scrape(
    req: TnecScrapeRequest,
    current_user: User = Depends(require_roles("CONSULTANT"))
):
    """Initiates an automated background TNREGINET EC extraction job."""
    job_id = tnec_service.start_ec_scrape(req)
    return success_envelope({"job_id": job_id, "status": "started", "surveys_count": len(req.surveys)})


@router.get("/scrape/status/{job_id}", response_model=SuccessEnvelope[TnecJobStatus])
async def get_scrape_status(
    job_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT"))
):
    """Polls the status of an ongoing EC extraction job."""
    res = await tnec_service.get_ec_status(job_id, session=session)
    return success_envelope(res)


@router.post("/scrape/captcha", response_model=SuccessEnvelope[Dict[str, Any]])
def submit_captcha(
    submit: TnecCaptchaSubmit,
    current_user: User = Depends(require_roles("CONSULTANT"))
):
    """Submits manual CAPTCHA response for an active EC job."""
    success = tnec_service.submit_captcha_response(submit)
    return success_envelope({"success": success, "job_id": submit.job_id})


@router.get("/download/{job_id}")
def download_ec_pdf(
    job_id: str,
):
    """Streams the downloaded EC PDF directly to the client."""
    path = tnec_service.get_job_pdf_path(job_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="EC document not found for this job.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=os.path.basename(path)
    )



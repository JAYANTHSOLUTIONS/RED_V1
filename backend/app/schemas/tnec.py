"""
Pydantic Schemas for TNREGINET Encumbrance Certificate (EC) Scraper & Hierarchy.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HierarchyItem(BaseModel):
    id: str
    name: str


class SurveySubdivisionItem(BaseModel):
    survey_no: str
    sub_division_no: Optional[str] = ""


class TnecScrapeRequest(BaseModel):
    property_id: Optional[str] = None
    zone_id: str
    zone_name: Optional[str] = None
    district_id: str
    district_name: Optional[str] = None
    sro_id: str
    sro_name: Optional[str] = None
    village_id: str
    village_name: Optional[str] = None
    start_date: str = Field("01/01/1975", description="Start date in DD/MM/YYYY format (defaults to 01/01/1975)")
    end_date: str = Field(..., description="End date in DD/MM/YYYY format")
    surveys: List[SurveySubdivisionItem] = Field(..., min_length=1, description="List of survey and subdivision numbers")


class TnecCaptchaSubmit(BaseModel):
    job_id: str
    captcha_text: str


class TnecJobStatus(BaseModel):
    job_id: str
    status: str = Field(..., description="running | waiting_for_captcha | completed | failed")
    current_step: int = Field(1, description="Step index from 1 to 5")
    message: str
    captcha_image: Optional[str] = None
    pdf_filename: Optional[str] = None
    pdf_url: Optional[str] = None
    document_id: Optional[str] = None
    surveys_count: int = 0
    is_nil_encumbrance: Optional[bool] = False
    error: Optional[str] = None


class HierarchyResponse(BaseModel):
    zones: List[HierarchyItem]

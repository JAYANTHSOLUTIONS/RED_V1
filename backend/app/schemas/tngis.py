"""Pydantic schemas for TNGIS Land & Revenue Record Extraction and Verification.

Models for mapping user search parameters (District, Taluk, Village, Survey, Subdivision),
parsing extracted TNGIS data (Owner details, Land classifications, Guideline valuations,
GPS coordinates), and saving verified records to properties.
"""
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TngisLookupRequest(BaseModel):
    """Search parameters for TNGIS land record extraction."""
    model_config = ConfigDict(str_strip_whitespace=True)

    district: str = Field(..., description="Tamil Nadu District name (e.g. Kancheepuram)")
    taluk: str = Field(..., description="Taluk name (e.g. Walajabad)")
    village: str = Field(..., description="Revenue village name (e.g. Walajabad)")
    survey_number: str = Field(..., description="Survey Number (e.g. 217)")
    subdivision: Optional[str] = Field(None, description="Subdivision Number (e.g. 1B2)")
    area_type: str = Field("rural", description="Area classification: 'rural' or 'urban'")
    live_scrape: bool = Field(False, description="Whether to execute live Selenium scraper against the TNGIS portal")


class TngisOwnerRecord(BaseModel):
    """Individual registered owner record from TNGIS."""
    model_config = ConfigDict(str_strip_whitespace=True)

    index: int = Field(..., description="Row serial number")
    owner: str = Field(..., description="Owner name in Tamil script or English")
    relative: Optional[str] = Field(None, description="Father/Husband/Guardian name")
    relation: Optional[str] = Field(None, description="Relationship (e.g. மகன் / மகள் / மனைவி)")


class TngisLandDetails(BaseModel):
    """Revenue classification and land extent details."""
    model_config = ConfigDict(str_strip_whitespace=True)

    land_type: Optional[str] = Field(None, description="e.g. Rayathuvari / ரயத்துவாரி")
    land_type_eng: Optional[str] = Field(None, description="e.g. Dry")
    land_type_tamil: Optional[str] = Field(None, description="e.g. புஞ்சை")
    govt_pri_code: Optional[str] = None
    soil_class: Optional[str] = None
    soil_type_pri: Optional[str] = None
    soil_type_sec: Optional[str] = None
    extent_hectares: Optional[str] = Field("0", description="Extent in Hectares")
    extent_ares: Optional[str] = Field("0", description="Extent in Ares")
    total_tax: Optional[str] = Field(None, description="Assessment or revenue tax")
    patta_number: Optional[str] = Field(None, description="Patta Number (e.g. 614)")
    poramboke: Optional[str] = Field("-", description="Poramboke classification indicator")
    assessed: Optional[str] = None
    cultivable: Optional[str] = None
    raw_fields: Dict[str, str] = Field(default_factory=dict)


class TngisVertex(BaseModel):
    """Corner vertex coordinate of survey parcel."""
    vertex_number: int
    latitude: float
    longitude: float


class TngisCoordinates(BaseModel):
    """Pinned geodetic location and boundary vertices."""
    latitude: float
    longitude: float
    google_maps_url: str
    vertices: List[TngisVertex] = Field(default_factory=list)


class TngisGuidelineValue(BaseModel):
    """Registration Department guideline valuation."""
    land_type: Optional[str] = None
    metric_rate: Optional[str] = None
    guideline_amount: Optional[str] = None


class TngisDocumentStatus(BaseModel):
    """Status of documentary artifacts in TNGIS portal."""
    patta_available: bool = False
    patta_rendered_pdf: Optional[str] = None
    fmb_available: bool = False
    fmb_rendered_pdf: Optional[str] = None
    fmb_screenshot: Optional[str] = None
    ec_available: bool = False
    ec_rendered_pdf: Optional[str] = None


class TngisLookupResponse(BaseModel):
    """Complete extracted and structured TNGIS dataset."""
    model_config = ConfigDict(str_strip_whitespace=True)

    search: Dict[str, str]
    owners: List[TngisOwnerRecord] = Field(default_factory=list)
    land_details: TngisLandDetails
    guideline_value: TngisGuidelineValue
    coordinates: Optional[TngisCoordinates] = None
    document_status: TngisDocumentStatus
    raw_sections: Dict[str, str] = Field(default_factory=dict)
    is_cached_sample: bool = False
    message: str = "TNGIS land details retrieved successfully."


class TngisSaveRequest(BaseModel):
    """Payload to persist verified and edited TNGIS details into the database."""
    model_config = ConfigDict(str_strip_whitespace=True)

    property_id: Optional[uuid.UUID] = Field(None, description="Existing property ID to update")
    create_new_property: bool = Field(False, description="Whether to create a new property listing")

    district: str
    taluk: str
    village: str
    survey_number: str
    subdivision: Optional[str] = None
    patta_number: Optional[str] = None

    land_type: Optional[str] = None
    land_type_detail: Optional[str] = None
    extent_hectares: Optional[str] = None
    extent_ares: Optional[str] = None
    total_tax: Optional[str] = None
    guideline_rate: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: Optional[str] = None

    owners: List[TngisOwnerRecord] = Field(default_factory=list)
    vertices: List[TngisVertex] = Field(default_factory=list, description="Parcel boundary vertex coordinates")
    consultant_notes: Optional[str] = None


class TngisScrapeStartRequest(BaseModel):
    """Parameters to initiate an interactive TNGIS live scraper session."""
    model_config = ConfigDict(str_strip_whitespace=True)

    district: str = Field(..., description="District name")
    taluk: str = Field(..., description="Taluk name")
    village: str = Field(..., description="Revenue village name")
    survey_number: str = Field(..., description="Survey number")
    subdivision: Optional[str] = Field(None, description="Subdivision number")
    area_type: str = Field("rural", description="Area classification: rural or urban")
    headless: bool = Field(False, description="Whether to run Chrome headlessly or visibly for map pin")


class TngisContinueRequest(BaseModel):
    """Payload to resume scraper extraction after map parcel pinning."""
    x_ratio: float = Field(0.5, description="Relative horizontal click offset (0.0 to 1.0, 0.5 is center)")
    y_ratio: float = Field(0.5, description="Relative vertical click offset (0.0 to 1.0, 0.5 is center)")


class TngisScrapeStatusResponse(BaseModel):
    """Real-time status of an ongoing TNGIS scraping session."""
    session_id: str
    status: str = Field(..., description="starting | logging_in | navigating | waiting_for_pin | extracting | completed | error")
    message: str = Field(..., description="User-friendly status message")
    timestamp: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    map_image: Optional[str] = Field(None, description="Base64 data URI of the captured map view for parcel pinning")
    data: Optional[TngisLookupResponse] = None

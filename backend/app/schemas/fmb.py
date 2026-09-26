"""Pydantic schemas for FMB Map Generation service.

Handles request/response contracts for generating FMB maps from
Tamil Nadu CollabLand government GIS service and saving them to
the Document Vault.
"""
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FmbGenerateRequest(BaseModel):
    """Request body for generating an FMB map PDF."""
    model_config = ConfigDict(str_strip_whitespace=True)

    survey_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Revenue survey number (e.g. '123', '123/2A')",
    )
    subdivision_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Sub-division / plot number where applicable (e.g. '1', '2B')",
    )

    @field_validator("survey_number")
    @classmethod
    def validate_survey_number(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Survey number must not be blank.")
        return cleaned


class FmbGenerateResponse(BaseModel):
    """Successful FMB map generation result.

    Returns the PDF as Base64 for client-side preview/download.
    The raw bytes are NOT stored until the user explicitly saves to vault.
    """
    pdf_base64: str = Field(..., description="Base64-encoded PDF content")
    filename: str = Field(..., description="Suggested filename for the PDF")
    file_size: int = Field(..., description="Size of the decoded PDF in bytes")
    district: str
    taluk: Optional[str] = None
    village: Optional[str] = None
    survey_number: str
    subdivision_number: Optional[str] = None
    gis_code: str = Field(..., description="Constructed CollabLand GIS code used in request")
    scale: int = 0
    source: str = "CollabLand"


class FmbSaveRequest(BaseModel):
    """Request body for saving a generated FMB map to the Document Vault."""
    model_config = ConfigDict(str_strip_whitespace=True)

    survey_number: str = Field(..., min_length=1, max_length=50)
    subdivision_number: Optional[str] = Field(None, max_length=50)
    pdf_base64: str = Field(..., description="Base64-encoded PDF received from generate step")
    filename: str = Field(..., min_length=1, max_length=255, description="Filename to store")
    force_duplicate: bool = Field(
        False,
        description="If True, saves even when an equivalent FMB map already exists.",
    )


class FmbSaveResponse(BaseModel):
    """Response after saving a generated FMB map to the Document Vault."""
    document_id: uuid.UUID
    document_type: str
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    notes: Optional[str] = None
    created_at: str
    duplicate_existed: bool = Field(
        False,
        description="True if an existing FMB map was found but save was forced.",
    )
    source: str = "CollabLand"

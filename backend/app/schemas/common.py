"""Standard API response envelopes.

Every endpoint in this system responds with one of these two shapes so API
consumers can rely on a single, predictable contract, per the master
specification's API response contract.
"""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorDetail


class SuccessEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = "Operation completed successfully."


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int


def success_envelope(data: Any = None, message: str = "Operation completed successfully.") -> dict:
    """Build a success envelope dict, e.g. for use in a JSONResponse."""
    return {"success": True, "data": data, "message": message}


def error_envelope(code: str, message: str) -> dict:
    """Build an error envelope dict, e.g. for use in an exception handler."""
    return {"success": False, "error": {"code": code, "message": message}}

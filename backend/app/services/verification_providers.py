"""External Authority Provider Interfaces for Tamil Nadu Property Verification.

Architectural foundation for future government portal integrations (e-Services Patta,
TNREGINET, TNRERA, CMDA, DTCP). Explicitly prevents fraudulent or fake scraping,
strictly marking live lookups as offline/unavailable until authoritative credentials
and APIs are officially licensed.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LandRecordProvider(ABC):
    """Interface for Tamil Nadu Land Records (Patta, Chitta, A-Register, TSLR)."""

    @abstractmethod
    async def fetch_patta_record(
        self, district: str, taluk: str, village: str, survey_number: str, subdivision: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch Patta/Chitta from Tamil Nadu Revenue Department."""
        pass


class RegistrationProvider(ABC):
    """Interface for Tamil Nadu Sub-Registrar / TNREGINET records."""

    @abstractmethod
    async def search_encumbrance(
        self, sro_name: str, survey_number: str, subdivision: Optional[str] = None, years: int = 30
    ) -> Dict[str, Any]:
        """Query Encumbrance Certificate from TNREGINET."""
        pass


class RERAProvider(ABC):
    """Interface for Tamil Nadu Real Estate Regulatory Authority (TNRERA)."""

    @abstractmethod
    async def verify_rera_registration(
        self, rera_registration_number: str
    ) -> Dict[str, Any]:
        """Query project approval status from TNRERA."""
        pass


class PlanningApprovalProvider(ABC):
    """Interface for CMDA / DTCP Planning & Layout Approvals."""

    @abstractmethod
    async def verify_layout_approval(
        self, authority: str, approval_number: str, survey_number: str
    ) -> Dict[str, Any]:
        """Query CMDA / DTCP planning permissions."""
        pass


class DefaultOfflineProvider(
    LandRecordProvider, RegistrationProvider, RERAProvider, PlanningApprovalProvider
):
    """Conservative default provider acknowledging absence of live government integrations.

    Adheres strictly to the requirement: DO NOT fake government verification.
    """

    async def fetch_patta_record(
        self, district: str, taluk: str, village: str, survey_number: str, subdivision: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "is_connected": False,
            "status": "NOT_AVAILABLE",
            "message": "Live Tamil Nadu Revenue Land Records (e-Services) integration is not configured. Relying on supplied documentary evidence.",
        }

    async def search_encumbrance(
        self, sro_name: str, survey_number: str, subdivision: Optional[str] = None, years: int = 30
    ) -> Dict[str, Any]:
        return {
            "is_connected": False,
            "status": "NOT_AVAILABLE",
            "message": "Live TNREGINET Sub-Registrar API integration is not configured. Relying on supplied documentary evidence.",
        }

    async def verify_rera_registration(
        self, rera_registration_number: str
    ) -> Dict[str, Any]:
        return {
            "is_connected": False,
            "status": "NOT_AVAILABLE",
            "message": "Live TNRERA portal API integration is not configured. Relying on supplied documentary evidence.",
        }

    async def verify_layout_approval(
        self, authority: str, approval_number: str, survey_number: str
    ) -> Dict[str, Any]:
        return {
            "is_connected": False,
            "status": "NOT_AVAILABLE",
            "message": "Live CMDA/DTCP planning portal API integration is not configured. Relying on supplied documentary evidence.",
        }


class TamilNaduVerificationProvider(ABC):
    """Unified authoritative Tamil Nadu government verification provider interface.

    Returns PROVIDER_NOT_CONFIGURED until officially authenticated live government APIs exist.
    """

    @abstractmethod
    async def verify_ec(self, sro_name: str, survey_number: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_patta(self, district: str, taluk: str, village: str, survey_number: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_registration(self, sro_name: str, document_number: str, year: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_planning_approval(self, authority: str, approval_number: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_rera(self, rera_registration_number: str) -> Dict[str, Any]:
        pass


class DefaultTamilNaduVerificationProvider(TamilNaduVerificationProvider):
    """Offline-safe default implementation returning PROVIDER_NOT_CONFIGURED."""

    async def verify_ec(self, sro_name: str, survey_number: str) -> Dict[str, Any]:
        return {
            "status": "PROVIDER_NOT_CONFIGURED",
            "message": "Direct TNREGINET EC verification provider is not configured.",
        }

    async def verify_patta(self, district: str, taluk: str, village: str, survey_number: str) -> Dict[str, Any]:
        return {
            "status": "PROVIDER_NOT_CONFIGURED",
            "message": "Direct AnyTN Patta verification provider is not configured.",
        }

    async def verify_registration(self, sro_name: str, document_number: str, year: int) -> Dict[str, Any]:
        return {
            "status": "PROVIDER_NOT_CONFIGURED",
            "message": "Direct SRO registration verification provider is not configured.",
        }

    async def verify_planning_approval(self, authority: str, approval_number: str) -> Dict[str, Any]:
        return {
            "status": "PROVIDER_NOT_CONFIGURED",
            "message": "Direct CMDA/DTCP planning approval verification provider is not configured.",
        }

    async def verify_rera(self, rera_registration_number: str) -> Dict[str, Any]:
        return {
            "status": "PROVIDER_NOT_CONFIGURED",
            "message": "Direct TNRERA registration verification provider is not configured.",
        }


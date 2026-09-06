"""Planning jurisdiction intelligence for Tamil Nadu.

Delineates CMDA (Chennai Metropolitan Area) and DTCP (Directorate of Town and
Country Planning) boundaries using structured configuration rather than monolithic logic.
Exposes authority, basis, confidence, and confirmation flags.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set


class PlanningAuthority(str, Enum):
    CMDA = "CMDA"
    DTCP = "DTCP"
    LOCAL_PLANNING_AUTHORITY = "LOCAL_PLANNING_AUTHORITY"
    LOCAL_BODY = "LOCAL_BODY"
    UNKNOWN = "UNKNOWN"


class JurisdictionConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Known Chennai Metropolitan Area (CMA) core and expanded localities / taluks
CMA_EXPANDED_LOCALITIES: Set[str] = {
    "anna nagar", "t. nagar", "t nagar", "adyar", "velachery", "mylapore", "egmore",
    "alwarpet", "nandanam", "kodambakkam", "guindy", "alandur", "pallavaram", "tambaram",
    "porur", "ambattur", "avadi", "poonamallee", "sholinganallur", "thiruvanmiyur",
    "besant nagar", "perambur", "kilpauk", "nungambakkam", "royapettah", "saidapet",
    "vadapalani", "chromepet", "medavakkam", "perungudi", "omr", "ecr", "madipakkam",
    "manapakkam", "mugalivakkam", "kolathur", "villivakkam", "triplicane", "chetpet",
    "thiruvanmiyur", "tharamani", "palavakkam", "kottivakkam", "injambakkam", "neelankarai",
}

# Districts outside CMDA jurisdiction where DTCP governs planning approvals
DTCP_DISTRICTS: Set[str] = {
    "coimbatore", "madurai", "tiruchirappalli", "salem", "tirunelveli", "erode",
    "vellore", "thanjavur", "dindigul", "tiruppur", "cuddalore", "dharmapuri",
    "karur", "nagapattinam", "namakkal", "perambalur", "pudukkottai", "ramanathapuram",
    "sivaganga", "theni", "thiruvannamalai", "thiruvarur", "thoothukudi", "tirupathur",
    "ranipet", "tenkasi", "mayiladuthurai", "kallakurichi", "nilgiris", "krishnagiri",
    "ariyalur", "virudhunagar", "kanyakumari",
}


@dataclass
class PlanningDetermination:
    """Structured planning authority determination with explainable provenance."""
    authority: PlanningAuthority
    basis: str
    confidence: JurisdictionConfidence
    requires_consultant_confirmation: bool


def determine_planning_jurisdiction(
    district: Optional[str],
    locality: Optional[str],
    explicit_authority: Optional[str] = None,
) -> PlanningDetermination:
    """Evaluate planning authority jurisdiction deterministically.

    NOTE: Determining planning authority DOES NOT confirm planning approval or ownership.
    """
    if explicit_authority:
        ea = explicit_authority.strip().upper()
        if "CMDA" in ea:
            return PlanningDetermination(
                authority=PlanningAuthority.CMDA,
                basis="explicit_consultant_override",
                confidence=JurisdictionConfidence.HIGH,
                requires_consultant_confirmation=False,
            )
        if "DTCP" in ea:
            return PlanningDetermination(
                authority=PlanningAuthority.DTCP,
                basis="explicit_consultant_override",
                confidence=JurisdictionConfidence.HIGH,
                requires_consultant_confirmation=False,
            )
        if "LOCAL_BODY" in ea:
            return PlanningDetermination(
                authority=PlanningAuthority.LOCAL_BODY,
                basis="explicit_consultant_override",
                confidence=JurisdictionConfidence.HIGH,
                requires_consultant_confirmation=False,
            )
        if "LPA" in ea or "LOCAL_PLANNING" in ea:
            return PlanningDetermination(
                authority=PlanningAuthority.LOCAL_PLANNING_AUTHORITY,
                basis="explicit_consultant_override",
                confidence=JurisdictionConfidence.HIGH,
                requires_consultant_confirmation=False,
            )

    d = (district or "").strip().lower()
    loc = (locality or "").strip().lower()

    # Chennai district is 100% within CMDA jurisdiction
    if d == "chennai":
        return PlanningDetermination(
            authority=PlanningAuthority.CMDA,
            basis="district_statutory_jurisdiction",
            confidence=JurisdictionConfidence.HIGH,
            requires_consultant_confirmation=False,
        )

    # Check locality match against CMA expanded bounds
    if any(cma_loc in loc for cma_loc in CMA_EXPANDED_LOCALITIES):
        return PlanningDetermination(
            authority=PlanningAuthority.CMDA,
            basis="cma_expanded_locality_configuration",
            confidence=JurisdictionConfidence.MEDIUM,
            requires_consultant_confirmation=False,
        )

    # Chengalpattu / Kanchipuram / Tiruvallur have partial CMA overlap
    if d in ("chengalpattu", "kanchipuram", "tiruvallur"):
        return PlanningDetermination(
            authority=PlanningAuthority.DTCP,
            basis="peripheral_cma_boundary_default_dtcp",
            confidence=JurisdictionConfidence.MEDIUM,
            requires_consultant_confirmation=True,
        )

    # Standard DTCP districts across Tamil Nadu
    if d in DTCP_DISTRICTS:
        return PlanningDetermination(
            authority=PlanningAuthority.DTCP,
            basis="state_planning_jurisdiction",
            confidence=JurisdictionConfidence.HIGH,
            requires_consultant_confirmation=False,
        )

    return PlanningDetermination(
        authority=PlanningAuthority.UNKNOWN,
        basis="unrecognized_district_or_locality",
        confidence=JurisdictionConfidence.LOW,
        requires_consultant_confirmation=True,
    )

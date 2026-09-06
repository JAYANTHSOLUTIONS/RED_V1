"""Structured consultant action intelligence for Tamil Nadu property verification.

Generates recommended next steps based on preliminary documentary findings.
Actions DO NOT alter calculated risk scores automatically.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class ConsultantActionType(str, Enum):
    REVIEW_DOCUMENT = "REVIEW_DOCUMENT"
    REQUEST_MISSING_DOCUMENT = "REQUEST_MISSING_DOCUMENT"
    VERIFY_SRO_RECORD = "VERIFY_SRO_RECORD"
    VERIFY_REVENUE_RECORD = "VERIFY_REVENUE_RECORD"
    VERIFY_PLANNING_APPROVAL = "VERIFY_PLANNING_APPROVAL"
    VERIFY_RERA_RECORD = "VERIFY_RERA_RECORD"
    CONSULT_ADVOCATE = "CONSULT_ADVOCATE"
    MARK_INFORMATION_SUFFICIENT = "MARK_INFORMATION_SUFFICIENT"


@dataclass
class ConsultantActionItem:
    """Actionable recommendation for the real-estate consultant."""
    action_type: ConsultantActionType
    priority: str  # "HIGH", "MEDIUM", "LOW"
    target_document_type: Optional[str]
    description: str


def generate_consultant_actions(
    risk_flags: List[str],
    missing_info: List[str],
    has_active_ec_charge: bool = False,
    is_rera_missing: bool = False,
    is_planning_missing: bool = False,
    has_survey_mismatch: bool = False,
    has_owner_mismatch: bool = False,
) -> List[ConsultantActionItem]:
    """Derive prioritized actions for the consultant based on evaluation output."""
    actions: List[ConsultantActionItem] = []

    if has_active_ec_charge:
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.CONSULT_ADVOCATE,
                priority="HIGH",
                target_document_type="EC",
                description="Consult an empanelled legal advocate to examine active mortgage or charge entries noted in the Encumbrance Certificate.",
            )
        )
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.VERIFY_SRO_RECORD,
                priority="HIGH",
                target_document_type="EC",
                description="Request certified copies from the Sub-Registrar Office (SRO) for all registered charge entries.",
            )
        )

    if has_survey_mismatch:
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.VERIFY_REVENUE_RECORD,
                priority="HIGH",
                target_document_type="PATTA",
                description="Reconcile survey subdivision discrepancy against Tamil Nadu Taluk Office 'A-Register' and FMB sketch.",
            )
        )

    if has_owner_mismatch:
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.CONSULT_ADVOCATE,
                priority="HIGH",
                target_document_type="SALE_DEED",
                description="Examine identity proofs and title deeds to resolve conflicting owner name tokens or initials.",
            )
        )

    for item in missing_info:
        item_lower = item.lower()
        if "patta" in item_lower:
            actions.append(
                ConsultantActionItem(
                    action_type=ConsultantActionType.REQUEST_MISSING_DOCUMENT,
                    priority="HIGH",
                    target_document_type="PATTA",
                    description="Request valid computerized Patta/Chitta from the property owner or Taluk Revenue portal.",
                )
            )
        elif "title" in item_lower or "sale deed" in item_lower:
            actions.append(
                ConsultantActionItem(
                    action_type=ConsultantActionType.REQUEST_MISSING_DOCUMENT,
                    priority="HIGH",
                    target_document_type="SALE_DEED",
                    description="Request complete copy of current registered title deed with registration stamp and schedule.",
                )
            )
        elif "parent" in item_lower:
            actions.append(
                ConsultantActionItem(
                    action_type=ConsultantActionType.REQUEST_MISSING_DOCUMENT,
                    priority="MEDIUM",
                    target_document_type="PARENT_DOCUMENT",
                    description="Obtain prior link documents covering minimum 30-year lineage for legal opinion scrutiny.",
                )
            )
        elif "ec" in item_lower:
            actions.append(
                ConsultantActionItem(
                    action_type=ConsultantActionType.VERIFY_SRO_RECORD,
                    priority="MEDIUM",
                    target_document_type="EC",
                    description="Apply for computerized Encumbrance Certificate (EC) covering 30+ years from the respective SRO.",
                )
            )

    if is_planning_missing:
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.VERIFY_PLANNING_APPROVAL,
                priority="MEDIUM",
                target_document_type="LAYOUT_APPROVAL",
                description="Verify layout approval number against CMDA or DTCP approved layout registers to confirm regularization.",
            )
        )

    if is_rera_missing:
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.VERIFY_RERA_RECORD,
                priority="MEDIUM",
                target_document_type="TNRERA_REGISTRATION",
                description="Check TNRERA public register for project registration status.",
            )
        )

    if not actions:
        actions.append(
            ConsultantActionItem(
                action_type=ConsultantActionType.MARK_INFORMATION_SUFFICIENT,
                priority="LOW",
                target_document_type=None,
                description="All primary documentary evidence is supplied without obvious contradiction. Proceed to advocate legal title opinion.",
            )
        )

    return actions

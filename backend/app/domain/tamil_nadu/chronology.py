"""Lightweight Document Relationship and Chronology Graph.

Tracks title link dependencies (Current Deed -> Parent Deed -> Earlier Parent Deeds)
and verifies chronological integrity:
- Future parent deed detection (parent deed dated after derived deed)
- Circular relationship detection
- Missing parent link detection
- Unexplained gap detection
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import uuid


class DocumentRelationship(str, Enum):
    PARENT_OF = "PARENT_OF"
    DERIVED_FROM = "DERIVED_FROM"
    REFERENCED_BY = "REFERENCED_BY"
    UNKNOWN_RELATIONSHIP = "UNKNOWN_RELATIONSHIP"


class ChronologyStatus(str, Enum):
    CHRONOLOGY_OK = "CHRONOLOGY_OK"
    CHRONOLOGY_REVIEW = "CHRONOLOGY_REVIEW"
    CHRONOLOGY_INCOMPLETE = "CHRONOLOGY_INCOMPLETE"


@dataclass
class DocumentNode:
    """Document node in the title chain relationship graph."""
    doc_id: Optional[uuid.UUID]
    doc_type: str
    doc_date: Optional[date] = None
    title: Optional[str] = None
    parent_ids: List[uuid.UUID] = field(default_factory=list)


@dataclass
class ChronologyAnalysis:
    """Result of chronological graph integrity evaluation."""
    status: ChronologyStatus
    issues: List[str] = field(default_factory=list)
    nodes: List[Dict[str, str]] = field(default_factory=list)
    edges: List[Dict[str, str]] = field(default_factory=list)


def analyze_document_chronology(
    current_doc_id: Optional[uuid.UUID],
    current_doc_date: Optional[date],
    parent_doc_id: Optional[uuid.UUID],
    parent_doc_date: Optional[date],
    additional_parents: Optional[List[Tuple[uuid.UUID, date]]] = None,
) -> ChronologyAnalysis:
    """Evaluate chronological sanity of title documents.

    Does NOT conclude legal invalidity; returns structured review flags.
    """
    issues: List[str] = []
    nodes: List[Dict[str, str]] = []
    edges: List[Dict[str, str]] = []

    # Current document node
    cur_id_str = str(current_doc_id or "current-deed")
    nodes.append({
        "id": cur_id_str,
        "type": "CURRENT_TITLE_DEED",
        "date": current_doc_date.isoformat() if current_doc_date else "Unknown",
    })

    if not parent_doc_id and not parent_doc_date:
        issues.append("No parent or prior link document identified in title chain.")
        return ChronologyAnalysis(
            status=ChronologyStatus.CHRONOLOGY_INCOMPLETE,
            issues=issues,
            nodes=nodes,
            edges=edges,
        )

    parent_id_str = str(parent_doc_id or "parent-deed")
    nodes.append({
        "id": parent_id_str,
        "type": "PARENT_DOCUMENT",
        "date": parent_doc_date.isoformat() if parent_doc_date else "Unknown",
    })

    # Check for circular self-reference
    if current_doc_id and parent_doc_id and current_doc_id == parent_doc_id:
        issues.append("Circular relationship detected: document references itself as parent.")
        return ChronologyAnalysis(
            status=ChronologyStatus.CHRONOLOGY_REVIEW,
            issues=issues,
            nodes=nodes,
            edges=edges,
        )

    edges.append({
        "source": parent_id_str,
        "target": cur_id_str,
        "relationship": DocumentRelationship.PARENT_OF.value,
    })

    # Chronological date sequence sanity check
    if current_doc_date and parent_doc_date:
        if parent_doc_date > current_doc_date:
            issues.append(
                f"Future parent deed anomaly: Parent document date ({parent_doc_date}) "
                f"is dated after current title deed ({current_doc_date})."
            )
        elif (current_doc_date.year - parent_doc_date.year) > 50:
            issues.append(
                f"Unexplained title gap: Over {current_doc_date.year - parent_doc_date.year} "
                "years between parent and current deed without intermediary link deeds."
            )

    # Process additional chain parents if present
    if additional_parents:
        prev_parent_id = parent_id_str
        prev_parent_date = parent_doc_date

        visited_ids: Set[str] = {cur_id_str, parent_id_str}

        for p_id, p_date in additional_parents:
            p_id_str = str(p_id)
            if p_id_str in visited_ids:
                issues.append(f"Circular link or duplicate document detected in chain: {p_id_str}.")
                continue
            visited_ids.add(p_id_str)

            nodes.append({
                "id": p_id_str,
                "type": "EARLIER_LINK_DOCUMENT",
                "date": p_date.isoformat() if p_date else "Unknown",
            })
            edges.append({
                "source": p_id_str,
                "target": prev_parent_id,
                "relationship": DocumentRelationship.PARENT_OF.value,
            })

            if prev_parent_date and p_date and p_date > prev_parent_date:
                issues.append(
                    f"Chronological inversion in parent chain: Link deed ({p_date}) is dated "
                    f"after subsequent deed ({prev_parent_date})."
                )

            prev_parent_id = p_id_str
            prev_parent_date = p_date

    if issues:
        return ChronologyAnalysis(
            status=ChronologyStatus.CHRONOLOGY_REVIEW,
            issues=issues,
            nodes=nodes,
            edges=edges,
        )

    return ChronologyAnalysis(
        status=ChronologyStatus.CHRONOLOGY_OK,
        issues=[],
        nodes=nodes,
        edges=edges,
    )

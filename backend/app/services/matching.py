"""Deterministic, rule-based Property Matching Engine.

Evaluates candidate properties against customer property requirements criteria-by-criteria
with full transparency, explainability, and percentage scoring.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from app.models.property import Property
from app.models.requirement import PropertyRequirement


@dataclass
class MatchEvaluation:
    is_match: bool
    score: int
    match_grade: str  # "EXACT_MATCH", "PARTIAL_MATCH", "NO_MATCH"
    matched_criteria: List[str] = field(default_factory=list)
    unmatched_criteria: List[str] = field(default_factory=list)


class DeterministicMatchingEngine:
    """Deterministic rule-based matching engine without AI/ML complexity."""

    @staticmethod
    def normalize_transaction_type(tx: str) -> str:
        tx_upper = tx.strip().upper()
        if tx_upper in ("BUY", "SALE"):
            return "SALE"
        return tx_upper

    def evaluate(
        self, requirement: PropertyRequirement, property_obj: Property
    ) -> MatchEvaluation:
        """Evaluate a single property against a property requirement deterministically."""
        matched: List[str] = []
        unmatched: List[str] = []

        # 1. Transaction Type (Strict prerequisite)
        req_tx = self.normalize_transaction_type(requirement.transaction_type)
        prop_tx = self.normalize_transaction_type(property_obj.transaction_type)
        if req_tx == prop_tx:
            matched.append("transaction_type")
        else:
            unmatched.append("transaction_type")
            # Incompatible transaction type -> immediate NO_MATCH
            return MatchEvaluation(
                is_match=False,
                score=0,
                match_grade="NO_MATCH",
                matched_criteria=matched,
                unmatched_criteria=unmatched,
            )

        # 2. Property Type
        if requirement.property_types and requirement.property_types.strip():
            req_types = [
                t.strip().lower()
                for t in requirement.property_types.replace(";", ",").split(",")
                if t.strip()
            ]
            prop_type = property_obj.property_type.lower()
            if any(t in prop_type or prop_type in t for t in req_types):
                matched.append("property_type")
            else:
                unmatched.append("property_type")

        # 3. Budget (Price bounds)
        budget_evaluated = False
        budget_matched = True

        if requirement.min_budget is not None:
            budget_evaluated = True
            if property_obj.price < requirement.min_budget:
                budget_matched = False

        if requirement.max_budget is not None:
            budget_evaluated = True
            if property_obj.price > requirement.max_budget:
                budget_matched = False

        if budget_evaluated:
            if budget_matched:
                matched.append("budget")
            else:
                unmatched.append("budget")

        # 4. Area Bounds
        area_evaluated = False
        area_matched = True
        prop_area = property_obj.built_up_area or property_obj.plot_area

        if requirement.min_area is not None:
            area_evaluated = True
            if prop_area is None or prop_area < requirement.min_area:
                area_matched = False

        if requirement.max_area is not None:
            area_evaluated = True
            if prop_area is None or prop_area > requirement.max_area:
                area_matched = False

        if area_evaluated:
            if area_matched:
                matched.append("area")
            else:
                unmatched.append("area")

        # 5. Location
        if requirement.target_locations and requirement.target_locations.strip():
            tokens = [
                loc.strip().lower()
                for loc in requirement.target_locations.replace(";", ",").split(",")
                if loc.strip()
            ]
            loc_candidates = [
                property_obj.district.lower(),
                property_obj.city.lower(),
                property_obj.locality.lower(),
            ]
            if any(
                any(token in cand or cand in token for cand in loc_candidates)
                for token in tokens
            ):
                matched.append("location")
            else:
                unmatched.append("location")

        # 6. Bedrooms
        if requirement.bedrooms is not None:
            if property_obj.bedrooms is not None and property_obj.bedrooms >= requirement.bedrooms:
                matched.append("bedrooms")
            else:
                unmatched.append("bedrooms")

        # 7. Bathrooms
        if requirement.bathrooms is not None:
            if property_obj.bathrooms is not None and property_obj.bathrooms >= requirement.bathrooms:
                matched.append("bathrooms")
            else:
                unmatched.append("bathrooms")

        # 8. Facing Orientation
        if requirement.facing and requirement.facing.strip():
            req_facing = requirement.facing.strip().lower()
            prop_facing = (property_obj.facing or "").strip().lower()
            if req_facing in prop_facing or prop_facing in req_facing:
                matched.append("facing")
            else:
                unmatched.append("facing")

        # 9. Furnishing State
        if requirement.furnishing_state and requirement.furnishing_state.strip():
            req_furnishing = requirement.furnishing_state.strip().lower()
            prop_furnishing = (property_obj.furnishing_state or "").strip().lower()
            if req_furnishing in prop_furnishing or prop_furnishing in req_furnishing:
                matched.append("furnishing_state")
            else:
                unmatched.append("furnishing_state")

        total_evaluated = len(matched) + len(unmatched)
        score = round((len(matched) / total_evaluated) * 100) if total_evaluated > 0 else 100

        if len(unmatched) == 0:
            match_grade = "EXACT_MATCH"
            is_match = True
        elif score >= 50:
            match_grade = "PARTIAL_MATCH"
            is_match = True
        else:
            match_grade = "NO_MATCH"
            is_match = False

        return MatchEvaluation(
            is_match=is_match,
            score=score,
            match_grade=match_grade,
            matched_criteria=matched,
            unmatched_criteria=unmatched,
        )

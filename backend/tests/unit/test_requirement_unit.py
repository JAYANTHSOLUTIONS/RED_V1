"""Unit tests for Property Requirement schemas and Deterministic Matching Engine."""
from decimal import Decimal
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.requirement import (
    PropertyRequirementCreate,
    PropertyRequirementUpdate,
)
from app.services.matching import DeterministicMatchingEngine


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------

def test_requirement_create_valid():
    client_id = uuid.uuid4()
    payload = {
        "client_id": client_id,
        "transaction_type": "buy",
        "property_types": "Apartment, Villa",
        "min_budget": Decimal("5000000"),
        "max_budget": Decimal("7500000"),
        "min_area": Decimal("1000"),
        "max_area": Decimal("1500"),
        "target_locations": "Anna Nagar, Chennai",
        "bedrooms": 3,
        "bathrooms": 2,
        "facing": "North",
        "furnishing_state": "SEMI_FURNISHED",
        "notes": "Prefer high floor",
    }
    req = PropertyRequirementCreate(**payload)
    assert req.client_id == client_id
    assert req.transaction_type == "BUY"
    assert req.property_types == "Apartment, Villa"
    assert req.facing == "North"
    assert req.furnishing_state == "SEMI_FURNISHED"
    assert req.min_budget == Decimal("5000000")
    assert req.max_budget == Decimal("7500000")
    assert req.min_area == Decimal("1000")
    assert req.max_area == Decimal("1500")
    assert req.target_locations == "Anna Nagar, Chennai"


def test_requirement_create_budget_range_invalid():
    with pytest.raises(ValidationError) as exc:
        PropertyRequirementCreate(
            client_id=uuid.uuid4(),
            transaction_type="BUY",
            property_types="Apartment",
            min_budget=Decimal("10000000"),
            max_budget=Decimal("5000000"),
        )
    assert "min_budget cannot be greater than max_budget" in str(exc.value)


def test_requirement_create_area_range_invalid():
    with pytest.raises(ValidationError) as exc:
        PropertyRequirementCreate(
            client_id=uuid.uuid4(),
            transaction_type="BUY",
            property_types="Apartment",
            min_area=Decimal("2000"),
            max_area=Decimal("1200"),
        )
    assert "min_area cannot be greater than max_area" in str(exc.value)


def test_requirement_create_negative_values():
    with pytest.raises(ValidationError):
        PropertyRequirementCreate(
            client_id=uuid.uuid4(),
            transaction_type="BUY",
            min_budget=Decimal("-100"),
        )

    with pytest.raises(ValidationError):
        PropertyRequirementCreate(
            client_id=uuid.uuid4(),
            transaction_type="BUY",
            bedrooms=-1,
        )


def test_requirement_create_invalid_transaction_type():
    with pytest.raises(ValidationError) as exc:
        PropertyRequirementCreate(
            client_id=uuid.uuid4(),
            transaction_type="TRADE",
        )
    assert "Invalid transaction type" in str(exc.value)


def test_requirement_update_range_validation():
    with pytest.raises(ValidationError) as exc:
        PropertyRequirementUpdate(
            min_budget=Decimal("8000000"),
            max_budget=Decimal("6000000"),
        )
    assert "min_budget cannot be greater than max_budget" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        PropertyRequirementUpdate(
            min_area=Decimal("3000"),
            max_area=Decimal("1500"),
        )
    assert "min_area cannot be greater than max_area" in str(exc.value)


# ---------------------------------------------------------------------------
# Deterministic Matching Engine Tests
# ---------------------------------------------------------------------------

class MockProperty:
    """Mock candidate property for engine unit testing."""
    def __init__(
        self,
        id=None,
        title="Sample Villa",
        transaction_type="SALE",
        property_type="RESIDENTIAL_VILLA",
        price=Decimal("6000000"),
        built_up_area=Decimal("1500"),
        plot_area=None,
        district="Chennai",
        city="Chennai",
        locality="Adyar",
        bedrooms=3,
        bathrooms=3,
        facing="EAST",
        furnishing_state="SEMI_FURNISHED",
        status="PUBLISHED",
        is_archived=False,
    ):
        self.id = id or uuid.uuid4()
        self.title = title
        self.transaction_type = transaction_type
        self.property_type = property_type
        self.price = price
        self.built_up_area = built_up_area
        self.plot_area = plot_area
        self.district = district
        self.city = city
        self.locality = locality
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.facing = facing
        self.furnishing_state = furnishing_state
        self.status = status
        self.is_archived = is_archived


class MockRequirement:
    """Mock requirement for engine unit testing."""
    def __init__(
        self,
        transaction_type="BUY",
        property_types="RESIDENTIAL_VILLA",
        min_budget=Decimal("5000000"),
        max_budget=Decimal("7000000"),
        min_area=Decimal("1200"),
        max_area=Decimal("1800"),
        target_locations="Adyar",
        bedrooms=3,
        bathrooms=3,
        facing="EAST",
        furnishing_state="SEMI_FURNISHED",
    ):
        self.transaction_type = transaction_type
        self.property_types = property_types
        self.min_budget = min_budget
        self.max_budget = max_budget
        self.min_area = min_area
        self.max_area = max_area
        self.target_locations = target_locations
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.facing = facing
        self.furnishing_state = furnishing_state


def test_engine_exact_match():
    engine = DeterministicMatchingEngine()
    req = MockRequirement()
    prop = MockProperty()

    eval_result = engine.evaluate(req, prop)
    assert eval_result.is_match is True
    assert eval_result.score == 100
    assert eval_result.match_grade == "EXACT_MATCH"
    assert len(eval_result.unmatched_criteria) == 0
    assert "transaction_type" in eval_result.matched_criteria
    assert "property_type" in eval_result.matched_criteria
    assert "budget" in eval_result.matched_criteria
    assert "area" in eval_result.matched_criteria
    assert "location" in eval_result.matched_criteria
    assert "bedrooms" in eval_result.matched_criteria
    assert "bathrooms" in eval_result.matched_criteria
    assert "facing" in eval_result.matched_criteria
    assert "furnishing_state" in eval_result.matched_criteria


def test_engine_transaction_type_incompatible():
    engine = DeterministicMatchingEngine()
    req = MockRequirement(transaction_type="RENT")
    prop = MockProperty(transaction_type="SALE")

    eval_result = engine.evaluate(req, prop)
    assert eval_result.is_match is False
    assert eval_result.score == 0
    assert eval_result.match_grade == "NO_MATCH"
    assert "transaction_type" in eval_result.unmatched_criteria


def test_engine_transaction_type_equivalence():
    engine = DeterministicMatchingEngine()
    # BUY should match SALE
    assert engine.normalize_transaction_type("BUY") == "SALE"
    assert engine.normalize_transaction_type("SALE") == "SALE"
    assert engine.normalize_transaction_type("RENT") == "RENT"
    assert engine.normalize_transaction_type("LEASE") == "LEASE"

    req = MockRequirement(transaction_type="BUY")
    prop = MockProperty(transaction_type="SALE")
    eval_result = engine.evaluate(req, prop)
    assert "transaction_type" in eval_result.matched_criteria


def test_engine_partial_match_scoring():
    engine = DeterministicMatchingEngine()
    # Mismatch facing and bathrooms
    req = MockRequirement(
        facing="WEST",  # prop is EAST
        bathrooms=4,  # prop is 3
    )
    prop = MockProperty()

    eval_result = engine.evaluate(req, prop)
    assert eval_result.is_match is True
    assert 50 <= eval_result.score < 100
    assert eval_result.match_grade == "PARTIAL_MATCH"
    assert "facing" in eval_result.unmatched_criteria
    assert "bathrooms" in eval_result.unmatched_criteria
    assert "transaction_type" in eval_result.matched_criteria
    assert "budget" in eval_result.matched_criteria

"""Unit tests for Property schemas, validations, public reference formatting, and lifecycle rules."""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from pydantic import ValidationError

from app.db.sequence import format_property_reference
from app.models.property import Property
from app.schemas.property import (
    PrivatePropertyResponse,
    PropertyCreate,
    PropertyFilterParams,
    PropertyUpdate,
    PublicPropertyResponse,
)
from app.services.property import VALID_TRANSITIONS


def test_property_reference_formatting():
    """Verify standard format PR-YYYY-XXXXXX."""
    assert format_property_reference(1, year=2026) == "PR-2026-000001"
    assert format_property_reference(9999, year=2026) == "PR-2026-009999"
    assert format_property_reference(123456, year=2025) == "PR-2025-123456"


def test_property_create_valid_schema():
    """Verify valid PropertyCreate instantiation and normalization."""
    data = {
        "title": "Luxury 3BHK Villa",
        "property_type": "Independent House / Villa",
        "transaction_type": "sale",
        "price": Decimal("12500000.00"),
        "district": "Coimbatore",
        "city": "Coimbatore",
        "locality": "RS Puram",
        "pincode": "641002",
        "bedrooms": 3,
        "bathrooms": 3,
        "built_up_area": Decimal("2400.00"),
        "latitude": Decimal("11.0168"),
        "longitude": Decimal("76.9558"),
        "owner_name": "Private Owner",
        "owner_phone": "+919876543210",
        "internal_notes": "Very motivated seller.",
    }
    schema = PropertyCreate(**data)
    assert schema.transaction_type == "SALE"
    assert schema.price == Decimal("12500000.00")
    assert schema.bedrooms == 3


def test_property_create_rejects_negative_price():
    """Reject negative price."""
    with pytest.raises(ValidationError):
        PropertyCreate(
            title="Invalid Villa",
            property_type="Villa",
            transaction_type="SALE",
            price=Decimal("-5000.00"),
            district="Coimbatore",
            city="Coimbatore",
            locality="RS Puram",
            pincode="641002",
        )


def test_property_create_rejects_invalid_transaction_type():
    """Reject unsupported transaction types."""
    with pytest.raises(ValidationError):
        PropertyCreate(
            title="Invalid Villa",
            property_type="Villa",
            transaction_type="AUCTION",
            price=Decimal("5000000.00"),
            district="Coimbatore",
            city="Coimbatore",
            locality="RS Puram",
            pincode="641002",
        )


def test_property_create_rejects_out_of_range_coordinates():
    """Latitude must be between -90 and 90, longitude between -180 and 180."""
    base_data = {
        "title": "Luxury Villa",
        "property_type": "Villa",
        "transaction_type": "SALE",
        "price": Decimal("5000000.00"),
        "district": "Coimbatore",
        "city": "Coimbatore",
        "locality=":"RS Puram",
        "pincode": "641002",
    }
    with pytest.raises(ValidationError):
        PropertyCreate(
            title="Luxury Villa",
            property_type="Villa",
            transaction_type="SALE",
            price=Decimal("5000000.00"),
            district="Coimbatore",
            city="Coimbatore",
            locality="RS Puram",
            pincode="641002",
            latitude=Decimal("95.000"),
        )

    with pytest.raises(ValidationError):
        PropertyCreate(
            title="Luxury Villa",
            property_type="Villa",
            transaction_type="SALE",
            price=Decimal("5000000.00"),
            district="Coimbatore",
            city="Coimbatore",
            locality="RS Puram",
            pincode="641002",
            longitude=Decimal("-195.000"),
        )


def test_public_property_response_strictly_omits_private_fields():
    """Verify PublicPropertyResponse excludes owner info, notes, and internal UUID."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000042",
        title="Commercial Space",
        property_type="Commercial",
        transaction_type="RENT",
        status="PUBLISHED",
        price=Decimal("85000.00"),
        price_negotiable=True,
        district="Coimbatore",
        city="Coimbatore",
        locality="Gandhipuram",
        pincode="641012",
        owner_name="Confidential Landlord",
        owner_phone="+919876543210",
        owner_email="landlord@example.com",
        inventory_source="Direct Call",
        advertisement_authorized=True,
        internal_notes="Do not disturb after 8 PM",
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    public_resp = PublicPropertyResponse.model_validate(prop)
    dumped = public_resp.model_dump()

    # Public fields present
    assert dumped["public_reference"] == "PR-2026-000042"
    assert dumped["title"] == "Commercial Space"
    assert dumped["price"] == Decimal("85000.00")

    # Sensitive/internal fields absent
    assert "id" not in dumped
    assert "owner_name" not in dumped
    assert "owner_phone" not in dumped
    assert "owner_email" not in dumped
    assert "inventory_source" not in dumped
    assert "internal_notes" not in dumped
    assert "advertisement_authorized" not in dumped
    assert "is_archived" not in dumped


def test_private_property_response_includes_private_fields():
    """Verify PrivatePropertyResponse includes internal UUID, owner details, and notes."""
    prop_id = uuid.uuid4()
    prop = Property(
        id=prop_id,
        public_reference="PR-2026-000042",
        title="Commercial Space",
        property_type="Commercial",
        transaction_type="RENT",
        status="PUBLISHED",
        price=Decimal("85000.00"),
        price_negotiable=True,
        district="Coimbatore",
        city="Coimbatore",
        locality="Gandhipuram",
        pincode="641012",
        owner_name="Confidential Landlord",
        owner_phone="+919876543210",
        owner_email="landlord@example.com",
        inventory_source="Direct Call",
        advertisement_authorized=True,
        internal_notes="Do not disturb after 8 PM",
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    private_resp = PrivatePropertyResponse.model_validate(prop)
    dumped = private_resp.model_dump()

    assert dumped["id"] == prop_id
    assert dumped["owner_name"] == "Confidential Landlord"
    assert dumped["owner_phone"] == "+919876543210"
    assert dumped["internal_notes"] == "Do not disturb after 8 PM"


def test_lifecycle_transition_rules_definition():
    """Verify valid transitions match the specification state machine."""
    assert VALID_TRANSITIONS["DRAFT"] == {"PUBLISHED", "ARCHIVED"}
    assert VALID_TRANSITIONS["PUBLISHED"] == {"PAUSED", "SOLD", "RENTED", "ARCHIVED"}
    assert VALID_TRANSITIONS["PAUSED"] == {"PUBLISHED", "ARCHIVED"}
    assert VALID_TRANSITIONS["SOLD"] == {"ARCHIVED"}
    assert VALID_TRANSITIONS["RENTED"] == {"ARCHIVED"}
    assert VALID_TRANSITIONS["ARCHIVED"] == set()

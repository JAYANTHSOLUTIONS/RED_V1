"""Unit tests for Lead Pydantic schemas and lifecycle rules."""
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.lead import LeadCreate, LeadLostPayload, LeadUpdate
from app.services.lead import LEAD_VALID_TRANSITIONS


def test_lead_create_valid():
    client_id = uuid.uuid4()
    lead_in = LeadCreate(
        client_id=client_id,
        source="  WEBSITE  ",
        notes="Looking for villa",
    )
    assert lead_in.client_id == client_id
    assert lead_in.source == "WEBSITE"
    assert lead_in.property_id is None


def test_lead_create_empty_source():
    client_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        LeadCreate(client_id=client_id, source="   ")


def test_lead_update_cannot_mutate_status():
    """Verify that LeadUpdate schema has no status field, preventing unrestricted status changes."""
    assert "status" not in LeadUpdate.model_fields


def test_lead_lost_payload_validation():
    payload = LeadLostPayload(lost_reason="  Client purchased elsewhere  ")
    assert payload.lost_reason == "Client purchased elsewhere"

    with pytest.raises(ValidationError):
        LeadLostPayload(lost_reason="   ")


def test_lead_lifecycle_matrix():
    """Verify the expected valid transition table matches specification."""
    assert "CONTACTED" in LEAD_VALID_TRANSITIONS["NEW"]
    assert "LOST" in LEAD_VALID_TRANSITIONS["NEW"]
    assert "CONVERTED" not in LEAD_VALID_TRANSITIONS["NEW"]

    assert "INTERESTED" in LEAD_VALID_TRANSITIONS["CONTACTED"]
    assert "LOST" in LEAD_VALID_TRANSITIONS["CONTACTED"]

    assert "SITE_VISIT" in LEAD_VALID_TRANSITIONS["INTERESTED"]
    assert "LOST" in LEAD_VALID_TRANSITIONS["INTERESTED"]

    assert "NEGOTIATION" in LEAD_VALID_TRANSITIONS["SITE_VISIT"]
    assert "LOST" in LEAD_VALID_TRANSITIONS["SITE_VISIT"]

    assert "CONVERTED" in LEAD_VALID_TRANSITIONS["NEGOTIATION"]
    assert "LOST" in LEAD_VALID_TRANSITIONS["NEGOTIATION"]

    assert len(LEAD_VALID_TRANSITIONS["CONVERTED"]) == 0
    assert len(LEAD_VALID_TRANSITIONS["LOST"]) == 0

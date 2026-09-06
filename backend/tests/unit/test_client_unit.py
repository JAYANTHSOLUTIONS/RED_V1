"""Unit tests for Client Pydantic schemas and validation."""
import pytest
from pydantic import ValidationError

from app.schemas.client import ClientCreate, ClientUpdate


def test_client_create_valid():
    payload = {
        "full_name": "  Ramesh Kumar  ",
        "phone": " +91 9876543210 ",
        "email": "ramesh@example.com",
        "preferred_contact_method": "whatsapp",
        "classification": "buyer",
        "notes": "Interested in 3BHK villas",
    }
    client_in = ClientCreate(**payload)
    assert client_in.full_name == "Ramesh Kumar"
    assert client_in.phone == "+91 9876543210"
    assert client_in.preferred_contact_method == "WHATSAPP"
    assert client_in.classification == "BUYER"


def test_client_create_whitespace_only_name():
    with pytest.raises(ValidationError) as exc:
        ClientCreate(full_name="   ", phone="9876543210")
    assert "Field cannot be empty or whitespace-only." in str(exc.value)


def test_client_create_whitespace_only_phone():
    with pytest.raises(ValidationError) as exc:
        ClientCreate(full_name="John Doe", phone="   ")
    assert "Field cannot be empty or whitespace-only." in str(exc.value)


def test_client_create_invalid_email():
    with pytest.raises(ValidationError):
        ClientCreate(full_name="John Doe", phone="9876543210", email="not-an-email")


def test_client_create_invalid_contact_method():
    with pytest.raises(ValidationError) as exc:
        ClientCreate(
            full_name="John Doe",
            phone="9876543210",
            preferred_contact_method="CARRIER_PIGEON",
        )
    assert "Invalid contact method" in str(exc.value)


def test_client_create_invalid_classification():
    with pytest.raises(ValidationError) as exc:
        ClientCreate(
            full_name="John Doe",
            phone="9876543210",
            classification="SUPER_HERO",
        )
    assert "Invalid classification" in str(exc.value)


def test_client_update_whitespace_handling():
    update_in = ClientUpdate(full_name="  Jane Doe  ", preferred_contact_method="call")
    assert update_in.full_name == "Jane Doe"
    assert update_in.preferred_contact_method == "CALL"

    with pytest.raises(ValidationError):
        ClientUpdate(phone="   ")

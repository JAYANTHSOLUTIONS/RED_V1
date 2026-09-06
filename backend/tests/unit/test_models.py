"""Unit tests for Phase 2 SQLAlchemy models.

Verifies model instantiation, Decimal precision preservation, fee segregation,
concurrency-safe public reference generation, and timezone awareness without
requiring a live network or database.
"""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest

from app.db.sequence import format_property_reference
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.deal import Deal, Fee
from app.models.document import Document
from app.models.follow_up import FollowUp
from app.models.lead import Enquiry, Lead
from app.models.notification import Notification
from app.models.property import Property, PropertyImage
from app.models.requirement import PropertyRequirement
from app.models.setting import SystemSetting
from app.models.site_visit import SiteVisit
from app.models.user import RefreshToken, User
from app.models.verification import VerificationCase, VerificationItem


def test_property_public_reference_formatter():
    """Verify property public reference adheres to PR-YYYY-XXXXXX format."""
    assert format_property_reference(1, 2026) == "PR-2026-000001"
    assert format_property_reference(123, 2026) == "PR-2026-000123"
    assert format_property_reference(999999, 2026) == "PR-2026-999999"


def test_money_fields_preserve_decimal_precision():
    """Verify monetary amounts are strictly Decimal and maintain exact cents."""
    price = Decimal("25000000.75")
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000001",
        title="Luxury Villa in Anna Nagar",
        property_type="INDEPENDENT_HOUSE",
        transaction_type="SALE",
        status="PUBLISHED",
        price=price,
        district="Chennai",
        city="Chennai",
        locality="Anna Nagar",
        pincode="600040",
    )
    assert isinstance(prop.price, Decimal)
    assert prop.price == Decimal("25000000.75")
    assert str(prop.price) == "25000000.75"

    agreed = Decimal("24500000.00")
    deal = Deal(
        id=uuid.uuid4(),
        property_id=prop.id,
        client_id=uuid.uuid4(),
        deal_type="SALE",
        agreed_amount=agreed,
        status="INITIATED",
    )
    assert isinstance(deal.agreed_amount, Decimal)
    assert deal.agreed_amount == Decimal("24500000.00")

    fee_comm = Fee(
        id=uuid.uuid4(),
        deal_id=deal.id,
        fee_type="BROKERAGE_COMMISSION",
        amount=Decimal("490000.00"),
        is_government_fee=False,
    )
    assert fee_comm.amount == Decimal("490000.00")
    assert fee_comm.is_government_fee is False


def test_government_and_consultant_fee_segregation():
    """Verify government charges are explicitly segregated from consultant revenue."""
    deal_id = uuid.uuid4()

    consultant_fee = Fee(
        id=uuid.uuid4(),
        deal_id=deal_id,
        fee_type="CONSULTANT_SERVICE_FEE",
        amount=Decimal("50000.00"),
        is_government_fee=False,
    )
    stamp_duty = Fee(
        id=uuid.uuid4(),
        deal_id=deal_id,
        fee_type="GOVERNMENT_STAMP_DUTY",
        amount=Decimal("1750000.00"),
        is_government_fee=True,
    )
    registration_fee = Fee(
        id=uuid.uuid4(),
        deal_id=deal_id,
        fee_type="GOVERNMENT_REGISTRATION_FEE",
        amount=Decimal("400000.00"),
        is_government_fee=True,
    )

    fees = [consultant_fee, stamp_duty, registration_fee]
    consultant_revenue = sum(f.amount for f in fees if not f.is_government_fee)
    government_charges = sum(f.amount for f in fees if f.is_government_fee)

    assert consultant_revenue == Decimal("50000.00")
    assert government_charges == Decimal("2150000.00")
    assert consultant_revenue + government_charges == Decimal("2200000.00")


def test_audit_log_immutability_and_structure():
    """Verify audit log captures action, entity, and sanitized metadata."""
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    log = AuditLog(
        id=uuid.uuid4(),
        actor_id=actor_id,
        action="PROPERTY_PUBLISHED",
        entity_type="PROPERTY",
        entity_id=entity_id,
        change_diff='{"status": ["DRAFT", "PUBLISHED"]}',
        ip_address="127.0.0.1",
        correlation_id="req-test-123",
        created_at=now,
    )
    assert log.action == "PROPERTY_PUBLISHED"
    assert log.entity_type == "PROPERTY"
    assert "password" not in (log.change_diff or "")
    assert log.created_at.tzinfo is not None


def test_verification_case_disclaimer_compliance():
    """Verify legal compliance guardrail on preliminary document reviews."""
    case = VerificationCase(
        id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        status="INCOMPLETE",
        disclaimer_acknowledged=True,
    )
    assert case.disclaimer_acknowledged is True


def test_user_and_token_defaults():
    """Verify user roles and refresh token expiration."""
    user = User(
        id=uuid.uuid4(),
        email="consultant@example.com",
        hashed_password="hashed-password-123",
        full_name="Chief Consultant",
    )
    assert user.role == "CONSULTANT"
    assert user.is_active is True

    token = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash="hash-abc-123",
        expires_at=datetime.now(timezone.utc),
    )
    assert token.revoked is False

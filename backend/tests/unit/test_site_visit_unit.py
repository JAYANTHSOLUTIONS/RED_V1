"""Unit tests for Site Visit coordination logic, state machine, intervals, and timezone."""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from pydantic import ValidationError

from app.core.exceptions import ValidationAppError
from app.schemas.site_visit import (
    SiteVisitCancel,
    SiteVisitCreate,
    SiteVisitFilterParams,
    SiteVisitReschedule,
    VALID_STATUSES,
)
from app.services.site_visit import (
    CONFLICT_BUFFER_MINUTES,
    KOLKATA_TZ,
    VALID_TRANSITIONS,
    normalize_datetime,
)


def test_site_visit_statuses_and_transitions_definition():
    """Verify state machine transitions conform to the master specification."""
    assert VALID_STATUSES == {"REQUESTED", "CONFIRMED", "COMPLETED", "CANCELLED", "RESCHEDULED"}

    # REQUESTED transitions
    assert "CONFIRMED" in VALID_TRANSITIONS["REQUESTED"]
    assert "CANCELLED" in VALID_TRANSITIONS["REQUESTED"]
    assert "RESCHEDULED" in VALID_TRANSITIONS["REQUESTED"]
    assert "COMPLETED" not in VALID_TRANSITIONS["REQUESTED"]  # Cannot complete without confirmation

    # CONFIRMED transitions
    assert "COMPLETED" in VALID_TRANSITIONS["CONFIRMED"]
    assert "CANCELLED" in VALID_TRANSITIONS["CONFIRMED"]
    assert "RESCHEDULED" in VALID_TRANSITIONS["CONFIRMED"]

    # Terminal states
    assert len(VALID_TRANSITIONS["COMPLETED"]) == 0
    assert len(VALID_TRANSITIONS["CANCELLED"]) == 0
    assert len(VALID_TRANSITIONS["RESCHEDULED"]) == 0


def test_timezone_normalization():
    """Verify naive datetimes default to Asia/Kolkata (IST) and aware datetimes are preserved in UTC."""
    # 1. Naive datetime: 10:00 AM on 2026-10-15
    naive_dt = datetime(2026, 10, 15, 10, 0, 0)
    normalized = normalize_datetime(naive_dt)

    assert normalized.tzinfo == timezone.utc
    # 10:00 IST is 04:30 UTC
    assert normalized.hour == 4
    assert normalized.minute == 30
    assert normalized.day == 15

    # 2. Aware datetime in IST
    ist_dt = datetime(2026, 10, 15, 10, 0, 0, tzinfo=KOLKATA_TZ)
    normalized_ist = normalize_datetime(ist_dt)
    assert normalized_ist == normalized

    # 3. Aware datetime in UTC
    utc_dt = datetime(2026, 10, 15, 4, 30, 0, tzinfo=timezone.utc)
    assert normalize_datetime(utc_dt) == normalized


def test_conflict_interval_math():
    """Verify that interval overlap follows [T - buffer, T + buffer] exclusive."""
    buffer = timedelta(minutes=CONFLICT_BUFFER_MINUTES)
    base_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc)

    # Overlapping intervals: delta < 60 min
    overlap_cases = [
        base_time,                                        # Exact same time
        base_time + timedelta(minutes=30),               # 10:30 (overlaps 10:00-11:00)
        base_time - timedelta(minutes=30),               # 09:30 (overlaps 10:00-11:00)
        base_time + timedelta(minutes=59),               # 10:59
        base_time - timedelta(minutes=59),               # 09:01
    ]

    for t in overlap_cases:
        diff = abs(t - base_time)
        assert diff < buffer, f"Expected {t} to conflict with {base_time}"

    # Non-overlapping boundary cases: delta >= 60 min
    touching_and_disjoint = [
        base_time + timedelta(minutes=60),               # 11:00 touching boundary
        base_time - timedelta(minutes=60),               # 09:00 touching boundary
        base_time + timedelta(minutes=90),               # 11:30
        base_time - timedelta(hours=2),                  # 08:00
        base_time + timedelta(days=1),                   # Next day
    ]

    for t in touching_and_disjoint:
        diff = abs(t - base_time)
        assert diff >= buffer, f"Expected {t} NOT to conflict with {base_time}"


def test_schema_validations():
    """Verify schema constraints on cancel and create payloads."""
    # Cancellation requires reason with at least 3 chars
    with pytest.raises(ValidationError):
        SiteVisitCancel(cancellation_reason="")

    with pytest.raises(ValidationError):
        SiteVisitCancel(cancellation_reason="no")

    valid_cancel = SiteVisitCancel(cancellation_reason="Client had a family emergency")
    assert valid_cancel.cancellation_reason == "Client had a family emergency"

    # Creation with invalid initial status
    with pytest.raises(ValidationError):
        SiteVisitCreate(
            client_id=uuid.uuid4(),
            property_id=uuid.uuid4(),
            scheduled_at=datetime.now(timezone.utc),
            status="COMPLETED",  # Invalid initial status
        )


def test_filter_params_initialization():
    """Verify filter params parsing and defaults."""
    params = SiteVisitFilterParams(
        status="  confirmed  ",
        limit=50,
        offset=10,
        upcoming_only=True,
    )
    assert params.status == "CONFIRMED"
    assert params.limit == 50
    assert params.offset == 10
    assert params.upcoming_only is True

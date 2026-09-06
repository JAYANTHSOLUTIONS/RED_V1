"""Unit tests for Follow-up state machine, target validations, and timezone handling."""
from datetime import datetime, timezone
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.follow_up import (
    VALID_ACTION_TYPES,
    VALID_STATUSES,
    FollowUpCreate,
    FollowUpFilterParams,
    FollowUpUpdate,
)
from app.services.follow_up import (
    KOLKATA_TZ,
    VALID_TRANSITIONS,
    normalize_datetime,
)


def test_follow_up_constants_and_transitions():
    """Verify action types, statuses, and valid state transitions."""
    assert VALID_ACTION_TYPES == {
        "CALL",
        "SEND_DOCS",
        "ARRANGE_VISIT",
        "OWNER_FOLLOW_UP",
        "MISSING_PAPERWORK",
    }
    assert VALID_STATUSES == {"SCHEDULED", "COMPLETED", "MISSED"}

    # Allowed transitions
    assert VALID_TRANSITIONS["SCHEDULED"] == {"COMPLETED", "MISSED"}
    assert len(VALID_TRANSITIONS["COMPLETED"]) == 0
    assert len(VALID_TRANSITIONS["MISSED"]) == 0


def test_target_validation_rules():
    """Verify that a FollowUpCreate requires at least one target: client_id or lead_id."""
    scheduled_time = datetime.now(timezone.utc)

    # 1. Valid with only client_id
    f1 = FollowUpCreate(
        client_id=uuid.uuid4(),
        action_type="CALL",
        scheduled_at=scheduled_time,
    )
    assert f1.client_id is not None
    assert f1.lead_id is None

    # 2. Valid with only lead_id
    f2 = FollowUpCreate(
        lead_id=uuid.uuid4(),
        action_type="SEND_DOCS",
        scheduled_at=scheduled_time,
    )
    assert f2.lead_id is not None
    assert f2.client_id is None

    # 3. Valid with both client_id and lead_id
    f3 = FollowUpCreate(
        client_id=uuid.uuid4(),
        lead_id=uuid.uuid4(),
        action_type="ARRANGE_VISIT",
        scheduled_at=scheduled_time,
    )
    assert f3.client_id is not None and f3.lead_id is not None

    # 4. Invalid with neither -> Must fail validation
    with pytest.raises(ValidationError) as exc_info:
        FollowUpCreate(
            action_type="CALL",
            scheduled_at=scheduled_time,
        )
    assert "Follow-up requires at least one target" in str(exc_info.value)


def test_action_type_validation():
    """Verify invalid action types are rejected."""
    scheduled_time = datetime.now(timezone.utc)
    client_id = uuid.uuid4()

    # Invalid action type
    with pytest.raises(ValidationError):
        FollowUpCreate(
            client_id=client_id,
            action_type="INVALID_ACTION",
            scheduled_at=scheduled_time,
        )

    # Valid action type is normalized to uppercase
    f = FollowUpCreate(
        client_id=client_id,
        action_type="  call  ",
        scheduled_at=scheduled_time,
    )
    assert f.action_type == "CALL"


def test_timezone_normalization():
    """Verify naive datetimes default to Asia/Kolkata and aware datetimes are converted to UTC."""
    naive_dt = datetime(2026, 11, 20, 14, 30, 0)
    normalized = normalize_datetime(naive_dt)

    assert normalized.tzinfo == timezone.utc
    # 14:30 IST is 09:00 UTC
    assert normalized.hour == 9
    assert normalized.minute == 0

    aware_ist = datetime(2026, 11, 20, 14, 30, 0, tzinfo=KOLKATA_TZ)
    assert normalize_datetime(aware_ist) == normalized


def test_filter_params():
    """Verify query filter params parsing and defaults."""
    params = FollowUpFilterParams(
        status="  scheduled  ",
        action_type="call",
        limit=50,
        offset=10,
    )
    assert params.status == "SCHEDULED"
    assert params.action_type == "CALL"
    assert params.limit == 50
    assert params.offset == 10

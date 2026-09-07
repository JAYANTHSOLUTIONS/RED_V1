"""Unit tests for audit sanitization engine and action catalog."""
import json
import pytest

from app.core.sanitizer import REDACTED_MARKER, sanitize_audit_diff, sanitize_data
from app.schemas.audit import AuditAction


def test_sanitize_data_redacts_sensitive_keys():
    """Verify that passwords, tokens, API keys, and secrets are replaced with [REDACTED]."""
    raw = {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "consultant@example.com",
        "password": "SuperSecretPassword123!",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$abc$def",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.signature",
        "refresh_token": "opaque_refresh_token_12345",
        "storage_secret_key": "my-aws-secret-key",
        "api_key": "private_api_key_value",
        "nested": {
            "smtp_password": "email_password",
            "normal_field": "safe_value",
        },
        "token_list": [
            {"token": "secret_in_list", "name": "item_1"},
            {"secret_key": "another_secret", "name": "item_2"},
        ],
    }

    sanitized = sanitize_data(raw)

    assert sanitized["password"] == REDACTED_MARKER
    assert sanitized["hashed_password"] == REDACTED_MARKER
    assert sanitized["access_token"] == REDACTED_MARKER
    assert sanitized["refresh_token"] == REDACTED_MARKER
    assert sanitized["storage_secret_key"] == REDACTED_MARKER
    assert sanitized["api_key"] == REDACTED_MARKER
    assert sanitized["nested"]["smtp_password"] == REDACTED_MARKER
    assert sanitized["nested"]["normal_field"] == "safe_value"
    assert sanitized["token_list"][0]["token"] == REDACTED_MARKER
    assert sanitized["token_list"][0]["name"] == "item_1"
    assert sanitized["token_list"][1]["secret_key"] == REDACTED_MARKER
    assert sanitized["user_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert sanitized["email"] == "consultant@example.com"


def test_sanitize_data_redacts_jwt_and_bearer_strings():
    """Verify inline JWT patterns and Bearer strings inside plain text are masked."""
    jwt_str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN_p_placeholder_sample_sig"
    raw_str = f"Error communicating with service using {jwt_str}."
    sanitized_str = sanitize_data(raw_str)
    assert REDACTED_MARKER in sanitized_str
    assert "eyJ" not in sanitized_str

    bearer_str = "Headers: Authorization: Bearer my_secret_token_123"
    sanitized_bearer = sanitize_data(bearer_str)
    assert f"Bearer {REDACTED_MARKER}" in sanitized_bearer


def test_sanitize_audit_diff_handles_json_and_none():
    """Verify sanitize_audit_diff produces clean JSON and handles None gracefully."""
    assert sanitize_audit_diff(None) is None
    assert sanitize_audit_diff("") is None
    assert sanitize_audit_diff("   ") is None

    diff_dict = {"status": "ACTIVE", "password": "confidential"}
    diff_json = sanitize_audit_diff(diff_dict)
    assert diff_json is not None
    parsed = json.loads(diff_json)
    assert parsed["status"] == "ACTIVE"
    assert parsed["password"] == REDACTED_MARKER

    # JSON string input
    json_str_input = '{"token": "xyz123", "action": "UPDATE"}'
    diff_from_str = sanitize_audit_diff(json_str_input)
    assert diff_from_str is not None
    parsed_str = json.loads(diff_from_str)
    assert parsed_str["token"] == REDACTED_MARKER
    assert parsed_str["action"] == "UPDATE"


def test_audit_action_enum_completeness():
    """Verify standard action catalog defines essential operational actions."""
    assert AuditAction.AUTH_LOGIN_SUCCESS.value == "LOGIN_SUCCESS"
    assert AuditAction.AUTH_LOGIN_FAILURE.value == "LOGIN_FAILURE"
    assert AuditAction.PROPERTY_CREATED.value == "PROPERTY_CREATED"
    assert AuditAction.CLIENT_CREATED.value == "CLIENT_CREATED"
    assert AuditAction.LEAD_CREATED.value == "LEAD_CREATED"
    assert AuditAction.DOCUMENT_UPLOADED.value == "DOCUMENT_UPLOADED"
    assert AuditAction.VERIFICATION_REQUESTED.value == "VERIFICATION_REQUESTED"
    assert AuditAction.SITE_VISIT_CONFIRMED.value == "SITE_VISIT_CONFIRMED"
    assert AuditAction.FOLLOW_UP_COMPLETED.value == "FOLLOW_UP_COMPLETED"
    assert AuditAction.NOTIFICATION_CREATED.value == "NOTIFICATION_CREATED"

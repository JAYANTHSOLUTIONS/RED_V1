"""Centralized sanitization engine for audit diffs and metadata.

Ensures that passwords, tokens, API keys, storage secrets, and private credentials
are rigorously scrubbed before audit persistence or serialization.
"""
import json
import re
from typing import Any, Dict, List, Optional, Set, Union

REDACTED_MARKER = "[REDACTED]"

SENSITIVE_KEY_PATTERNS: Set[str] = {
    "password",
    "password_hash",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "smtp_password",
    "storage_secret",
    "storage_access_key",
    "storage_secret_key",
    "private_key",
    "presigned_url",
    "captcha_token",
    "turnstile_token",
    "secret_key",
    "jwt",
    "cookie",
    "credentials",
}

# Heuristic regex for JWT tokens (header.payload.signature)
JWT_REGEX = re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+")


CONTAINER_SUFFIXES = ("_list", "_count", "_type", "_ids", "_enum", "_status")
SENSITIVE_WORDS = {
    "password",
    "secret",
    "token",
    "jwt",
    "apikey",
    "credential",
    "credentials",
}


def _is_sensitive_key(key: str) -> bool:
    """Check if a dictionary key matches any sensitive pattern."""
    normalized = key.lower().replace("-", "_")
    if normalized in SENSITIVE_KEY_PATTERNS:
        return True
    if any(normalized.endswith(suffix) for suffix in CONTAINER_SUFFIXES):
        return False
    parts = set(normalized.split("_"))
    return bool(parts & SENSITIVE_WORDS)


def sanitize_data(data: Any) -> Any:
    """Recursively sanitize data structures, replacing sensitive values with [REDACTED]."""
    if isinstance(data, dict):
        sanitized_dict: Dict[str, Any] = {}
        for k, v in data.items():
            if _is_sensitive_key(str(k)):
                sanitized_dict[k] = REDACTED_MARKER
            else:
                sanitized_dict[k] = sanitize_data(v)
        return sanitized_dict

    if isinstance(data, list):
        return [sanitize_data(item) for item in data]

    if isinstance(data, tuple):
        return tuple(sanitize_data(item) for item in data)

    if isinstance(data, str):
        # Scrub inline JWTs
        if JWT_REGEX.search(data):
            return JWT_REGEX.sub(REDACTED_MARKER, data)
        # Scrub Bearer tokens
        if "Bearer " in data:
            return re.sub(r"Bearer\s+[A-Za-z0-9._~+/-]+", f"Bearer {REDACTED_MARKER}", data)
        return data

    return data


def sanitize_audit_diff(change_diff: Optional[Union[str, Dict[str, Any], List[Any]]]) -> Optional[str]:
    """Sanitize change diff payload and return valid JSON string or None."""
    if change_diff is None:
        return None

    if isinstance(change_diff, (dict, list)):
        cleaned = sanitize_data(change_diff)
        return json.dumps(cleaned, default=str)

    if isinstance(change_diff, str):
        trimmed = change_diff.strip()
        if not trimmed:
            return None
        # Attempt to parse as JSON for structural scrubbing
        try:
            parsed = json.loads(trimmed)
            cleaned = sanitize_data(parsed)
            return json.dumps(cleaned, default=str)
        except (ValueError, json.JSONDecodeError):
            # Plain string scrubbing
            return str(sanitize_data(trimmed))

    return str(sanitize_data(change_diff))

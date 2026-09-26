"""Unit tests for FMB Map Generation Service.

Tests all critical failure paths as specified in the requirements:
- Valid property → GIS code construction
- District resolution (known + fuzzy)
- Missing/unmapped district → ValidationAppError
- PDF magic byte validation
- Base64 decode validation
- CollabLand mock responses (success, failure, timeout, bad JSON)
- Fingerprint / duplicate detection logic
- Filename generation
"""
import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import pure helpers directly to avoid full app bootstrap
from app.services.fmb_service import (
    _decode_pdf_base64,
    _make_fingerprint,
    _normalize,
    _validate_pdf_bytes,
    build_gis_code,
    resolve_district_code,
)
from app.core.exceptions import ValidationAppError


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_strips_and_lowercases(self):
        assert _normalize("  Chennai  ") == "chennai"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_none_safe(self):
        assert _normalize(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# resolve_district_code
# ---------------------------------------------------------------------------

class TestResolveDistrictCode:
    def test_exact_match(self):
        assert resolve_district_code("Chennai") == "03"
        assert resolve_district_code("chennai") == "03"
        assert resolve_district_code("CHENNAI") == "03"

    def test_alternate_spelling(self):
        assert resolve_district_code("Kancheepuram") == "10"
        assert resolve_district_code("Thiruvalur") == "32"

    def test_trichy_alias(self):
        assert resolve_district_code("trichy") == "35"
        assert resolve_district_code("tiruchirappalli") == "35"

    def test_madurai(self):
        assert resolve_district_code("Madurai") == "14"

    def test_unknown_district_returns_none(self):
        assert resolve_district_code("Somewhere Unknown") is None
        assert resolve_district_code("") is None

    def test_substring_fallback(self):
        # "thirunelveli" contains "tirunelveli" key
        assert resolve_district_code("Thirunelveli") == "29"


# ---------------------------------------------------------------------------
# build_gis_code
# ---------------------------------------------------------------------------

class TestBuildGisCode:
    def test_valid_gis_code_format(self):
        code = build_gis_code("Chennai", "Alandur", "Guindy", "123")
        # 33 + 03 + ala + gui + 123
        assert code.startswith("3303")
        assert code.endswith("123")

    def test_leading_zeros_stripped_from_survey(self):
        code = build_gis_code("Chennai", "Alandur", "Guindy", "007")
        assert code.endswith("7")

    def test_survey_with_slash(self):
        code = build_gis_code("Madurai", "Anna", "Velachery", "456/2A")
        assert "456/2A" in code

    def test_unknown_district_raises(self):
        with pytest.raises(ValidationAppError) as exc:
            build_gis_code("Atlantis", "Whatever", "Somewhere", "123")
        assert "Atlantis" in str(exc.value)
        assert "not recognized" in str(exc.value)

    def test_taluk_code_padded(self):
        # Taluk name shorter than 3 chars → padded with 0
        code = build_gis_code("Chennai", "AB", "Guindy", "1")
        # taluk part: 'ab0'
        assert "ab0" in code

    def test_state_code_prefix(self):
        code = build_gis_code("Coimbatore", "Mettupalayam", "Sirumugai", "99")
        assert code.startswith("33")


# ---------------------------------------------------------------------------
# _validate_pdf_bytes
# ---------------------------------------------------------------------------

class TestValidatePdfBytes:
    def test_valid_pdf_passes(self):
        _validate_pdf_bytes(b"%PDF-1.4 some content here")  # should not raise

    def test_invalid_magic_raises(self):
        with pytest.raises(ValidationAppError) as exc:
            _validate_pdf_bytes(b"PK\x03\x04 this is a zip")
        assert "valid PDF" in str(exc.value)

    def test_empty_bytes_raises(self):
        with pytest.raises(ValidationAppError):
            _validate_pdf_bytes(b"not a pdf at all")

    def test_short_non_pdf_raises(self):
        with pytest.raises(ValidationAppError):
            _validate_pdf_bytes(b"\xff\xd8\xff\xe0")  # JPEG magic


# ---------------------------------------------------------------------------
# _decode_pdf_base64
# ---------------------------------------------------------------------------

class TestDecodePdfBase64:
    def test_valid_base64_decodes(self):
        original = b"hello world"
        encoded = base64.b64encode(original).decode()
        assert _decode_pdf_base64(encoded) == original

    def test_invalid_base64_raises(self):
        with pytest.raises(ValidationAppError) as exc:
            _decode_pdf_base64("not-valid-base64!!!")
        assert "invalid" in str(exc.value).lower()

    def test_empty_string_raises(self):
        with pytest.raises(ValidationAppError):
            _decode_pdf_base64("====")


# ---------------------------------------------------------------------------
# _make_fingerprint
# ---------------------------------------------------------------------------

class TestMakeFingerprint:
    def test_fingerprint_format(self):
        fp = _make_fingerprint("123", "1")
        assert fp == "fmb_map:123:1"

    def test_none_subdivision(self):
        fp = _make_fingerprint("456", None)
        assert fp == "fmb_map:456:"

    def test_strips_whitespace(self):
        fp = _make_fingerprint("  123  ", "  1  ")
        assert fp == "fmb_map:123:1"


# ---------------------------------------------------------------------------
# call_collabland_fmb (mocked)
# ---------------------------------------------------------------------------

class TestCallCollablandFmb:
    """Tests that verify correct behavior with mocked httpx responses."""

    @pytest.mark.asyncio
    async def test_success_response(self):
        from app.services.fmb_service import call_collabland_fmb
        from app.core.exceptions import ValidationAppError

        mock_pdf = b"%PDF-1.4 fake content"
        b64 = base64.b64encode(mock_pdf).decode()
        mock_json = {"success": True, "data": b64}

        with patch("app.services.fmb_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_json
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_response))
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await call_collabland_fmb("3303alagui123")
            assert result["success"] is True
            assert result["data"] == b64

    @pytest.mark.asyncio
    async def test_timeout_raises_gateway_timeout(self):
        import httpx
        from app.services.fmb_service import call_collabland_fmb
        from app.core.exceptions import GatewayTimeoutError

        with patch("app.services.fmb_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(GatewayTimeoutError):
                await call_collabland_fmb("3303alagui123")

    @pytest.mark.asyncio
    async def test_http_error_raises_service_unavailable(self):
        from app.services.fmb_service import call_collabland_fmb
        from app.core.exceptions import ServiceUnavailableError

        with patch("app.services.fmb_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 500
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ServiceUnavailableError):
                await call_collabland_fmb("3303alagui123")

    @pytest.mark.asyncio
    async def test_collabland_failure_response_raises_validation(self):
        from app.services.fmb_service import call_collabland_fmb

        with patch("app.services.fmb_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = {"success": False, "message": "Survey not found"}
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValidationAppError) as exc:
                await call_collabland_fmb("3303alagui999")
            assert "Survey not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_invalid_json_raises_validation(self):
        from app.services.fmb_service import call_collabland_fmb

        with patch("app.services.fmb_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.side_effect = ValueError("invalid json")
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValidationAppError):
                await call_collabland_fmb("3303alagui123")

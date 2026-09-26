"""
Unit tests for TNEC Service & Hierarchy.
"""

import pytest
from app.services import tnec_service
from app.schemas.tnec import SurveySubdivisionItem, TnecScrapeRequest


def test_tnec_hierarchy_zones():
    zones = tnec_service.get_zones()
    assert isinstance(zones, list)
    assert len(zones) >= 2
    zone_names = [z["name"] for z in zones]
    assert "Chengalpattu" in zone_names
    assert "Chennai" in zone_names


def test_tnec_hierarchy_districts():
    # Zone 15 is Chengalpattu
    districts = tnec_service.get_districts("15")
    assert len(districts) >= 1
    dist_names = [d["name"] for d in districts]
    assert any("Chengalpattu" in name or "Kancheepuram" in name for name in dist_names)


def test_tnec_hierarchy_sros_and_villages():
    # Find SRO under District 20004 (Chengalpattu)
    sros = tnec_service.get_sros("15", "20004")
    assert len(sros) >= 1
    sro_id = sros[0]["id"]
    assert ":" in sro_id or len(sro_id) > 0

    # Find Villages under this SRO
    villages = tnec_service.get_villages(sro_id)
    assert len(villages) >= 1
    assert "name" in villages[0]
    assert "id" in villages[0]


def test_tnec_scrape_request_model():
    req = TnecScrapeRequest(
        zone_id="15",
        district_id="20004",
        sro_id="20088:1",
        village_id="961",
        start_date="01/01/2000",
        end_date="09/09/2026",
        surveys=[
            SurveySubdivisionItem(survey_no="217", sub_division_no="6"),
            SurveySubdivisionItem(survey_no="217", sub_division_no="1B2")
        ]
    )
    assert req.zone_id == "15"
    assert len(req.surveys) == 2
    assert req.surveys[0].survey_no == "217"

"""Unit tests for TNGIS Land & Revenue extraction parser."""
import pytest
from app.services.tngis_parser import load_tngis_results, parse_tngis_content


def test_tngis_parser_from_file():
    """Verify that tngis_map_results.txt is parsed accurately into structured models."""
    res = load_tngis_results()
    assert res is not None

    # Owners
    assert len(res.owners) == 3
    assert res.owners[0].index == 1
    assert res.owners[0].owner == "ராமலிங்கம்"
    assert res.owners[0].relative == "நாகப்பன்"
    assert res.owners[0].relation == "மகன்"

    assert res.owners[1].owner == "நடராஜன்"
    assert res.owners[2].owner == "தேவராஜன்"

    # Land details
    assert res.land_details.patta_number == "614"
    assert "ரயத்துவாரி" in res.land_details.land_type
    assert res.land_details.extent_hectares == "0"
    assert res.land_details.extent_ares == "2"
    assert res.land_details.total_tax == "0.08"
    assert res.land_details.soil_class == "4"

    # Coordinates
    assert res.coordinates is not None
    assert res.coordinates.latitude == 12.801274
    assert res.coordinates.longitude == 79.810308
    assert "https://www.google.com/maps?q=" in res.coordinates.google_maps_url

    # Guideline valuation
    assert res.guideline_value.metric_rate == "₹55,00,000"
    assert res.guideline_value.guideline_amount == "₹55,00,000"


def test_tngis_parser_search_overrides():
    """Verify that querying a different parcel does not return old owners, and sample parcel returns verified owners."""
    # 1. Uncached survey parcel should NOT return Walajabad 217's owners
    res = load_tngis_results(search_params={
        "district": "Coimbatore",
        "taluk": "Pollachi",
        "village": "Anamalai",
        "survey_number": "100",
        "subdivision": "3A",
    })
    assert res.search["district"] == "Coimbatore"
    assert res.search["taluk"] == "Pollachi"
    assert res.search["village"] == "Anamalai"
    assert res.search["survey_number"] == "100"
    assert res.search["subdivision"] == "3A"
    assert len(res.owners) == 0
    assert res.land_details.patta_number == ""
    assert res.is_cached_sample is False

    # 2. Sample Walajabad 217/1B2 should return verified dataset
    sample_res = load_tngis_results(search_params={
        "district": "Kancheepuram",
        "taluk": "Walajabad",
        "village": "Walajabad",
        "survey_number": "217",
        "subdivision": "1B2",
    })
    assert len(sample_res.owners) == 3
    assert sample_res.owners[0].owner == "ராமலிங்கம்"
    assert sample_res.land_details.patta_number == "614"
    assert sample_res.is_cached_sample is True

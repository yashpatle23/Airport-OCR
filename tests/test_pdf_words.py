import json
from pathlib import Path

import pytest

from airport_ocr.pdf_words import (
    expand_taxiway_ranges,
    extract_from_words,
    parse_taxiway_legend,
)
from airport_ocr.pipeline import normalize

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vobl-words-sample.json"


@pytest.fixture
def words_dump():
    with SAMPLE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_expand_taxiway_ranges():
    assert expand_taxiway_ranges("H1 to H10") == "H1 H2 H3 H4 H5 H6 H7 H8 H9 H10"
    assert expand_taxiway_ranges("A, B") == "A, B"


def test_parse_taxiway_legend_widths():
    text = "23 M WIDE TAXIWAY- A, A1, H1 to H3, M 15 M WIDE TAXIWAY - B3 NOTE:"
    features = parse_taxiway_legend(text)
    by_id = {f["designator"]: f["width"]["value"] for f in features}
    assert by_id["A"] == 23
    assert by_id["H2"] == 23
    assert by_id["M"] == 23
    assert by_id["B3"] == 15


def test_extract_airport_and_runways(words_dump):
    doc = extract_from_words(words_dump)
    assert doc["airport_icao"] == "VOBL"
    assert doc["operational_use"] is False
    assert doc["airport"]["arp"]["latitude_source"].startswith("13")
    assert {r["designator_pair"] for r in doc["runways"]} == {"09L/27R", "09R/27L"}

    thresholds = {
        d["designator"]: d["threshold"]
        for r in doc["runways"]
        for d in r["directions"]
    }
    # Authoritative native-text values (correct the earlier raster guesses).
    assert thresholds["09L"]["latitude_source"] == "13\u00b012'25.79\" N"
    assert thresholds["27L"]["latitude_source"] == "13\u00b011'21.89\" N"
    assert thresholds["27L"]["longitude_source"] == "077\u00b043'36.74\" E"
    assert thresholds["09L"]["elevation"]["value"] == 3003
    assert thresholds["27R"]["tdz_elevation"]["value"] == 2937


def test_extract_taxiway_inventory(words_dump):
    doc = extract_from_words(words_dump)
    designators = [f["designator"] for f in doc["taxiways"]["features"]]
    assert len(designators) == 43
    assert len(set(designators)) == 43
    assert "B3" in designators and "H10" in designators and "A11" in designators
    b3 = next(f for f in doc["taxiways"]["features"] if f["designator"] == "B3")
    assert b3["width"]["value"] == 15
    a = next(f for f in doc["taxiways"]["features"] if f["designator"] == "A")
    assert a["width"]["value"] == 23


def test_extract_holding_positions_remain_blocked(words_dump):
    doc = extract_from_words(words_dump)
    hp = doc["runway_holding_positions"]
    assert hp["features"] == []
    assert hp["completeness_status"] == "BLOCKED_SOURCE_BYTES_REQUIRED"
    assert hp["empty_array_semantics"] == "NOT_EXTRACTED_NOT_ABSENT"


def test_extracted_document_passes_pipeline(words_dump):
    doc = extract_from_words(words_dump)
    normalized, geojson, report = normalize(doc)
    assert report["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert report["failure_count"] == 0
    assert normalized["taxiways"]["count"] == 43
    # Taxiways are text-only; the GeoJSON keeps 7 geometry features + inventory list.
    assert len(geojson["features"]) == 7
    assert len(geojson["properties"]["taxiway_inventory"]) == 43
    assert normalized["airport"]["elevation"]["selected_value"] is None


def test_extractor_accepts_page_list(words_dump):
    doc = extract_from_words([words_dump])
    assert doc["airport_icao"] == "VOBL"
    assert len(doc["taxiways"]["features"]) == 43

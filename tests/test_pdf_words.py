import json
from pathlib import Path

import pytest

from airport_ocr.pdf_words import (
    ExtractionError,
    expand_taxiway_ranges,
    extract_from_words,
    parse_taxiway_legend,
)
from airport_ocr.pipeline import normalize

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vobl-words-sample.json"
VOMM_SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "vomm-synthetic-words.json"


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
    doc = extract_from_words(words_dump, profile="vobl-sample")
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
    doc = extract_from_words(words_dump, profile="vobl-sample")
    designators = [f["designator"] for f in doc["taxiways"]["features"]]
    assert len(designators) == 43
    assert len(set(designators)) == 43
    assert "B3" in designators and "H10" in designators and "A11" in designators
    b3 = next(f for f in doc["taxiways"]["features"] if f["designator"] == "B3")
    assert b3["width"]["value"] == 15
    a = next(f for f in doc["taxiways"]["features"] if f["designator"] == "A")
    assert a["width"]["value"] == 23


def test_extract_holding_positions_remain_blocked(words_dump):
    doc = extract_from_words(words_dump, profile="vobl-sample")
    hp = doc["runway_holding_positions"]
    assert hp["features"] == []
    assert hp["completeness_status"] == "BLOCKED_SOURCE_BYTES_REQUIRED"
    assert hp["empty_array_semantics"] == "NOT_EXTRACTED_NOT_ABSENT"


def test_extracted_document_passes_pipeline(words_dump):
    doc = extract_from_words(words_dump, profile="vobl-sample")
    normalized, geojson, report = normalize(doc)
    assert report["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert report["failure_count"] == 0
    assert normalized["taxiways"]["count"] == 43
    # Taxiways are text-only; the GeoJSON keeps 7 geometry features + inventory list.
    assert len(geojson["features"]) == 7
    assert len(geojson["properties"]["taxiway_inventory"]) == 43
    assert normalized["airport"]["elevation"]["selected_value"] is None


def test_extractor_accepts_page_list(words_dump):
    doc = extract_from_words([words_dump], profile="vobl-sample")
    assert doc["airport_icao"] == "VOBL"
    assert len(doc["taxiways"]["features"]) == 43



def test_taxiway_legend_rejects_prose_tokens():
    assert parse_taxiway_legend("23 M WIDE TAXIWAYS - A AND B FOR RWY 07") == []


def test_auto_profile_never_injects_vobl_compatibility_facts(words_dump):
    doc = extract_from_words(words_dump, profile="auto")
    assert doc["extraction"]["profile"] == "auto"
    assert all(runway["length"]["value"] is None for runway in doc["runways"])
    assert len(doc["airport"]["elevation"]["claims"]) == 1
    assert doc["airport"]["name"]["status"] == "NOT_EXTRACTED_PLACEHOLDER"
    assert "Bengaluru" not in doc["airport"]["name"]["value"]


def test_header_arp_is_not_changed_by_runway_block_order(words_dump):
    words_dump["words"] = sorted(
        words_dump["words"], key=lambda word: 0 if word[5] == 806 else 1
    )
    doc = extract_from_words(words_dump, profile="auto")
    assert doc["airport"]["arp"]["latitude_source"] == "13° 11' 56\" N"
    assert doc["airport"]["arp"]["longitude_source"] == "077° 42' 20\" E"
    assert doc["airport"]["arp"]["evidence"]["block"] == 901


def test_missing_runway_bearing_is_controlled_extraction_error(words_dump):
    words_dump["words"] = [
        word for word in words_dump["words"] if not (word[5] == 806 and word[6] == 1)
    ]
    with pytest.raises(ExtractionError, match="displayed runway bearing not found for 09L"):
        extract_from_words(words_dump, profile="auto")


def test_vomm_synthetic_multi_layout_regression():
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    doc = extract_from_words(dump, profile="auto")

    assert doc["airport_icao"] == "VOMM"
    assert doc["airport"]["name"]["value"] == "Chennai International Airport"
    assert doc["airport"]["name"]["status"] == "EXTRACTED_FROM_NATIVE_TEXT"
    assert doc["source"]["displayed_date"] == "30 NOV 2023"
    assert doc["extraction"]["status"] == "PARTIAL"
    assert {r["designator_pair"] for r in doc["runways"]} == {"07/25", "12/30"}
    dimensions = {
        r["designator_pair"]: (r["length"]["value"], r["width"]["value"])
        for r in doc["runways"]
    }
    assert dimensions == {"07/25": (3658, 45), "12/30": (2890, 45)}
    thresholds = {
        d["designator"]: d["threshold"]
        for runway in doc["runways"]
        for d in runway["directions"]
    }
    assert {key: value["elevation"]["value"] for key, value in thresholds.items()} == {
        "07": 43, "25": 54, "12": 44, "30": 48
    }
    assert all(value["tdz_elevation"]["value"] is None for value in thresholds.values())
    assert [feature["designator"] for feature in doc["taxiways"]["features"]] == [
        "B", "C", "E", "F", "G", "I", "M"
    ]

    normalized, _, report = normalize(doc)
    assert normalized["extraction"]["status"] == "PARTIAL"
    assert report["failure_count"] == 0


def test_user_supplied_name_keeps_fallback_provenance():
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    dump["words"] = [
        word for word in dump["words"] if not (word[5] == 100 and word[6] == 1)
    ]
    doc = extract_from_words(dump, profile="auto", airport_name="Reviewed Chennai Name")
    assert doc["airport"]["status"] == "PARTIAL_WITH_USER_SUPPLIED_NAME"
    assert doc["airport"]["name"] == {
        "source_text": "Reviewed Chennai Name",
        "value": "Reviewed Chennai Name",
        "status": "USER_SUPPLIED_REVIEWED_FALLBACK",
    }



def test_invalid_arp_dms_is_controlled_extraction_error():
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    arp_latitude = next(
        word for word in dump["words"] if word[5] == 100 and word[6] == 2 and word[7] == 0
    )
    arp_latitude[4] = "99°59'42.356\""
    with pytest.raises(ExtractionError, match="invalid ARP latitude"):
        extract_from_words(dump, profile="auto")


def test_invalid_threshold_dms_is_controlled_extraction_error():
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    threshold_latitude = next(
        word for word in dump["words"] if word[5] == 200 and word[6] == 2 and word[7] == 0
    )
    threshold_latitude[4] = "95°59'50.000\""
    with pytest.raises(ExtractionError, match="invalid threshold 07 latitude"):
        extract_from_words(dump, profile="auto")



def test_axis_maximum_with_nonzero_remainder_is_rejected_for_arp():
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    arp_latitude = next(
        word for word in dump["words"] if word[5] == 100 and word[6] == 2 and word[7] == 0
    )
    arp_latitude[4] = "90°00'00.001\""
    with pytest.raises(ExtractionError, match="invalid ARP latitude"):
        extract_from_words(dump, profile="auto")


def test_axis_maximum_with_nonzero_remainder_is_rejected_for_threshold():
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    threshold_longitude = next(
        word for word in dump["words"] if word[5] == 200 and word[6] == 3 and word[7] == 0
    )
    threshold_longitude[4] = "180°00'00.001\""
    with pytest.raises(ExtractionError, match="invalid threshold 07 longitude"):
        extract_from_words(dump, profile="auto")



@pytest.mark.parametrize("availability", ["false", "no", 1, 0, [], {}])
def test_metadata_byte_availability_requires_literal_true(availability):
    dump = json.loads(VOMM_SAMPLE.read_text(encoding="utf-8"))
    document = extract_from_words(
        dump,
        profile="auto",
        source_metadata={
            "original_bytes_available": availability,
            "sha256": "a" * 64,
        },
    )
    assert document["source"]["original_bytes_available"] is False
    _, _, report = normalize(document)
    source_check = next(
        check for check in report["checks"] if check["id"] == "source.original_bytes"
    )
    assert source_check["status"] == "EXPECTED_BLOCKER"

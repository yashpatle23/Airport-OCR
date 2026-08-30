import copy

import pytest

from airport_ocr.pipeline import PipelineError, normalize


def test_pipeline_passes_with_expected_blockers(observation_document):
    normalized, geojson, report = normalize(observation_document)
    assert report["status"] == "PASS_WITH_EXPECTED_BLOCKERS"
    assert report["failure_count"] == 0
    assert report["counts"]["PASS"] == 24
    assert report["counts"]["EXPECTED_BLOCKER"] == 4
    assert report["counts"]["INFO"] == 2
    assert normalized["operational_use"] is False


def test_pipeline_arp_and_thresholds_are_crs84(observation_document):
    normalized, _, _ = normalize(observation_document)
    assert normalized["airport"]["arp"]["coordinates"] == [77.7055555556, 13.1988888889]
    assert normalized["airport"]["arp"]["axis_order"] == "longitude_latitude"
    thresholds = {
        d["designator"]: d["threshold"]["position"]["coordinates"]
        for r in normalized["runways"]
        for d in r["directions"]
    }
    assert thresholds == {
        "09L": [77.6860722222, 13.2071638889],
        "27R": [77.7229694444, 13.2068472222],
        "09R": [77.6899777778, 13.1897333333],
        "27L": [77.7268722222, 13.1894138889],
    }


def test_pipeline_preserves_elevation_conflict(observation_document):
    normalized, _, _ = normalize(observation_document)
    elevation = normalized["airport"]["elevation"]
    assert elevation["selected_value"] is None
    assert {c["value"] for c in elevation["claims"]} == {3001, 3003}


def test_pipeline_blocked_collections_are_not_absence(observation_document):
    normalized, geojson, _ = normalize(observation_document)
    for key in ("taxiways", "runway_holding_positions"):
        assert normalized[key]["features"] == []
        assert normalized[key]["empty_array_semantics"] == "NOT_EXTRACTED_NOT_ABSENT"
    assert geojson["properties"]["taxiway_completeness"] == "BLOCKED_SOURCE_BYTES_REQUIRED"


def test_geojson_features_are_provisional_and_connectors_labelled(observation_document):
    _, geojson, _ = normalize(observation_document)
    assert len(geojson["features"]) == 7
    assert all(f["properties"]["status"] == "PROVISIONAL_RESEARCH_ONLY" for f in geojson["features"])
    connectors = [f for f in geojson["features"] if f["properties"]["feature_type"] == "runway_threshold_connector"]
    assert connectors
    assert all(
        f["properties"]["geometry_role"] == "DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT"
        for f in connectors
    )


def test_pipeline_flags_selected_elevation_as_failure(observation_document):
    tampered = copy.deepcopy(observation_document)
    tampered["airport"]["elevation"]["selected_value"] = 3003
    _, _, report = normalize(tampered)
    assert report["status"] == "FAIL"
    assert any(c["id"] == "airport.elevation_conflict" and c["status"] == "FAIL" for c in report["checks"])


def test_pipeline_flags_broken_reciprocal_pair(observation_document):
    tampered = copy.deepcopy(observation_document)
    tampered["runways"][0]["designator_pair"] = "09L/27L"
    tampered["runways"][0]["directions"][1]["designator"] = "27L"
    _, _, report = normalize(tampered)
    assert report["failure_count"] >= 1


def test_pipeline_missing_top_level_key_raises(observation_document):
    broken = copy.deepcopy(observation_document)
    del broken["runways"]
    with pytest.raises(PipelineError):
        normalize(broken)



def test_pipeline_reports_missing_bearing_without_type_error(observation_document):
    tampered = copy.deepcopy(observation_document)
    tampered["runways"][0]["directions"][0]["displayed_direction"]["value"] = None
    _, _, report = normalize(tampered)
    assert report["status"] == "FAIL"
    assert any(
        check["id"] == "runway_direction.09L.displayed_direction"
        and check["status"] == "FAIL"
        for check in report["checks"]
    )



def test_pipeline_wraps_invalid_threshold_dms_as_pipeline_error(observation_document):
    tampered = copy.deepcopy(observation_document)
    tampered["runways"][0]["directions"][0]["threshold"]["latitude_source"] = "99°00'00\" N"
    with pytest.raises(PipelineError, match="Invalid threshold coordinates for 09L"):
        normalize(tampered)



def test_source_bytes_require_explicit_availability_and_valid_sha(observation_document):
    unavailable = copy.deepcopy(observation_document)
    unavailable["source"]["original_bytes_available"] = False
    unavailable["source"]["sha256"] = "a" * 64
    _, _, unavailable_report = normalize(unavailable)
    unavailable_check = next(
        check for check in unavailable_report["checks"] if check["id"] == "source.original_bytes"
    )
    assert unavailable_check["status"] == "EXPECTED_BLOCKER"

    invalid_digest = copy.deepcopy(observation_document)
    invalid_digest["source"]["original_bytes_available"] = True
    invalid_digest["source"]["sha256"] = "not-a-sha256"
    _, _, invalid_report = normalize(invalid_digest)
    invalid_check = next(
        check for check in invalid_report["checks"] if check["id"] == "source.original_bytes"
    )
    assert invalid_check["status"] == "EXPECTED_BLOCKER"

    available = copy.deepcopy(observation_document)
    available["source"]["original_bytes_available"] = True
    available["source"]["sha256"] = "a" * 64
    _, _, available_report = normalize(available)
    available_check = next(
        check for check in available_report["checks"] if check["id"] == "source.original_bytes"
    )
    assert available_check["status"] == "PASS"

import pytest

from airport_ocr.pipeline import normalize
from airport_ocr.search import SearchError, search_features


@pytest.fixture
def collection(observation_document):
    _, geojson, _ = normalize(observation_document)
    return geojson


def test_search_by_feature_type(collection):
    result = search_features(collection, feature_type="runway_threshold")
    assert result["properties"]["match_count"] == 4
    assert all(f["properties"]["feature_type"] == "runway_threshold" for f in result["features"])


def test_search_by_designator(collection):
    result = search_features(collection, designator="09L")
    assert result["properties"]["match_count"] == 1
    assert result["features"][0]["properties"]["designator"] == "09L"


def test_search_by_airport(collection):
    result = search_features(collection, airport_icao="VOBL")
    assert result["properties"]["match_count"] == len(collection["features"])
    empty = search_features(collection, airport_icao="ZZZZ")
    assert empty["properties"]["match_count"] == 0


def test_search_by_bbox(collection):
    # Tight box around the VOBL ARP.
    result = search_features(collection, bbox=[77.70, 13.19, 77.71, 13.20])
    types = {f["properties"]["feature_type"] for f in result["features"]}
    assert "aerodrome_reference_point" in types


def test_search_bbox_must_have_four_values(collection):
    with pytest.raises(SearchError):
        search_features(collection, bbox=[1, 2, 3])


def test_search_rejects_non_collection():
    with pytest.raises(SearchError):
        search_features({"type": "Feature"})

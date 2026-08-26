from airport_ocr.holding import (
    filter_marking_segments,
    holding_candidates,
    segment_length,
    segment_midpoint,
)


def _marking_cluster(cx, cy, n, spacing=2.0, length=10.0):
    """n short parallel horizontal segments centered near (cx, cy)."""
    segs = []
    for i in range(n):
        y = cy + i * spacing
        segs.append((cx - length / 2, y, cx + length / 2, y))
    return segs


def test_segment_helpers():
    assert segment_length((0, 0, 3, 4)) == 5.0
    assert segment_midpoint((0, 0, 10, 20)) == (5.0, 10.0)


def test_filter_marking_segments_drops_long_and_zero():
    segs = [(0, 0, 10, 0), (0, 0, 500, 0), (5, 5, 5, 5)]
    kept = filter_marking_segments(segs, min_length=2.0, max_length=60.0)
    assert kept == [(0, 0, 10, 0)]


def test_two_clusters_associate_to_nearest_taxiway():
    segments = _marking_cluster(100, 100, 6) + _marking_cluster(300, 300, 5)
    labels = [
        {"designator": "A", "x": 108, "y": 105},
        {"designator": "B", "x": 292, "y": 296},
    ]
    result = holding_candidates(segments, labels, cell=14.0, min_segments=4)

    assert result["completeness_status"] == "CANDIDATES_PENDING_REVIEW"
    assert result["operational_use"] is False
    assert result["review_required"] is True
    assert len(result["features"]) == 2
    assert all(f["status"] == "NEEDS_REVIEW" for f in result["features"])
    assert all(f["feature_type"] == "runway_holding_position_candidate" for f in result["features"])

    associations = {f["associated_taxiway"] for f in result["features"]}
    assert associations == {"A", "B"}


def test_min_segments_threshold_filters_noise():
    # A dense cluster (kept) plus scattered singletons far apart (dropped).
    segments = _marking_cluster(100, 100, 6) + [(500, 500, 508, 500), (700, 700, 708, 700)]
    result = holding_candidates(segments, [{"designator": "A", "x": 100, "y": 100}], min_segments=4)
    assert len(result["features"]) == 1
    assert result["features"][0]["associated_taxiway"] == "A"


def test_unassociated_when_no_label_in_range():
    segments = _marking_cluster(100, 100, 6)
    labels = [{"designator": "Z", "x": 900, "y": 900}]  # far away
    result = holding_candidates(segments, labels, max_label_distance=60.0)
    feature = result["features"][0]
    assert feature["associated_taxiway"] is None
    assert feature["association_confidence"] == "none"
    assert "unassociated" in feature["feature_id"]


def test_detector_metadata_counts():
    segments = _marking_cluster(100, 100, 6)
    result = holding_candidates(segments, [], page_size=[1191.0, 842.0])
    det = result["detector"]
    assert det["input_segment_count"] == 6
    assert det["marking_segment_count"] == 6
    assert det["candidate_count"] == len(result["features"]) == 1
    assert det["page_size"] == [1191.0, 842.0]

"""Runway holding-position candidate detection (review-only).

Aerodrome-chart holding-position markings are drawn in the generic black
linework layer, so they cannot be isolated by colour. This module offers a
best-effort, **candidate-grade** detector: it clusters short marking-sized line
segments into groups and associates each group with the nearest taxiway label.

Every result is emitted with ``status = "NEEDS_REVIEW"`` inside a collection
whose completeness is ``CANDIDATES_PENDING_REVIEW``. These candidates are NOT
accepted holding positions and MUST NOT be published or used operationally:
short black strokes also occur in dashed taxiway centrelines and other linework,
so false positives are expected and human review is mandatory.

Inputs are plain geometry (page-space), so the module has no PDF dependency and
is fully unit-testable:

- ``segments``: list of ``(x1, y1, x2, y2)`` line segments (page coordinates),
- ``taxiway_labels``: list of ``{"designator": str, "x": float, "y": float}``.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

Segment = Sequence[float]  # (x1, y1, x2, y2)


def segment_length(seg: Segment) -> float:
    return math.hypot(seg[2] - seg[0], seg[3] - seg[1])


def segment_midpoint(seg: Segment) -> Tuple[float, float]:
    return ((seg[0] + seg[2]) / 2.0, (seg[1] + seg[3]) / 2.0)


def filter_marking_segments(
    segments: Sequence[Segment],
    min_length: float = 2.0,
    max_length: float = 60.0,
) -> List[Segment]:
    """Keep only marking-sized segments (drops long edges and zero-length noise)."""
    return [s for s in segments if min_length <= segment_length(s) <= max_length]


def _cluster_midpoints(
    midpoints: List[Tuple[float, float]],
    cell: float,
    min_count: int,
    max_count: int,
) -> List[Dict[str, Any]]:
    """Grid connected-component clustering over 8-neighbour cells."""
    buckets: Dict[Tuple[int, int], List[int]] = {}
    for idx, (x, y) in enumerate(midpoints):
        key = (int(math.floor(x / cell)), int(math.floor(y / cell)))
        buckets.setdefault(key, []).append(idx)

    visited: set = set()
    clusters: List[Dict[str, Any]] = []
    for key in list(buckets):
        if key in visited:
            continue
        component_cells = []
        queue = deque([key])
        visited.add(key)
        while queue:
            ck = queue.popleft()
            component_cells.append(ck)
            cx, cy = ck
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (cx + dx, cy + dy)
                    if nk in buckets and nk not in visited:
                        visited.add(nk)
                        queue.append(nk)
        indices = [i for ck in component_cells for i in buckets[ck]]
        count = len(indices)
        if count < min_count or count > max_count:
            continue
        xs = [midpoints[i][0] for i in indices]
        ys = [midpoints[i][1] for i in indices]
        clusters.append(
            {
                "x": round(sum(xs) / count, 2),
                "y": round(sum(ys) / count, 2),
                "segment_count": count,
                "bbox": [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)],
            }
        )
    clusters.sort(key=lambda c: (-c["segment_count"], c["x"], c["y"]))
    return clusters


def _nearest_label(
    x: float, y: float, labels: Sequence[Dict[str, Any]], max_distance: float
) -> Tuple[Optional[str], Optional[float]]:
    best_designator: Optional[str] = None
    best_distance: Optional[float] = None
    for label in labels:
        d = math.hypot(x - label["x"], y - label["y"])
        if best_distance is None or d < best_distance:
            best_distance = d
            best_designator = label.get("designator")
    if best_distance is None or best_distance > max_distance:
        return None, (round(best_distance, 2) if best_distance is not None else None)
    return best_designator, round(best_distance, 2)


def holding_candidates(
    segments: Sequence[Segment],
    taxiway_labels: Sequence[Dict[str, Any]],
    *,
    airport_icao: str = "VOBL",
    page_size: Optional[Sequence[float]] = None,
    cell: float = 14.0,
    min_segments: int = 4,
    max_segments: int = 400,
    min_length: float = 2.0,
    max_length: float = 60.0,
    max_label_distance: float = 60.0,
) -> Dict[str, Any]:
    """Detect candidate runway holding positions from marking-sized segments.

    Returns a collection compatible in shape with the observation model, but
    marked ``CANDIDATES_PENDING_REVIEW`` with per-feature ``NEEDS_REVIEW`` status.
    Nothing here is an accepted holding position.
    """
    marking = filter_marking_segments(segments, min_length, max_length)
    midpoints = [segment_midpoint(s) for s in marking]
    clusters = _cluster_midpoints(midpoints, cell, min_segments, max_segments)

    features: List[Dict[str, Any]] = []
    per_taxiway: Dict[str, int] = {}
    for cluster in clusters:
        designator, distance = _nearest_label(
            cluster["x"], cluster["y"], taxiway_labels, max_label_distance
        )
        seq = per_taxiway.get(designator or "?", 0) + 1
        per_taxiway[designator or "?"] = seq
        suffix = f"{designator}#{seq}" if designator else f"unassociated#{seq}"
        features.append(
            {
                "feature_id": f"holding-candidate:{airport_icao}:{suffix}",
                "feature_type": "runway_holding_position_candidate",
                "status": "NEEDS_REVIEW",
                "page_point": {"x": cluster["x"], "y": cluster["y"], "space": "pdf_page"},
                "page_bbox": cluster["bbox"],
                "segment_count": cluster["segment_count"],
                "associated_taxiway": designator,
                "association_distance_px": distance,
                "association_confidence": (
                    "none" if designator is None
                    else "low" if (distance or 0) > max_label_distance / 2
                    else "medium"
                ),
                "note": (
                    "Candidate from clustered black marking strokes; may be a dashed "
                    "centreline or other linework. Requires human review before use."
                ),
            }
        )

    return {
        "feature_type": "runway_holding_position_collection",
        "features": features,
        "presence_observed": True,
        "empty_array_semantics": "CANDIDATES_NOT_ACCEPTED",
        "completeness_status": "CANDIDATES_PENDING_REVIEW",
        "operational_use": False,
        "detector": {
            "method": "grid connected-component clustering of black marking segments",
            "page_size": list(page_size) if page_size else None,
            "params": {
                "cell": cell,
                "min_segments": min_segments,
                "max_segments": max_segments,
                "min_length": min_length,
                "max_length": max_length,
                "max_label_distance": max_label_distance,
            },
            "input_segment_count": len(segments),
            "marking_segment_count": len(marking),
            "candidate_count": len(features),
        },
        "review_required": True,
        "warning": (
            "These are UNVERIFIED candidates, not accepted holding positions. "
            "False positives are expected; do not publish or use operationally."
        ),
    }

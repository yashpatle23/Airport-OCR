"""Small GeoJSON search projection.

Filters a generated FeatureCollection by feature type, airport, designator, and
bounding box. This demonstrates search semantics without introducing a second
source of truth; the GeoJSON remains a rebuildable projection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

BBox = Sequence[float]  # [min_lon, min_lat, max_lon, max_lat]


class SearchError(ValueError):
    """Raised when a query is malformed."""


def _point_in_bbox(coordinates: Sequence[float], bbox: BBox) -> bool:
    lon, lat = coordinates[0], coordinates[1]
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def _geometry_in_bbox(geometry: Dict[str, Any], bbox: BBox) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point":
        return _point_in_bbox(coords, bbox)
    if gtype == "LineString":
        return any(_point_in_bbox(position, bbox) for position in coords)
    return False


def search_features(
    collection: Dict[str, Any],
    feature_type: Optional[str] = None,
    airport_icao: Optional[str] = None,
    designator: Optional[str] = None,
    bbox: Optional[BBox] = None,
) -> Dict[str, Any]:
    """Return a filtered FeatureCollection matching all provided criteria."""
    if collection.get("type") != "FeatureCollection":
        raise SearchError("Input is not a GeoJSON FeatureCollection.")
    if bbox is not None and len(bbox) != 4:
        raise SearchError("bbox must be [min_lon, min_lat, max_lon, max_lat].")

    matches: List[Dict[str, Any]] = []
    for feature in collection.get("features", []):
        props = feature.get("properties", {})
        if feature_type is not None and props.get("feature_type") != feature_type:
            continue
        if airport_icao is not None and props.get("airport_icao") != airport_icao:
            continue
        if designator is not None and designator not in (
            props.get("designator"),
            props.get("designator_pair"),
        ):
            continue
        if bbox is not None and not _geometry_in_bbox(feature.get("geometry", {}), bbox):
            continue
        matches.append(feature)

    return {
        "type": "FeatureCollection",
        "name": "airport-ocr search result",
        "properties": {
            "operational_use": False,
            "query": {
                "feature_type": feature_type,
                "airport_icao": airport_icao,
                "designator": designator,
                "bbox": list(bbox) if bbox is not None else None,
            },
            "match_count": len(matches),
        },
        "features": matches,
    }

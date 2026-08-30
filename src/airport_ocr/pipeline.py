"""Normalization and export pipeline.

Consumes a source-preserving observation document and produces:
- a normalized domain JSON object;
- an RFC 7946 GeoJSON FeatureCollection (OGC:CRS84, longitude/latitude);
- a structured validation report.

The pipeline never fabricates missing data. Blocked collections (taxiways,
runway holding positions) remain explicitly empty with NOT_EXTRACTED_NOT_ABSENT
semantics, and conflicting claims are preserved without selection.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Tuple

from .coordinates import (
    CoordinateError,
    is_valid_designator,
    parse_dms,
    reciprocal_designator,
    to_float,
)
from .validation import Validation

_EARTH_RADIUS_M = 6371008.8
_TAXIWAY_DESIGNATOR_RE = re.compile(r"^[A-Z]{1,3}\d{0,2}$")
_ALLOWED_BLOCKED_STATUSES = {
    "BLOCKED_SOURCE_BYTES_REQUIRED",  # legacy VOBL fixture
    "BLOCKED_LAYOUT_OR_REVIEW_REQUIRED",
    "BLOCKED_GEOMETRY_OR_REVIEW_REQUIRED",
}
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_positive_number(value: Any) -> bool:
    return _is_finite_number(value) and value > 0


class PipelineError(Exception):
    """Raised when the input document is structurally unusable."""


def _haversine_m(first: Tuple[float, float], second: Tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point(coordinates: List[float], components_lat, components_lon, source: Dict[str, str]) -> Dict[str, Any]:
    return {
        "type": "Point",
        "coordinates": coordinates,
        "crs": "OGC:CRS84",
        "axis_order": "longitude_latitude",
        "source": {
            "latitude": source["latitude"],
            "longitude": source["longitude"],
            "latitude_parts": components_lat.to_dict(),
            "longitude_parts": components_lon.to_dict(),
        },
        "status": "DERIVED_FROM_PROVISIONAL_DMS_TRANSCRIPTION",
    }


def _blocked_collection(node: Dict[str, Any], name: str, validation: Validation) -> Dict[str, Any]:
    status = node.get("completeness_status")
    is_blocked = (
        node.get("features") == []
        and node.get("presence_observed") is True
        and node.get("empty_array_semantics") == "NOT_EXTRACTED_NOT_ABSENT"
        and status in _ALLOWED_BLOCKED_STATUSES
    )
    validation.blocker(
        is_blocked,
        f"{name}.completeness",
        f"{name} are present but not extracted ({status}); empty features are not absence.",
        f"{name} blocked-completeness semantics are invalid.",
    )
    return {
        "features": [],
        "presence_observed": True,
        "completeness_status": status,
        "empty_array_semantics": node.get("empty_array_semantics"),
    }


def _taxiway_collection(node: Dict[str, Any], validation: Validation) -> Dict[str, Any]:
    """Validate a populated taxiway inventory, including partial label candidates."""
    features = node.get("features") or []
    if not features:
        return _blocked_collection(node, "taxiways", validation)

    designators = [f.get("designator") for f in features]
    valid = all(bool(d) and bool(_TAXIWAY_DESIGNATOR_RE.match(d)) for d in designators)
    unique = len(set(designators)) == len(designators)
    validation.require(
        valid and unique,
        "taxiways.designators_valid",
        f"All {len(features)} taxiway designators are valid and unique.",
        "Taxiway designators are invalid or duplicated.",
    )
    known_widths = [f for f in features if (f.get("width") or {}).get("value") is not None]
    widths_ok = all(
        (f.get("width") or {}).get("unit") == "M"
        and _is_positive_number((f.get("width") or {}).get("value"))
        for f in known_widths
    )
    widths_missing = len(known_widths) != len(features)
    if widths_ok and widths_missing:
        validation.blocker(
            True,
            "taxiways.widths",
            f"Widths are unavailable for {len(features) - len(known_widths)} text-reference taxiway candidates.",
            "All taxiway widths are present.",
        )
    else:
        validation.require(
            widths_ok,
            "taxiways.widths",
            "All extracted taxiway widths are positive values in metres.",
            "One or more extracted taxiway widths are invalid.",
        )
    normalized = [
        {
            "feature_id": f.get("feature_id"),
            "designator": f.get("designator"),
            "status": f.get("status"),
            "width": f.get("width"),
            "source": f.get("source"),
        }
        for f in features
    ]
    return {
        "features": normalized,
        "count": len(normalized),
        "presence_observed": True,
        "completeness_status": node.get("completeness_status"),
        "empty_array_semantics": node.get("empty_array_semantics"),
    }


def normalize(document: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Normalize an observation document; return (normalized, geojson, report)."""
    validation = Validation()

    for key in ("airport", "runways", "taxiways", "runway_holding_positions", "source"):
        if key not in document:
            raise PipelineError(f"Missing required top-level key: {key!r}")

    validation.require(
        document.get("dataset_status") == "PROVISIONAL_BOOTSTRAP_NOT_GOLD",
        "dataset.provisional_status",
        "Dataset is explicitly provisional and not gold.",
        "Dataset must be explicitly provisional and not gold.",
    )
    validation.require(
        document.get("operational_use") is False,
        "dataset.non_operational",
        "Operational use is explicitly false.",
        "Operational use must be false.",
    )

    source = document["source"]
    sha256 = source.get("sha256")
    source_bytes_ready = (
        source.get("original_bytes_available") is True
        and isinstance(sha256, str)
        and bool(_SHA256_RE.fullmatch(sha256))
    )
    validation.blocker(
        not source_bytes_ready,
        "source.original_bytes",
        "Original source-byte availability and a valid SHA-256 were not both recorded; extraction benchmark stays blocked.",
        "Original source bytes are explicitly available and have a valid SHA-256.",
    )
    validation.blocker(
        source.get("rights_status") == "UNCONFIRMED_PERMISSION_REQUIRED",
        "source.rights",
        "Source processing/training rights are unconfirmed.",
        "Source rights status is confirmed.",
    )

    airport = document["airport"]
    icao = airport["icao"]["value"]
    validation.require(
        len(icao) == 4 and icao.isalpha() and icao.isupper(),
        "airport.icao_format",
        f"ICAO identifier {icao} is four uppercase letters.",
        "ICAO identifier format is invalid.",
    )

    arp = airport["arp"]
    try:
        arp_lat, arp_lat_parts = parse_dms(arp["latitude_source"], "latitude")
        arp_lon, arp_lon_parts = parse_dms(arp["longitude_source"], "longitude")
    except CoordinateError as exc:
        raise PipelineError(f"Invalid ARP coordinates: {exc}") from exc
    arp_coordinates = [to_float(arp_lon), to_float(arp_lat)]
    validation.require(
        -180 <= arp_coordinates[0] <= 180 and -90 <= arp_coordinates[1] <= 90,
        "airport.arp_range",
        "ARP coordinates are within valid ranges.",
        "ARP coordinates are out of range.",
    )
    validation.require(
        arp.get("axis_order_target") == "longitude_latitude"
        and arp.get("normalized_crs_target") == "OGC:CRS84",
        "airport.arp_axis_crs",
        "Target output declares OGC:CRS84 longitude/latitude order.",
        "Target output must declare OGC:CRS84 longitude/latitude order.",
    )

    elevation = airport["elevation"]
    claims = elevation.get("claims") or []
    claim_values = {(claim.get("value"), claim.get("unit")) for claim in claims}
    positive_ft = bool(claims) and all(
        claim.get("unit") == "FT" and _is_positive_number(claim.get("value"))
        for claim in claims
    )
    has_conflict = len(claim_values) > 1
    if has_conflict:
        elevation_ok = (
            positive_ft
            and elevation.get("selected_value") is None
            and elevation.get("conflict_status") == "OPEN_EFFECTIVE_EDITION_RECONCILIATION_REQUIRED"
        )
        elevation_detail = "Differing elevation claims remain separate, unselected, and unresolved."
    else:
        elevation_ok = (
            positive_ft
            and elevation.get("selected_value") is None
            and elevation.get("conflict_status") in {"SINGLE_SOURCE", "CORROBORATED_SAME_VALUE"}
        )
        elevation_detail = "Aerodrome elevation claims are positive FT values with a consistent claim status."
    validation.require(
        elevation_ok,
        "airport.elevation_conflict",
        elevation_detail,
        "Aerodrome elevation claims/status are missing, invalid, or prematurely selected.",
    )

    runways = document["runways"]
    validation.require(
        len(runways) >= 1,
        "runways.pair_count",
        f"{len(runways)} reciprocal runway-pair record(s) are present.",
        "At least one reciprocal runway-pair record is required.",
    )

    normalized_runways: List[Dict[str, Any]] = []
    geojson_features: List[Dict[str, Any]] = []
    all_designators: List[str] = []

    for runway in runways:
        pair = runway["designator_pair"]
        pair_key = pair.replace("/", "-")
        directions = runway["directions"]
        pair_parts = pair.split("/")
        pair_ok = (
            len(pair_parts) == 2
            and len(directions) == 2
            and directions[0]["designator"] == pair_parts[0]
            and directions[1]["designator"] == pair_parts[1]
        )
        if pair_ok:
            try:
                pair_ok = (
                    reciprocal_designator(pair_parts[0]) == pair_parts[1]
                    and reciprocal_designator(pair_parts[1]) == pair_parts[0]
                )
            except CoordinateError:
                pair_ok = False
        validation.require(
            pair_ok,
            f"runway.{pair_key}.reciprocal_pair",
            f"{pair} is a consistent reciprocal designator pair.",
            f"{pair} is not a consistent reciprocal designator pair.",
        )

        length = runway.get("length") or {}
        width = runway.get("width") or {}
        length_value = length.get("value")
        width_value = width.get("value")
        dimensions_missing = length_value is None or width_value is None
        dimensions_valid = (
            not dimensions_missing
            and length.get("unit") == "M"
            and width.get("unit") == "M"
            and _is_positive_number(length_value)
            and _is_positive_number(width_value)
        )
        if dimensions_missing:
            validation.blocker(
                True,
                f"runway.{pair_key}.dimensions",
                f"Physical dimensions for {pair} were not extracted; declared distances were not substituted.",
                f"Physical dimensions for {pair} are present.",
            )
        else:
            validation.require(
                dimensions_valid,
                f"runway.{pair_key}.dimensions",
                f"{pair} has positive physical dimensions in metres.",
                f"{pair} dimensions or units are invalid.",
            )

        normalized_directions: List[Dict[str, Any]] = []
        connector: List[List[float]] = []
        for direction in directions:
            designator = direction["designator"]
            all_designators.append(designator)
            validation.require(
                is_valid_designator(designator),
                f"runway_direction.{designator}.format",
                f"Runway direction {designator} has a valid designator format.",
                f"Runway direction {designator} has an invalid designator format.",
            )
            displayed = direction["displayed_direction"]
            displayed_value = displayed.get("value")
            displayed_valid = (
                displayed.get("unit") == "DEG"
                and _is_finite_number(displayed_value)
                and 0 <= displayed_value < 360
            )
            validation.require(
                displayed_valid,
                f"runway_direction.{designator}.displayed_direction",
                f"Displayed direction for {designator} is within 0-359 degrees.",
                f"Displayed direction for {designator} is invalid.",
            )

            threshold = direction["threshold"]
            try:
                lat, lat_parts = parse_dms(threshold["latitude_source"], "latitude")
                lon, lon_parts = parse_dms(threshold["longitude_source"], "longitude")
            except CoordinateError as exc:
                raise PipelineError(f"Invalid threshold coordinates for {designator}: {exc}") from exc
            coordinates = [to_float(lon), to_float(lat)]
            if not (-180 <= coordinates[0] <= 180 and -90 <= coordinates[1] <= 90):
                raise PipelineError(
                    f"Threshold coordinates for {designator} are outside RFC 7946 ranges"
                )
            connector.append(coordinates)
            threshold_elevation = threshold.get("elevation") or {}
            tdz_elevation = threshold.get("tdz_elevation") or {}
            threshold_ok = (
                threshold_elevation.get("unit") == "FT"
                and _is_positive_number(threshold_elevation.get("value"))
            )
            tdz_missing = tdz_elevation.get("value") is None
            tdz_ok = (
                tdz_elevation.get("unit") == "FT"
                and _is_positive_number(tdz_elevation.get("value"))
            )
            if not threshold_ok:
                validation.require(
                    False,
                    f"threshold.{designator}.elevations",
                    "",
                    f"Threshold elevation or unit is invalid for {designator}.",
                )
            elif tdz_missing:
                validation.blocker(
                    True,
                    f"threshold.{designator}.elevations",
                    f"Threshold elevation for {designator} is valid; TDZ elevation was not extracted.",
                    f"Threshold and TDZ elevations for {designator} are present.",
                )
            else:
                validation.require(
                    tdz_ok,
                    f"threshold.{designator}.elevations",
                    f"Threshold and TDZ elevations for {designator} are positive and in FT.",
                    f"TDZ elevation or unit is invalid for {designator}.",
                )

            normalized_directions.append(
                {
                    "feature_id": direction["feature_id"],
                    "designator": designator,
                    "displayed_direction": displayed,
                    "threshold": {
                        "feature_id": threshold["feature_id"],
                        "designator": designator,
                        "position": _point(
                            coordinates, lat_parts, lon_parts,
                            {"latitude": threshold["latitude_source"], "longitude": threshold["longitude_source"]},
                        ),
                        "elevation": threshold["elevation"],
                        "tdz_elevation": threshold["tdz_elevation"],
                    },
                }
            )
            geojson_features.append(
                {
                    "type": "Feature",
                    "id": threshold["feature_id"],
                    "geometry": {"type": "Point", "coordinates": coordinates},
                    "properties": {
                        "feature_type": "runway_threshold",
                        "airport_icao": icao,
                        "designator": designator,
                        "threshold_elevation_ft": threshold["elevation"]["value"],
                        "tdz_elevation_ft": threshold["tdz_elevation"]["value"],
                        "source_latitude": threshold["latitude_source"],
                        "source_longitude": threshold["longitude_source"],
                        "status": "PROVISIONAL_RESEARCH_ONLY",
                    },
                }
            )

        distance = round(_haversine_m(tuple(connector[0]), tuple(connector[1])), 1)
        validation.info(
            f"runway.{pair_key}.threshold_distance",
            f"Threshold-to-threshold distance is {distance} m; not required to equal "
            "declared length because thresholds may be displaced.",
            threshold_distance_m=distance,
        )
        normalized_runways.append(
            {
                "feature_id": runway["feature_id"],
                "designator_pair": pair,
                "declared_length": runway["length"],
                "declared_width": runway["width"],
                "directions": normalized_directions,
                "threshold_connector": {
                    "type": "LineString",
                    "coordinates": connector,
                    "status": "DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT",
                    "distance_m": distance,
                },
                "runway_geometry": None,
            }
        )
        geojson_features.append(
            {
                "type": "Feature",
                "id": runway["feature_id"],
                "geometry": {"type": "LineString", "coordinates": connector},
                "properties": {
                    "feature_type": "runway_threshold_connector",
                    "airport_icao": icao,
                    "designator_pair": pair,
                    "declared_length_m": runway["length"]["value"],
                    "declared_width_m": runway["width"]["value"],
                    "connector_distance_m": distance,
                    "geometry_role": "DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT",
                    "status": "PROVISIONAL_RESEARCH_ONLY",
                },
            }
        )

    inventory_ok = (
        len(all_designators) == 2 * len(runways)
        and len(set(all_designators)) == len(all_designators)
        and all(is_valid_designator(value) for value in all_designators)
    )
    validation.require(
        inventory_ok,
        "runways.direction_inventory",
        f"Runway direction inventory contains {len(all_designators)} unique valid designators.",
        "Runway direction inventory is empty, duplicated, or invalid.",
    )

    taxiways = _taxiway_collection(document["taxiways"], validation)
    holds = _blocked_collection(document["runway_holding_positions"], "runway_holding_positions", validation)

    extraction = document.get("extraction") or {
        "status": "NOT_REPORTED_LEGACY_OBSERVATION",
        "profile": None,
        "adapters": [],
        "issues": [
            {
                "code": "EXTRACTION_DIAGNOSTICS_NOT_REPORTED",
                "detail": "The input observation predates extraction diagnostics.",
            }
        ],
    }
    normalized = {
        "schema_version": "1.0.0",
        "dataset_id": document["dataset_id"],
        "status": "PROVISIONAL_RESEARCH_ONLY",
        "operational_use": False,
        "extraction": extraction,
        "source": {
            "source_path": source.get("source_path"),
            "source_url": source.get("source_url"),
            "chart_identifier": source.get("chart_identifier"),
            "displayed_date": source.get("displayed_date"),
            "amendment": source.get("amendment"),
            "original_sha256": source.get("sha256"),
            "original_bytes_available": source.get("original_bytes_available"),
            "rights_status": source.get("rights_status"),
        },
        "airport": {
            "feature_id": airport["feature_id"],
            "icao": icao,
            "name": airport["name"]["value"],
            "name_provenance": {
                "status": airport["name"].get("status", airport.get("status")),
                "source_text": airport["name"].get("source_text"),
            },
            "arp": _point(
                arp_coordinates, arp_lat_parts, arp_lon_parts,
                {"latitude": arp["latitude_source"], "longitude": arp["longitude_source"]},
            ),
            "elevation": {
                "claims": elevation["claims"],
                "selected_value": None,
                "conflict_status": elevation["conflict_status"],
            },
        },
        "runways": normalized_runways,
        "taxiways": taxiways,
        "runway_holding_positions": holds,
    }

    geojson = {
        "type": "FeatureCollection",
        "name": f"{icao} provisional airport and runway-threshold features",
        "properties": {
            "dataset_id": document["dataset_id"],
            "status": "PROVISIONAL_RESEARCH_ONLY",
            "operational_use": False,
            "extraction_status": extraction.get("status"),
            "crs_semantics": "RFC 7946 longitude/latitude (OGC:CRS84)",
            "taxiway_completeness": taxiways["completeness_status"],
            "taxiway_inventory": [f["designator"] for f in taxiways.get("features", [])],
            "runway_holding_position_completeness": holds["completeness_status"],
            "warning": "Runway lines are threshold connectors, not surveyed runway extents.",
        },
        "features": [
            {
                "type": "Feature",
                "id": airport["feature_id"],
                "geometry": {"type": "Point", "coordinates": arp_coordinates},
                "properties": {
                    "feature_type": "aerodrome_reference_point",
                    "airport_icao": icao,
                    "airport_name": airport["name"]["value"],
                    "elevation_status": elevation["conflict_status"],
                    "selected_elevation": None,
                    "status": "PROVISIONAL_RESEARCH_ONLY",
                },
            }
        ]
        + geojson_features,
    }

    return normalized, geojson, validation.report()

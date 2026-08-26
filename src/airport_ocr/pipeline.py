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
from typing import Any, Dict, List, Tuple

from .coordinates import (
    CoordinateError,
    is_valid_designator,
    parse_dms,
    reciprocal_designator,
    to_float,
)
from .validation import Validation

_EXPECTED_DESIGNATORS = {"09L", "27R", "09R", "27L"}
_EARTH_RADIUS_M = 6371008.8


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
    is_blocked = (
        node.get("features") == []
        and node.get("presence_observed") is True
        and node.get("empty_array_semantics") == "NOT_EXTRACTED_NOT_ABSENT"
        and node.get("completeness_status") == "BLOCKED_SOURCE_BYTES_REQUIRED"
    )
    validation.blocker(
        is_blocked,
        f"{name}.completeness",
        f"{name} are present but not extracted; empty features are not absence.",
        f"{name} blocked-completeness semantics are invalid.",
    )
    return {
        "features": [],
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
    validation.blocker(
        source.get("original_bytes_available") is False and source.get("sha256") is None,
        "source.original_bytes",
        "Original source bytes and SHA-256 are unavailable; extraction benchmark stays blocked.",
        "Original source bytes and SHA-256 are available.",
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
    arp_lat, arp_lat_parts = parse_dms(arp["latitude_source"], "latitude")
    arp_lon, arp_lon_parts = parse_dms(arp["longitude_source"], "longitude")
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
    claim_values = {(c["value"], c["unit"]) for c in elevation["claims"]}
    validation.require(
        (3003, "FT") in claim_values
        and (3001, "FT") in claim_values
        and elevation.get("selected_value") is None
        and elevation.get("conflict_status") == "OPEN_EFFECTIVE_EDITION_RECONCILIATION_REQUIRED",
        "airport.elevation_conflict",
        "The 3003 FT and 3001 FT claims remain separate, unselected, and unresolved.",
        "The elevation conflict was lost or prematurely resolved.",
    )

    runways = document["runways"]
    validation.require(
        len(runways) == 2,
        "runways.pair_count",
        "Exactly two runway-pair records are present.",
        "Expected exactly two runway-pair records.",
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

        validation.require(
            runway["length"]["unit"] == "M"
            and runway["length"]["value"] == 4000
            and runway["width"]["unit"] == "M"
            and runway["width"]["value"] == 45,
            f"runway.{pair_key}.dimensions",
            f"{pair} preserves the displayed 4000 M x 45 M dimensions.",
            f"{pair} dimensions or units do not match the fixture.",
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
            validation.require(
                displayed["unit"] == "DEG" and 0 <= displayed["value"] < 360,
                f"runway_direction.{designator}.displayed_direction",
                f"Displayed direction for {designator} is within 0-359 degrees.",
                f"Displayed direction for {designator} is invalid.",
            )

            threshold = direction["threshold"]
            lat, lat_parts = parse_dms(threshold["latitude_source"], "latitude")
            lon, lon_parts = parse_dms(threshold["longitude_source"], "longitude")
            coordinates = [to_float(lon), to_float(lat)]
            connector.append(coordinates)
            validation.require(
                threshold["elevation"]["unit"] == "FT"
                and threshold["tdz_elevation"]["unit"] == "FT"
                and threshold["elevation"]["value"] > 0
                and threshold["tdz_elevation"]["value"] > 0,
                f"threshold.{designator}.elevations",
                f"Threshold and TDZ elevations for {designator} are positive and in FT.",
                f"Threshold/TDZ elevation or unit is invalid for {designator}.",
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

    validation.require(
        set(all_designators) == _EXPECTED_DESIGNATORS and len(all_designators) == 4,
        "runways.direction_inventory",
        "Direction inventory is exactly 09L, 27R, 09R, and 27L.",
        "Direction inventory is missing, duplicated, or unexpected.",
    )

    taxiways = _blocked_collection(document["taxiways"], "taxiways", validation)
    holds = _blocked_collection(document["runway_holding_positions"], "runway_holding_positions", validation)

    normalized = {
        "schema_version": "1.0.0",
        "dataset_id": document["dataset_id"],
        "status": "PROVISIONAL_RESEARCH_ONLY",
        "operational_use": False,
        "source": {
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
        "name": "VOBL provisional airport and runway-threshold features",
        "properties": {
            "dataset_id": document["dataset_id"],
            "status": "PROVISIONAL_RESEARCH_ONLY",
            "operational_use": False,
            "crs_semantics": "RFC 7946 longitude/latitude (OGC:CRS84)",
            "taxiway_completeness": taxiways["completeness_status"],
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

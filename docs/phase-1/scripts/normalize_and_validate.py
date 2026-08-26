#!/usr/bin/env python3
"""Normalize and validate the provisional VOBL Phase 1 bootstrap fixture.

This script uses only the Python standard library. It deliberately does not infer
missing taxiway or holding-position data and does not resolve the elevation
conflict. Outputs are research-only projections, not operational aviation data.
"""

import argparse
import hashlib
import json
import math
import platform
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

getcontext().prec = 28

DMS_RE = re.compile(
    r"^\s*(\d{1,3})\s*[°º]\s*(\d{1,2})\s*[′']\s*"
    r"(\d+(?:\.\d+)?)\s*[″\"]\s*([NSEW])\s*$",
    re.IGNORECASE,
)
DESIGNATOR_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-6])([LRC]?)$")
ICAO_RE = re.compile(r"^[A-Z]{4}$")


class Validation:
    def __init__(self) -> None:
        self.checks: List[Dict[str, Any]] = []

    def add(self, check_id: str, status: str, detail: str, **extra: Any) -> None:
        item: Dict[str, Any] = {"id": check_id, "status": status, "detail": detail}
        item.update(extra)
        self.checks.append(item)

    def require(self, condition: bool, check_id: str, pass_detail: str, fail_detail: str) -> None:
        self.add(check_id, "PASS" if condition else "FAIL", pass_detail if condition else fail_detail)

    @property
    def failures(self) -> List[Dict[str, Any]]:
        return [item for item in self.checks if item["status"] == "FAIL"]

    def counts(self) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for item in self.checks:
            result[item["status"]] = result.get(item["status"], 0) + 1
        return dict(sorted(result.items()))


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Top-level JSON value must be an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_dms(source: str, expected_axis: str) -> Tuple[Decimal, Dict[str, Any]]:
    match = DMS_RE.match(source)
    if not match:
        raise ValueError("Unsupported DMS coordinate: {!r}".format(source))

    degrees_text, minutes_text, seconds_text, hemisphere = match.groups()
    hemisphere = hemisphere.upper()
    degrees = int(degrees_text)
    minutes = int(minutes_text)
    try:
        seconds = Decimal(seconds_text)
    except InvalidOperation as exc:
        raise ValueError("Invalid seconds value: {!r}".format(seconds_text)) from exc

    if minutes >= 60 or seconds >= 60:
        raise ValueError("Minutes and seconds must be less than 60: {!r}".format(source))
    if expected_axis == "latitude":
        if hemisphere not in ("N", "S") or degrees > 90:
            raise ValueError("Invalid latitude: {!r}".format(source))
    elif expected_axis == "longitude":
        if hemisphere not in ("E", "W") or degrees > 180:
            raise ValueError("Invalid longitude: {!r}".format(source))
    else:
        raise ValueError("Unknown axis: {}".format(expected_axis))

    value = Decimal(degrees) + Decimal(minutes) / Decimal(60) + seconds / Decimal(3600)
    if hemisphere in ("S", "W"):
        value = -value

    seconds_decimal_places = max(0, -seconds.as_tuple().exponent)
    return value, {
        "source": source,
        "degrees": degrees,
        "minutes": minutes,
        "seconds": str(seconds),
        "hemisphere": hemisphere,
        "seconds_decimal_places": seconds_decimal_places,
    }


def decimal_number(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.0000000001")))


def reciprocal_designator(designator: str) -> str:
    match = DESIGNATOR_RE.match(designator)
    if not match:
        raise ValueError("Invalid runway designator: {}".format(designator))
    number = int(match.group(1))
    side = match.group(2)
    reciprocal_number = number + 18 if number <= 18 else number - 18
    reciprocal_side = {"L": "R", "R": "L", "C": "C", "": ""}[side]
    return "{:02d}{}".format(reciprocal_number, reciprocal_side)


def haversine_m(first: Tuple[float, float], second: Tuple[float, float]) -> float:
    """Return distance in metres for (longitude, latitude) pairs."""
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def normalize(input_data: Dict[str, Any], validation: Validation) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    validation.require(
        input_data.get("dataset_status") == "PROVISIONAL_BOOTSTRAP_NOT_GOLD",
        "dataset.provisional_status",
        "Dataset is explicitly provisional and not gold.",
        "Dataset must be explicitly provisional and not gold.",
    )
    validation.require(
        input_data.get("operational_use") is False,
        "dataset.non_operational",
        "Operational use is explicitly false.",
        "Operational use must be false for this benchmark.",
    )

    source = input_data["source"]
    original_unavailable = source.get("original_bytes_available") is False and source.get("sha256") is None
    validation.add(
        "source.original_bytes",
        "EXPECTED_BLOCKER" if original_unavailable else "PASS",
        "Original source bytes and SHA-256 are unavailable; PDF/OCR evidence benchmark remains blocked."
        if original_unavailable
        else "Original source bytes and SHA-256 are available.",
    )
    rights_unconfirmed = source.get("rights_status") == "UNCONFIRMED_PERMISSION_REQUIRED"
    validation.add(
        "source.rights",
        "EXPECTED_BLOCKER" if rights_unconfirmed else "PASS",
        "Source processing/training rights remain unconfirmed."
        if rights_unconfirmed
        else "Source rights status is no longer unconfirmed.",
    )

    airport = input_data["airport"]
    icao = airport["icao"]["value"]
    validation.require(
        bool(ICAO_RE.match(icao)),
        "airport.icao_format",
        "ICAO identifier VOBL has four uppercase letters.",
        "ICAO identifier format is invalid.",
    )

    arp = airport["arp"]
    arp_lat, arp_lat_parts = parse_dms(arp["latitude_source"], "latitude")
    arp_lon, arp_lon_parts = parse_dms(arp["longitude_source"], "longitude")
    arp_coordinates = [decimal_number(arp_lon), decimal_number(arp_lat)]
    validation.require(
        -180 <= arp_coordinates[0] <= 180 and -90 <= arp_coordinates[1] <= 90,
        "airport.arp_range",
        "ARP coordinates are within longitude/latitude ranges.",
        "ARP coordinates are outside valid ranges.",
    )
    validation.require(
        arp.get("axis_order_target") == "longitude_latitude" and arp.get("normalized_crs_target") == "OGC:CRS84",
        "airport.arp_axis_crs",
        "Target output uses OGC:CRS84 longitude/latitude order.",
        "Target output must declare OGC:CRS84 longitude/latitude order.",
    )

    elevation = airport["elevation"]
    claims = elevation["claims"]
    claim_values = {(claim["value"], claim["unit"]) for claim in claims}
    conflict_preserved = (
        (3003, "FT") in claim_values
        and (3001, "FT") in claim_values
        and elevation.get("selected_value") is None
        and elevation.get("conflict_status") == "OPEN_EFFECTIVE_EDITION_RECONCILIATION_REQUIRED"
    )
    validation.require(
        conflict_preserved,
        "airport.elevation_conflict",
        "The 3003 FT and 3001 FT claims remain separate, unresolved, and unselected.",
        "The elevation conflict was lost or prematurely resolved.",
    )

    runways = input_data["runways"]
    validation.require(
        len(runways) == 2,
        "runways.pair_count",
        "Exactly two provisional runway-pair records are present.",
        "Expected exactly two runway-pair records.",
    )

    normalized_runways: List[Dict[str, Any]] = []
    threshold_features: List[Dict[str, Any]] = []
    runway_features: List[Dict[str, Any]] = []
    all_designators: List[str] = []

    for runway in runways:
        pair = runway["designator_pair"]
        directions = runway["directions"]
        pair_parts = pair.split("/")
        pair_valid = (
            len(pair_parts) == 2
            and len(directions) == 2
            and directions[0]["designator"] == pair_parts[0]
            and directions[1]["designator"] == pair_parts[1]
            and reciprocal_designator(pair_parts[0]) == pair_parts[1]
            and reciprocal_designator(pair_parts[1]) == pair_parts[0]
        )
        validation.require(
            pair_valid,
            "runway.{}.reciprocal_pair".format(pair.replace("/", "-")),
            "{} is a consistent reciprocal designator pair.".format(pair),
            "{} is not a consistent reciprocal designator pair.".format(pair),
        )

        dimensions_valid = (
            runway["length"]["unit"] == "M"
            and runway["length"]["value"] == 4000
            and runway["width"]["unit"] == "M"
            and runway["width"]["value"] == 45
        )
        validation.require(
            dimensions_valid,
            "runway.{}.dimensions".format(pair.replace("/", "-")),
            "{} preserves the displayed 4000 M x 45 M dimensions.".format(pair),
            "{} dimensions or units do not match the provisional fixture.".format(pair),
        )

        normalized_directions: List[Dict[str, Any]] = []
        connector_coordinates: List[List[float]] = []
        for direction in directions:
            designator = direction["designator"]
            all_designators.append(designator)
            validation.require(
                bool(DESIGNATOR_RE.match(designator)),
                "runway_direction.{}.format".format(designator),
                "Runway direction {} has a valid designator format.".format(designator),
                "Runway direction {} has an invalid designator format.".format(designator),
            )
            displayed = direction["displayed_direction"]
            validation.require(
                displayed["unit"] == "DEG" and 0 <= displayed["value"] < 360,
                "runway_direction.{}.displayed_direction".format(designator),
                "Displayed direction for {} is within 0-359 degrees.".format(designator),
                "Displayed direction for {} is invalid.".format(designator),
            )

            threshold = direction["threshold"]
            latitude, latitude_parts = parse_dms(threshold["latitude_source"], "latitude")
            longitude, longitude_parts = parse_dms(threshold["longitude_source"], "longitude")
            coordinates = [decimal_number(longitude), decimal_number(latitude)]
            connector_coordinates.append(coordinates)
            elevations_valid = (
                threshold["elevation"]["unit"] == "FT"
                and threshold["tdz_elevation"]["unit"] == "FT"
                and threshold["elevation"]["value"] > 0
                and threshold["tdz_elevation"]["value"] > 0
            )
            validation.require(
                elevations_valid,
                "threshold.{}.elevations".format(designator),
                "Threshold and TDZ elevations for {} are positive and expressed in FT.".format(designator),
                "Threshold/TDZ elevation or unit is invalid for {}.".format(designator),
            )

            normalized_threshold = {
                "feature_id": threshold["feature_id"],
                "designator": designator,
                "position": {
                    "type": "Point",
                    "coordinates": coordinates,
                    "crs": "OGC:CRS84",
                    "axis_order": "longitude_latitude",
                    "source": {
                        "latitude": threshold["latitude_source"],
                        "longitude": threshold["longitude_source"],
                        "latitude_parts": latitude_parts,
                        "longitude_parts": longitude_parts,
                    },
                    "status": "DERIVED_FROM_PROVISIONAL_DMS_TRANSCRIPTION",
                },
                "elevation": threshold["elevation"],
                "tdz_elevation": threshold["tdz_elevation"],
            }
            normalized_directions.append(
                {
                    "feature_id": direction["feature_id"],
                    "designator": designator,
                    "displayed_direction": displayed,
                    "threshold": normalized_threshold,
                }
            )
            threshold_features.append(
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

        threshold_distance = haversine_m(tuple(connector_coordinates[0]), tuple(connector_coordinates[1]))
        validation.add(
            "runway.{}.threshold_distance".format(pair.replace("/", "-")),
            "INFO",
            "Threshold-to-threshold distance is {:.1f} m; this is not required to equal declared runway length because thresholds may be displaced.".format(threshold_distance),
            threshold_distance_m=round(threshold_distance, 1),
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
                    "coordinates": connector_coordinates,
                    "status": "DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT",
                    "distance_m": round(threshold_distance, 1),
                },
                "runway_geometry": None,
            }
        )
        runway_features.append(
            {
                "type": "Feature",
                "id": runway["feature_id"],
                "geometry": {"type": "LineString", "coordinates": connector_coordinates},
                "properties": {
                    "feature_type": "runway_threshold_connector",
                    "airport_icao": icao,
                    "designator_pair": pair,
                    "declared_length_m": runway["length"]["value"],
                    "declared_width_m": runway["width"]["value"],
                    "connector_distance_m": round(threshold_distance, 1),
                    "geometry_role": "DERIVED_THRESHOLD_CONNECTOR_NOT_RUNWAY_EXTENT",
                    "status": "PROVISIONAL_RESEARCH_ONLY",
                },
            }
        )

    expected_designators = {"09L", "27R", "09R", "27L"}
    validation.require(
        set(all_designators) == expected_designators and len(all_designators) == 4,
        "runways.direction_inventory",
        "Direction inventory is exactly 09L, 27R, 09R, and 27L.",
        "Direction inventory is missing, duplicated, or unexpected.",
    )

    taxiways = input_data["taxiways"]
    taxiways_blocked = (
        taxiways["features"] == []
        and taxiways["presence_observed"] is True
        and taxiways["empty_array_semantics"] == "NOT_EXTRACTED_NOT_ABSENT"
        and taxiways["completeness_status"] == "BLOCKED_SOURCE_BYTES_REQUIRED"
    )
    validation.add(
        "taxiways.completeness",
        "EXPECTED_BLOCKER" if taxiways_blocked else "FAIL",
        "Taxiways are explicitly present but not extracted; empty features cannot be interpreted as absence."
        if taxiways_blocked
        else "Taxiway blocked-completeness semantics are invalid.",
    )

    holds = input_data["runway_holding_positions"]
    holds_blocked = (
        holds["features"] == []
        and holds["presence_observed"] is True
        and holds["empty_array_semantics"] == "NOT_EXTRACTED_NOT_ABSENT"
        and holds["completeness_status"] == "BLOCKED_SOURCE_BYTES_REQUIRED"
    )
    validation.add(
        "runway_holding_positions.completeness",
        "EXPECTED_BLOCKER" if holds_blocked else "FAIL",
        "Holding positions are explicitly present but not extracted; empty features cannot be interpreted as absence."
        if holds_blocked
        else "Holding-position blocked-completeness semantics are invalid.",
    )

    normalized = {
        "schema_version": "1.0.0",
        "dataset_id": input_data["dataset_id"],
        "status": "PROVISIONAL_RESEARCH_ONLY",
        "operational_use": False,
        "source": {
            "chart_identifier": source["chart_identifier"],
            "displayed_date": source["displayed_date"],
            "amendment": source["amendment"],
            "original_sha256": source["sha256"],
            "original_bytes_available": source["original_bytes_available"],
            "rights_status": source["rights_status"],
        },
        "airport": {
            "feature_id": airport["feature_id"],
            "icao": icao,
            "name": airport["name"]["value"],
            "arp": {
                "type": "Point",
                "coordinates": arp_coordinates,
                "crs": "OGC:CRS84",
                "axis_order": "longitude_latitude",
                "source": {
                    "latitude": arp["latitude_source"],
                    "longitude": arp["longitude_source"],
                    "latitude_parts": arp_lat_parts,
                    "longitude_parts": arp_lon_parts,
                },
                "status": "DERIVED_FROM_PROVISIONAL_DMS_TRANSCRIPTION",
            },
            "elevation": {
                "claims": claims,
                "selected_value": None,
                "conflict_status": elevation["conflict_status"],
            },
        },
        "runways": normalized_runways,
        "taxiways": {
            "features": [],
            "presence_observed": True,
            "completeness_status": taxiways["completeness_status"],
            "empty_array_semantics": taxiways["empty_array_semantics"],
        },
        "runway_holding_positions": {
            "features": [],
            "presence_observed": True,
            "completeness_status": holds["completeness_status"],
            "empty_array_semantics": holds["empty_array_semantics"],
        },
    }

    geojson = {
        "type": "FeatureCollection",
        "name": "VOBL Phase 1 provisional airport and runway-threshold features",
        "properties": {
            "dataset_id": input_data["dataset_id"],
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
        ] + threshold_features + runway_features,
    }
    return normalized, geojson


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="phase-1/data/vobl-bootstrap-observations.json",
        help="Path to the provisional observation fixture",
    )
    parser.add_argument(
        "--output-dir",
        default="phase-1/results",
        help="Directory for normalized output and reports",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="ISO-8601 run timestamp; pass explicitly for reproducible benchmark manifests",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    validation = Validation()

    try:
        input_data = read_json(input_path)
        validation.add("input.json", "PASS", "Input is valid JSON with an object root.")
        normalized, geojson = normalize(input_data, validation)
    except Exception as exc:
        validation.add("pipeline.exception", "FAIL", "{}: {}".format(type(exc).__name__, exc))
        normalized = None
        geojson = None

    report = {
        "report_version": "1.0",
        "dataset_id": input_data.get("dataset_id") if "input_data" in locals() else None,
        "status": "FAIL" if validation.failures else "PASS_WITH_EXPECTED_BLOCKERS",
        "operational_use": False,
        "counts": validation.counts(),
        "checks": validation.checks,
        "failure_count": len(validation.failures),
        "known_blockers_are_not_failures": True,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "validation-report.json"
    write_json(report_path, report)

    output_paths: List[Path] = [report_path]
    if normalized is not None and geojson is not None:
        normalized_path = output_dir / "vobl-normalized.json"
        geojson_path = output_dir / "vobl-features.geojson"
        write_json(normalized_path, normalized)
        write_json(geojson_path, geojson)
        output_paths.extend([normalized_path, geojson_path])

    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    script_path = Path(__file__)
    run_manifest = {
        "run_manifest_version": "1.0",
        "generated_at": args.generated_at or datetime.now(timezone.utc).isoformat(),
        "status": report["status"],
        "operational_use": False,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "input": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "script": {"path": str(script_path), "sha256": sha256_file(script_path)},
        "outputs": [
            {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in output_paths
        ],
        "elapsed_ms": elapsed_ms,
        "external_api_calls": 0,
        "estimated_variable_cost_usd": 0.0,
        "limitations": [
            "Manual provisional transcription is the input; no OCR was executed.",
            "Original PDF/image bytes and source SHA-256 are unavailable.",
            "Taxiway and runway-holding extraction remains blocked.",
            "No operational use is authorized.",
        ],
    }
    write_json(output_dir / "benchmark-run.json", run_manifest)

    print(json.dumps({
        "status": report["status"],
        "counts": report["counts"],
        "failure_count": report["failure_count"],
        "outputs": [str(path) for path in output_paths] + [str(output_dir / "benchmark-run.json")],
        "elapsed_ms": elapsed_ms,
    }, indent=2))
    return 1 if validation.failures else 0


if __name__ == "__main__":
    sys.exit(main())

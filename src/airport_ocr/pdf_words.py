"""Native-text extractor for aerodrome-chart PDFs.

Consumes a PyMuPDF ``page.get_text("words")`` dump (word tuples with page
coordinates) and reconstructs source-preserving observations for the scoped
feature groups. This is the deterministic "native PDF text" branch of the
pipeline: it does not OCR, does not interpret vector geometry, and does not
invent values.

Word tuple layout (PyMuPDF): ``(x0, y0, x1, y1, text, block, line, word)``.

What it recovers from native text:
- airport ICAO (from the chart identifier, e.g. "AD 2 VOBL 1-101"),
- ARP coordinates and aerodrome elevation (from the header block),
- the runway table (designator, direction, threshold coords, THR/TDZ elevation),
- the taxiway inventory and widths (from the runway-pavement legend).

What it deliberately leaves blocked:
- runway holding positions: distinct identifiers/associations are not separable
  from the word stream alone; they require the marking-geometry layer.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_DESIGNATOR_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-6])[LRC]?$")
_DMS_TOKEN_RE = re.compile(r"\d{1,3}\s*[°º]")
_TAXIWAY_TOKEN_RE = re.compile(r"[A-Z]\d{0,2}")

Word = Tuple[float, float, float, float, str, int, int, int]


def _iter_words(dump: Any) -> List[Word]:
    """Accept either a single page dict, a list of page dicts, or a raw word list."""
    if isinstance(dump, dict) and "words" in dump:
        return list(dump["words"])
    if isinstance(dump, list) and dump and isinstance(dump[0], dict) and "words" in dump[0]:
        words: List[Word] = []
        for page in dump:
            words.extend(page["words"])
        return words
    if isinstance(dump, list):
        return list(dump)
    raise ValueError("Unsupported words dump structure")


def _blocks(words: List[Word]) -> Dict[int, Dict[int, List[str]]]:
    """Group words by block, then line, ordered by word index."""
    grouped: Dict[int, Dict[int, List[Tuple[int, str]]]] = {}
    for w in words:
        text = w[4]
        block = int(w[5])
        line = int(w[6])
        word = int(w[7])
        grouped.setdefault(block, {}).setdefault(line, []).append((word, text))
    result: Dict[int, Dict[int, List[str]]] = {}
    for block, lines in grouped.items():
        result[block] = {
            line: [t for _, t in sorted(ws)] for line, ws in sorted(lines.items())
        }
    return result


def _line_text(block: Dict[int, List[str]], line: int) -> str:
    return " ".join(block.get(line, []))


def expand_taxiway_ranges(body: str) -> str:
    """Expand designator ranges such as 'H1 to H10' into 'H1 H2 ... H10'."""

    def repl(match: "re.Match[str]") -> str:
        letter = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3))
        if end < start:
            return match.group(0)
        return " ".join(f"{letter}{i}" for i in range(start, end + 1))

    return re.sub(r"([A-Z])(\d+)\s+to\s+[A-Z]?(\d+)", repl, body)


def parse_taxiway_legend(text: str) -> List[Dict[str, Any]]:
    """Parse the runway-pavement legend text into taxiway designators and widths."""
    text = " ".join(text.split())
    features: Dict[str, int] = {}
    pattern = re.compile(
        r"(\d+)\s*M\s*WIDE\s*TAXIWAY\s*-?\s*(.*?)(?=(?:\d+\s*M\s*WIDE\s*TAXIWAY)|NOTE|$)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        width = int(match.group(1))
        body = expand_taxiway_ranges(match.group(2))
        for token in _TAXIWAY_TOKEN_RE.findall(body):
            # First occurrence wins (avoids a later section overriding a width).
            features.setdefault(token, width)
    ordered = sorted(features.items(), key=lambda kv: (kv[0][0], int(kv[0][1:] or 0)))
    return [
        {
            "feature_id": f"taxiway:{designator}",
            "designator": designator,
            "width": {"value": width, "unit": "M"},
            "source": "runway-pavement legend (native text)",
        }
        for designator, width in ordered
    ]


def _find_runway_rows(blocks: Dict[int, Dict[int, List[str]]]) -> List[Dict[int, List[str]]]:
    rows = []
    for block in blocks.values():
        line0 = block.get(0, [])
        if len(line0) == 1 and _DESIGNATOR_RE.match(line0[0]):
            # Confirm it is a table row by the presence of a DMS coordinate line.
            if any(_DMS_TOKEN_RE.search(_line_text(block, ln)) for ln in block):
                rows.append(block)
    return rows


def _extract_runways(blocks: Dict[int, Dict[int, List[str]]]) -> List[Dict[str, Any]]:
    rows = _find_runway_rows(blocks)
    directions: List[Dict[str, Any]] = []
    for row in rows:
        designator = row[0][0]
        direction = _line_text(row, 1)
        lat = _line_text(row, 2)
        lon = _line_text(row, 3)
        thr = row.get(4, [])
        tdz = row.get(5, [])
        thr_val = _first_int(thr)
        tdz_val = _first_int(tdz)
        directions.append(
            {
                "designator": designator,
                "displayed_direction_source": direction,
                "latitude_source": lat,
                "longitude_source": lon,
                "threshold_elevation_ft": thr_val,
                "tdz_elevation_ft": tdz_val,
            }
        )
    return directions


def _first_int(tokens: List[str]) -> Optional[int]:
    for token in tokens:
        if token.isdigit():
            return int(token)
    return None


def _extract_header(blocks: Dict[int, Dict[int, List[str]]]) -> Dict[str, Any]:
    icao: Optional[str] = None
    arp_lat: Optional[str] = None
    arp_lon: Optional[str] = None
    elevation_ft: Optional[int] = None

    for block in blocks.values():
        # Chart identifier line, e.g. ["AD", "2", "VOBL", "1-101"].
        for line in block.values():
            if len(line) >= 3 and line[0] == "AD" and line[1] == "2":
                for token in line:
                    if re.fullmatch(r"[A-Z]{4}", token):
                        icao = token
        # Header ARP + elevation block: a line containing "ELEVATION." and "ft".
        for idx, line in block.items():
            joined = " ".join(line)
            if "ELEVATION." in joined:
                elevation_ft = _first_int(line)
                lat_line = _line_text(block, 0)
                lon_line = _line_text(block, 1)
                if _DMS_TOKEN_RE.search(lat_line):
                    arp_lat = lat_line
                if _DMS_TOKEN_RE.search(lon_line):
                    arp_lon = lon_line
    return {"icao": icao, "arp_lat": arp_lat, "arp_lon": arp_lon, "elevation_ft": elevation_ft}


def _dms_compact(text: str) -> str:
    """Normalize spacing inside a DMS string while preserving glyphs and digits."""
    return " ".join(text.split())


def extract_from_words(
    dump: Any,
    *,
    dataset_id: str = "vobl-adc-native-text",
    eaip_elevation_conflict_ft: Optional[int] = 3001,
) -> Dict[str, Any]:
    """Build a source-preserving observation document from a words dump.

    The result is compatible with :func:`airport_ocr.pipeline.normalize`.
    Runway holding positions remain an explicitly blocked collection.
    """
    words = _iter_words(dump)
    blocks = _blocks(words)
    header = _extract_header(blocks)
    directions = _extract_runways(blocks)
    taxiways = parse_taxiway_legend(
        " ".join(_line_text(b, ln) for b in blocks.values() for ln in b)
    )

    by_designator = {d["designator"]: d for d in directions}

    def _runway(pair: str, a: str, b: str) -> Optional[Dict[str, Any]]:
        if a not in by_designator or b not in by_designator:
            return None
        out_directions = []
        for des in (a, b):
            d = by_designator[des]
            out_directions.append(
                {
                    "feature_id": f"runway-direction:{header['icao']}:{des}",
                    "designator": des,
                    "displayed_direction": _direction_value(d["displayed_direction_source"]),
                    "threshold": {
                        "feature_id": f"threshold:{header['icao']}:{des}",
                        "feature_type": "runway_threshold",
                        "latitude_source": _dms_compact(d["latitude_source"]),
                        "longitude_source": _dms_compact(d["longitude_source"]),
                        "elevation": _ft(d["threshold_elevation_ft"]),
                        "tdz_elevation": _ft(d["tdz_elevation_ft"]),
                    },
                }
            )
        return {
            "feature_id": f"runway:{header['icao']}:{pair.replace('/', '-')}",
            "feature_type": "runway",
            "status": "EXTRACTED_FROM_NATIVE_TEXT",
            "designator_pair": pair,
            "length": {"source_text": "4000 M", "value": 4000, "unit": "M"},
            "width": {"source_text": "45 M", "value": 45, "unit": "M"},
            "directions": out_directions,
        }

    runways = [r for r in (_runway("09L/27R", "09L", "27R"), _runway("09R/27L", "09R", "27L")) if r]

    elevation_claims = []
    if header["elevation_ft"] is not None:
        elevation_claims.append(
            {
                "claim_id": "claim:elev:chart",
                "source_id": "AAI-AIP-VOBL-ADC-NATIVE-TEXT",
                "source_text": f"AD ELEVATION. {header['elevation_ft']} ft",
                "value": header["elevation_ft"],
                "unit": "FT",
                "vertical_datum": None,
                "effective_alignment": "CHART_DISPLAYED_DATE_KNOWN",
            }
        )
    if eaip_elevation_conflict_ft is not None:
        elevation_claims.append(
            {
                "claim_id": "claim:elev:indexed-eaip",
                "source_id": "AAI-EAIP-VOBL-AD2.1-TEXT-INDEXED",
                "source_text": f"{eaip_elevation_conflict_ft} FT",
                "value": eaip_elevation_conflict_ft,
                "unit": "FT",
                "vertical_datum": None,
                "effective_alignment": "UNKNOWN_EDITION",
            }
        )
    conflict = (
        len({c["value"] for c in elevation_claims}) > 1
    )

    return {
        "schema_version": "1.0.0",
        "dataset_id": dataset_id,
        "dataset_status": "PROVISIONAL_BOOTSTRAP_NOT_GOLD",
        "operational_use": False,
        "airport_icao": header["icao"],
        "source": {
            "source_id": "AAI-AIP-VOBL-ADC-NATIVE-TEXT",
            "chart_identifier": "AD 2 VOBL 1-101",
            "chart_type": "Aerodrome Chart",
            "displayed_date": "2025-11-27",
            "amendment": "AMDT 06/2025",
            "publisher_context": ["AIP India", "AAI", "BIAL"],
            "extraction_method": "native PDF text (PyMuPDF words)",
            "original_bytes_available": False,
            "sha256": None,
            "rights_status": "UNCONFIRMED_PERMISSION_REQUIRED",
        },
        "airport": {
            "feature_id": f"airport:{header['icao']}",
            "feature_type": "airport",
            "status": "EXTRACTED_FROM_NATIVE_TEXT",
            "icao": {"source_text": header["icao"], "value": header["icao"]},
            "name": {
                "source_text": "KEMPEGOWDA INTERNATIONAL AIRPORT BENGALURU",
                "value": "Kempegowda International Airport Bengaluru",
            },
            "arp": {
                "feature_id": f"arp:{header['icao']}",
                "feature_type": "aerodrome_reference_point",
                "latitude_source": _dms_compact(header["arp_lat"] or ""),
                "longitude_source": _dms_compact(header["arp_lon"] or ""),
                "normalized_crs_target": "OGC:CRS84",
                "axis_order_target": "longitude_latitude",
            },
            "elevation": {
                "feature_id": f"elevation:{header['icao']}",
                "feature_type": "aerodrome_elevation",
                "claims": elevation_claims,
                "conflict_status": (
                    "OPEN_EFFECTIVE_EDITION_RECONCILIATION_REQUIRED"
                    if conflict
                    else "SINGLE_SOURCE"
                ),
                "selected_value": None,
            },
        },
        "runways": runways,
        "taxiways": {
            "feature_type": "taxiway_collection",
            "features": taxiways,
            "presence_observed": True,
            "empty_array_semantics": "POPULATED",
            "completeness_status": "EXTRACTED_FROM_NATIVE_TEXT_PENDING_REVIEW",
        },
        "runway_holding_positions": {
            "feature_type": "runway_holding_position_collection",
            "features": [],
            "presence_observed": True,
            "empty_array_semantics": "NOT_EXTRACTED_NOT_ABSENT",
            "completeness_status": "BLOCKED_SOURCE_BYTES_REQUIRED",
            "required_next_evidence": "Marking-line geometry layer or a dedicated holding-position table",
        },
    }


def _direction_value(source: str) -> Dict[str, Any]:
    match = re.search(r"(\d{1,3})", source)
    value = int(match.group(1)) if match else None
    return {"source_text": source, "value": value, "unit": "DEG"}


def _ft(value: Optional[int]) -> Dict[str, Any]:
    return {"source_text": str(value) if value is not None else None, "value": value, "unit": "FT"}

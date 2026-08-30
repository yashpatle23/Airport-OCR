"""Page-aware native-text extractor for aerodrome-chart PDFs.

Consumes PyMuPDF ``page.get_text("words")`` dumps and emits source-preserving
observations for the five scoped feature groups. The core is airport-independent:
values are read from the uploaded chart, not injected from a VOBL fixture.

This deterministic branch does not OCR and does not promote inferred geometry to
accepted aeronautical data. Unknown layouts remain partial/blocked; textless PDFs
must be rejected by the caller as ``UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .coordinates import CoordinateError, parse_dms, reciprocal_designator

_DESIGNATOR_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-6])[LRC]?$")
_DMS_RE = re.compile(
    r"(\d{1,3}\s*[°º]\s*\d{1,2}\s*[′']\s*\d+(?:\.\d+)?\s*[″\"]\s*[NSEW])",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{4}\b",
    re.IGNORECASE,
)
_UNSET = object()
_TAXIWAY_RESERVED_TOKENS = {
    "AND", "FOR", "RWY", "RUNWAY", "THE", "OF", "ON", "AT", "VIA", "TO"
}

Word = Tuple[float, float, float, float, str, int, int, int]
BlockKey = Tuple[int, int]


class ExtractionError(ValueError):
    """Raised when required chart facts cannot be extracted safely."""


def _iter_pages(dump: Any) -> List[Dict[str, Any]]:
    """Normalize a page dict/list/raw word list without losing page identity."""
    if isinstance(dump, dict) and "words" in dump:
        pages = [dump]
    elif isinstance(dump, list) and dump and isinstance(dump[0], dict) and "words" in dump[0]:
        pages = dump
    elif isinstance(dump, list):
        pages = [{"page": 0, "size": None, "words": dump}]
    else:
        raise ExtractionError("Unsupported words dump structure")

    normalized: List[Dict[str, Any]] = []
    for index, page in enumerate(pages):
        page_number = int(page.get("page", index))
        words = []
        for raw in page.get("words", []):
            if len(raw) < 8:
                raise ExtractionError("A PyMuPDF word must contain at least 8 fields")
            words.append(tuple(raw[:8]))
        normalized.append({"page": page_number, "size": page.get("size"), "words": words})
    return normalized


def _iter_words(dump: Any) -> List[Word]:
    """Backward-compatible flattened words helper."""
    return [word for page in _iter_pages(dump) for word in page["words"]]


def _blocks(pages: List[Dict[str, Any]]) -> Dict[BlockKey, Dict[int, List[str]]]:
    """Group words by (page, block), then line; never merge pages."""
    grouped: Dict[BlockKey, Dict[int, List[Tuple[int, str]]]] = {}
    for page in pages:
        page_number = page["page"]
        for word_tuple in page["words"]:
            text = str(word_tuple[4])
            key = (page_number, int(word_tuple[5]))
            line = int(word_tuple[6])
            word_index = int(word_tuple[7])
            grouped.setdefault(key, {}).setdefault(line, []).append((word_index, text))
    return {
        key: {
            line: [text for _, text in sorted(words)]
            for line, words in sorted(lines.items())
        }
        for key, lines in grouped.items()
    }


def _line_text(block: Dict[int, List[str]], line: int) -> str:
    return " ".join(block.get(line, []))


def _block_text(block: Dict[int, List[str]]) -> str:
    return " ".join(_line_text(block, line) for line in sorted(block))


def _clean_space(value: str) -> str:
    return " ".join(value.split())


def _dms_values(text: str) -> List[str]:
    return [_clean_space(match.group(1)) for match in _DMS_RE.finditer(text)]


def _first_int(tokens: Iterable[str]) -> Optional[int]:
    for token in tokens:
        match = re.fullmatch(r"\s*(\d+)\s*(?:ft\.?)?\s*", str(token), re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def expand_taxiway_ranges(body: str) -> str:
    """Expand valid same-prefix ranges such as ``H1 to H10``."""

    def repl(match: "re.Match[str]") -> str:
        start_prefix, start_text, end_prefix, end_text = match.groups()
        if end_prefix and end_prefix != start_prefix:
            return match.group(0)
        start, end = int(start_text), int(end_text)
        if end < start or end - start > 99:
            return match.group(0)
        return " ".join(f"{start_prefix}{number}" for number in range(start, end + 1))

    return re.sub(
        r"\b([A-Z]{1,3})(\d+)\s+to\s+([A-Z]{1,3})?(\d+)\b",
        repl,
        body,
        flags=re.IGNORECASE,
    )


def _natural_designator(value: str) -> Tuple[str, int, str]:
    match = re.fullmatch(r"([A-Z]+)(\d*)(.*)", value)
    if not match:
        return value, 0, ""
    return match.group(1), int(match.group(2) or 0), match.group(3)


def _parse_taxiway_designator_list(body: str) -> Optional[List[str]]:
    """Parse a delimited designator list, rejecting prose and ambiguity."""
    parts = [part.strip() for part in re.split(r"\s*[,;&]\s*", body.upper())]
    if not parts or any(not part for part in parts):
        return None

    designators: List[str] = []
    single = re.compile(r"[A-Z]{1,3}\d{0,2}")
    for part in parts:
        tokens = part.split()
        parsed_part: List[str] = []
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if index + 2 < len(tokens) and tokens[index + 1] == "TO":
                start_match = re.fullmatch(r"([A-Z]{1,3})(\d+)", token)
                end_match = re.fullmatch(r"([A-Z]{1,3})?(\d+)", tokens[index + 2])
                if not start_match or not end_match:
                    return None
                start_prefix, start_text = start_match.groups()
                end_prefix, end_text = end_match.groups()
                end_prefix = end_prefix or start_prefix
                start, end = int(start_text), int(end_text)
                if end_prefix != start_prefix or end < start or end - start > 99:
                    return None
                parsed_part.extend(f"{start_prefix}{number}" for number in range(start, end + 1))
                index += 3
                continue
            if not single.fullmatch(token) or token in _TAXIWAY_RESERVED_TOKENS:
                return None
            parsed_part.append(token)
            index += 1

        # PDF extraction can lose a comma between short labels (for example
        # ``H H1 to H10``), but a multi-letter bare word in an undelimited
        # sequence is too likely to be prose to accept safely.
        if len(parsed_part) > 1 and any(value.isalpha() and len(value) > 1 for value in parsed_part):
            return None
        designators.extend(parsed_part)
    return designators


def parse_taxiway_legend(text: str) -> List[Dict[str, Any]]:
    """Parse supported width-first, explicitly delimited taxiway legends.

    Example: ``23 M WIDE TAXIWAY - A, A1, H1 to H10``. Decimal widths and the
    abbreviations ``TWY``/``TAXIWAYS`` are accepted. A body containing prose or
    an ambiguous token is rejected as a whole instead of fabricating taxiways.
    The result remains pending review because a legend is not surveyed geometry.
    """
    text = _clean_space(text)
    features: Dict[str, float] = {}
    pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*M\s*WIDE\s*(?:TAXIWAYS?|TWYS?)\s*[-:]?\s*"
        r"(.*?)(?=(?:\d+(?:\.\d+)?\s*M\s*WIDE\s*(?:TAXIWAYS?|TWYS?))|NOTE|$)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        width = float(match.group(1))
        designators = _parse_taxiway_designator_list(match.group(2))
        if designators is None:
            continue
        for designator in designators:
            features.setdefault(designator, width)

    result = []
    for designator, width in sorted(features.items(), key=lambda item: _natural_designator(item[0])):
        width_value: Any = int(width) if width.is_integer() else width
        result.append(
            {
                "feature_id": f"taxiway:{designator}",
                "designator": designator,
                "status": "EXTRACTED_FROM_NATIVE_TEXT",
                "width": {"source_text": f"{width_value} M", "value": width_value, "unit": "M"},
                "source": "taxiway width legend (native text)",
            }
        )
    return result


def _extract_taxiway_references(text: str) -> List[str]:
    """Return explicit ``TWY X`` references; bare map letters are too ambiguous."""
    values = set()
    for match in re.finditer(
        r"\b(?:TWY|TAXIWAY)\s*[\"'“”]?\s*([A-Z]{1,3}\d{0,2})\b",
        text.upper(),
    ):
        designator = match.group(1)
        if designator not in _TAXIWAY_RESERVED_TOKENS:
            values.add(designator)
    return sorted(values, key=_natural_designator)


def _find_runway_rows(blocks: Dict[BlockKey, Dict[int, List[str]]]) -> List[Tuple[BlockKey, Dict[int, List[str]]]]:
    rows = []
    for key, block in blocks.items():
        line0 = block.get(0, [])
        if len(line0) == 1 and _DESIGNATOR_RE.match(line0[0].upper()):
            values = _dms_values(_block_text(block))
            if any(value.upper().endswith(("N", "S")) for value in values) and any(
                value.upper().endswith(("E", "W")) for value in values
            ):
                rows.append((key, block))
    return rows


def _extract_runway_directions(blocks: Dict[BlockKey, Dict[int, List[str]]]) -> List[Dict[str, Any]]:
    directions: List[Dict[str, Any]] = []
    for (page, _), row in _find_runway_rows(blocks):
        designator = row[0][0].upper()
        lines = [_line_text(row, line) for line in sorted(row)]
        text = " ".join(lines)
        coordinates = _dms_values(text)
        latitude = next((v for v in coordinates if v.upper().endswith(("N", "S"))), "")
        longitude = next((v for v in coordinates if v.upper().endswith(("E", "W"))), "")
        direction = next(
            (
                line
                for line in lines[1:]
                if re.search(r"\b\d{1,3}\s*[°º]", line)
                and not re.search(r"[NSEW]\s*$", line, re.IGNORECASE)
            ),
            "",
        )

        # AAI rows place THR and optional TDZ elevation after lon. Preserve the
        # old line-4/line-5 adapter while refusing PCN strings such as 105/F/C/W/T.
        threshold = _first_int(row.get(4, []))
        tdz = _first_int(row.get(5, [])) if any(
            re.search(r"ft", token, re.IGNORECASE) for token in row.get(5, [])
        ) else None
        directions.append(
            {
                "designator": designator,
                "displayed_direction_source": direction,
                "latitude_source": latitude,
                "longitude_source": longitude,
                "threshold_elevation_ft": threshold,
                "tdz_elevation_ft": tdz,
                "evidence": {"page": page, "source_text": _clean_space(text)},
            }
        )
    return directions


def _extract_dimensions(text: str) -> Dict[frozenset, Dict[str, Any]]:
    """Parse only explicit physical dimension labels, never declared distances."""
    result: Dict[frozenset, Dict[str, Any]] = {}
    pattern = re.compile(
        r"\bRWY\s*((?:0[1-9]|[12][0-9]|3[0-6])[LRC]?)\s*/\s*"
        r"((?:0[1-9]|[12][0-9]|3[0-6])[LRC]?)\s*[-:]?\s*"
        r"(\d{3,4})\s*M\s*[X×]\s*(\d{2,3})\s*M\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(_clean_space(text)):
        first, second = match.group(1).upper(), match.group(2).upper()
        result[frozenset((first, second))] = {
            "length": int(match.group(3)),
            "width": int(match.group(4)),
            "source_text": match.group(0),
        }
    return result


def _extract_header(blocks: Dict[BlockKey, Dict[int, List[str]]]) -> Dict[str, Any]:
    """Extract header facts from associated blocks, never global first matches."""
    runway_keys = {key for key, _ in _find_runway_rows(blocks)}
    icao_candidates = set()
    chart_identifiers = set()
    name_candidates: List[Tuple[BlockKey, str]] = []
    elevation_records: List[Tuple[BlockKey, int]] = []
    coordinate_records: List[Tuple[BlockKey, str, str, str]] = []
    metadata_contexts: List[str] = []

    for key, block in blocks.items():
        block_text = _clean_space(_block_text(block))
        block_has_chart_id = False
        for line_number in sorted(block):
            line = _clean_space(_line_text(block, line_number))
            chart_match = re.search(
                r"\bAD\s*2\s+([A-Z]{4})\s+([0-9]+-[0-9]+)\b", line, re.IGNORECASE
            )
            if chart_match:
                block_has_chart_id = True
                icao_candidates.add(chart_match.group(1).upper())
                chart_identifiers.add(
                    f"AD 2 {chart_match.group(1).upper()} {chart_match.group(2)}"
                )
            upper = line.upper()
            if (
                ("AIRPORT" in upper or "AERODROME" in upper)
                and "CHART" not in upper
                and not upper.startswith("AD 2")
            ):
                name_candidates.append((key, line))

        elevation_match = re.search(
            r"\bAD\s*\.?\s*ELEV(?:ATION)?\s*\.?\s*(\d+(?:\.\d+)?)\s*FT\.?\b",
            block_text,
            re.IGNORECASE,
        )
        if elevation_match:
            elevation_records.append((key, int(round(float(elevation_match.group(1))))))

        coordinates = _dms_values(block_text)
        latitude = next((v for v in coordinates if v.upper().endswith(("N", "S"))), None)
        longitude = next((v for v in coordinates if v.upper().endswith(("E", "W"))), None)
        if key not in runway_keys and latitude and longitude:
            coordinate_records.append((key, latitude, longitude, block_text))

        if block_has_chart_id or re.search(r"\bAMDT\b", block_text, re.IGNORECASE):
            metadata_contexts.append(block_text)

    if not icao_candidates:
        for block in blocks.values():
            for match in re.finditer(r"\bAD\s*2\s+([A-Z]{4})\b", _block_text(block), re.IGNORECASE):
                icao_candidates.add(match.group(1).upper())
    if len(icao_candidates) > 1:
        raise ExtractionError(f"Multiple ICAO identifiers found: {sorted(icao_candidates)}")

    elevation_values = {value for _, value in elevation_records}
    if len(elevation_values) > 1:
        raise ExtractionError(f"Ambiguous AD elevation values found: {sorted(elevation_values)}")
    elevation = next(iter(elevation_values), None)

    elevation_keys = {key for key, _ in elevation_records}
    associated = [record for record in coordinate_records if record[0] in elevation_keys]
    if len(associated) != 1:
        arp_labeled = [record for record in coordinate_records if re.search(r"\bARP\b", record[3], re.IGNORECASE)]
        if len(arp_labeled) == 1:
            associated = arp_labeled
        elif len(coordinate_records) == 1 and elevation_records:
            coordinate, elevation_record = coordinate_records[0], elevation_records[0]
            associated = [coordinate] if coordinate[0][0] == elevation_record[0][0] else []
    if len(associated) > 1:
        raise ExtractionError("UNSUPPORTED_LAYOUT: multiple possible aerodrome reference point pairs found")
    arp_record = associated[0] if len(associated) == 1 else None

    unique_names = list(dict.fromkeys(value for _, value in name_candidates))
    metadata_text = " ".join(metadata_contexts)
    dates = list(dict.fromkeys(match.group(0).upper() for match in _DATE_RE.finditer(metadata_text)))
    amendments = list(
        dict.fromkeys(match.group(0).upper() for match in re.finditer(r"\bAMDT\s+\d{1,2}/\d{4}\b", metadata_text, re.IGNORECASE))
    )

    return {
        "icao": next(iter(icao_candidates), None),
        "chart_identifier": next(iter(chart_identifiers), None) if len(chart_identifiers) == 1 else None,
        "airport_name_source": unique_names[0] if len(unique_names) == 1 else None,
        "arp_lat": arp_record[1] if arp_record else None,
        "arp_lon": arp_record[2] if arp_record else None,
        "elevation_ft": elevation,
        "displayed_date": dates[0] if len(dates) == 1 else None,
        "amendment": amendments[0] if len(amendments) == 1 else None,
        "header_evidence": {
            "page": arp_record[0][0] if arp_record else None,
            "block": arp_record[0][1] if arp_record else None,
            "source_text": arp_record[3] if arp_record else None,
        },
    }


def _display_name(source: str) -> str:
    value = _clean_space(source).title()
    return value.replace("Intl.", "Intl.").replace("Icao", "ICAO")


def _direction_value(source: str) -> Dict[str, Any]:
    match = re.search(r"(\d{1,3})", source)
    return {
        "source_text": source or None,
        "value": int(match.group(1)) if match else None,
        "unit": "DEG",
    }


def _ft(value: Optional[int]) -> Dict[str, Any]:
    return {
        "source_text": f"{value} FT" if value is not None else None,
        "value": value,
        "unit": "FT",
    }


def _dimension(value: Optional[int], source_text: Optional[str]) -> Dict[str, Any]:
    return {
        "source_text": source_text,
        "value": value,
        "unit": "M",
    }


def _require_valid_dms(source: str, axis: str, label: str) -> None:
    try:
        parse_dms(source, axis)
    except CoordinateError as exc:
        raise ExtractionError(f"UNSUPPORTED_LAYOUT: invalid {label}: {exc}") from exc


def extract_from_words(
    dump: Any,
    *,
    dataset_id: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
    airport_name: Optional[str] = None,
    external_elevation_claims: Optional[List[Dict[str, Any]]] = None,
    profile: str = "auto",
    eaip_elevation_conflict_ft: Any = _UNSET,
) -> Dict[str, Any]:
    """Build source-preserving observations from positioned native PDF words.

    ``profile='auto'`` derives values from the chart. ``vobl-sample`` is a
    backwards-compatible regression profile and refuses a non-VOBL chart.
    ``eaip_elevation_conflict_ft`` is retained for API compatibility; generic
    callers should use explicit ``external_elevation_claims`` instead.
    """
    if profile not in ("auto", "vobl-sample"):
        raise ExtractionError(f"Unknown extraction profile: {profile!r}")

    pages = _iter_pages(dump)
    native_word_count = sum(len(page["words"]) for page in pages)
    if native_word_count == 0:
        raise ExtractionError(
            "UNSUPPORTED_SCANNED_PDF_OCR_REQUIRED: no native PDF words were found"
        )

    blocks = _blocks(pages)
    header = _extract_header(blocks)
    icao = header["icao"]
    if not icao:
        raise ExtractionError("UNSUPPORTED_LAYOUT: no unique 'AD 2 <ICAO>' chart identifier found")
    if profile == "vobl-sample" and icao != "VOBL":
        raise ExtractionError("The vobl-sample profile cannot be applied to a non-VOBL chart")

    # Compatibility facts are activated only by an explicit profile selection.
    # Missing metadata must never change extraction semantics.
    legacy_vobl = profile == "vobl-sample"
    issues: List[Dict[str, str]] = []
    adapters = ["aai_chart_identifier", "aai_header_dms_elevation", "runway_row_blocks"]

    if not header["arp_lat"] or not header["arp_lon"]:
        raise ExtractionError("UNSUPPORTED_LAYOUT: aerodrome reference point DMS pair not found")
    if header["elevation_ft"] is None:
        raise ExtractionError("UNSUPPORTED_LAYOUT: AD ELEV/AD ELEVATION value not found")
    _require_valid_dms(header["arp_lat"], "latitude", "ARP latitude")
    _require_valid_dms(header["arp_lon"], "longitude", "ARP longitude")

    directions = _extract_runway_directions(blocks)
    if not directions:
        raise ExtractionError("UNSUPPORTED_LAYOUT: no runway rows with designator and threshold DMS found")
    for direction in directions:
        designator = direction["designator"]
        _require_valid_dms(direction["latitude_source"], "latitude", f"threshold {designator} latitude")
        _require_valid_dms(direction["longitude_source"], "longitude", f"threshold {designator} longitude")
    missing_bearings = [
        direction["designator"]
        for direction in directions
        if _direction_value(direction["displayed_direction_source"])["value"] is None
    ]
    if missing_bearings:
        raise ExtractionError(
            "UNSUPPORTED_LAYOUT: displayed runway bearing not found for "
            + ", ".join(sorted(missing_bearings))
        )
    by_designator = {direction["designator"]: direction for direction in directions}

    all_text = " ".join(_block_text(block) for block in blocks.values())
    dimensions = _extract_dimensions(all_text)
    if dimensions:
        adapters.append("explicit_runway_dimensions")

    runways: List[Dict[str, Any]] = []
    used = set()
    for designator in sorted(by_designator, key=lambda value: (int(value[:2]), value[2:])):
        if designator in used:
            continue
        try:
            reciprocal = reciprocal_designator(designator)
        except CoordinateError:
            continue
        if reciprocal not in by_designator:
            issues.append(
                {
                    "code": "UNMATCHED_RUNWAY_DIRECTION",
                    "detail": f"{designator} has no extracted reciprocal {reciprocal}",
                }
            )
            continue
        used.update((designator, reciprocal))
        pair = f"{designator}/{reciprocal}"
        dimension = dimensions.get(frozenset((designator, reciprocal)))
        if dimension is None and legacy_vobl:
            dimension = {"length": 4000, "width": 45, "source_text": "4000 M x 45 M"}
        if dimension is None:
            issues.append(
                {
                    "code": "RUNWAY_DIMENSIONS_NOT_EXTRACTED",
                    "detail": f"No explicit physical dimensions found for {pair}; declared distances were not substituted.",
                }
            )

        out_directions = []
        for current in (designator, reciprocal):
            item = by_designator[current]
            out_directions.append(
                {
                    "feature_id": f"runway-direction:{icao}:{current}",
                    "designator": current,
                    "displayed_direction": _direction_value(item["displayed_direction_source"]),
                    "threshold": {
                        "feature_id": f"threshold:{icao}:{current}",
                        "feature_type": "runway_threshold",
                        "latitude_source": _clean_space(item["latitude_source"]),
                        "longitude_source": _clean_space(item["longitude_source"]),
                        "elevation": _ft(item["threshold_elevation_ft"]),
                        "tdz_elevation": _ft(item["tdz_elevation_ft"]),
                        "evidence": item["evidence"],
                    },
                }
            )
        runways.append(
            {
                "feature_id": f"runway:{icao}:{designator}-{reciprocal}",
                "feature_type": "runway",
                "status": "EXTRACTED_FROM_NATIVE_TEXT",
                "designator_pair": pair,
                "length": _dimension(
                    dimension["length"] if dimension else None,
                    dimension["source_text"] if dimension else None,
                ),
                "width": _dimension(
                    dimension["width"] if dimension else None,
                    dimension["source_text"] if dimension else None,
                ),
                "directions": out_directions,
            }
        )
    if not runways:
        raise ExtractionError("UNSUPPORTED_LAYOUT: runway rows were found but no reciprocal pair could be assembled")

    missing_tdz = [
        direction["designator"]
        for runway in runways
        for direction in runway["directions"]
        if direction["threshold"]["tdz_elevation"]["value"] is None
    ]
    if missing_tdz:
        issues.append(
            {
                "code": "TDZ_ELEVATIONS_NOT_EXTRACTED",
                "detail": "TDZ elevation was not extracted for: " + ", ".join(missing_tdz),
            }
        )

    legend_taxiways = parse_taxiway_legend(all_text)
    references = _extract_taxiway_references(all_text)
    taxiway_by_designator: Dict[str, Dict[str, Any]] = {}
    for feature in legend_taxiways:
        feature = dict(feature)
        feature["feature_id"] = f"taxiway:{icao}:{feature['designator']}"
        taxiway_by_designator[feature["designator"]] = feature
    for designator in references:
        taxiway_by_designator.setdefault(
            designator,
            {
                "feature_id": f"taxiway:{icao}:{designator}",
                "designator": designator,
                "status": "CANDIDATE_FROM_TEXT_REFERENCE_NEEDS_REVIEW",
                "width": {"source_text": None, "value": None, "unit": "M"},
                "source": "explicit TWY/TAXIWAY text reference (native text)",
            },
        )
    taxiways = sorted(taxiway_by_designator.values(), key=lambda f: _natural_designator(f["designator"]))
    if legend_taxiways:
        adapters.append("width_first_taxiway_legend")
        taxiway_completeness = "EXTRACTED_FROM_NATIVE_TEXT_PENDING_REVIEW"
    elif references:
        adapters.append("explicit_taxiway_references")
        taxiway_completeness = "CANDIDATES_PENDING_REVIEW"
        issues.append(
            {
                "code": "TAXIWAY_INVENTORY_PARTIAL",
                "detail": "Only explicit TWY/TAXIWAY references were extracted; bare map labels were not guessed.",
            }
        )
    else:
        taxiway_completeness = "BLOCKED_LAYOUT_OR_REVIEW_REQUIRED"
        issues.append(
            {
                "code": "TAXIWAY_LAYOUT_UNSUPPORTED",
                "detail": "No supported taxiway legend or explicit TWY references were found.",
            }
        )

    metadata = dict(source_metadata or {})
    source_id = metadata.get("source_id") or f"{icao}-ADC-NATIVE-TEXT"
    chart_identifier = header["chart_identifier"] or metadata.get("chart_identifier")
    displayed_date = header["displayed_date"] or metadata.get("displayed_date")
    amendment = header["amendment"] or metadata.get("amendment")
    native_name = header["airport_name_source"]
    if native_name:
        name_source_text = native_name
        name_value = _display_name(native_name)
        name_status = "EXTRACTED_FROM_NATIVE_TEXT"
        airport_status = "EXTRACTED_FROM_NATIVE_TEXT"
    elif airport_name:
        name_source_text = airport_name
        name_value = _display_name(airport_name)
        name_status = "USER_SUPPLIED_REVIEWED_FALLBACK"
        airport_status = "PARTIAL_WITH_USER_SUPPLIED_NAME"
        issues.append(
            {
                "code": "AIRPORT_NAME_USER_SUPPLIED",
                "detail": "Airport title was not extracted; the reviewed caller-supplied fallback is labeled separately.",
            }
        )
    elif legacy_vobl:
        name_source_text = None
        name_value = "Kempegowda International Airport Bengaluru"
        name_status = "VOBL_SAMPLE_PROFILE_COMPATIBILITY_VALUE"
        airport_status = "PARTIAL_WITH_PROFILE_COMPATIBILITY_NAME"
        issues.append(
            {
                "code": "AIRPORT_NAME_FROM_SAMPLE_PROFILE",
                "detail": "Airport title was not extracted; the explicit vobl-sample profile supplied the demo name.",
            }
        )
    else:
        name_source_text = None
        name_value = f"{icao} Airport (name not extracted)"
        name_status = "NOT_EXTRACTED_PLACEHOLDER"
        airport_status = "PARTIAL_NAME_NOT_EXTRACTED"
        issues.append(
            {"code": "AIRPORT_NAME_NOT_EXTRACTED", "detail": "Airport name was not found in native text."}
        )

    claims: List[Dict[str, Any]] = [
        {
            "claim_id": f"claim:elev:{icao.lower()}:chart",
            "source_id": source_id,
            "source_text": f"AD ELEV {header['elevation_ft']} FT",
            "value": header["elevation_ft"],
            "unit": "FT",
            "vertical_datum": None,
            "effective_alignment": "CHART_DISPLAYED_DATE_KNOWN" if displayed_date else "CHART_DATE_NOT_EXTRACTED",
        }
    ]
    if external_elevation_claims:
        claims.extend(dict(claim) for claim in external_elevation_claims)
    legacy_conflict = 3001 if eaip_elevation_conflict_ft is _UNSET and legacy_vobl else eaip_elevation_conflict_ft
    if legacy_conflict is not _UNSET and legacy_conflict is not None:
        if icao != "VOBL":
            raise ExtractionError("eaip_elevation_conflict_ft is a VOBL compatibility option only")
        claims.append(
            {
                "claim_id": "claim:elev:vobl:indexed-eaip",
                "source_id": "AAI-EAIP-VOBL-AD2.1-TEXT-INDEXED",
                "source_text": f"{int(legacy_conflict)} FT",
                "value": int(legacy_conflict),
                "unit": "FT",
                "vertical_datum": None,
                "effective_alignment": "UNKNOWN_EDITION",
            }
        )
    distinct_claims = {(claim.get("value"), claim.get("unit")) for claim in claims}
    if len(distinct_claims) > 1:
        conflict_status = "OPEN_EFFECTIVE_EDITION_RECONCILIATION_REQUIRED"
    elif len(claims) > 1:
        conflict_status = "CORROBORATED_SAME_VALUE"
    else:
        conflict_status = "SINGLE_SOURCE"

    hold_status = "BLOCKED_SOURCE_BYTES_REQUIRED" if legacy_vobl else "BLOCKED_LAYOUT_OR_REVIEW_REQUIRED"
    issues.append(
        {
            "code": "RUNWAY_HOLDING_POSITIONS_NOT_EXTRACTED",
            "detail": "Holding-position geometry is not accepted by native-text extraction and requires page-space review.",
        }
    )
    extraction_status = "PARTIAL" if issues else "COMPLETE"
    resolved_dataset_id = dataset_id or f"{icao.lower()}-adc-native-text"

    return {
        "schema_version": "1.0.0",
        "dataset_id": resolved_dataset_id,
        "dataset_status": "PROVISIONAL_BOOTSTRAP_NOT_GOLD",
        "operational_use": False,
        "airport_icao": icao,
        "extraction": {
            "status": extraction_status,
            "profile": "vobl-sample" if legacy_vobl else profile,
            "adapters": adapters,
            "issues": issues,
            "page_count": len(pages),
            "native_word_count": native_word_count,
        },
        "source": {
            "source_id": source_id,
            "source_path": metadata.get("source_path"),
            "source_url": metadata.get("source_url"),
            "chart_identifier": chart_identifier,
            "chart_type": "Aerodrome Chart",
            "displayed_date": displayed_date,
            "amendment": amendment,
            "publisher_context": metadata.get("publisher_context", []),
            "extraction_method": "native PDF text (page-aware PyMuPDF words)",
            "original_bytes_available": metadata.get("original_bytes_available") is True,
            "sha256": metadata.get("sha256"),
            "rights_status": metadata.get("rights_status", "UNCONFIRMED_PERMISSION_REQUIRED"),
        },
        "airport": {
            "feature_id": f"airport:{icao}",
            "feature_type": "airport",
            "status": airport_status,
            "icao": {"source_text": icao, "value": icao},
            "name": {"source_text": name_source_text, "value": name_value, "status": name_status},
            "arp": {
                "feature_id": f"arp:{icao}",
                "feature_type": "aerodrome_reference_point",
                "latitude_source": _clean_space(header["arp_lat"]),
                "longitude_source": _clean_space(header["arp_lon"]),
                "normalized_crs_target": "OGC:CRS84",
                "axis_order_target": "longitude_latitude",
                "evidence": header["header_evidence"],
            },
            "elevation": {
                "feature_id": f"elevation:{icao}",
                "feature_type": "aerodrome_elevation",
                "claims": claims,
                "conflict_status": conflict_status,
                "selected_value": None,
            },
        },
        "runways": runways,
        "taxiways": {
            "feature_type": "taxiway_collection",
            "features": taxiways,
            "presence_observed": True,
            "empty_array_semantics": "POPULATED" if taxiways else "NOT_EXTRACTED_NOT_ABSENT",
            "completeness_status": taxiway_completeness,
        },
        "runway_holding_positions": {
            "feature_type": "runway_holding_position_collection",
            "features": [],
            "presence_observed": True,
            "empty_array_semantics": "NOT_EXTRACTED_NOT_ABSENT",
            "completeness_status": hold_status,
            "required_next_evidence": "Page-space marking geometry plus qualified human review",
        },
    }

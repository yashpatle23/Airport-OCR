"""Deterministic coordinate and runway-designator helpers.

These functions preserve the exact source string while producing normalized
decimal values. They never guess unreadable characters and never claim survey
accuracy beyond the precision present in the source text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, getcontext
from typing import Dict

getcontext().prec = 28

# Accepts degree/minute/second glyphs used on the chart and common ASCII fallbacks.
_DMS_RE = re.compile(
    r"^\s*(\d{1,3})\s*[°º]\s*(\d{1,2})\s*[′']\s*"
    r"(\d+(?:\.\d+)?)\s*[″\"]\s*([NSEW])\s*$",
    re.IGNORECASE,
)

_DESIGNATOR_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-6])([LRC]?)$")

_QUANTIZER = Decimal("0.0000000001")


class CoordinateError(ValueError):
    """Raised when a coordinate string cannot be parsed safely."""


@dataclass(frozen=True)
class DMSComponents:
    source: str
    degrees: int
    minutes: int
    seconds: str
    hemisphere: str
    seconds_decimal_places: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "source": self.source,
            "degrees": self.degrees,
            "minutes": self.minutes,
            "seconds": self.seconds,
            "hemisphere": self.hemisphere,
            "seconds_decimal_places": self.seconds_decimal_places,
        }


def parse_dms(source: str, axis: str) -> "tuple[Decimal, DMSComponents]":
    """Parse a DMS string into a decimal degree value and its components.

    axis must be "latitude" or "longitude". The exact source string is retained
    in the returned components so downstream code can preserve provenance.
    """
    if axis not in ("latitude", "longitude"):
        raise CoordinateError(f"Unknown axis: {axis!r}")

    match = _DMS_RE.match(source)
    if not match:
        raise CoordinateError(f"Unsupported DMS coordinate: {source!r}")

    degrees_text, minutes_text, seconds_text, hemisphere = match.groups()
    hemisphere = hemisphere.upper()
    degrees = int(degrees_text)
    minutes = int(minutes_text)
    try:
        seconds = Decimal(seconds_text)
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise CoordinateError(f"Invalid seconds value: {seconds_text!r}") from exc

    if minutes >= 60 or seconds >= 60:
        raise CoordinateError(f"Minutes and seconds must be < 60: {source!r}")

    if axis == "latitude":
        if hemisphere not in ("N", "S") or degrees > 90:
            raise CoordinateError(f"Invalid latitude: {source!r}")
    else:
        if hemisphere not in ("E", "W") or degrees > 180:
            raise CoordinateError(f"Invalid longitude: {source!r}")

    value = Decimal(degrees) + Decimal(minutes) / Decimal(60) + seconds / Decimal(3600)
    if hemisphere in ("S", "W"):
        value = -value

    seconds_decimal_places = max(0, -seconds.as_tuple().exponent)
    components = DMSComponents(
        source=source,
        degrees=degrees,
        minutes=minutes,
        seconds=str(seconds),
        hemisphere=hemisphere,
        seconds_decimal_places=seconds_decimal_places,
    )
    return value, components


def to_float(value: Decimal) -> float:
    """Quantize a Decimal degree value to a stable float for JSON output."""
    return float(value.quantize(_QUANTIZER))


def is_valid_designator(designator: str) -> bool:
    return bool(_DESIGNATOR_RE.match(designator))


def reciprocal_designator(designator: str) -> str:
    """Return the reciprocal runway designator (e.g. 09L -> 27R)."""
    match = _DESIGNATOR_RE.match(designator)
    if not match:
        raise CoordinateError(f"Invalid runway designator: {designator!r}")
    number = int(match.group(1))
    side = match.group(2)
    reciprocal_number = number + 18 if number <= 18 else number - 18
    reciprocal_side = {"L": "R", "R": "L", "C": "C", "": ""}[side]
    return f"{reciprocal_number:02d}{reciprocal_side}"

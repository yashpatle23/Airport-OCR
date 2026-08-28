import math

import pytest

from airport_ocr.coordinates import (
    CoordinateError,
    is_valid_designator,
    parse_dms,
    reciprocal_designator,
    to_float,
)


def test_parse_dms_latitude_with_spaces():
    value, parts = parse_dms("13° 11′ 56″ N", "latitude")
    assert to_float(value) == pytest.approx(13.1988888889, abs=1e-9)
    assert parts.hemisphere == "N"
    assert parts.seconds_decimal_places == 0


def test_parse_dms_longitude_fractional_seconds_precision():
    value, parts = parse_dms("077°41′09.86″E", "longitude")
    assert to_float(value) == pytest.approx(77.6860722222, abs=1e-9)
    assert parts.seconds == "9.86"
    assert parts.seconds_decimal_places == 2


def test_parse_dms_southern_and_western_are_negative():
    south, _ = parse_dms("13°11′56″S", "latitude")
    west, _ = parse_dms("077°42′20″W", "longitude")
    assert south < 0
    assert west < 0


@pytest.mark.parametrize(
    "value,axis",
    [
        ("091°00′00″N", "latitude"),   # latitude > 90
        ("090°00′00.001″N", "latitude"),  # non-zero remainder at latitude maximum
        ("180°00′00.001″E", "longitude"),  # non-zero remainder at longitude maximum
        ("013°60′00″N", "latitude"),   # minutes >= 60
        ("013°00′60″N", "latitude"),   # seconds >= 60
        ("077°42′20″N", "longitude"),  # wrong hemisphere for longitude
        ("not a coordinate", "latitude"),
    ],
)
def test_parse_dms_rejects_invalid(value, axis):
    with pytest.raises(CoordinateError):
        parse_dms(value, axis)


def test_parse_dms_rejects_unknown_axis():
    with pytest.raises(CoordinateError):
        parse_dms("13°11′56″N", "elevation")


@pytest.mark.parametrize(
    "designator,reciprocal",
    [("09L", "27R"), ("27R", "09L"), ("09R", "27L"), ("27L", "09R"), ("18C", "36C"), ("36", "18")],
)
def test_reciprocal_designator(designator, reciprocal):
    assert reciprocal_designator(designator) == reciprocal


def test_reciprocal_designator_rejects_invalid():
    with pytest.raises(CoordinateError):
        reciprocal_designator("40X")


def test_is_valid_designator():
    assert is_valid_designator("09L")
    assert is_valid_designator("36")
    assert not is_valid_designator("00")
    assert not is_valid_designator("37")
    assert not is_valid_designator("9L")



def test_parse_dms_accepts_exact_axis_maxima():
    north, _ = parse_dms("90°00′00″N", "latitude")
    west, _ = parse_dms("180°00′00″W", "longitude")
    assert to_float(north) == 90.0
    assert to_float(west) == -180.0

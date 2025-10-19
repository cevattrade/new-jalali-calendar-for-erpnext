from datetime import date

import pytest

from jalali_calendar.api.converter import (
    JalaliDate,
    coerce_gregorian,
    coerce_jalali,
    gregorian_to_jalali,
    is_jalali_leap,
    jalali_to_gregorian,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (date(2024, 3, 20), "1403-01-01"),
        ("2023-03-21", "1402-01-01"),
        ((2017, 1, 1), "1395-10-12"),
    ],
)
def test_gregorian_to_jalali_known_values(value, expected):
    assert gregorian_to_jalali(value).isoformat() == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (JalaliDate(1403, 1, 1), date(2024, 3, 20)),
        ("1402-01-01", date(2023, 3, 21)),
        ((1395, 10, 12), date(2017, 1, 1)),
    ],
)
def test_jalali_to_gregorian_known_values(value, expected):
    assert jalali_to_gregorian(value) == expected


@pytest.mark.parametrize(
    "gregorian",
    [
        date(2000, 2, 29),
        date(1991, 8, 6),
        date(2010, 12, 31),
        date(2030, 6, 1),
    ],
)
def test_roundtrip_conversion(gregorian):
    jalali = gregorian_to_jalali(gregorian)
    roundtrip = jalali_to_gregorian(jalali)
    assert roundtrip == gregorian


def test_coerce_helpers_accept_various_inputs():
    assert coerce_gregorian("2024/03/20") == (2024, 3, 20)
    assert coerce_jalali("1403/01/01") == (1403, 1, 1)
    assert coerce_gregorian((2022, 11, 5)) == (2022, 11, 5)
    assert coerce_jalali(JalaliDate(1402, 12, 29)) == (1402, 12, 29)


def test_is_jalali_leap_matches_known_years():
    assert is_jalali_leap(1399)
    assert not is_jalali_leap(1400)
    assert is_jalali_leap(1403)

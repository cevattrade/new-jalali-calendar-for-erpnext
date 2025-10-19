"""Gregorian ↔ Jalali conversion helpers used by the ERPNext app."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Tuple, Union

__all__ = [
    "JalaliDate",
    "coerce_gregorian",
    "coerce_jalali",
    "gregorian_to_jalali",
    "jalali_to_gregorian",
    "is_jalali_leap",
]

_GREGORIAN_MONTH_LENGTHS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_JALALI_MONTH_LENGTHS = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]


@dataclass(frozen=True)
class JalaliDate:
    """Immutable representation of a Jalali (Persian) calendar date."""

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:  # pragma: no cover - validation only
        if not (1 <= self.month <= 12):
            raise ValueError("month must be in 1..12 for Jalali calendar")
        max_day = _jalali_month_length(self.year, self.month)
        if not (1 <= self.day <= max_day):
            raise ValueError(f"day must be in 1..{max_day} for month {self.month}")

    def isoformat(self, sep: str = "-") -> str:
        return f"{self.year:04d}{sep}{self.month:02d}{sep}{self.day:02d}"

    def to_gregorian(self) -> date:
        return jalali_to_gregorian((self.year, self.month, self.day))


def _is_gregorian_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _jalali_month_length(year: int, month: int) -> int:
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if is_jalali_leap(year) else 29


def is_jalali_leap(year: int) -> bool:
    start = jalali_to_gregorian((year, 1, 1))
    next_start = jalali_to_gregorian((year + 1, 1, 1))
    return (next_start - start).days == 366


def coerce_gregorian(value: Union[str, date, datetime, Iterable[int]]) -> Tuple[int, int, int]:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.year, value.month, value.day
    if isinstance(value, str):
        tokens = value.replace("/", "-").split("-")
        if len(tokens) != 3:
            raise ValueError(f"Unsupported Gregorian date string: {value!r}")
        return tuple(int(part) for part in tokens)  # type: ignore[return-value]
    try:
        year, month, day = value  # type: ignore[misc]
    except Exception as exc:  # type: ignore
        raise TypeError("Expected a date, string, or iterable of three integers") from exc
    return int(year), int(month), int(day)


def coerce_jalali(value: Union[str, JalaliDate, Iterable[int]]) -> Tuple[int, int, int]:
    if isinstance(value, JalaliDate):
        return value.year, value.month, value.day
    if isinstance(value, str):
        tokens = value.replace("/", "-").split("-")
        if len(tokens) != 3:
            raise ValueError(f"Unsupported Jalali date string: {value!r}")
        return tuple(int(part) for part in tokens)  # type: ignore[return-value]
    try:
        year, month, day = value  # type: ignore[misc]
    except Exception as exc:
        raise TypeError("Expected a JalaliDate, string, or iterable of three integers") from exc
    return int(year), int(month), int(day)


def gregorian_to_jalali(value: Union[str, date, datetime, Iterable[int]]) -> JalaliDate:
    gy, gm, gd = coerce_gregorian(value)
    target = date(gy, gm, gd)

    jy = gy - 621
    start_of_year = jalali_to_gregorian((jy, 1, 1))
    if target < start_of_year:
        jy -= 1
        start_of_year = jalali_to_gregorian((jy, 1, 1))

    days = (target - start_of_year).days
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        days -= 186
        jm = 7 + days // 30
        jd = 1 + days % 30

    return JalaliDate(jy, jm, jd)


def jalali_to_gregorian(value: Union[str, JalaliDate, Iterable[int]]) -> date:
    jy, jm, jd = coerce_jalali(value)
    jy -= 979
    jm -= 1
    jd -= 1

    j_day_no = 365 * jy + jy // 33 * 8 + ((jy % 33) + 3) // 4
    for i in range(jm):
        j_day_no += _JALALI_MONTH_LENGTHS[i]
    j_day_no += jd

    g_day_no = j_day_no + 79

    gy = 1600 + 400 * (g_day_no // 146097)
    g_day_no %= 146097

    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100 * (g_day_no // 36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False

    gy += 4 * (g_day_no // 1461)
    g_day_no %= 1461

    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no // 365
        g_day_no %= 365

    for i, month_len in enumerate(_GREGORIAN_MONTH_LENGTHS):
        month_length = month_len
        if i == 1 and leap:
            month_length += 1
        if g_day_no < month_length:
            gm = i + 1
            gd = g_day_no + 1
            break
        g_day_no -= month_length
    else:  # pragma: no cover - defensive
        raise ValueError("Failed to convert Jalali date to Gregorian")

    return date(gy, gm, gd)

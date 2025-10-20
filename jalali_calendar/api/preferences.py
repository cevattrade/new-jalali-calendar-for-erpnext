"""Calendar preference helpers exposed to both server and client layers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional

try:  # pragma: no cover - frappe is unavailable during tests
    import frappe  # type: ignore
except Exception:  # pragma: no cover - handled via fallback store
    frappe = None  # type: ignore

__all__ = [
    "CalendarSelection",
    "DEFAULT_CALENDAR",
    "VALID_CALENDARS",
    "get_calendar_preference",
    "get_preference_context",
    "get_system_calendar",
    "get_user_calendar",
    "is_jalali_enabled",
    "resolve_calendar",
    "set_calendar_preference",
    "set_system_calendar",
    "set_user_calendar",
]

CalendarSource = Literal["default", "system", "user"]

DEFAULT_CALENDAR = "jalali"
VALID_CALENDARS = {"jalali", "gregorian"}
_PREFERENCE_KEY = "jalali_calendar_mode"


@dataclass(frozen=True)
class CalendarSelection:
    """Resolved calendar and metadata about its origin."""

    value: str
    source: CalendarSource


_FALLBACK_STORE: Dict[str, Dict[Optional[str], Optional[str]]] = {
    "system": {None: None},
    "user": {},
}


def _normalize_calendar(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in VALID_CALENDARS:
            return normalized
    return None


def _require_calendar(value: Optional[str]) -> str:
    normalized = _normalize_calendar(value)
    if not normalized:
        raise ValueError(
            "calendar must be one of: {}".format(", ".join(sorted(VALID_CALENDARS)))
        )
    return normalized


def _read_system_value() -> Optional[str]:
    if frappe:
        stored = frappe.db.get_default(_PREFERENCE_KEY)  # type: ignore[attr-defined]
        return _normalize_calendar(stored)
    return _FALLBACK_STORE["system"].get(None)


def _write_system_value(calendar: str) -> None:
    if frappe:
        frappe.db.set_default(_PREFERENCE_KEY, calendar)  # type: ignore[attr-defined]
        if hasattr(frappe, "clear_cache"):
            frappe.clear_cache()
        return
    _FALLBACK_STORE["system"][None] = calendar


def _read_user_value(user: Optional[str]) -> Optional[str]:
    if frappe:
        if not user:
            user = getattr(getattr(frappe, "session", None), "user", None)  # type: ignore[attr-defined]
        if not user or user == "Guest":
            return None
        stored = frappe.db.get_default(_PREFERENCE_KEY, user=user)  # type: ignore[attr-defined]
        return _normalize_calendar(stored)
    if user is None:
        return None
    return _FALLBACK_STORE["user"].get(user)


def _write_user_value(calendar: str, user: Optional[str]) -> None:
    if frappe:
        if not user:
            user = getattr(getattr(frappe, "session", None), "user", None)  # type: ignore[attr-defined]
        if not user or user == "Guest":  # pragma: no cover - depends on Frappe session
            raise ValueError("Cannot store calendar preference for anonymous sessions")
        frappe.db.set_default(_PREFERENCE_KEY, calendar, user=user)  # type: ignore[attr-defined]
        if hasattr(frappe, "defaults") and hasattr(frappe.defaults, "clear_cache"):
            frappe.defaults.clear_cache(user=user)  # type: ignore[attr-defined]
        return
    if user is None:
        raise RuntimeError("user must be provided when frappe is unavailable")
    _FALLBACK_STORE["user"][user] = calendar


def get_system_calendar(*, raw: bool = False) -> str:
    """Return the system-wide calendar selection."""

    stored = _read_system_value()
    if raw:
        return stored or ""
    return stored or DEFAULT_CALENDAR


def set_system_calendar(calendar: str) -> CalendarSelection:
    """Persist the system-wide calendar preference."""

    selected = _require_calendar(calendar)
    _write_system_value(selected)
    return resolve_calendar()


def get_user_calendar(user: Optional[str] = None) -> Optional[str]:
    """Return the calendar preference stored for a user, if any."""

    return _read_user_value(user)


def set_user_calendar(calendar: str, user: Optional[str] = None) -> CalendarSelection:
    """Persist the calendar preference for a specific user."""

    selected = _require_calendar(calendar)
    _write_user_value(selected, user)
    return resolve_calendar(user)


def resolve_calendar(user: Optional[str] = None) -> CalendarSelection:
    """Resolve the active calendar for a user taking overrides into account."""

    user_value = get_user_calendar(user)
    if user_value:
        return CalendarSelection(user_value, "user")

    system_raw = get_system_calendar(raw=True)
    if system_raw:
        return CalendarSelection(system_raw, "system")

    return CalendarSelection(DEFAULT_CALENDAR, "default")


def is_jalali_enabled(user: Optional[str] = None) -> bool:
    """Return ``True`` if Jalali calendar should be active for the user."""

    return resolve_calendar(user).value == "jalali"


def get_preference_context(user: Optional[str] = None) -> Dict[str, object]:
    """Return a serialisable representation of the resolved preference."""

    resolved = resolve_calendar(user)
    context: Dict[str, object] = {
        "active_calendar": resolved.value,
        "source": resolved.source,
        "is_jalali_enabled": resolved.value == "jalali",
    }

    system_raw = get_system_calendar(raw=True)
    if system_raw:
        context["system_calendar"] = system_raw

    user_raw = get_user_calendar(user)
    if user_raw:
        context["user_calendar"] = user_raw

    return context


def set_calendar_preference(scope: str, calendar: str, user: Optional[str] = None) -> Dict[str, object]:
    """Update a calendar preference and return the resulting context."""

    normalized_scope = (scope or "user").strip().lower()
    if normalized_scope == "system":
        set_system_calendar(calendar)
        return get_preference_context()
    if normalized_scope == "user":
        set_user_calendar(calendar, user)
        return get_preference_context(user)
    raise ValueError("scope must be either 'system' or 'user'")


def get_calendar_preference(user: Optional[str] = None) -> Dict[str, object]:
    """Return the currently resolved preference context."""

    return get_preference_context(user)


def _maybe_whitelist(func):  # pragma: no cover - exercised in Frappe environments
    if frappe and hasattr(frappe, "whitelist"):
        return frappe.whitelist()(func)  # type: ignore[attr-defined]
    return func


get_calendar_preference = _maybe_whitelist(get_calendar_preference)
set_calendar_preference = _maybe_whitelist(set_calendar_preference)

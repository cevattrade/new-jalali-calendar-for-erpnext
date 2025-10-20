"""Hook implementations that integrate the Jalali calendar with Frappe."""
from __future__ import annotations

from .api import preferences


def boot_session(bootinfo):  # pragma: no cover - executed in Frappe runtime
    """Inject the resolved calendar preference into the boot payload."""

    context = preferences.get_preference_context()
    if isinstance(bootinfo, dict):
        bootinfo.setdefault("jalali_calendar", context)
    else:  # ``bootinfo`` is typically a ``frappe._dict``
        setattr(bootinfo, "jalali_calendar", context)

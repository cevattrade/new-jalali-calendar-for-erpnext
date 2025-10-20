import importlib

import pytest


def reload_preferences():
    module = importlib.import_module("jalali_calendar.api.preferences")
    return importlib.reload(module)


def test_default_preference_is_jalali():
    preferences = reload_preferences()
    resolved = preferences.resolve_calendar()
    assert resolved.value == "jalali"
    assert resolved.source == "default"
    assert preferences.is_jalali_enabled()


def test_system_preference_overrides_default():
    preferences = reload_preferences()
    preferences.set_system_calendar("gregorian")
    resolved = preferences.resolve_calendar()
    assert resolved.value == "gregorian"
    assert resolved.source == "system"
    context = preferences.get_preference_context()
    assert context["active_calendar"] == "gregorian"
    assert context["source"] == "system"


def test_user_preference_has_priority_over_system():
    preferences = reload_preferences()
    preferences.set_system_calendar("gregorian")
    preferences.set_user_calendar("jalali", user="demo@example.com")
    resolved = preferences.resolve_calendar(user="demo@example.com")
    assert resolved.value == "jalali"
    assert resolved.source == "user"
    context = preferences.get_preference_context(user="demo@example.com")
    assert context["active_calendar"] == "jalali"
    assert context["user_calendar"] == "jalali"
    assert context["source"] == "user"


def test_setting_invalid_calendar_raises_value_error():
    preferences = reload_preferences()
    with pytest.raises(ValueError):
        preferences.set_system_calendar("lunar")

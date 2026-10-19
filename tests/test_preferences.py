"""WindowPreferences: the saved display choice and its tolerant parsing."""

from pygame_display_kit import WindowPreferences


def test_default_is_fullscreen_with_no_window_size():
    prefs = WindowPreferences()
    assert prefs.fullscreen is True
    assert (prefs.window_width, prefs.window_height) == (0, 0)


def test_round_trip_through_a_dict():
    prefs = WindowPreferences(fullscreen=False, window_width=1600, window_height=900)
    assert WindowPreferences.from_dict(prefs.to_dict()) == prefs


def test_garbage_yields_the_default():
    assert WindowPreferences.from_dict(None) == WindowPreferences()
    assert WindowPreferences.from_dict("fullscreen") == WindowPreferences()
    assert WindowPreferences.from_dict([1, 2]) == WindowPreferences()


def test_bad_fields_fall_back_one_by_one():
    parsed = WindowPreferences.from_dict({"fullscreen": "yes", "window_width": -5, "window_height": True})
    assert parsed == WindowPreferences()
    parsed = WindowPreferences.from_dict({"fullscreen": False, "window_width": 1280})
    assert parsed == WindowPreferences(fullscreen=False, window_width=1280, window_height=0)


def test_explicit_default_is_used_for_missing_fields():
    fallback = WindowPreferences(fullscreen=False, window_width=1280, window_height=720)
    assert WindowPreferences.from_dict({}, default=fallback) == fallback
    assert WindowPreferences.from_dict({"fullscreen": True}, default=fallback) == WindowPreferences(
        True, 1280, 720
    )

"""Unit tests for ``select_best_resolution``.

Ports the policy regression tests from Broken Moon Redux that pin the
"prefer native over BASE" choice. The previous policy (BASE preference)
left users on 2560×1440 / 4K monitors with a small windowed game by
default; the new policy returns native when available.
"""

from unittest.mock import patch

from pygame_display_kit import ResolutionConfig, select_best_resolution
from pygame_display_kit.strategies.grow import GrowStrategy


def _make_config(native_width: int, native_height: int) -> ResolutionConfig:
    """Build a config with a specific native resolution (no real detection)."""
    config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
    config.native_width = native_width
    config.native_height = native_height
    return config


class TestPrefersNative:
    """Native wins over BASE when both fit."""

    def test_2560x1440_picks_native(self):
        """Reproduces the user-reported issue: BASE preference left
        users on 2560x1440 with a small 1600x1200 box. New policy
        returns native.
        """
        config = _make_config(2560, 1440)
        result = select_best_resolution(config)
        assert result == (2560, 1440)

    def test_4k_picks_native(self):
        config = _make_config(3840, 2160)
        result = select_best_resolution(config)
        assert result == (3840, 2160)

    def test_1920x1080_picks_native(self):
        """Most common modern monitor."""
        config = _make_config(1920, 1080)
        result = select_best_resolution(config)
        assert result == (1920, 1080)

    def test_legacy_4_3_picks_native(self):
        """1600x1200 monitor: native and BASE happen to be identical."""
        config = _make_config(1600, 1200)
        result = select_best_resolution(config)
        assert result == (1600, 1200)


class TestFallback:
    """Tiny / non-standard displays."""

    def test_small_display_picks_native_via_explicit_append(self):
        """1024x768 monitor: get_available_resolutions appends native
        explicitly, so selection still works.
        """
        config = _make_config(1024, 768)
        result = select_best_resolution(config)
        assert result == (1024, 768)

    def test_no_preset_fits_falls_back_to_80_percent(self):
        """Defensive: if available is empty, fall back to 80% of native."""
        config = _make_config(100, 100)
        with patch.object(config, "get_available_resolutions", return_value=[]):
            result = select_best_resolution(config)
        assert result == (80, 80)


class TestNoBasePreference:
    """The old BASE-preference policy must not be reintroduced."""

    def test_2560x1440_does_not_pick_base(self):
        """Direct anti-regression: future refactor that returns BASE
        when it fits will fail this test.
        """
        config = _make_config(2560, 1440)
        result = select_best_resolution(config)
        assert result != (config.base_width, config.base_height), (
            "select_best_resolution must NOT prefer BASE over native"
        )

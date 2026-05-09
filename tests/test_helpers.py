"""Unit tests for per-element scale helpers.

These helpers convert BASE-coordinate values to display coordinates
using the active config's strategy (offset + scale). Used by DK_Arena
for UI widgets, sprite sizes, font sizes.
"""

import pytest

from pygame_display_kit import (
    GrowStrategy,
    LetterboxStrategy,
    ResolutionConfig,
    get_font_size,
    scale_position,
    scale_size,
    scale_value,
)


def _letterbox_config_at(display_width: int, display_height: int) -> ResolutionConfig:
    config = ResolutionConfig(base=(1920, 1080), strategy=LetterboxStrategy, auto_detect=False)
    config.set_resolution(display_width, display_height)
    LetterboxStrategy.update_viewport(config, display_width, display_height)
    return config


def _grow_config_at(display_width: int, display_height: int) -> ResolutionConfig:
    config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
    config.set_resolution(display_width, display_height)
    GrowStrategy.update_viewport(config, display_width, display_height)
    return config


class TestScaleValue:
    """``scale_value`` multiplies by ``config.scale``."""

    def test_scale_value_at_native(self):
        """At native resolution, scale = 1.0, so values pass through."""
        config = _letterbox_config_at(1920, 1080)
        assert scale_value(config, 100) == 100

    def test_scale_value_at_half(self):
        config = _letterbox_config_at(960, 540)  # half scale
        assert scale_value(config, 100) == pytest.approx(50.0)

    def test_scale_value_at_double(self):
        config = _letterbox_config_at(3840, 2160)  # 2x scale
        assert scale_value(config, 100) == pytest.approx(200.0)


class TestScalePosition:
    """``scale_position`` includes the strategy's letterbox offset."""

    def test_letterbox_position_includes_offset(self):
        """21:9 ultrawide pillarbox: offset_x = 320, offset_y = 0."""
        config = _letterbox_config_at(2560, 1080)
        x, y = scale_position(config, 100, 100)
        # scale = 1.0; offset = (320, 0); final = (100*1.0 + 320, 100*1.0 + 0)
        assert x == pytest.approx(420.0)
        assert y == pytest.approx(100.0)

    def test_grow_position_no_offset(self):
        """GrowStrategy always returns (0, 0) offset."""
        config = _grow_config_at(1920, 1080)
        x, y = scale_position(config, 100, 100)
        # offset = (0, 0); scale = 1.0
        assert x == pytest.approx(100.0)
        assert y == pytest.approx(100.0)


class TestScaleSize:
    """``scale_size`` multiplies dimensions by ``config.scale`` (no offset)."""

    def test_scale_size_no_offset(self):
        """Sizes don't get the centering offset — they're widths/heights."""
        config = _letterbox_config_at(2560, 1080)
        w, h = scale_size(config, 200, 100)
        # scale = 1.0
        assert w == pytest.approx(200.0)
        assert h == pytest.approx(100.0)

    def test_scale_size_at_half(self):
        config = _letterbox_config_at(960, 540)
        w, h = scale_size(config, 200, 100)
        assert w == pytest.approx(100.0)
        assert h == pytest.approx(50.0)


class TestGetFontSize:
    """``get_font_size`` scales + enforces readability minimum."""

    def test_at_native_returns_base_size(self):
        config = _letterbox_config_at(1920, 1080)
        assert get_font_size(config, 24) == 24

    def test_scaled_down_respects_minimum(self):
        """At 0.4x scale, base 16 → 6, but minimum is 12."""
        config = _letterbox_config_at(768, 432)  # ~0.4x
        assert get_font_size(config, 16) == 12

    def test_custom_minimum(self):
        config = _letterbox_config_at(192, 108)  # 0.1x scale
        assert get_font_size(config, 24, minimum=8) == 8

    def test_scaled_up_no_clamp(self):
        config = _letterbox_config_at(3840, 2160)  # 2x
        assert get_font_size(config, 24) == 48

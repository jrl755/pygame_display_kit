"""Unit tests for ``ResolutionConfig`` resolution clamping.

The ``min_size`` / ``max_size`` constructor params clamp inputs to
:meth:`ResolutionConfig.set_resolution`. Float inputs raise
``ValueError`` (silent ``int()`` truncation hides bugs).

DK_Arena uses ``min_size=(1280, 720)``, ``max_size=(7680, 4320)`` —
these tests pin those bounds work correctly post-extraction.
"""

import pytest

from pygame_display_kit import GrowStrategy, ResolutionConfig


def _make_config(min_size=None, max_size=None) -> ResolutionConfig:
    return ResolutionConfig(
        base=(1920, 1080),
        strategy=GrowStrategy,
        auto_detect=False,
        min_size=min_size,
        max_size=max_size,
    )


class TestNoBoundsByDefault:
    """Without min_size / max_size, set_resolution accepts any int."""

    def test_no_bounds_accepts_tiny(self):
        config = _make_config()
        config.set_resolution(100, 100)
        assert config.current_width == 100
        assert config.current_height == 100

    def test_no_bounds_accepts_huge(self):
        config = _make_config()
        config.set_resolution(99999, 99999)
        assert config.current_width == 99999


class TestMinSizeClamping:
    """``min_size`` floors set_resolution inputs."""

    def test_below_min_clamped_to_min(self):
        config = _make_config(min_size=(1280, 720))
        config.set_resolution(640, 480)
        assert config.current_width == 1280
        assert config.current_height == 720

    def test_at_min_passes_through(self):
        config = _make_config(min_size=(1280, 720))
        config.set_resolution(1280, 720)
        assert config.current_width == 1280
        assert config.current_height == 720

    def test_one_axis_below_clamps_only_that_axis(self):
        """Width above min, height below → only height gets clamped."""
        config = _make_config(min_size=(1280, 720))
        config.set_resolution(1920, 480)
        assert config.current_width == 1920
        assert config.current_height == 720


class TestMaxSizeClamping:
    """``max_size`` ceils set_resolution inputs."""

    def test_above_max_clamped_to_max(self):
        config = _make_config(max_size=(7680, 4320))
        config.set_resolution(15360, 8640)
        assert config.current_width == 7680
        assert config.current_height == 4320

    def test_at_max_passes_through(self):
        config = _make_config(max_size=(7680, 4320))
        config.set_resolution(7680, 4320)
        assert config.current_width == 7680


class TestBothBounds:
    """min_size + max_size both apply (DK_Arena's actual config)."""

    def test_dk_arena_bounds_clamp_correctly(self):
        config = _make_config(min_size=(1280, 720), max_size=(7680, 4320))
        config.set_resolution(640, 480)
        assert config.current_width == 1280  # clamped up
        config.set_resolution(15360, 8640)
        assert config.current_width == 7680  # clamped down
        config.set_resolution(1920, 1080)
        assert config.current_width == 1920  # in range, unchanged


class TestFloatRejection:
    """set_resolution rejects float inputs explicitly."""

    def test_float_width_raises(self):
        config = _make_config()
        with pytest.raises(ValueError, match="must be integers"):
            config.set_resolution(1920.5, 1080)

    def test_float_height_raises(self):
        config = _make_config()
        with pytest.raises(ValueError, match="must be integers"):
            config.set_resolution(1920, 1080.0)

    def test_both_float_raises(self):
        config = _make_config()
        with pytest.raises(ValueError):
            config.set_resolution(1920.0, 1080.0)

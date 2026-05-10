"""Unit tests for ResolutionConfig."""

from unittest.mock import patch

import pygame
import pytest

from pygame_display_kit import ResolutionConfig
from pygame_display_kit.strategies.grow import GrowStrategy


class TestResolutionConfigInit:
    """Construction defaults and attribute population."""

    def test_base_dimensions_stored(self):
        config = ResolutionConfig(base=(1920, 1080), strategy=GrowStrategy, auto_detect=False)
        assert config.base_width == 1920
        assert config.base_height == 1080

    def test_base_aspect_computed(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.base_aspect == pytest.approx(1.333, abs=0.001)

    def test_current_defaults_to_base(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.current_width == 1600
        assert config.current_height == 1200

    def test_viewport_defaults_to_base(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.viewport_width == 1600
        assert config.viewport_height == 1200

    def test_initial_scale_is_one(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.scale == 1.0
        assert config.scale_x == 1.0
        assert config.scale_y == 1.0

    def test_fullscreen_defaults_false(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.fullscreen is False

    def test_strategy_stored(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.strategy is GrowStrategy

    def test_auto_detect_false_leaves_native_zero(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        assert config.native_width == 0
        assert config.native_height == 0

    def test_auto_detect_true_populates_native(self):
        with patch("pygame_display_kit.config.detect_native", return_value=(2560, 1440)):
            config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=True)
        assert config.native_width == 2560
        assert config.native_height == 1440


class TestSetResolution:
    """``set_resolution`` updates state + recomputes scale."""

    def test_set_resolution_updates_current(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        config.set_resolution(1920, 1080)
        assert config.current_width == 1920
        assert config.current_height == 1080

    def test_set_resolution_recomputes_scale(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        config.set_resolution(800, 600)
        # 800/1600 = 0.5, 600/1200 = 0.5. Uniform.
        assert config.scale_x == pytest.approx(0.5)
        assert config.scale_y == pytest.approx(0.5)
        assert config.scale == pytest.approx(0.5)

    def test_set_resolution_uniform_uses_min(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        config.set_resolution(1920, 1080)
        # 1920/1600 = 1.2, 1080/1200 = 0.9. Uniform = min = 0.9.
        assert config.scale == pytest.approx(0.9)

    def test_set_resolution_fullscreen_default_unchanged(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False, fullscreen=False)
        config.set_resolution(1920, 1080)  # no fullscreen kwarg
        assert config.fullscreen is False

    def test_set_resolution_fullscreen_kwarg_applies(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False, fullscreen=False)
        config.set_resolution(1920, 1080, fullscreen=True)
        assert config.fullscreen is True


class TestDisplayFlags:
    """``get_display_flags`` returns pygame flags reflecting state."""

    def test_windowed_returns_resizable(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False, fullscreen=False)
        assert config.get_display_flags() & pygame.RESIZABLE

    def test_fullscreen_returns_fullscreen_flag(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False, fullscreen=True)
        assert config.get_display_flags() & pygame.FULLSCREEN


class TestAvailableResolutions:
    """``get_available_resolutions`` filters presets by native size."""

    def test_native_always_included(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        config.native_width = 2560
        config.native_height = 1440
        available = config.get_available_resolutions()
        assert (2560, 1440) in available

    def test_filters_to_fitting_resolutions(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        config.native_width = 1920
        config.native_height = 1080
        available = config.get_available_resolutions()
        # 1600x1200 doesn't fit (1200 > 1080); should be excluded.
        assert (1600, 1200) not in available
        # 1920x1080 fits and is native.
        assert (1920, 1080) in available

    def test_sorted_by_pixel_count(self):
        config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
        config.native_width = 3840
        config.native_height = 2160
        available = config.get_available_resolutions()
        pixel_counts = [w * h for w, h in available]
        assert pixel_counts == sorted(pixel_counts)


class TestStrategyAwareDisplayFlags:
    """get_display_flags() returns SCALED iff active strategy is ScaledStrategy.

    The strategy-awareness is what lets FullscreenManager.toggle()
    preserve Skodrak's SCALED flag across windowed ↔ fullscreen toggles
    without per-strategy branching at the call site.
    """

    def test_get_display_flags_includes_scaled_under_scaled_strategy(self):
        from pygame_display_kit.strategies.scaled import ScaledStrategy

        config = ResolutionConfig(
            base=(1920, 1080), strategy=ScaledStrategy, auto_detect=False
        )
        assert config.get_display_flags() & pygame.SCALED

    def test_get_display_flags_omits_scaled_under_grow_strategy(self):
        config = ResolutionConfig(
            base=(1600, 1200), strategy=GrowStrategy, auto_detect=False
        )
        assert config.get_display_flags() & pygame.SCALED == 0

    def test_get_display_flags_omits_scaled_under_letterbox_strategy(self):
        from pygame_display_kit.strategies.letterbox import LetterboxStrategy

        config = ResolutionConfig(
            base=(1920, 1080), strategy=LetterboxStrategy, auto_detect=False
        )
        assert config.get_display_flags() & pygame.SCALED == 0

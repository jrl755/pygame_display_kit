"""Unit tests for GrowStrategy — the v0.1 viewport implementation.

Ports the widescreen regression tests from Broken Moon Redux that
pinned the viewport-grow math: render-surface aspect must match display
aspect (no stretching) AND fill the entire screen (no letterboxing).
"""

import pygame

from pygame_display_kit import ResolutionConfig
from pygame_display_kit.strategies.grow import GrowStrategy


def _make_config_at(display_width: int, display_height: int) -> ResolutionConfig:
    """Build a config and drive its strategy update for a display size."""
    config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
    config.set_resolution(display_width, display_height)
    GrowStrategy.update_viewport(config, display_width, display_height)
    return config


class TestWidescreenGrowsHorizontally:
    """16:9 displays — viewport widens; height stays at BASE."""

    def test_1920x1080_grows_viewport_width(self):
        config = _make_config_at(1920, 1080)
        assert config.viewport_width > config.base_width
        assert config.viewport_height == config.base_height

    def test_1280x720_still_grows_viewport(self):
        """Smaller widescreen also grows — what matters is aspect, not size."""
        config = _make_config_at(1280, 720)
        assert config.viewport_width > config.base_width
        assert config.viewport_height == config.base_height

    def test_widescreen_aspect_matches_display(self):
        """Render-surface aspect must equal display aspect (no stretch under uniform scale)."""
        config = _make_config_at(2560, 1440)
        rs_aspect = config.viewport_width / config.viewport_height
        screen_aspect = 2560 / 1440
        assert abs(rs_aspect - screen_aspect) < 0.01


class TestBaseAspectIsNoOp:
    """4:3 display matching BASE aspect: viewport == base."""

    def test_1600x1200_keeps_base_dimensions(self):
        config = _make_config_at(1600, 1200)
        assert config.viewport_width == config.base_width
        assert config.viewport_height == config.base_height


class TestPortraitGrowsVertically:
    """Taller-than-base displays grow VIEWPORT_HEIGHT instead of WIDTH."""

    def test_portrait_grows_height(self):
        """1080×1920 (rotated): width stays at BASE, height grows."""
        config = _make_config_at(1080, 1920)
        assert config.viewport_width == config.base_width
        assert config.viewport_height > config.base_height


class TestNoLetterboxing:
    """Strategy fills the screen — no offset, scale = display dims."""

    def test_offset_is_zero(self):
        config = _make_config_at(1920, 1080)
        offset = GrowStrategy.compute_viewport_offset(config, (1920, 1080))
        assert offset == (0, 0)

    def test_scale_equals_display_size(self):
        config = _make_config_at(2560, 1440)
        scale = GrowStrategy.compute_viewport_scale(config, (2560, 1440))
        assert scale == (2560, 1440)


class TestCreateRenderSurface:
    """Render surface allocated at viewport dimensions."""

    def test_surface_sized_to_viewport(self):
        config = _make_config_at(1920, 1080)
        surface = GrowStrategy.create_render_surface(config)
        assert surface.get_size() == (config.viewport_width, config.viewport_height)

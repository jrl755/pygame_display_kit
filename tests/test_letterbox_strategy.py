"""Unit tests for LetterboxStrategy — DK_Arena's viewport math.

Pins the uniform aspect-preserving + centered-offset behavior that
DK_Arena's existing ``ResolutionConfig._calculate_scaling`` produces.
The strategy implementation is a verbatim port of that math; these
tests catch any regression in the port.
"""

import pygame

from pygame_display_kit import LetterboxStrategy, ResolutionConfig


def _make_config_at(display_width: int, display_height: int, base=(1920, 1080)) -> ResolutionConfig:
    """Build a config and run the LetterboxStrategy update for a display size."""
    config = ResolutionConfig(base=base, strategy=LetterboxStrategy, auto_detect=False)
    config.set_resolution(display_width, display_height)
    LetterboxStrategy.update_viewport(config, display_width, display_height)
    return config


class TestLetterboxKeepsViewportAtBase:
    """Letterbox renders at BASE; viewport never grows."""

    def test_widescreen_keeps_viewport_at_base(self):
        config = _make_config_at(2560, 1080)  # 21:9 ultrawide
        assert config.viewport_width == config.base_width
        assert config.viewport_height == config.base_height

    def test_4_3_display_keeps_viewport_at_base(self):
        config = _make_config_at(1600, 1200, base=(1920, 1080))  # taller than 16:9
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080

    def test_native_aspect_keeps_viewport_at_base(self):
        config = _make_config_at(1920, 1080)
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080


class TestUniformScale:
    """Letterbox uses ``min(scale_x, scale_y)`` for aspect preservation."""

    def test_scale_is_min_of_axis_scales(self):
        config = _make_config_at(2560, 1080, base=(1920, 1080))
        # scale_x = 2560/1920 = 1.333, scale_y = 1080/1080 = 1.000
        # Uniform = min = 1.000
        assert abs(config.scale - 1.000) < 0.001

    def test_widescreen_height_limited(self):
        """On 21:9 with 16:9 base, height is the limiting axis."""
        config = _make_config_at(2560, 1080, base=(1920, 1080))
        assert config.scale == config.scale_y

    def test_taller_display_width_limited(self):
        """On 4:3 with 16:9 base, width is the limiting axis."""
        config = _make_config_at(1600, 1200, base=(1920, 1080))
        # scale_x = 1600/1920 = 0.833, scale_y = 1200/1080 = 1.111
        # Uniform = 0.833 (width-limited)
        assert config.scale == config.scale_x


class TestCenteredOffset:
    """Letterbox centers the rendered area within the display."""

    def test_widescreen_pillarbox_centered_horizontally(self):
        """21:9 display with 16:9 base: bars on left + right."""
        config = _make_config_at(2560, 1080, base=(1920, 1080))
        offset = LetterboxStrategy.compute_viewport_offset(config, (2560, 1080))
        # render_width = 1920 * 1.000 = 1920
        # offset_x = (2560 - 1920) // 2 = 320
        assert offset == (320, 0)

    def test_4_3_letterbox_centered_vertically(self):
        """4:3 display with 16:9 base: bars on top + bottom."""
        config = _make_config_at(1600, 1200, base=(1920, 1080))
        offset = LetterboxStrategy.compute_viewport_offset(config, (1600, 1200))
        # scale = 0.833, render_height = 1080 * 0.833 = 900
        # offset_y = (1200 - 900) // 2 = 150
        assert offset == (0, 150)

    def test_matching_aspect_no_offset(self):
        """Display aspect == BASE aspect: no letterbox needed."""
        config = _make_config_at(1920, 1080, base=(1920, 1080))
        offset = LetterboxStrategy.compute_viewport_offset(config, (1920, 1080))
        assert offset == (0, 0)


class TestRenderAreaScale:
    """``compute_viewport_scale`` returns the letterboxed render dims."""

    def test_render_area_is_base_times_scale(self):
        config = _make_config_at(2560, 1080, base=(1920, 1080))
        scale = LetterboxStrategy.compute_viewport_scale(config, (2560, 1080))
        # 1920 * 1.000 = 1920, 1080 * 1.000 = 1080
        assert scale == (1920, 1080)

    def test_4_3_render_area_smaller_than_display(self):
        config = _make_config_at(1600, 1200, base=(1920, 1080))
        scale = LetterboxStrategy.compute_viewport_scale(config, (1600, 1200))
        # scale = 0.833, render = (1920*0.833, 1080*0.833) = (1600, 900)
        assert scale == (1600, 900)


class TestRenderSurfaceAtBaseDims:
    """Render surface is allocated at BASE — DK design assumption."""

    def test_surface_size_equals_base(self):
        config = _make_config_at(2560, 1080, base=(1920, 1080))
        surface = LetterboxStrategy.create_render_surface(config)
        assert surface.get_size() == (1920, 1080)

    def test_surface_unaffected_by_display_size(self):
        """Surface dims don't change when display changes — that's
        exactly the property letterbox preserves vs. grow."""
        s1 = LetterboxStrategy.create_render_surface(
            _make_config_at(1920, 1080, base=(1920, 1080))
        )
        s2 = LetterboxStrategy.create_render_surface(
            _make_config_at(2560, 1080, base=(1920, 1080))
        )
        assert s1.get_size() == s2.get_size()

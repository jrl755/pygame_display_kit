"""Unit tests for ScaledStrategy — Skodrak's SDL-handled scaling.

Pins the contract that ``ScaledStrategy`` keeps the viewport at BASE
dimensions, returns 1.0 for all scale factors (since SDL handles the
actual scaling at the OS / GPU level), and provides ``add_scaled_flag``
for composing the SCALED flag with existing display flags.
"""

import pygame

from pygame_display_kit import ResolutionConfig, ScaledStrategy, add_scaled_flag


def _make_config_at(display_width: int, display_height: int, base=(1920, 1080)) -> ResolutionConfig:
    """Build a config and run the ScaledStrategy update for a display size."""
    config = ResolutionConfig(base=base, strategy=ScaledStrategy, auto_detect=False)
    config.set_resolution(display_width, display_height)
    ScaledStrategy.update_viewport(config, display_width, display_height)
    return config


class TestViewportStaysAtBase:
    """ScaledStrategy keeps the logical viewport at BASE — SDL scales physically."""

    def test_native_aspect_viewport_is_base(self):
        config = _make_config_at(1920, 1080)
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080

    def test_widescreen_viewport_stays_at_base(self):
        config = _make_config_at(2560, 1080)
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080

    def test_4k_viewport_stays_at_base(self):
        config = _make_config_at(3840, 2160)
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080

    def test_smaller_display_viewport_stays_at_base(self):
        """Even on undersized display, SDL handles the down-scale."""
        config = _make_config_at(1280, 720)
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080


class TestScaleFactorsAreUnity:
    """Game code draws in BASE coords; SDL applies the actual scale.

    From the consumer's perspective, scale_x / scale_y / scale are all
    1.0 because there's no per-element scaling to apply — SDL does it
    all at the OS level.
    """

    def test_scale_x_is_unity(self):
        config = _make_config_at(2560, 1080)
        assert config.scale_x == 1.0

    def test_scale_y_is_unity(self):
        config = _make_config_at(2560, 1080)
        assert config.scale_y == 1.0

    def test_uniform_scale_is_unity(self):
        config = _make_config_at(2560, 1080)
        assert config.scale == 1.0

    def test_scale_is_unity_at_4k(self):
        """4K output is scaled 2× by SDL — but from the game's POV, scale = 1.0."""
        config = _make_config_at(3840, 2160)
        assert config.scale_x == 1.0
        assert config.scale_y == 1.0
        assert config.scale == 1.0


class TestZeroOffset:
    """ScaledStrategy returns (0, 0) — SDL handles letterbox positioning."""

    def test_native_aspect_no_offset(self):
        config = _make_config_at(1920, 1080)
        assert ScaledStrategy.compute_viewport_offset(config, (1920, 1080)) == (0, 0)

    def test_widescreen_no_offset(self):
        """SDL adds black bars internally; game code doesn't see an offset."""
        config = _make_config_at(2560, 1080)
        assert ScaledStrategy.compute_viewport_offset(config, (2560, 1080)) == (0, 0)

    def test_4_3_display_no_offset(self):
        config = _make_config_at(1600, 1200)
        assert ScaledStrategy.compute_viewport_offset(config, (1600, 1200)) == (0, 0)


class TestComputeViewportScale:
    """``compute_viewport_scale`` returns ``screen_size`` for ABC compliance.

    Consumers using SCALED don't actually call this — they let
    ``pygame.display.flip()`` do the work — but the ABC requires it.
    """

    def test_returns_screen_size_at_native(self):
        config = _make_config_at(1920, 1080)
        assert ScaledStrategy.compute_viewport_scale(config, (1920, 1080)) == (1920, 1080)

    def test_returns_screen_size_at_4k(self):
        config = _make_config_at(3840, 2160)
        assert ScaledStrategy.compute_viewport_scale(config, (3840, 2160)) == (3840, 2160)


class TestRenderSurfaceAtBaseDims:
    """Render surface is allocated at BASE for ABC compliance."""

    def test_surface_size_equals_base(self):
        config = _make_config_at(2560, 1080)
        surface = ScaledStrategy.create_render_surface(config)
        assert surface.get_size() == (1920, 1080)

    def test_surface_unaffected_by_display_size(self):
        """SDL handles scaling regardless of display — surface dims are constant."""
        s1 = ScaledStrategy.create_render_surface(_make_config_at(1920, 1080))
        s2 = ScaledStrategy.create_render_surface(_make_config_at(3840, 2160))
        assert s1.get_size() == s2.get_size()


class TestAddScaledFlag:
    """``add_scaled_flag`` composes ``pygame.SCALED`` with existing flags."""

    def test_adds_scaled_to_zero(self):
        assert add_scaled_flag(0) == pygame.SCALED

    def test_preserves_resizable(self):
        flags = add_scaled_flag(pygame.RESIZABLE)
        assert flags & pygame.SCALED
        assert flags & pygame.RESIZABLE

    def test_preserves_fullscreen(self):
        flags = add_scaled_flag(pygame.FULLSCREEN)
        assert flags & pygame.SCALED
        assert flags & pygame.FULLSCREEN

    def test_idempotent_on_already_scaled(self):
        """Adding SCALED twice is a no-op (bitwise OR is idempotent)."""
        once = add_scaled_flag(0)
        twice = add_scaled_flag(once)
        assert once == twice

    def test_combines_multiple_flags(self):
        flags = add_scaled_flag(pygame.RESIZABLE | pygame.DOUBLEBUF)
        assert flags & pygame.SCALED
        assert flags & pygame.RESIZABLE
        assert flags & pygame.DOUBLEBUF

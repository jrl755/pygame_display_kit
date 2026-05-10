"""Unit tests for FullscreenManager.

Ports the regression tests from Broken Moon Redux that pinned the
"fullscreen doesn't center" bug fix: ``set_mode((0, 0), FULLSCREEN)``
returns a desktop-resolution surface, but the config's ``current_*``
must be synced to the actual surface size before any viewport recompute.
"""

from unittest.mock import patch

import pygame

from pygame_display_kit import FullscreenManager, ResolutionConfig
from pygame_display_kit.strategies.grow import GrowStrategy


def _make_config(width: int = 1920, height: int = 1080) -> ResolutionConfig:
    config = ResolutionConfig(base=(1600, 1200), strategy=GrowStrategy, auto_detect=False)
    config.set_resolution(width, height)
    return config


class TestToggleToFullscreenSyncsCurrent:
    """Going to fullscreen syncs CURRENT to the actual surface size."""

    def test_toggle_to_fullscreen_updates_current_to_actual_dims(self):
        """Reproduces the centering bug pre-fix: stale CURRENT_*
        misaligned the viewport. Post-fix, CURRENT must match
        ``screen.get_size()`` after toggle.
        """
        config = _make_config(1920, 1080)  # windowed at 1920×1080
        mgr = FullscreenManager(config)
        # Simulate desktop being 2560×1440 (larger than windowed).
        with patch("pygame.display.set_mode", return_value=pygame.Surface((2560, 1440))):
            mgr.toggle()

        assert config.current_width == 2560
        assert config.current_height == 1440

    def test_fullscreen_flag_set_after_toggle(self):
        config = _make_config(1920, 1080)
        mgr = FullscreenManager(config)
        with patch("pygame.display.set_mode", return_value=pygame.Surface((2560, 1440))):
            mgr.toggle()
        assert config.fullscreen is True


class TestToggleBackPreservesWindowedSize:
    """Toggle-back must restore the windowed size, not the desktop size."""

    def test_toggle_back_restores_windowed_dims(self):
        """User picks 1920×1080 windowed → goes fullscreen (desktop is
        2560×1440) → toggles back. Window must be 1920×1080 again, not
        2560×1440 (the desktop dims captured in fullscreen).
        """
        config = _make_config(1920, 1080)
        mgr = FullscreenManager(config)

        with patch("pygame.display.set_mode") as mock_set_mode:
            # Going to fullscreen: pygame returns desktop-size surface.
            mock_set_mode.return_value = pygame.Surface((2560, 1440))
            mgr.toggle()
            assert config.fullscreen is True

            # Going back: pygame returns the windowed size we asked for.
            mock_set_mode.return_value = pygame.Surface((1920, 1080))
            mgr.toggle()

            # Toggle-back must request the original windowed size.
            last_call = mock_set_mode.call_args
            assert last_call[0][0] == (1920, 1080), (
                f"Toggle-back must restore stashed windowed size; got {last_call[0][0]}"
            )
            assert config.fullscreen is False


class TestStrategyAwareFlagsAndSize:
    """v0.4 behavior: SCALED preserved across toggle, size swapped under SCALED.

    The size-swap is critical: under ``pygame.SCALED``, the size arg
    to ``set_mode`` is the *logical* render surface (SDL scales it
    physically). Passing ``(0, 0)`` would make the logical size =
    desktop resolution, silently breaking Skodrak's BASE-logical-surface
    contract on any non-BASE-resolution monitor.
    """

    def test_toggle_preserves_scaled_under_scaled_strategy(self):
        """Going-fullscreen under ScaledStrategy: flags include SCALED,
        size argument is (base_w, base_h) — NOT (0, 0)."""
        from pygame_display_kit.strategies.scaled import ScaledStrategy

        config = ResolutionConfig(
            base=(1920, 1080), strategy=ScaledStrategy, auto_detect=False
        )
        config.set_resolution(1920, 1080)
        mgr = FullscreenManager(config)

        with patch("pygame.display.set_mode") as mock_set_mode:
            mock_set_mode.return_value = pygame.Surface((1920, 1080))
            mgr.toggle()  # → fullscreen

            # Both bits must be set
            size_arg, flags_arg = mock_set_mode.call_args[0]
            assert flags_arg & pygame.SCALED, (
                f"SCALED bit lost on going-fullscreen; got flags={flags_arg}"
            )
            assert flags_arg & pygame.FULLSCREEN
            # Size-swap: logical surface stays at BASE under SCALED.
            assert size_arg == (1920, 1080), (
                f"Going-fullscreen under SCALED must use (base_w, base_h) "
                f"as the logical-surface size, not (0, 0); got {size_arg}"
            )

            # Toggle back to windowed: SCALED still present.
            mock_set_mode.return_value = pygame.Surface((1920, 1080))
            mgr.toggle()  # → windowed
            _, flags_back = mock_set_mode.call_args[0]
            assert flags_back & pygame.SCALED, (
                f"SCALED bit lost on toggle-back to windowed; got flags={flags_back}"
            )

    def test_toggle_under_grow_strategy_passes_zero_size_to_fullscreen(self):
        """Defensive: under non-SCALED strategies (Grow, Letterbox), the
        going-fullscreen size argument stays at (0, 0). Catches a future
        bug that erroneously applied the size-swap to all strategies."""
        config = _make_config(1920, 1080)  # uses GrowStrategy
        mgr = FullscreenManager(config)

        with patch("pygame.display.set_mode") as mock_set_mode:
            mock_set_mode.return_value = pygame.Surface((2560, 1440))
            mgr.toggle()  # → fullscreen

            size_arg, flags_arg = mock_set_mode.call_args[0]
            assert size_arg == (0, 0), (
                f"Going-fullscreen under non-SCALED must use (0, 0) for "
                f"desktop resolution; got {size_arg}"
            )
            # No SCALED bit (Grow doesn't add it).
            assert flags_arg & pygame.SCALED == 0
            assert flags_arg & pygame.FULLSCREEN

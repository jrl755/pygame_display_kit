"""ScaledStrategy — wraps ``pygame.SCALED``; SDL handles scaling.

Used by Skodrak. The consumer creates the display surface with
``pygame.display.set_mode((BASE_W, BASE_H), pygame.SCALED | flags)`` —
SDL then internally scales the BASE-sized logical surface to whatever
the physical display happens to be (HiDPI, 4K, ultrawide, fullscreen
on a smaller monitor, etc.). Game code draws to the screen surface in
BASE coordinates; SDL's scaler handles the rest.

Trade-off vs. Grow / Letterbox:

- **Simpler implementation** — no manual ``transform.scale`` in
  present(); SDL handles everything. No separate render surface
  needed.
- **Hardware-accelerated where available** — SDL uses GPU scaling on
  modern setups, software scaling as a fallback. Generally faster
  than ``pygame.transform.scale``.
- **Letterboxes on aspect mismatch** — like LetterboxStrategy, SDL
  preserves aspect ratio and adds black bars on the un-grown axis. No
  widescreen-grow benefit (Grow's gameplay advantage is unavailable).
- **Event coordinates always in BASE** — ``pygame.event.get()``
  returns mouse positions in 0–BASE_W / 0–BASE_H coordinates regardless
  of physical display, simplifying input handling.

Contract notes for consumers using this strategy:

The strategy returns a render surface at BASE dims, but the *typical*
usage with SCALED is to draw directly to the screen surface returned
by ``set_mode``. The render surface is a buffer the consumer can
choose to use (intermediate compositing) or ignore. SDL handles the
actual scaling regardless.
"""

from typing import TYPE_CHECKING, Tuple

import pygame

from ..viewport import ViewportStrategy

if TYPE_CHECKING:
    from ..config import ResolutionConfig


class ScaledStrategy(ViewportStrategy):
    """SDL-handled scaling — wraps ``pygame.SCALED``."""

    @staticmethod
    def update_viewport(config: "ResolutionConfig", display_width: int, display_height: int) -> None:
        """Viewport stays at BASE; SDL handles physical-display scaling.

        ``scale_x``, ``scale_y``, and ``scale`` all stay at 1.0 because
        the consumer draws in BASE coordinates and SDL applies the
        actual scale at the OS / GPU level. Scale factors are
        irrelevant from the game's perspective.
        """
        config.viewport_width = config.base_width
        config.viewport_height = config.base_height
        config.scale_x = 1.0
        config.scale_y = 1.0
        config.scale = 1.0

    @staticmethod
    def compute_viewport_offset(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Always (0, 0) — SDL handles letterbox positioning."""
        return (0, 0)

    @staticmethod
    def compute_viewport_scale(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Returns ``screen_size`` — SDL scales the BASE surface to fill the screen.

        Provided for ABC compliance; consumers using SCALED typically
        don't need this (they call ``pygame.display.flip()`` directly
        without any manual scale).
        """
        return screen_size

    @staticmethod
    def create_render_surface(config: "ResolutionConfig") -> pygame.Surface:
        """Allocate a Surface at BASE dimensions.

        Provided for ABC compliance. The *typical* SCALED workflow has
        the consumer draw directly to the screen surface returned by
        ``pygame.display.set_mode((BASE_W, BASE_H), pygame.SCALED |
        flags)`` — that screen surface IS the render surface, and SDL
        scales it. This method's return value is a separate buffer the
        consumer can use for compositing or ignore.
        """
        return pygame.Surface((config.base_width, config.base_height))


def add_scaled_flag(flags: int) -> int:
    """Helper to add ``pygame.SCALED`` to existing display flags.

    Consumers using ScaledStrategy must call ``pygame.display.set_mode``
    with the SCALED flag for SDL to engage the scaler. This helper
    composes SCALED with whatever flags the consumer's
    ``ResolutionConfig.get_display_flags()`` already returns.

    Args:
        flags: Existing pygame display flags (e.g. from
            ``config.get_display_flags()`` — typically RESIZABLE or
            FULLSCREEN).

    Returns:
        ``flags | pygame.SCALED``.

    Example::

        from pygame_display_kit import ResolutionConfig
        from pygame_display_kit.strategies.scaled import (
            ScaledStrategy, add_scaled_flag,
        )

        config = ResolutionConfig(base=(1920, 1080), strategy=ScaledStrategy)
        screen = pygame.display.set_mode(
            (config.base_width, config.base_height),
            add_scaled_flag(config.get_display_flags()),
        )
    """
    return flags | pygame.SCALED

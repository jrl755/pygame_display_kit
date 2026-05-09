"""LetterboxStrategy — uniform aspect-preserving scale + centered letterbox.

Used by Death_Knight_Arena. The render surface is allocated at BASE
dimensions; the strategy uses ``scale = min(scale_x, scale_y)`` to find
the largest aspect-preserving fit on the display, then centers the
scaled render area inside the display with ``viewport_offset =
((display_w - render_w) // 2, (display_h - render_h) // 2)``. Black
bars (letterbox or pillarbox) appear on the un-grown axis.

Math example: BASE = 1920×1080, display = 2560×1080 (21:9 ultrawide).

- scale_x = 2560/1920 = 1.333
- scale_y = 1080/1080 = 1.000
- scale = min = 1.000 (height-limited; uniform)
- render_width = 1920 * 1.000 = 1920
- render_height = 1080 * 1.000 = 1080
- viewport_offset = ((2560 - 1920) // 2, (1080 - 1080) // 2) = (320, 0)
- viewport_scale = (1920, 1080) — letterboxed area inside the display

Game content fills 1920×1080 in the center of the screen with 320 px
black bars on left + right (pillarbox).

Compared to GrowStrategy: GrowStrategy widens the *viewport* (render
surface) to match display aspect, eliminating letterbox bars at the
cost of showing more game world. LetterboxStrategy keeps the viewport
fixed at BASE and centers it — the game world is exactly what the
designer intended at every aspect ratio.
"""

from typing import TYPE_CHECKING, Tuple

import pygame

from ..viewport import ViewportStrategy

if TYPE_CHECKING:
    from ..config import ResolutionConfig


class LetterboxStrategy(ViewportStrategy):
    """Uniform aspect-preserving scale + centered letterbox bars."""

    @staticmethod
    def update_viewport(config: "ResolutionConfig", display_width: int, display_height: int) -> None:
        """Set viewport == BASE; compute scale factors.

        Letterbox renders at BASE dimensions and scales the entire
        render surface uniformly to fit the display. Viewport stays
        at BASE; ``compute_viewport_scale`` and
        ``compute_viewport_offset`` produce the actual centered
        letterbox area later.
        """
        config.viewport_width = config.base_width
        config.viewport_height = config.base_height
        config.scale_x = display_width / config.base_width
        config.scale_y = display_height / config.base_height
        # Uniform = the largest factor that keeps both axes within display.
        config.scale = min(config.scale_x, config.scale_y)

    @staticmethod
    def compute_viewport_offset(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Centered offset = (display - render_area) // 2 per axis."""
        display_width, display_height = screen_size
        render_width = int(config.base_width * config.scale)
        render_height = int(config.base_height * config.scale)
        return (
            (display_width - render_width) // 2,
            (display_height - render_height) // 2,
        )

    @staticmethod
    def compute_viewport_scale(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Render area dimensions = base * uniform_scale.

        The render surface (at BASE dims) is scaled to this size before
        being blitted at ``compute_viewport_offset`` to letterbox it.
        """
        return (
            int(config.base_width * config.scale),
            int(config.base_height * config.scale),
        )

    @staticmethod
    def create_render_surface(config: "ResolutionConfig") -> pygame.Surface:
        """Allocate a Surface at BASE dimensions.

        The strategy renders the entire game world at BASE pixel-perfect
        coordinates; the display-side scale is applied during
        ``present()``. This preserves DK's design assumption that game
        objects (warriors, projectiles, UI) are authored against BASE.
        """
        return pygame.Surface((config.base_width, config.base_height))

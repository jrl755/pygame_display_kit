"""GrowStrategy — viewport widens to match display aspect.

Used by Broken Moon Redux. On widescreen displays (16:9 or wider when
BASE is 4:3), the viewport grows along the longer axis so the camera
shows MORE game world horizontally than the BASE dimensions imply.
Result on a 1920×1080 monitor with BASE=1600×1200:

- BASE_HEIGHT (1200) stays at 1200.
- VIEWPORT_WIDTH grows to ``int(1200 * 1920/1080) = 2133``.
- Render surface = 2133×1200.
- ``viewport_scale = (1920, 1080)`` — uniform 0.9× scale to fill the screen.
- ``viewport_offset = (0, 0)`` — no letterbox; the render-surface aspect
  matches the display aspect by construction.

For a 4:3 display where ``display_aspect == base_aspect``, the math
collapses to ``viewport == base`` (no growth needed). For displays
*taller* than BASE, the strategy grows VIEWPORT_HEIGHT instead of WIDTH.
"""

from typing import TYPE_CHECKING, Tuple

import pygame

from ..viewport import ViewportStrategy

if TYPE_CHECKING:
    from ..config import ResolutionConfig


class GrowStrategy(ViewportStrategy):
    """Viewport widens to match display aspect — no letterboxing."""

    @staticmethod
    def update_viewport(config: "ResolutionConfig", display_width: int, display_height: int) -> None:
        """Grow VIEWPORT along the longer display axis to match aspect."""
        display_aspect = display_width / display_height

        if display_aspect > config.base_aspect:
            # Display is wider than base — keep vertical at BASE, grow horizontal.
            config.viewport_height = config.base_height
            config.viewport_width = int(config.base_height * display_aspect)
        else:
            # Display is equal-or-taller than base — keep horizontal at BASE,
            # grow vertical (covers the matching-aspect case as a no-op too).
            config.viewport_width = config.base_width
            config.viewport_height = int(config.base_width / display_aspect)

        # Game logic still positions sprites in BASE units along the
        # un-grown axis; SCALE values stay 1.0 because rendering happens
        # at viewport (= aspect-matched) dimensions, not BASE.
        config.scale_x = 1.0
        config.scale_y = 1.0
        config.scale = 1.0

    @staticmethod
    def compute_viewport_offset(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Always (0, 0) — render surface fills the whole screen."""
        return (0, 0)

    @staticmethod
    def compute_viewport_scale(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Returns ``screen_size`` — render surface scales to fill display."""
        return screen_size

    @staticmethod
    def create_render_surface(config: "ResolutionConfig") -> pygame.Surface:
        """Allocate a Surface at viewport dimensions.

        Sized to match display aspect (set by :meth:`update_viewport`)
        so the subsequent scale-to-screen is uniform — no aspect distortion.
        """
        return pygame.Surface((config.viewport_width, config.viewport_height))

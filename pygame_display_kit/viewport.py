"""Viewport strategy abstract base class.

Strategies decide how the BASE design resolution maps onto an arbitrary
display size — three production approaches exist across the projects
this library was extracted from:

- :class:`GrowStrategy` (v0.1): viewport widens to match display aspect.
  Used by Broken Moon Redux.
- ``LetterboxStrategy`` (planned v0.2): uniform aspect-preserving scale
  with centered offset. Used by Death_Knight_Arena.
- ``ScaledStrategy`` (planned v0.3): wraps ``pygame.SCALED``, lets SDL
  handle the scaling. Used by Skodrak.

The ABC guarantees Phase 1's API can support all three siblings without
breaking changes when later strategies land.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple

import pygame

if TYPE_CHECKING:  # avoid circular import at runtime
    from .config import ResolutionConfig


class ViewportStrategy(ABC):
    """Decides how BASE coordinates map onto display dimensions.

    Subclasses implement four hooks. Each hook is a pure function over
    ``config`` plus the actual display size — no hidden state.
    """

    @staticmethod
    @abstractmethod
    def update_viewport(config: "ResolutionConfig", display_width: int, display_height: int) -> None:
        """Mutate ``config.viewport_width/height`` for the new display size.

        Args:
            config: ResolutionConfig instance to mutate.
            display_width: Actual display width in pixels.
            display_height: Actual display height in pixels.
        """

    @staticmethod
    @abstractmethod
    def compute_viewport_offset(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Return ``(offset_x, offset_y)`` for centering the rendered surface.

        Returns ``(0, 0)`` for strategies that fill the whole screen.
        """

    @staticmethod
    @abstractmethod
    def compute_viewport_scale(
        config: "ResolutionConfig", screen_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Return ``(scaled_w, scaled_h)`` — the size the render surface
        is scaled to before blitting onto the screen.

        Most strategies return ``screen_size`` (fill the screen).
        Letterboxing strategies return a smaller box centered by
        ``compute_viewport_offset``.
        """

    @staticmethod
    @abstractmethod
    def create_render_surface(config: "ResolutionConfig") -> pygame.Surface:
        """Return the pygame.Surface that game code draws onto.

        For Grow/Letterbox: a separate Surface at viewport dimensions
        that ``present()`` later scales onto the screen.
        For Scaled: returns the screen itself (SDL handles scaling).
        """

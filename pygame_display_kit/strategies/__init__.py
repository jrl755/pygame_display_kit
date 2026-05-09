"""Viewport strategies — pluggable implementations of viewport math.

Available strategies:

- :class:`GrowStrategy` (v0.1): widescreen viewport-grow (Broken Moon style)

Planned strategies:

- ``LetterboxStrategy`` (v0.2): centered letterbox (DK_Arena style)
- ``ScaledStrategy`` (v0.3): pygame.SCALED wrapper (Skodrak style)
"""

from .grow import GrowStrategy

__all__ = ["GrowStrategy"]

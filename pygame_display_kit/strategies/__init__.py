"""Viewport strategies — pluggable implementations of viewport math.

Available strategies:

- :class:`GrowStrategy` (v0.1): widescreen viewport-grow (Broken Moon style)
- :class:`LetterboxStrategy` (v0.2): centered letterbox (DK_Arena style)

Planned strategies:

- ``ScaledStrategy`` (v0.3): pygame.SCALED wrapper (Skodrak style)
"""

from .grow import GrowStrategy
from .letterbox import LetterboxStrategy

__all__ = ["GrowStrategy", "LetterboxStrategy"]

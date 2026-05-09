"""pygame_display_kit — resolution and scaling utilities for pygame-ce games.

Public API (v0.2.0):

- :class:`ResolutionConfig` — runtime resolution state + viewport strategy
- :func:`detect_native` — read native resolution via pygame.display.Info()
- :func:`select_best_resolution` — pick the best startup resolution
- :class:`FullscreenManager` — fullscreen toggle with proper sync
- :class:`ViewportStrategy` — ABC for viewport math implementations
- :class:`GrowStrategy` — widescreen viewport-grow strategy (Broken Moon style)
- :class:`LetterboxStrategy` — uniform aspect-preserving + letterbox (DK_Arena style)
- :func:`adjust_for_platform` — subtract macOS Dock / Windows taskbar / Linux panel
- :func:`scale_value`, :func:`scale_position`, :func:`scale_size`,
  :func:`get_font_size` — per-element scale helpers
"""

from .config import ResolutionConfig
from .detection import detect_native
from .fullscreen import FullscreenManager
from .helpers import get_font_size, scale_position, scale_size, scale_value
from .platform_adjust import adjust_for_platform
from .selection import select_best_resolution
from .strategies.grow import GrowStrategy
from .strategies.letterbox import LetterboxStrategy
from .viewport import ViewportStrategy

__version__ = "0.2.0"

__all__ = [
    "ResolutionConfig",
    "detect_native",
    "FullscreenManager",
    "select_best_resolution",
    "ViewportStrategy",
    "GrowStrategy",
    "LetterboxStrategy",
    "adjust_for_platform",
    "scale_value",
    "scale_position",
    "scale_size",
    "get_font_size",
    "__version__",
]

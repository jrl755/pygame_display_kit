"""pygame_display_kit — resolution and scaling utilities for pygame-ce games.

Public API (v0.1.0):

- :class:`ResolutionConfig` — runtime resolution state + viewport strategy
- :func:`detect_native` — read native resolution via pygame.display.Info()
- :func:`select_best_resolution` — pick the best startup resolution
- :class:`FullscreenManager` — fullscreen toggle with proper sync
- :class:`ViewportStrategy` — ABC for viewport math implementations
- :class:`GrowStrategy` — widescreen viewport-grow strategy (BM-style)
"""

from .config import ResolutionConfig
from .detection import detect_native
from .fullscreen import FullscreenManager
from .selection import select_best_resolution
from .strategies.grow import GrowStrategy
from .viewport import ViewportStrategy

__version__ = "0.1.0"

__all__ = [
    "ResolutionConfig",
    "detect_native",
    "FullscreenManager",
    "select_best_resolution",
    "ViewportStrategy",
    "GrowStrategy",
    "__version__",
]

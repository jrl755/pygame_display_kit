"""Resolution selection policy.

Picks the best startup resolution for a given :class:`ResolutionConfig`.
Prefers native (the user's actual desktop resolution) when it's in the
available preset list — the widescreen pipeline scales correctly to
whatever the user picks at runtime, so opening at native gives the
sharpest, largest image with no scaling artifacts.

Earlier policies preferred BASE (1600×1200) when it fit. That made
sense when the engine used letterboxed scaling and BASE-pixel-perfect
rendering avoided blur. After modern viewport pipelines that handle any
aspect ratio uniformly, the BASE preference left users on 2560×1440 / 4K
monitors with a small windowed game by default — the present library
inherits the corrected policy.
"""

import logging
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .config import ResolutionConfig

logger = logging.getLogger(__name__)


def select_best_resolution(config: "ResolutionConfig") -> Tuple[int, int]:
    """Pick the best startup resolution for the given config.

    Fallback chain:
        1. Native resolution if it's in the available preset list
           (``get_available_resolutions`` ensures it is unless empty).
        2. Largest preset resolution that fits the display.
        3. 80% of native if no preset fits (defensive — only triggers
           on extreme small-display edge cases).

    Args:
        config: The :class:`ResolutionConfig` to select for.

    Returns:
        Tuple of ``(width, height)`` for the chosen resolution.
    """
    available = config.get_available_resolutions()

    if not available:
        # No preset fits the display — fall back to 80% of native so
        # the game opens windowed inside the desktop with margin.
        logger.warning("No preset resolutions fit display; using 80%% of native")
        return (
            int(config.native_width * 0.8),
            int(config.native_height * 0.8),
        )

    native = (config.native_width, config.native_height)
    if native in available:
        logger.info("Selected native resolution: %dx%d", *native)
        return native

    # Native somehow not in available (defensive — get_available_resolutions
    # adds it explicitly, but this branch protects against custom configs
    # with native_width/height = 0).
    best = available[-1]
    logger.info("Native not in preset list; selected largest fit: %dx%d", *best)
    return best

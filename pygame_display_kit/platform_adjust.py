"""Platform-aware native resolution adjustment.

The OS reports the *desktop* resolution via ``pygame.display.Info()``,
but the *usable* resolution for a windowed game is smaller — system
chrome (macOS Dock + menu bar, Windows taskbar, Linux panel) eats
some of the display. Without subtracting that chrome, a windowed game
opened "at native" gets clipped at the bottom (or sides, depending on
where the user docks their taskbar).

Each platform reserves a different amount; this module encapsulates
the heuristics. Originally extracted from
``Death_Knight_Arena/dk_modules/core/resolution.py``.

The adjustments preserve the BASE aspect ratio rather than just
subtracting pixels — that way a 16:9 game on a 16:9 monitor with
a Dock at the bottom still gets a 16:9 windowed area (slightly
smaller than the full screen) instead of a near-16:9-but-slightly-
shorter region that produces letterbox bars.
"""

import logging
import platform
from typing import Tuple

logger = logging.getLogger(__name__)


def adjust_for_platform(
    detected_width: int,
    detected_height: int,
    base_aspect: float,
) -> Tuple[int, int]:
    """Return platform-adjusted ``(width, height)`` for windowed mode.

    Args:
        detected_width: OS-reported desktop width.
        detected_height: OS-reported desktop height.
        base_aspect: ``base_width / base_height`` of the game's design
            resolution. Used to preserve aspect when subtracting chrome.

    Returns:
        Adjusted ``(width, height)`` that fits inside the desktop with
        system chrome accounted for.
    """
    system = platform.system()
    if system == "Darwin":
        return _adjust_for_macos(detected_height, base_aspect)
    if system == "Windows":
        return _adjust_for_windows(detected_width, detected_height, base_aspect)
    return _adjust_for_linux(detected_height, base_aspect, system)


def _adjust_for_macos(detected_height: int, aspect_ratio: float) -> Tuple[int, int]:
    """macOS: subtract ~100 px for menu bar + Dock.

    Width is computed from height × aspect, preserving 16:9 (or
    whatever BASE) rather than blindly subtracting pixels. Result:
    the game window opens with menu bar + Dock visible above and
    below, no clipping.
    """
    adjusted_height = detected_height - 100
    adjusted_width = int(adjusted_height * aspect_ratio)
    logger.info(
        "macOS detected: adjusted to %dx%d to clear Dock (preserves %.3f aspect)",
        adjusted_width, adjusted_height, aspect_ratio,
    )
    return adjusted_width, adjusted_height


def _adjust_for_windows(
    detected_width: int, detected_height: int, aspect_ratio: float
) -> Tuple[int, int]:
    """Windows: subtract 5% of height for taskbar.

    Width is height × aspect to preserve the design ratio. If that
    width exceeds detected (ultrawide displays where 5%-shorter
    height × 16:9 still fits horizontally), fall back to fitting
    width-first.
    """
    taskbar_height = int(detected_height * 0.05)
    adjusted_height = detected_height - taskbar_height
    adjusted_width = int(adjusted_height * aspect_ratio)

    # On ultrawide displays, height × aspect can exceed actual width.
    # Refit width-first in that case.
    if adjusted_width > detected_width:
        adjusted_width = detected_width
        adjusted_height = int(adjusted_width / aspect_ratio)

    logger.info(
        "Windows detected: adjusted to %dx%d to clear taskbar (reserved %dpx)",
        adjusted_width, adjusted_height, taskbar_height,
    )
    return adjusted_width, adjusted_height


def _adjust_for_linux(
    detected_height: int, aspect_ratio: float, system: str
) -> Tuple[int, int]:
    """Linux + other Unix: subtract 5% of height for panel/dock.

    Linux desktops vary widely — KDE has a 36 px panel by default,
    GNOME has a thicker top bar, i3 has none. 5% is a conservative
    estimate that leaves margin on most setups.
    """
    adjusted_height = int(detected_height * 0.95)
    adjusted_width = int(adjusted_height * aspect_ratio)
    logger.info(
        "%s detected: adjusted to %dx%d to clear panels (5%% margin)",
        system, adjusted_width, adjusted_height,
    )
    return adjusted_width, adjusted_height

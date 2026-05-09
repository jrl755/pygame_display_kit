"""Native display resolution detection.

Wraps ``pygame.display.Info()`` so callers can mock it cleanly. The
SDL dummy driver returns synthetic 1024×768 for ``current_w/.current_h``
regardless of the actual monitor (verified during library design). Tests
that assert detection-of-real-native MUST mock this function rather than
rely on ``SDL_VIDEODRIVER=dummy`` returning real dims.
"""

from typing import Tuple

import pygame


def detect_native() -> Tuple[int, int]:
    """Return ``(width, height)`` of the OS-reported desktop resolution.

    Reads ``pygame.display.Info()`` once at call time. Caller is
    responsible for ensuring ``pygame.init()`` has been called first
    (typically true at library-import time on any pygame-using app).

    Returns:
        Tuple of ``(current_w, current_h)`` from pygame.display.Info().
        Note: under ``SDL_VIDEODRIVER=dummy`` this returns 1024×768
        synthetically — tests must mock ``pygame.display.Info`` to
        verify detection logic against arbitrary monitor sizes.
    """
    info = pygame.display.Info()
    return (info.current_w, info.current_h)

"""Fullscreen toggle with desktop-resolution + sync.

The bug this class prevents: when fullscreen is requested via
``pygame.display.set_mode((0, 0), pygame.FULLSCREEN)``, pygame uses
the desktop resolution. But naive callers don't update their config's
``current_*`` to match the actual surface size, leaving viewport math
computed against stale dims. The result is a smaller surface drawn at
the top-left of a larger screen with black bars on the opposite edges
(reproduced in Broken Moon Redux during library design).

:class:`FullscreenManager` handles three things atomically:

1. Stash windowed dims before going fullscreen, so toggle-back restores
   the user's chosen size.
2. Use ``set_mode((0, 0), FULLSCREEN)`` for desktop-resolution fullscreen
   (avoids OS-level scaling artifacts when pygame is asked for a
   non-native fullscreen mode).
3. Read the actual surface size via ``screen.get_size()`` and sync
   ``config.current_width/height`` before any viewport recompute.
"""

import logging
from typing import Optional, Tuple

import pygame

from .config import ResolutionConfig

logger = logging.getLogger(__name__)


class FullscreenManager:
    """Stateful fullscreen toggle helper.

    Holds one piece of state: the windowed dims to restore on
    toggle-back. The fullscreen flag itself lives on the config.

    Usage:

    .. code-block:: python

        mgr = FullscreenManager(config)
        screen = mgr.toggle()  # returns the new pygame.Surface
        # config.current_width/height are now in sync with screen.get_size()
    """

    def __init__(self, config: ResolutionConfig):
        """Initialize with a ResolutionConfig instance.

        Args:
            config: The config to mutate during toggles.
        """
        self.config = config
        self._windowed_size: Optional[Tuple[int, int]] = None

    def toggle(self) -> pygame.Surface:
        """Toggle between windowed and fullscreen.

        Returns:
            The new ``pygame.Surface`` from ``pygame.display.set_mode``.
            ``config.current_width/height`` are synced to its actual
            ``get_size()`` after the call.

        Both branches compose flags via :meth:`ResolutionConfig.get_display_flags`,
        which is strategy-aware (preserves SCALED for Skodrak across the
        toggle). The fullscreen branch additionally swaps the size
        argument: under SCALED, the size arg is the *logical* render
        surface (SDL scales it physically), so it must stay at BASE
        rather than ``(0, 0)`` (which would make the logical size =
        desktop resolution and silently break Skodrak's design contract).
        """
        going_fullscreen = not self.config.fullscreen

        if going_fullscreen:
            # Stash windowed dims so we can restore them on toggle-back.
            self._windowed_size = (self.config.current_width, self.config.current_height)
            self.config.fullscreen = True
            flags = self.config.get_display_flags()
            if flags & pygame.SCALED:
                # ScaledStrategy: logical surface stays at BASE; SDL
                # handles physical scaling.
                size = (self.config.base_width, self.config.base_height)
            else:
                # Non-SCALED (Letterbox, Grow): (0, 0) → desktop resolution.
                # Avoids OS-level letterboxing / scaling that happens
                # when pygame is asked for a non-native fullscreen mode.
                size = (0, 0)
            screen = pygame.display.set_mode(size, flags)
        else:
            self.config.fullscreen = False
            windowed_w, windowed_h = self._windowed_size or (
                self.config.current_width,
                self.config.current_height,
            )
            screen = pygame.display.set_mode(
                (windowed_w, windowed_h), self.config.get_display_flags()
            )

        # Sync current_* to the actual surface dims. Critical for any
        # subsequent viewport recompute — strategies read current_*.
        actual_w, actual_h = screen.get_size()
        self.config.set_resolution(actual_w, actual_h)

        mode = "fullscreen" if self.config.fullscreen else "windowed"
        logger.info("Switched to %s mode: %dx%d", mode, actual_w, actual_h)
        return screen

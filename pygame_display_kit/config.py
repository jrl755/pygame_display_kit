"""ResolutionConfig — the runtime resolution/scaling state for a game.

Holds: design (BASE) dimensions, current display dimensions, native
monitor dimensions, viewport dimensions (may differ from BASE under
GROW strategy on widescreen), scale factors, fullscreen flag, and the
chosen :class:`ViewportStrategy`.

Game code reads attributes (``config.base_width``, ``config.scale``,
etc.). The strategy mutates ``viewport_*`` and ``scale*`` when the
display size changes.
"""

import logging
from typing import List, Optional, Tuple, Type

import pygame

from .detection import detect_native
from .platform_adjust import adjust_for_platform
from .viewport import ViewportStrategy

logger = logging.getLogger(__name__)


# Common resolutions that fit most consumer monitors. Used by
# ``get_available_resolutions`` to filter against the actual native size.
_PRESET_RESOLUTIONS: List[Tuple[int, int]] = [
    (1280, 720),    # 720p
    (1600, 900),    # 900p
    (1600, 1200),   # 4:3 (legacy BM design res)
    (1920, 1080),   # 1080p (most common modern)
    (2560, 1440),   # 1440p (QHD)
    (3840, 2160),   # 2160p (4K UHD)
]


class ResolutionConfig:
    """Runtime resolution state + chosen viewport strategy.

    Attributes:
        base_width, base_height: Design resolution (immutable after init).
        base_aspect: ``base_width / base_height``.
        native_width, native_height: OS-detected desktop size at init.
        current_width, current_height: Currently-active window dimensions
            (mutated by ``set_resolution`` and fullscreen toggling).
        viewport_width, viewport_height: Logical viewport dims that the
            strategy chose for the current display size. May exceed
            base_* under GROW; equal base_* otherwise.
        scale, scale_x, scale_y: Display-to-base scale factors. ``scale``
            is the uniform factor (``min(scale_x, scale_y)``) for
            aspect-preserving scaling.
        fullscreen: Current fullscreen flag.
        strategy: The :class:`ViewportStrategy` subclass used to compute
            viewport math. Class attribute, not instance — strategies
            are stateless.
    """

    def __init__(
        self,
        base: Tuple[int, int],
        strategy: Type[ViewportStrategy],
        auto_detect: bool = True,
        fullscreen: bool = False,
        platform_adjust: bool = False,
        min_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[Tuple[int, int]] = None,
    ):
        """Initialize the resolution config.

        Args:
            base: ``(width, height)`` of the game's design resolution.
            strategy: A :class:`ViewportStrategy` subclass (the *class*,
                not an instance — strategies are stateless).
            auto_detect: If True, populate ``native_*`` via
                :func:`detect_native`. If False, callers must set
                ``native_width`` / ``native_height`` manually before
                calling ``select_best_resolution``.
            fullscreen: Initial fullscreen flag.
            platform_adjust: If True (and ``auto_detect`` also True),
                pass detected native dims through
                :func:`pygame_display_kit.platform_adjust.adjust_for_platform`
                to subtract macOS Dock / Windows taskbar / Linux panel
                space. Useful for windowed-mode startup; not relevant
                for fullscreen since system chrome is hidden in
                fullscreen mode. Default: False (preserve raw native
                dims, opt-in adjustment).
            min_size: Optional ``(width, height)`` lower bound; calls to
                :meth:`set_resolution` clamp to this minimum. Default:
                None (no clamping). DK_Arena uses ``(1280, 720)``.
            max_size: Optional ``(width, height)`` upper bound. DK_Arena
                uses ``(7680, 4320)`` (8K).
        """
        self.base_width: int = base[0]
        self.base_height: int = base[1]
        self.base_aspect: float = base[0] / base[1]

        self.min_size: Optional[Tuple[int, int]] = min_size
        self.max_size: Optional[Tuple[int, int]] = max_size

        if auto_detect:
            detected = detect_native()
            if platform_adjust:
                detected = adjust_for_platform(detected[0], detected[1], self.base_aspect)
            self.native_width, self.native_height = detected
        else:
            self.native_width: int = 0
            self.native_height: int = 0

        # Current = BASE until select_best_resolution / set_resolution
        # picks something else.
        self.current_width: int = base[0]
        self.current_height: int = base[1]

        # Viewport defaults to BASE until update_viewport_dimensions
        # is called by a strategy.
        self.viewport_width: int = base[0]
        self.viewport_height: int = base[1]

        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.scale: float = 1.0  # uniform = min(scale_x, scale_y)

        self.fullscreen: bool = fullscreen
        self.resizable: bool = True
        self.vsync: bool = True

        self.strategy: Type[ViewportStrategy] = strategy

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def set_resolution(self, width: int, height: int, fullscreen: Optional[bool] = None) -> None:
        """Update current dimensions + recompute scale factors.

        Does NOT call ``pygame.display.set_mode`` — that's the caller's
        responsibility (or :class:`FullscreenManager`'s). This method
        just updates the config state.

        If ``min_size`` / ``max_size`` were set at construction, the
        input is clamped + a warning logged. Floats raise ``ValueError``
        — silently truncating to int corrupts test cases that pass
        ``800.5`` expecting an error.

        Args:
            width: New current width in pixels.
            height: New current height in pixels.
            fullscreen: If provided, also update the fullscreen flag.

        Raises:
            ValueError: If ``width`` or ``height`` is not an integer.
        """
        # Reject floats explicitly. Silent int() truncation hides bugs
        # in callers passing computed values without rounding.
        if isinstance(width, float) or isinstance(height, float):
            raise ValueError(
                f"Resolution dimensions must be integers, got "
                f"width={type(width).__name__}, height={type(height).__name__}"
            )

        if self.min_size is not None:
            min_w, min_h = self.min_size
            if width < min_w or height < min_h:
                logger.warning(
                    "Resolution %dx%d below min_size %dx%d; clamping",
                    width, height, min_w, min_h,
                )
                width = max(width, min_w)
                height = max(height, min_h)

        if self.max_size is not None:
            max_w, max_h = self.max_size
            if width > max_w or height > max_h:
                logger.warning(
                    "Resolution %dx%d exceeds max_size %dx%d; clamping",
                    width, height, max_w, max_h,
                )
                width = min(width, max_w)
                height = min(height, max_h)

        self.current_width = width
        self.current_height = height
        if fullscreen is not None:
            self.fullscreen = fullscreen
        self.scale_x = width / self.base_width
        self.scale_y = height / self.base_height
        self.scale = min(self.scale_x, self.scale_y)

    def update_viewport_dimensions(self, display_width: int, display_height: int) -> None:
        """Delegate viewport recomputation to the strategy."""
        self.strategy.update_viewport(self, display_width, display_height)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_display_flags(self) -> int:
        """Return pygame display flags reflecting fullscreen + resizable state."""
        flags = 0
        if self.resizable and not self.fullscreen:
            flags |= pygame.RESIZABLE
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        return flags

    def get_available_resolutions(self) -> List[Tuple[int, int]]:
        """Return preset resolutions that fit the native display.

        Always includes ``(native_width, native_height)`` even if not
        in the preset list, so :func:`select_best_resolution` always
        has native as an option.
        """
        available = [
            (w, h)
            for w, h in _PRESET_RESOLUTIONS
            if w <= self.native_width and h <= self.native_height
        ]
        native = (self.native_width, self.native_height)
        if native not in available and self.native_width > 0:
            available.append(native)
        return sorted(available, key=lambda x: x[0] * x[1])

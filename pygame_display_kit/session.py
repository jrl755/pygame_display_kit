"""DisplaySession — one object that opens, toggles, resizes and presents the display.

Everything the four games used to wire by hand, once:

- **Startup policy** (``open``): the saved :class:`WindowPreferences`
  decides, and with none saved the game opens fullscreen. A window is
  refused when it cannot be a usable one: under Scaled (the window is the
  design size) on a monitor at or below the design after subtracting OS
  chrome; under Letterbox / Grow when even the largest window this
  desktop can show is smaller than the game's minimum (``min_window`` or
  the config's ``min_size``). A Letterbox game with a small minimum keeps
  its fitted window on a laptop. Fullscreen is always the desktop's own resolution — never
  a monitor mode switch — except under ``pygame.SCALED``, where the
  base size is passed and SDL scales it to the desktop.
- **One toggle** (``toggle_fullscreen``) that every entry point calls
  (hotkey and menu alike), so the config, the saved preference and the
  real surface always agree.
- **Events** (``handle_event``): the F11 hotkey and ``WINDOWRESIZED``
  (resync to what the OS granted, enforce a minimum window).
- **Present** (``present``): flip under Scaled; scale + centred blit
  under Letterbox; blit under Grow.

The window-size rules (offered presets under a chrome allowance, fitting
a saved size to this desktop, the macOS leave-fullscreen quirk, resyncing
to the granted size) come from SP_Adventure's ``core/display.py``, where
each was found by a real player report.
"""

import logging
from collections.abc import Callable, Sequence
from typing import Optional, Tuple

import pygame

from .auto_fullscreen import should_auto_fullscreen
from .config import ResolutionConfig
from .detection import detect_native
from .platform_adjust import adjust_for_platform
from .preferences import WindowPreferences
from .strategies.grow import GrowStrategy
from .strategies.scaled import ScaledStrategy

logger = logging.getLogger(__name__)

# Window sizes offered by default, all 16:9; entries whose aspect differs
# from the design's are filtered out for other designs.
WINDOW_SIZES: Tuple[Tuple[int, int], ...] = (
    (1280, 720),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
)
# What a window must leave free of the desktop's height to be wholly
# visible: its own title bar plus the taskbar, Dock or menu bar. An
# estimate — pygame cannot ask the OS for the usable area.
DEFAULT_CHROME_ALLOWANCE = 100
_ASPECT_TOLERANCE = 0.01


def largest_window(config: ResolutionConfig, desktop: Tuple[int, int], chrome_allowance: int) -> Tuple[int, int]:
    """The largest design-aspect window wholly visible on *desktop*."""
    desktop_w, desktop_h = desktop
    height = min(desktop_h - chrome_allowance, int(desktop_w / config.base_aspect))
    height = max(1, height)
    return int(height * config.base_aspect), height


def offered_window_sizes(
    config: ResolutionConfig,
    desktop: Tuple[int, int],
    sizes: Sequence[Tuple[int, int]] = WINDOW_SIZES,
    chrome_allowance: int = DEFAULT_CHROME_ALLOWANCE,
) -> list[Tuple[int, int]]:
    """Window sizes to offer on this desktop, smallest first.

    Every entry of *sizes* with the design's aspect that fits under the
    chrome allowance, or the largest window that does when none of them
    fit (a 1366x768 laptop).
    """
    fits_w, fits_h = largest_window(config, desktop, chrome_allowance)
    fitting = [
        (w, h)
        for w, h in sizes
        if w <= fits_w and h <= fits_h and abs(w / h - config.base_aspect) < _ASPECT_TOLERANCE
    ]
    return fitting or [(fits_w, fits_h)]


def fit_window(
    config: ResolutionConfig,
    desktop: Tuple[int, int],
    width: int,
    height: int,
    sizes: Sequence[Tuple[int, int]] = WINDOW_SIZES,
    chrome_allowance: int = DEFAULT_CHROME_ALLOWANCE,
) -> Tuple[int, int]:
    """``(width, height)`` if wholly visible on this desktop, else the largest offered size."""
    fits_w, fits_h = largest_window(config, desktop, chrome_allowance)
    if 0 < width <= fits_w and 0 < height <= fits_h:
        return width, height
    if width or height:
        logger.warning(
            "Saved window %dx%d does not fit the %dx%d desktop; using the largest that does",
            width,
            height,
            *desktop,
        )
    return offered_window_sizes(config, desktop, sizes, chrome_allowance)[-1]


class DisplaySession:
    """Owns the display for one game process. See the module docstring."""

    def __init__(
        self,
        config: ResolutionConfig,
        *,
        preferences: Optional[WindowPreferences] = None,
        on_preferences_changed: Optional[Callable[[WindowPreferences], None]] = None,
        window_sizes: Sequence[Tuple[int, int]] = WINDOW_SIZES,
        chrome_allowance: int = DEFAULT_CHROME_ALLOWANCE,
        min_window: Optional[Tuple[int, int]] = (960, 540),
        hotkey: Optional[int] = pygame.K_F11,
        extra_flags: int = 0,
        resizable: Optional[bool] = None,
        desktop: Optional[Tuple[int, int]] = None,
    ) -> None:
        """
        Args:
            config: The game's resolution config; its strategy decides the
                scaling model. Mutated by the session (``current_*``,
                ``fullscreen``, ``resizable``).
            preferences: The saved choice, or None for "nothing saved yet"
                (opens fullscreen).
            on_preferences_changed: Called with the new preferences after
                every toggle or size change; the game persists them.
            window_sizes: Windowed sizes to offer (Letterbox / Grow).
            chrome_allowance: Desktop height reserved for title bar and
                taskbar when fitting a window.
            min_window: Smallest window a drag may leave (Letterbox /
                Grow); None disables the check.
            hotkey: Key that toggles fullscreen in ``handle_event``; None
                disables it.
            extra_flags: OR-ed into every ``set_mode`` (e.g. DOUBLEBUF).
            resizable: Overrides ``config.resizable`` when given.
            desktop: The desktop size when already known (a config that
                detected it); otherwise read once at ``open``.
        """
        self.config = config
        self._preferences = preferences
        self._on_changed = on_preferences_changed
        self._window_sizes = tuple(window_sizes)
        self._chrome = chrome_allowance
        self._min_window = min_window
        self._hotkey = hotkey
        self._extra_flags = extra_flags
        if resizable is not None:
            config.resizable = resizable
        self._desktop: Tuple[int, int] = desktop if desktop and desktop[0] > 0 and desktop[1] > 0 else (0, 0)
        self._screen: Optional[pygame.Surface] = None
        self._scaled_cache: Optional[pygame.Surface] = None

    # ------------------------------------------------------------------ state

    @property
    def screen(self) -> pygame.Surface:
        """The display surface from the last ``set_mode``."""
        if self._screen is None:
            raise RuntimeError("DisplaySession.open() has not been called")
        return self._screen

    @property
    def preferences(self) -> WindowPreferences:
        """The current choice (the saved one, or the family default)."""
        return self._preferences if self._preferences is not None else WindowPreferences()

    @property
    def scaled(self) -> bool:
        return self.config.strategy is ScaledStrategy

    @property
    def desktop(self) -> Tuple[int, int]:
        """The desktop's own resolution, read at ``open``."""
        return self._desktop

    @property
    def offered_window_sizes(self) -> list[Tuple[int, int]]:
        """Window sizes a menu may offer; empty under Scaled (the window is the base size)."""
        if self.scaled:
            return []
        return offered_window_sizes(self.config, self._desktop, self._window_sizes, self._chrome)

    # ------------------------------------------------------------------ policy

    def open(self) -> pygame.Surface:
        """Open the display per the startup policy. Re-entrant: re-applies the current choice."""
        self._ensure_desktop()
        forced = self._window_would_be_unusable()
        fullscreen = True if forced else self.preferences.fullscreen
        if forced:
            logger.info(
                "Desktop %dx%d cannot show a usable window for a %dx%d design; opening fullscreen",
                *self._desktop,
                self.config.base_width,
                self.config.base_height,
            )
        return self._apply(fullscreen)

    def _window_would_be_unusable(self) -> bool:
        """The small-monitor rule, per scaling model (see the module docstring)."""
        if self.scaled or self.config.strategy is GrowStrategy:
            _, usable_height = adjust_for_platform(self._desktop[0], self._desktop[1], self.config.base_aspect)
            return should_auto_fullscreen(
                self._desktop[0], usable_height, self.config.base_width, self.config.base_height
            )
        floors = [floor for floor in (self._min_window, self.config.min_size) if floor is not None]
        if not floors:
            return False
        floor_w, floor_h = max(f[0] for f in floors), max(f[1] for f in floors)
        fits_w, fits_h = largest_window(self.config, self._desktop, self._chrome)
        return fits_w < floor_w or fits_h < floor_h

    def toggle_fullscreen(self) -> pygame.Surface:
        """Switch between fullscreen and the preferred window; saves the choice."""
        return self.set_fullscreen(not self.config.fullscreen)

    def set_fullscreen(self, fullscreen: bool) -> pygame.Surface:
        """Go fullscreen, or to the preferred window; saves the choice. Idempotent."""
        self._ensure_desktop()
        screen = self._apply(fullscreen)
        self._remember(fullscreen=fullscreen)
        return screen

    def set_window_size(self, width: int, height: int, *, fit: bool = True) -> pygame.Surface:
        """Open a window of this size and save the choice.

        ``fit`` replaces a size this desktop cannot show wholly by the
        largest offered one; ``fit=False`` asks for exactly that size (the
        OS may still shrink it, and the config is synced to what it grants).

        Raises:
            NotImplementedError: under Scaled, where the window is the base size.
        """
        if self.scaled:
            raise NotImplementedError("under pygame.SCALED the window is the design size")
        self._ensure_desktop()
        if fit:
            width, height = fit_window(self.config, self._desktop, width, height, self._window_sizes, self._chrome)
        screen = self._apply(False, (width, height), fit=False)
        self._remember(fullscreen=False, window=(width, height))
        return screen

    # ------------------------------------------------------------------ events

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle the hotkey and window resizes. Returns True when consumed."""
        if self._hotkey is not None and event.type == pygame.KEYDOWN and event.key == self._hotkey:
            self.toggle_fullscreen()
            return True
        if event.type == pygame.WINDOWRESIZED and not self.config.fullscreen and not self.scaled:
            # pygame replaces the display surface on a drag; pick up the live one.
            self._screen = self._live_screen()
            self.sync_to_granted()
            self.keep_window_readable()
            return True
        return False

    # ------------------------------------------------------------------ present

    def present(
        self,
        render_surface: Optional[pygame.Surface] = None,
        *,
        screen: Optional[pygame.Surface] = None,
        smooth: bool = True,
        flip: bool = True,
    ) -> None:
        """Put the frame on screen.

        Scaled: flip (SDL scales the logical surface; a given
        *render_surface* is blitted at the origin first). Letterbox:
        *render_surface* is scaled to the viewport and centred with black
        bars, after resyncing the config to the screen's real size (a
        dragged window). Grow: blitted at the viewport offset. ``screen``
        overrides the live display surface; ``smooth`` picks
        ``smoothscale`` over ``scale``; ``flip=False`` leaves the flip to
        the caller.
        """
        if screen is None:
            screen = self._live_screen()
        self._screen = screen
        if render_surface is not None and render_surface is not screen:
            if self.scaled:
                screen.blit(render_surface, (0, 0))
            else:
                self.sync_to_granted()
                size = screen.get_size()
                target = self.config.strategy.compute_viewport_scale(self.config, size)
                offset = self.config.strategy.compute_viewport_offset(self.config, size)
                if target == render_surface.get_size():
                    frame = render_surface
                else:
                    if self._scaled_cache is None or self._scaled_cache.get_size() != target:
                        self._scaled_cache = pygame.Surface(target)
                    scale = pygame.transform.smoothscale if smooth else pygame.transform.scale
                    frame = scale(render_surface, target, self._scaled_cache)
                if offset != (0, 0) or target != size:
                    screen.fill((0, 0, 0))
                screen.blit(frame, offset)
        if flip:
            pygame.display.flip()

    # ------------------------------------------------------------------ internals

    def _ensure_desktop(self) -> None:
        if self._desktop == (0, 0):
            # Read once: after set_mode, pygame.display.Info() reports the
            # current video mode (the window), not the desktop.
            self._desktop = detect_native()
            if self._desktop[0] <= 0 or self._desktop[1] <= 0:
                self._desktop = (self.config.base_width, self.config.base_height)

    def _live_screen(self) -> pygame.Surface:
        live = pygame.display.get_surface()
        return live if live is not None else self.screen

    def _apply(
        self, fullscreen: bool, window: Optional[Tuple[int, int]] = None, *, fit: bool = True
    ) -> pygame.Surface:
        if self.scaled:
            size = (self.config.base_width, self.config.base_height)
        elif fullscreen:
            size = self._desktop
        else:
            size = window or (self.preferences.window_width, self.preferences.window_height)
            if fit:
                size = fit_window(self.config, self._desktop, *size, self._window_sizes, self._chrome)
        self.config.set_resolution(size[0], size[1], fullscreen=fullscreen)
        flags = self.config.get_display_flags() | self._extra_flags
        screen = pygame.display.set_mode(size, flags)
        if not fullscreen and not self.scaled and screen.get_size() != size:
            # Leaving fullscreen, macOS hands back a maximised window
            # whatever size was asked for; asked again now that it is a
            # window, it gives the size (SP_Adventure, measured 2026-10-01).
            screen = pygame.display.set_mode(size, flags)
        self._screen = screen
        self.sync_to_granted()
        logger.info(
            "Display %s %dx%d (strategy %s)",
            "fullscreen" if fullscreen else "windowed",
            self.config.current_width,
            self.config.current_height,
            self.config.strategy.__name__,
        )
        return screen

    def sync_to_granted(self) -> bool:
        """Resync the config to the size the OS actually granted; True when it differed.

        ``LetterboxStrategy`` reads ``config.scale``, which only
        ``set_resolution`` recomputes, so a size change the config does
        not hear about (the OS shrinking a window, a drag) would draw at
        a stale scale: too large clips the top and bottom rows.
        """
        granted = self.screen.get_size()
        if granted == (self.config.current_width, self.config.current_height):
            return False
        logger.warning(
            "Requested %dx%d but the OS granted %dx%d; syncing",
            self.config.current_width,
            self.config.current_height,
            *granted,
        )
        self.config.set_resolution(granted[0], granted[1])
        if self.config.strategy is GrowStrategy:
            self.config.update_viewport_dimensions(*granted)
        return True

    def keep_window_readable(self) -> None:
        """Grow a window dragged below ``min_window`` back up to it.

        Re-opens the window rather than asking the OS for a minimum size
        (pygame's only call for that is deprecated). Does nothing in
        fullscreen, under Scaled, or on a desktop too small to show the
        minimum at all (the OS would refuse, the refusal would arrive as
        another resize, and this would be asked again for ever).
        """
        if self._min_window is None or self.config.fullscreen or self.scaled:
            return
        try:
            width, height = pygame.display.get_window_size()
        except pygame.error:
            width, height = self.screen.get_size()
        min_w, min_h = self._min_window
        fits_w, fits_h = largest_window(self.config, self._desktop, self._chrome)
        if (width >= min_w and height >= min_h) or fits_w < min_w or fits_h < min_h:
            return
        self._apply(False, (max(width, min_w), max(height, min_h)), fit=False)

    def _remember(self, *, fullscreen: bool, window: Optional[Tuple[int, int]] = None) -> None:
        current = self.preferences
        if window is None:
            window = (current.window_width, current.window_height)
        self._preferences = WindowPreferences(fullscreen=fullscreen, window_width=window[0], window_height=window[1])
        if self._on_changed is not None:
            self._on_changed(self._preferences)

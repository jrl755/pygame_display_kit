"""DisplaySession: startup policy, the one toggle, events and present.

``set_mode`` is patched with a fake that returns a surface of the
requested size (or a size the test chooses, to play the OS granting
something else), and ``detect_native`` is patched for the desktop size —
the dummy driver always reports 1024x768. Chrome adjustment is real, so
"usable height" below is the desktop height minus the platform's
allowance (100 px on macOS).
"""

from unittest.mock import patch

import pygame
import pytest

from pygame_display_kit import DisplaySession, LetterboxStrategy, ResolutionConfig, WindowPreferences
from pygame_display_kit.session import fit_window, largest_window, offered_window_sizes
from pygame_display_kit.strategies.grow import GrowStrategy
from pygame_display_kit.strategies.scaled import ScaledStrategy

BASE = (1920, 1080)
BIG = (2560, 1440)
LAPTOP = (1366, 768)


class FakeSetMode:
    """Records calls; returns a surface of the requested size unless told otherwise."""

    def __init__(self, grant=None):
        self.calls = []
        self.grant = grant  # callable(size, flags) -> granted size, or None

    def __call__(self, size, flags=0, *args, **kwargs):
        self.calls.append((tuple(size), flags))
        granted = self.grant(tuple(size), flags) if self.grant else tuple(size)
        return pygame.Surface(granted)

    @property
    def last(self):
        return self.calls[-1]


def _config(strategy=LetterboxStrategy, **kwargs) -> ResolutionConfig:
    return ResolutionConfig(base=BASE, strategy=strategy, auto_detect=False, **kwargs)


def _open(session, desktop, fake=None):
    fake = fake or FakeSetMode()
    with patch("pygame_display_kit.session.detect_native", return_value=desktop), patch(
        "pygame.display.set_mode", fake
    ):
        screen = session.open()
    return screen, fake


class TestWindowSizeRules:
    def test_largest_window_leaves_the_chrome_allowance(self):
        assert largest_window(_config(), BIG, 100) == (int(1340 * 16 / 9), 1340)

    def test_offered_sizes_are_the_presets_that_fit(self):
        assert offered_window_sizes(_config(), BIG) == [(1280, 720), (1600, 900), (1920, 1080)]

    def test_offered_sizes_fall_back_to_the_largest_window_on_a_laptop(self):
        sizes = offered_window_sizes(_config(), LAPTOP)
        assert sizes == [largest_window(_config(), LAPTOP, 100)]

    def test_fit_window_keeps_a_size_that_fits_and_replaces_one_that_does_not(self):
        assert fit_window(_config(), BIG, 1600, 900) == (1600, 900)
        assert fit_window(_config(), BIG, 3840, 2160) == (1920, 1080)
        assert fit_window(_config(), BIG, 0, 0) == (1920, 1080)


class TestOpenPolicy:
    def test_no_saved_choice_opens_fullscreen_at_the_desktop_size(self):
        session = DisplaySession(_config())
        _, fake = _open(session, BIG)
        size, flags = fake.last
        assert size == BIG and flags & pygame.FULLSCREEN and not flags & pygame.RESIZABLE
        assert (session.config.current_width, session.config.current_height) == BIG
        assert session.config.fullscreen is True

    def test_scaled_fullscreen_passes_the_base_size(self):
        session = DisplaySession(_config(ScaledStrategy))
        _, fake = _open(session, BIG)
        size, flags = fake.last
        assert size == BASE and flags & pygame.FULLSCREEN and flags & pygame.SCALED

    def test_saved_window_that_fits_opens_as_that_window(self):
        prefs = WindowPreferences(fullscreen=False, window_width=1600, window_height=900)
        session = DisplaySession(_config(), preferences=prefs)
        _, fake = _open(session, BIG)
        size, flags = fake.last
        assert size == (1600, 900) and not flags & pygame.FULLSCREEN and flags & pygame.RESIZABLE

    def test_saved_window_that_does_not_fit_opens_the_largest_offered(self):
        prefs = WindowPreferences(fullscreen=False, window_width=3840, window_height=2160)
        session = DisplaySession(_config(), preferences=prefs)
        _, fake = _open(session, BIG)
        assert fake.last[0] == (1920, 1080)

    def test_scaled_on_a_small_monitor_forces_fullscreen_over_a_saved_window(self):
        # The window would be the 1920x1080 design size on a 1366x768 panel.
        prefs = WindowPreferences(fullscreen=False, window_width=1280, window_height=720)
        session = DisplaySession(_config(ScaledStrategy), preferences=prefs)
        _, fake = _open(session, LAPTOP)
        size, flags = fake.last
        assert size == BASE and flags & pygame.FULLSCREEN and flags & pygame.SCALED

    def test_letterbox_on_a_small_monitor_keeps_a_fitted_window(self):
        # Letterbox scales the content, so a 1187x668 window is a usable one.
        prefs = WindowPreferences(fullscreen=False, window_width=1280, window_height=720)
        session = DisplaySession(_config(), preferences=prefs)
        _, fake = _open(session, LAPTOP)
        size, flags = fake.last
        assert size == largest_window(_config(), LAPTOP, 100) and not flags & pygame.FULLSCREEN

    def test_letterbox_forces_fullscreen_when_its_minimum_window_cannot_fit(self):
        # Death Knight clamps its config to 1280x720: no such window fits a laptop.
        prefs = WindowPreferences(fullscreen=False, window_width=1280, window_height=720)
        session = DisplaySession(_config(min_size=(1280, 720)), preferences=prefs, min_window=None)
        _, fake = _open(session, LAPTOP)
        size, flags = fake.last
        assert size == LAPTOP and flags & pygame.FULLSCREEN

    def test_scaled_window_is_always_the_base_size(self):
        prefs = WindowPreferences(fullscreen=False, window_width=1600, window_height=900)
        session = DisplaySession(_config(ScaledStrategy), preferences=prefs)
        _, fake = _open(session, BIG)
        size, flags = fake.last
        assert size == BASE and flags & pygame.SCALED and not flags & pygame.FULLSCREEN
        assert session.offered_window_sizes == []

    def test_resizable_override_and_extra_flags(self):
        session = DisplaySession(_config(), resizable=False, extra_flags=pygame.DOUBLEBUF)
        prefs_session = DisplaySession(
            _config(), preferences=WindowPreferences(False, 1280, 720), resizable=False
        )
        _, fake = _open(session, BIG)
        assert fake.last[1] & pygame.DOUBLEBUF
        _, fake = _open(prefs_session, BIG)
        assert not fake.last[1] & pygame.RESIZABLE

    def test_open_is_reentrant(self):
        session = DisplaySession(_config())
        _, fake = _open(session, BIG)
        _open(session, BIG, fake)
        assert [c[0] for c in fake.calls] == [BIG, BIG]


class TestToggle:
    def test_round_trip_restores_the_preferred_window_and_saves_each_step(self):
        saved = []
        session = DisplaySession(_config(), on_preferences_changed=saved.append)
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            session.toggle_fullscreen()
            assert fake.last[0] == (1920, 1080) and not fake.last[1] & pygame.FULLSCREEN
            assert session.config.fullscreen is False
            session.toggle_fullscreen()
            assert fake.last[0] == BIG and fake.last[1] & pygame.FULLSCREEN
        assert [p.fullscreen for p in saved] == [False, True]
        assert saved[-1] == WindowPreferences(fullscreen=True, window_width=0, window_height=0)

    def test_toggle_keeps_a_saved_window_size(self):
        saved = []
        prefs = WindowPreferences(fullscreen=True, window_width=1600, window_height=900)
        session = DisplaySession(_config(), preferences=prefs, on_preferences_changed=saved.append)
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            session.toggle_fullscreen()
        assert fake.last[0] == (1600, 900)
        assert saved == [WindowPreferences(False, 1600, 900)]

    def test_scaled_toggle_keeps_the_base_logical_size_both_ways(self):
        session = DisplaySession(_config(ScaledStrategy))
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            session.toggle_fullscreen()
            session.toggle_fullscreen()
        assert [c[0] for c in fake.calls] == [BASE, BASE, BASE]
        assert all(c[1] & pygame.SCALED for c in fake.calls)
        assert [bool(c[1] & pygame.FULLSCREEN) for c in fake.calls] == [True, False, True]

    def test_macos_maximised_window_is_asked_for_again(self):
        asks = []

        def grant(size, flags):
            asks.append(size)
            if not flags & pygame.FULLSCREEN and len(asks) == 2:
                return BIG  # the first windowed ask after fullscreen comes back maximised
            return size

        session = DisplaySession(_config())
        _, fake = _open(session, BIG, FakeSetMode(grant))
        with patch("pygame.display.set_mode", fake):
            screen = session.toggle_fullscreen()
        assert [c[0] for c in fake.calls] == [BIG, (1920, 1080), (1920, 1080)]
        assert screen.get_size() == (1920, 1080)

    def test_a_size_the_os_shrinks_is_synced_into_the_config(self):
        session = DisplaySession(_config(), preferences=WindowPreferences(False, 1920, 1080))
        _, fake = _open(session, BIG, FakeSetMode(lambda size, flags: (1920, 1000)))
        assert (session.config.current_width, session.config.current_height) == (1920, 1000)
        assert session.config.scale == pytest.approx(1000 / 1080)


class TestSetWindowSize:
    def test_letterbox_applies_fits_and_remembers(self):
        saved = []
        session = DisplaySession(_config(), on_preferences_changed=saved.append)
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            session.set_window_size(1280, 720)
            session.set_window_size(3840, 2160)
        assert [c[0] for c in fake.calls[1:]] == [(1280, 720), (1920, 1080)]
        assert saved[-1] == WindowPreferences(False, 1920, 1080)

    def test_scaled_refuses(self):
        session = DisplaySession(_config(ScaledStrategy))
        _open(session, BIG)
        with pytest.raises(NotImplementedError):
            session.set_window_size(1280, 720)


class TestEvents:
    def test_hotkey_toggles_and_is_consumed(self):
        session = DisplaySession(_config())
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            consumed = session.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
            other = session.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
        assert consumed is True and other is False
        assert session.config.fullscreen is False

    def test_hotkey_can_be_disabled(self):
        session = DisplaySession(_config(), hotkey=None)
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            assert session.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11)) is False
        assert len(fake.calls) == 1

    def test_resize_resyncs_and_grows_a_too_small_window(self):
        session = DisplaySession(_config(), preferences=WindowPreferences(False, 1280, 720))
        _, fake = _open(session, BIG)
        dragged = pygame.Surface((800, 450))  # what the drag left
        with patch("pygame.display.set_mode", fake), patch(
            "pygame.display.get_surface", return_value=dragged
        ), patch("pygame.display.get_window_size", return_value=(800, 450)):
            consumed = session.handle_event(pygame.event.Event(pygame.WINDOWRESIZED, x=800, y=450))
        assert consumed is True
        assert fake.last[0] == (960, 540)

    def test_resize_within_limits_only_resyncs(self):
        session = DisplaySession(_config(), preferences=WindowPreferences(False, 1280, 720))
        _, fake = _open(session, BIG)
        dragged = pygame.Surface((1400, 788))
        with patch("pygame.display.set_mode", fake), patch(
            "pygame.display.get_surface", return_value=dragged
        ), patch("pygame.display.get_window_size", return_value=(1400, 788)):
            session.handle_event(pygame.event.Event(pygame.WINDOWRESIZED, x=1400, y=788))
        assert len(fake.calls) == 1
        assert (session.config.current_width, session.config.current_height) == (1400, 788)

    def test_a_desktop_too_small_for_the_minimum_is_never_asked_for_it(self):
        session = DisplaySession(_config(), preferences=WindowPreferences(False, 800, 450))
        _, fake = _open(session, (900, 600))
        with patch("pygame.display.set_mode", fake), patch(
            "pygame.display.get_surface", return_value=pygame.Surface((400, 225))
        ), patch("pygame.display.get_window_size", return_value=(400, 225)):
            session.handle_event(pygame.event.Event(pygame.WINDOWRESIZED, x=400, y=225))
        assert len(fake.calls) == 1


class TestSetFullscreenAndExactSizes:
    def test_set_fullscreen_is_idempotent_and_remembers(self):
        saved = []
        session = DisplaySession(_config(), on_preferences_changed=saved.append)
        _, fake = _open(session, BIG)
        with patch("pygame.display.set_mode", fake):
            session.set_fullscreen(True)
            session.set_fullscreen(False)
            session.set_fullscreen(False)
        assert [c[0] for c in fake.calls] == [BIG, BIG, (1920, 1080), (1920, 1080)]
        assert [p.fullscreen for p in saved] == [True, False, False]

    def test_unfitted_size_is_asked_for_exactly_and_synced_to_the_grant(self):
        session = DisplaySession(_config())
        _, fake = _open(session, BIG, FakeSetMode(lambda size, flags: (size[0], min(size[1], 1290))))
        with patch("pygame.display.set_mode", fake):
            session.set_window_size(2560, 1440, fit=False)
        assert [c[0] for c in fake.calls[1:]] == [(2560, 1440), (2560, 1440)]  # asked twice, no more
        assert (session.config.current_width, session.config.current_height) == (2560, 1290)

    def test_a_known_desktop_skips_detection(self):
        session = DisplaySession(_config(), desktop=BIG)
        fake = FakeSetMode()
        with patch("pygame_display_kit.session.detect_native", side_effect=AssertionError("not called")), patch(
            "pygame.display.set_mode", fake
        ):
            session.set_fullscreen(True)
        assert fake.last[0] == BIG

    def test_present_with_an_explicit_screen_and_no_flip(self):
        session = DisplaySession(_config())
        _open(session, BIG)
        dragged = pygame.Surface((1280, 800))
        frame = pygame.Surface(BASE)
        frame.fill((40, 160, 240))
        with patch("pygame.display.flip") as flip:
            session.present(frame, screen=dragged, flip=False, smooth=False)
        flip.assert_not_called()
        assert (session.config.current_width, session.config.current_height) == (1280, 800)
        assert dragged.get_at((0, 40))[:3] == (40, 160, 240) and dragged.get_at((0, 0))[:3] == (0, 0, 0)

    def test_resize_is_ignored_under_scaled_and_in_fullscreen(self):
        scaled = DisplaySession(_config(ScaledStrategy))
        _open(scaled, BIG)
        assert scaled.handle_event(pygame.event.Event(pygame.WINDOWRESIZED, x=1, y=1)) is False
        full = DisplaySession(_config())
        _open(full, BIG)
        assert full.handle_event(pygame.event.Event(pygame.WINDOWRESIZED, x=1, y=1)) is False


class TestPresent:
    @staticmethod
    def _render():
        surface = pygame.Surface(BASE)
        surface.fill((10, 200, 30))
        return surface

    def test_letterbox_fills_a_same_aspect_screen(self):
        session = DisplaySession(_config())
        _open(session, BIG)
        session._screen = pygame.Surface(BIG)
        with patch("pygame.display.flip") as flip:
            session.present(self._render())
        flip.assert_called_once()
        screen = session.screen
        # Same aspect: 1920x1080 at 1.333 fills 2560x1440 edge to edge, no bars.
        for point in ((0, 0), (1280, 0), (2559, 1439), (1280, 720)):
            assert screen.get_at(point)[:3] == (10, 200, 30), point

    def test_letterbox_pillarboxes_a_wider_screen(self):
        session = DisplaySession(_config())
        _open(session, (3440, 1440))
        session._screen = pygame.Surface((3440, 1440))
        with patch("pygame.display.flip"):
            session.present(self._render())
        screen = session.screen
        assert screen.get_at((100, 720))[:3] == (0, 0, 0)
        assert screen.get_at((1720, 720))[:3] == (10, 200, 30)

    def test_scaled_only_flips(self):
        session = DisplaySession(_config(ScaledStrategy))
        _open(session, BIG)
        session._screen = pygame.Surface(BASE)
        with patch("pygame.display.flip") as flip, patch("pygame.transform.smoothscale") as smooth, patch(
            "pygame.transform.scale"
        ) as scale:
            session.present()
            session.present(self._render())
        assert flip.call_count == 2
        smooth.assert_not_called()
        scale.assert_not_called()
        assert session.screen.get_at((5, 5))[:3] == (10, 200, 30)

    def test_grow_blits_at_the_origin(self):
        session = DisplaySession(_config(GrowStrategy))
        _open(session, BIG)
        session._screen = pygame.Surface(BIG)
        frame = pygame.Surface(BIG)
        frame.fill((1, 2, 3))
        with patch("pygame.display.flip"):
            session.present(frame)
        assert session.screen.get_at((0, 0))[:3] == (1, 2, 3)

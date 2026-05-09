"""Unit tests for ``should_auto_fullscreen``.

The rule (verbatim port from Skodrak's display_manager) is:

    monitor_width <= design_width OR monitor_height <= design_height

Either dimension at-or-below design forces fullscreen — even an
exact match counts because OS chrome (title bar, taskbar) eats pixels
from windowed mode.
"""

from pygame_display_kit import should_auto_fullscreen


class TestExactMatchForcesFullscreen:
    """At exact-match resolution, windowed mode is broken — force fullscreen."""

    def test_exact_match_returns_true(self):
        """1920×1080 monitor on 1920×1080 design → fullscreen."""
        assert should_auto_fullscreen(1920, 1080, 1920, 1080) is True


class TestUndersizedForcesFullscreen:
    """Smaller-than-design monitors must use fullscreen."""

    def test_smaller_width_returns_true(self):
        assert should_auto_fullscreen(1280, 1080, 1920, 1080) is True

    def test_smaller_height_returns_true(self):
        assert should_auto_fullscreen(1920, 720, 1920, 1080) is True

    def test_both_smaller_returns_true(self):
        assert should_auto_fullscreen(1280, 720, 1920, 1080) is True


class TestPartialMatchForcesFullscreen:
    """Either-axis at-or-below design is enough — even if the other is huge."""

    def test_ultrawide_with_design_height_returns_true(self):
        """2560×1080 (21:9 ultrawide on 1080p height) → fullscreen.

        Width is way above design but height is exact-match — that
        means the height budget is gone, so windowed is broken.
        """
        assert should_auto_fullscreen(2560, 1080, 1920, 1080) is True

    def test_design_width_with_taller_returns_true(self):
        """1920×1440 (4:3-ish on design width) → fullscreen.

        Width exact-match, height has headroom — but the width budget
        is gone, so windowed mode is broken.
        """
        assert should_auto_fullscreen(1920, 1440, 1920, 1080) is True


class TestLargerMonitorAllowsWindowed:
    """When BOTH axes exceed design, windowed mode is viable."""

    def test_both_larger_returns_false(self):
        """2560×1440 monitor on 1920×1080 design → windowed OK."""
        assert should_auto_fullscreen(2560, 1440, 1920, 1080) is False

    def test_4k_returns_false(self):
        """3840×2160 monitor on 1920×1080 design → windowed OK."""
        assert should_auto_fullscreen(3840, 2160, 1920, 1080) is False

    def test_marginally_larger_returns_false(self):
        """1921×1081 (1px more on each axis) → windowed OK by the rule."""
        assert should_auto_fullscreen(1921, 1081, 1920, 1080) is False


class TestAlternateDesignDimensions:
    """The rule is parametric — works for non-1920×1080 designs."""

    def test_smaller_design_resolution(self):
        """1366×768 design on 1920×1080 monitor → windowed OK."""
        assert should_auto_fullscreen(1920, 1080, 1366, 768) is False

    def test_larger_design_resolution(self):
        """1366×768 monitor on 1920×1080 design → fullscreen."""
        assert should_auto_fullscreen(1366, 768, 1920, 1080) is True

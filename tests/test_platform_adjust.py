"""Unit tests for platform-aware native resolution adjustment.

Each platform reserves a different amount of screen for system chrome
(macOS Dock + menu bar, Windows taskbar, Linux panel). These tests
mock ``platform.system`` to verify each branch produces the expected
adjustments without depending on the actual machine's OS.
"""

from unittest.mock import patch

from pygame_display_kit import adjust_for_platform


class TestMacOSAdjustment:
    """macOS subtracts ~100 px for menu bar + Dock."""

    def test_macos_subtracts_100px_height(self):
        with patch("platform.system", return_value="Darwin"):
            w, h = adjust_for_platform(1920, 1080, base_aspect=16/9)
        # 1080 - 100 = 980 height; width = 980 * 16/9 = 1742
        assert h == 980
        assert w == int(980 * 16 / 9)

    def test_macos_preserves_aspect_ratio(self):
        with patch("platform.system", return_value="Darwin"):
            w, h = adjust_for_platform(2560, 1440, base_aspect=16/9)
        # h = 1440 - 100 = 1340; w = 1340 * 16/9 = 2382 (preserves aspect)
        assert h == 1340
        assert abs((w / h) - (16 / 9)) < 0.01


class TestWindowsAdjustment:
    """Windows subtracts 5% of height for taskbar."""

    def test_windows_subtracts_5_percent_height(self):
        with patch("platform.system", return_value="Windows"):
            w, h = adjust_for_platform(1920, 1080, base_aspect=16/9)
        # 1080 - 54 = 1026 height (5% of 1080 = 54)
        assert h == 1026
        assert w == int(1026 * 16 / 9)

    def test_windows_ultrawide_falls_back_to_width_first(self):
        """On a 32:9 ultrawide where height × aspect would exceed
        actual width, the function falls back to width-first fitting.
        """
        with patch("platform.system", return_value="Windows"):
            # 5120×1440 super-ultrawide, base_aspect = 16:9 (1.778).
            # naive: height = 1440-72 = 1368, width = 1368*1.778 = 2432.
            # 2432 < 5120, so naive case actually works here. Let me
            # use a case where naive fails: 1920×1080 with base_aspect 32:9.
            w, h = adjust_for_platform(1920, 1080, base_aspect=32/9)
        # naive: h = 1026, w = 1026 * 32/9 = 3648 → exceeds 1920.
        # Refit: w = 1920, h = 1920 / (32/9) = 540
        assert w == 1920
        assert h == 540


class TestLinuxAdjustment:
    """Linux subtracts 5% of height for panel."""

    def test_linux_subtracts_5_percent_height(self):
        with patch("platform.system", return_value="Linux"):
            w, h = adjust_for_platform(1920, 1080, base_aspect=16/9)
        # 1080 * 0.95 = 1026
        assert h == int(1080 * 0.95)
        assert w == int(h * 16 / 9)


class TestUnknownPlatformFallsBackToLinux:
    """Unknown ``platform.system()`` returns use the Linux 5% heuristic."""

    def test_freebsd_treated_as_linux_path(self):
        with patch("platform.system", return_value="FreeBSD"):
            w, h = adjust_for_platform(1920, 1080, base_aspect=16/9)
        # Same as Linux: 1080 * 0.95
        assert h == int(1080 * 0.95)

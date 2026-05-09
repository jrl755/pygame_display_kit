"""Unit tests for detect_native().

The dummy SDL driver returns synthetic 1024×768 for
``pygame.display.Info().current_w/.current_h`` regardless of the actual
monitor — verified during library design. These tests use
``unittest.mock.patch`` to verify detection logic against arbitrary
monitor sizes rather than relying on the dummy driver returning real
native dims.
"""

from unittest.mock import MagicMock, patch

import pygame  # noqa: F401  (initializes via conftest)

from pygame_display_kit.detection import detect_native


class TestDetectNative:
    """``detect_native()`` reads pygame.display.Info().current_w/.current_h."""

    def test_returns_pygame_info_dims(self):
        """Mocking pygame.display.Info verifies the wrapper plumbing."""
        mock_info = MagicMock(current_w=2560, current_h=1440)
        with patch("pygame.display.Info", return_value=mock_info):
            assert detect_native() == (2560, 1440)

    def test_returns_4k_for_4k_monitor(self):
        mock_info = MagicMock(current_w=3840, current_h=2160)
        with patch("pygame.display.Info", return_value=mock_info):
            assert detect_native() == (3840, 2160)

    def test_returns_laptop_dims_for_laptop(self):
        """1366×768 monitor: detection must not synthesize values."""
        mock_info = MagicMock(current_w=1366, current_h=768)
        with patch("pygame.display.Info", return_value=mock_info):
            assert detect_native() == (1366, 768)

    def test_returns_portrait_dims_for_rotated_display(self):
        """Rotated displays are reported by pygame as their physical orientation."""
        mock_info = MagicMock(current_w=1080, current_h=1920)
        with patch("pygame.display.Info", return_value=mock_info):
            assert detect_native() == (1080, 1920)

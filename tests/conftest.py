"""Headless pygame setup for the library test suite.

Uses ``SDL_VIDEODRIVER=dummy`` (no windowing system needed) rather than
``pygame.HIDDEN`` (requires xvfb on Linux CI without a display). The
trade-off: tests cannot visually inspect output, only verify dimensions
and scale math — fine for unit tests of viewport / scaling logic.

Important caveat (verified during library design): the dummy driver
returns synthetic 1024×768 for ``pygame.display.Info().current_w/.current_h``
regardless of the actual monitor. Tests that need to verify
``detect_native()`` for arbitrary monitor sizes MUST mock
``pygame.display.Info`` directly rather than rely on the dummy driver.
"""

import os
import sys

import pytest

# Set the dummy driver before importing pygame anywhere — pygame reads
# the env var during ``pygame.init()`` and caches the choice.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402  (intentionally after env-var set)


@pytest.fixture(autouse=True, scope="session")
def setup_pygame():
    """Initialize pygame once per test session.

    Auto-applied to every test. Quits pygame at session teardown to
    free SDL resources (matters when running pytest in a long-lived
    pytest-xdist worker).
    """
    pygame.init()
    yield
    pygame.quit()

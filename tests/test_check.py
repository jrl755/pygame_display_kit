"""The display check writes a screenshot of the granted surface and reports the facts."""

import json

import pygame
import pytest

from pygame_display_kit import DisplaySession, LetterboxStrategy, ResolutionConfig
from pygame_display_kit.check import BORDER, main, run_display_check
from pygame_display_kit.strategies.scaled import ScaledStrategy

# The dummy driver's desktop is 1024x768: with nothing saved each session
# opens fullscreen there — a 4:3 panel for a 16:9 game, which is exactly the
# letterbox case worth checking.


@pytest.mark.parametrize("strategy", [LetterboxStrategy, ScaledStrategy], ids=["letterbox", "scaled"])
def test_screenshot_is_the_granted_surface_with_the_border_at_the_viewport_corners(tmp_path, strategy, capsys):
    config = ResolutionConfig(base=(1920, 1080), strategy=strategy, auto_detect=False)
    session = DisplaySession(config, preferences=None)
    out = tmp_path / "check.png"
    facts = run_display_check(session, out, smallest_text_px=20, label="test")

    assert out.exists()
    shot = pygame.image.load(str(out))
    assert shot.get_bitsize() == 24, "the screenshot must carry no alpha channel"
    assert list(shot.get_size()) == facts["granted"]
    assert facts["corners_ok"] is True
    assert facts["fullscreen"] is True  # nothing saved: fullscreen
    assert facts["strategy"] == strategy.__name__
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["granted"] == facts["granted"] and printed["corners_ok"] is True
    left, top, width, height = facts["viewport"]
    assert shot.get_at((left, top))[:3] == BORDER
    assert shot.get_at((left + width - 1, top + height - 1))[:3] == BORDER
    if strategy is LetterboxStrategy:
        assert top > 0  # 16:9 inside 4:3: bars above and below
        assert shot.get_at((0, 0))[:3] == (0, 0, 0)


def test_cli_runs_headless(tmp_path, capsys):
    out = tmp_path / "cli.png"
    assert main(["--strategy", "letterbox", "--out", str(out), "--seconds", "0", "--label", "cli"]) == 0
    assert out.exists()
    facts = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert facts["label"] == "cli" and facts["corners_ok"] is True
    pygame.init()  # main() quit pygame; the session fixture expects it initialised

"""Display check — draw a calibration frame, save a screenshot, print the facts.

The only way to know what a real panel does with a game's display is to
open it there. Each game exposes a ``--display-check`` flag that builds
its own session and calls :func:`run_display_check`; the kit's
``python -m pygame_display_kit.check`` does the same with a bare
config. The frame carries a 1 px border, corner markers with their
design coordinates, a centre cross, a 16:9 frame and three text sizes,
and a caption with the design, requested and granted sizes. The JSON
line it prints and the ``corners_ok`` flag in it (border pixels present
at all four viewport corners of the *granted* surface) are the evidence
a screen matrix is built from.
"""

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import pygame

from .config import ResolutionConfig
from .preferences import WindowPreferences
from .session import DisplaySession
from .strategies.grow import GrowStrategy
from .strategies.letterbox import LetterboxStrategy
from .strategies.scaled import ScaledStrategy

BORDER = (255, 255, 0)
BACKGROUND = (24, 32, 48)
TEXT = (240, 240, 240)
STRATEGIES = {"scaled": ScaledStrategy, "letterbox": LetterboxStrategy, "grow": GrowStrategy}


def draw_calibration_frame(surface: pygame.Surface, caption: str, smallest_text_px: int) -> None:
    """Draw the calibration content onto *surface* (the design-sized render surface)."""
    width, height = surface.get_size()
    surface.fill(BACKGROUND)
    pygame.draw.line(surface, (90, 90, 120), (width // 2, 0), (width // 2, height))
    pygame.draw.line(surface, (90, 90, 120), (0, height // 2), (width, height // 2))
    frame_h = int(width * 9 / 16)
    pygame.draw.rect(surface, (120, 200, 255), pygame.Rect(0, (height - frame_h) // 2, width, frame_h), 1)
    # The border goes on last: it is what the corner check samples, and on a
    # 16:9 design the 16:9 frame above coincides with it.
    pygame.draw.rect(surface, BORDER, pygame.Rect(0, 0, width, height), 1)
    small = pygame.font.Font(None, smallest_text_px)
    for x, y, label in (
        (4, 4, "(0,0)"),
        (width - 4, 4, f"({width},0)"),
        (4, height - 4, f"(0,{height})"),
        (width - 4, height - 4, f"({width},{height})"),
    ):
        pygame.draw.rect(surface, BORDER, pygame.Rect(min(x, width - 12), min(y, height - 12), 8, 8))
        text = small.render(label, True, TEXT)
        surface.blit(text, (min(x + 10, width - text.get_width() - 4), min(y + 10, height - text.get_height() - 4)))
    y = height // 4
    for factor in (1, 2, 4):
        font = pygame.font.Font(None, smallest_text_px * factor)
        text = font.render(f"text {smallest_text_px * factor}px: The quick brown fox", True, TEXT)
        surface.blit(text, (width // 8, y))
        y += text.get_height() + 8
    cap = pygame.font.Font(None, max(smallest_text_px, 28)).render(caption, True, TEXT)
    surface.blit(cap, (width // 8, height * 3 // 4))


def _corners_ok(screen: pygame.Surface, config: ResolutionConfig) -> Tuple[bool, Tuple[int, int, int, int]]:
    """True when the border colour is present at all four viewport corners of the granted surface."""
    size = screen.get_size()
    if config.strategy is ScaledStrategy:
        offset, target = (0, 0), size
    else:
        offset = config.strategy.compute_viewport_offset(config, size)
        target = config.strategy.compute_viewport_scale(config, size)
    left, top = offset
    right, bottom = left + target[0] - 1, top + target[1] - 1
    ok = all(
        screen.get_at((x, y))[:3] == BORDER
        for x, y in ((left, top), (right, top), (left, bottom), (right, bottom))
    )
    return ok, (left, top, target[0], target[1])


def run_display_check(
    session: DisplaySession,
    out_path: Path,
    *,
    smallest_text_px: int = 24,
    seconds: float = 0.0,
    label: str = "",
) -> dict:
    """Open *session*, draw and present the frame, save a screenshot, return the facts.

    Prints the returned dict as one JSON line. *seconds* > 0 keeps the
    frame on screen for a human look.
    """
    screen = session.open()
    config = session.config
    render = config.strategy.create_render_surface(config)
    requested = (config.base_width, config.base_height) if session.scaled else (config.current_width, config.current_height)
    caption = (
        f"{label} design {config.base_width}x{config.base_height} | requested {requested[0]}x{requested[1]} | "
        f"granted {screen.get_width()}x{screen.get_height()} | window {pygame.display.get_window_size()} | "
        f"{config.strategy.__name__} {'fullscreen' if config.fullscreen else 'windowed'} | {platform.system()}"
    )
    draw_calibration_frame(render, caption, smallest_text_px)
    if session.scaled:
        screen.blit(render, (0, 0))
        pygame.display.flip()
    else:
        session.present(render, smooth=False)
    ok, viewport = _corners_ok(session.screen, config)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(session.screen, str(out_path))
    facts = {
        "label": label,
        "platform": platform.system(),
        "strategy": config.strategy.__name__,
        "fullscreen": config.fullscreen,
        "design": [config.base_width, config.base_height],
        "desktop": list(session.desktop),
        "requested": list(requested),
        "granted": list(session.screen.get_size()),
        "window": list(pygame.display.get_window_size()),
        "viewport": list(viewport),
        "corners_ok": ok,
        "screenshot": str(out_path),
    }
    print(json.dumps(facts))
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                deadline = 0
        pygame.time.wait(50)
    return facts


def _parse_size(text: str) -> Tuple[int, int]:
    w, _, h = text.lower().partition("x")
    return int(w), int(h)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Open a calibration frame and record what the display granted.")
    parser.add_argument("--strategy", choices=sorted(STRATEGIES), default="scaled")
    parser.add_argument("--base", type=_parse_size, default=(1920, 1080), help="design size, e.g. 1920x1080")
    parser.add_argument("--windowed", type=_parse_size, default=None, help="open a window of this size instead of fullscreen")
    parser.add_argument("--out", type=Path, default=Path("display_check.png"))
    parser.add_argument("--seconds", type=float, default=3.0, help="how long to show the frame")
    parser.add_argument("--text-px", type=int, default=24, help="smallest text size the game uses")
    parser.add_argument("--label", default="")
    args = parser.parse_args(argv)
    pygame.init()
    config = ResolutionConfig(base=args.base, strategy=STRATEGIES[args.strategy], auto_detect=True)
    prefs = None
    if args.windowed is not None:
        prefs = WindowPreferences(fullscreen=False, window_width=args.windowed[0], window_height=args.windowed[1])
    session = DisplaySession(config, preferences=prefs)
    run_display_check(session, args.out, smallest_text_px=args.text_px, seconds=args.seconds, label=args.label)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())

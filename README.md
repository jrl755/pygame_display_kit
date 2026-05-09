# pygame_display_kit

Resolution and scaling utilities for pygame-ce games. Extracted from
[Broken Moon Redux](https://github.com/jrl755/Broken_Moon),
[Skodrak](https://github.com/jrl755/Skodrak), and
[Death_Knight_Arena](https://github.com/jrl755/Death_Knight_Arena) — three
games that each handled the same problem differently. This library
absorbs the best patterns from each into a single configurable shape.

## Status

**v0.1.0** — initial release. `GROW` viewport strategy only. Subsequent
versions will add `LETTERBOX` (v0.2) and `SCALED` (v0.3) strategies +
DRS controller (v0.4) + per-element scale helpers (v0.5).

## Install

```bash
pip install git+https://github.com/jrl755/pygame_display_kit.git@v0.1.0
```

## Quick start

```python
from pygame_display_kit import ResolutionConfig
from pygame_display_kit.strategies.grow import GrowStrategy

config = ResolutionConfig(
    base=(1600, 1200),       # design resolution
    strategy=GrowStrategy,   # widescreen viewport-grow (BM-style)
    auto_detect=True,        # detect native via pygame.display.Info()
    fullscreen=False,
)
```

## Strategies

- `GrowStrategy` (v0.1): viewport widens to match display aspect — more
  game world visible on widescreen monitors. No letterboxing for matching
  aspects. *Strategy used by Broken Moon Redux.*
- `LetterboxStrategy` (planned v0.2): uniform aspect-preserving scale
  with centered letterbox bars on aspect mismatch. Cross-platform aware
  (macOS Dock, Windows taskbar, Linux panel offsets). *Strategy used by
  Death_Knight_Arena.*
- `ScaledStrategy` (planned v0.3): wraps `pygame.SCALED` and lets SDL
  handle scaling. Simplest implementation; trusts the platform. *Strategy
  used by Skodrak.*

## License

MIT — see [LICENSE](LICENSE).

# Display matrix — what each game's `--display-check` granted

Evidence for the display session plan, phase 8. Each cell is one run of the
game's `--display-check` flag on real hardware: the JSON line it prints plus
the screenshot it writes to `<game>/reports/display_check_<platform>.png`
(untracked). `corners_ok` means the calibration border was found at all
four corners of the viewport on the surface the OS actually granted — no
clipping, no wrong logical size. Cells that were not run are marked, not
inferred.

## 2026-10-19 — macOS, desktop 2560×1440 (external monitor), pygame-ce 2.5.8

| Game | Strategy | Mode | Requested | Granted | Window | Viewport | corners_ok |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Skodrak | Scaled | fullscreen | 1920×1080 | 1920×1080 (logical) | 2560×1440 | 0,0 1920×1080 | yes |
| Death Knight | Letterbox | fullscreen | 2560×1440 | 2560×1440 | 2560×1440 | 0,0 2560×1440 | yes |
| Broken Moon | Scaled | fullscreen | 1920×1080 | 1920×1080 (logical) | 2560×1440 | 0,0 1920×1080 | yes |
| SP_Adventure | Letterbox | fullscreen | 2560×1440 | 2560×1440 | 2560×1440 | 0,0 2560×1440 | yes |

All four opened fullscreen with nothing saved (the family default) at the
desktop's own resolution, no monitor mode switch. Under Scaled the granted
surface is the 1920×1080 logical one that SDL scales to the 2560×1440
window; the screenshot is that logical surface (pygame cannot capture the
physical frame), so Scaled rows prove the logical contract, not SDL's
scaling. Letterbox rows are the physical frame: the 16:9 design filled the
16:9 panel edge to edge.

Raw facts (one line per run):

```text
{"label": "Skodrak", "platform": "Darwin", "strategy": "ScaledStrategy", "fullscreen": true, "design": [1920, 1080], "desktop": [2560, 1440], "requested": [1920, 1080], "granted": [1920, 1080], "window": [2560, 1440], "viewport": [0, 0, 1920, 1080], "corners_ok": true}
{"label": "Death_Knight", "platform": "Darwin", "strategy": "LetterboxStrategy", "fullscreen": true, "design": [1920, 1080], "desktop": [2560, 1440], "requested": [2560, 1440], "granted": [2560, 1440], "window": [2560, 1440], "viewport": [0, 0, 2560, 1440], "corners_ok": true}
{"label": "Broken_Moon", "platform": "Darwin", "strategy": "ScaledStrategy", "fullscreen": true, "design": [1920, 1080], "desktop": [2560, 1440], "requested": [1920, 1080], "granted": [1920, 1080], "window": [2560, 1440], "viewport": [0, 0, 1920, 1080], "corners_ok": true}
{"label": "SP_Adventure", "platform": "Darwin", "strategy": "LetterboxStrategy", "fullscreen": true, "design": [1920, 1080], "desktop": [2560, 1440], "requested": [2560, 1440], "granted": [2560, 1440], "window": [2560, 1440], "viewport": [0, 0, 2560, 1440], "corners_ok": true}
```

## Not yet run

| Screen | Status |
| --- | --- |
| MacBook panel (Retina, laptop size) | not run — needs the laptop undocked |
| External 1080p | not run |
| 4K | not run |
| Ultrawide 21:9 | not run |
| Windows machine | not run |
| Sub-1080p panel (the auto-fullscreen rule on hardware) | not run — cannot be simulated: under SCALED an oversized window is not shrunk (measured 2026-10-19) |
| F11 once and relaunch in the saved mode, on hardware | not run on hardware; pinned by each game's tests through a fake `set_mode` |

To add a row: run the game with `--display-check` on that screen, paste
the JSON line, and keep the screenshot.

## Found by running the checks

- macOS desktop-fullscreen display surfaces carry an alpha channel that
  opaque blits leave at 0; the first screenshots read as transparent (text
  as white blocks in a viewer). The check now saves RGB only.
- Broken Moon's first run opened windowed: a test in its suite had written
  the player's real `display_preferences.json` through the session's
  persist callback. Both Broken Moon and Death Knight now route that file
  into `tmp_path` for every test (autouse fixtures), and the stray file
  was removed.

# Display session: fullscreen and screen sizes for all four games

**Status:** v3 — EXECUTED 2026-10-19, phases 1–8 (phase 8 on one screen so far). Branches, unmerged: kit `feat/display-session` (tag `v0.5.0`, local), Skodrak `fix/options-fullscreen-toggle`, Broken Moon `fix/splash-fullscreen-keeps-scaled` → `feat/display-session`, SP_Adventure `feat/display-session`, Death Knight `feat/display-session`. See "Execution notes" at the end.

## v2 → v3 audit findings

| Question investigated | Finding (command / source) | Plan impact |
| --- | --- | --- |
| Can a game choose the physical window size under `pygame.SCALED`? | Run on the real 2560×1440 display (`scratchpad/scaled_window_experiment.py`, pygame-ce 2.5.8): `set_mode((1920,1080), SCALED)` → logical (1920, 1080), window (1920, 1080); `set_mode((1600,900), SCALED)` → logical **and** window (1600, 900); `Window.size = (1280, 720)` left the window at (1920, 1080); `set_mode((3000,1688), SCALED)` on a 2560×1440 desktop → window reported (3000, 1688), **not shrunk to fit**; `SCALED | FULLSCREEN` → logical (1920, 1080), window (2560, 1440). | **Under SCALED the window size is the logical size.** A "window size" preference would change the design resolution, so for Scaled games `WindowPreferences` carries the fullscreen flag only, windowed is always the base-size window, and the small-monitor auto-fullscreen rule is load-bearing (SCALED does not clamp an oversized window). Phases 2, 5, 6, 8 rewritten below. |
| Does the dummy driver report the flags the phase 1 tests need? | `SDL_VIDEODRIVER=dummy`: after `set_mode(..., SCALED | FULLSCREEN)`, `get_flags() & FULLSCREEN` → True, `get_flags() & SCALED` → **False** (also False on the real display: SCALED is never reported on the surface). Skodrak's `test_fullscreen_toggle.py:60-105` therefore patches `pygame.display.set_mode` and asserts on its call args. | Phase 1 acceptance: FULLSCREEN agreement may use `get_flags()`; SCALED preservation is asserted on the `set_mode` call args, following the existing tests. |
| Do SP's other settings screens persist a default `WindowPreferences`? | `grep -rn "save_settings(" sp_adventure` → audio (`:61`), accessibility (`:72`), controls (`:123`) all pass the `window` value they got from `load_settings()` (e.g. `audio_options_state.py:60-61`), which is `None` until the display screen saves one. | The default flip in phase 4 is safe; assumption validated. |
| Direction of the kit toggle in Broken Moon's standalone path | `FullscreenManager.toggle()` reads `config.fullscreen` to decide direction (`fullscreen.py:70`); the standalone branch currently flips `self.fullscreen` and calls `DisplayConfig.set_resolution(..., self.fullscreen)` *before* `set_mode`. | Phase 1 (Broken Moon): leave `_config.fullscreen` untouched before `toggle()`, read `self.fullscreen` back from `DisplayConfig.FULLSCREEN` after. Stated explicitly. |

## v1 → v2 audit findings

| Question investigated | Finding (command / source) | Plan impact |
| --- | --- | --- |
| Does the kit recompute scale after a toggle, or must consumers call `update_viewport_dimensions`? | `ResolutionConfig.set_resolution` (`config.py:134-186`) sets `current_*` **and** `scale_x / scale_y / scale`; `update_viewport_dimensions` only drives the strategy (needed for Grow's viewport size; Letterbox and Scaled leave viewport = base). DK calls it once at init (`resolution.py:113`), SP never, and both are correct. | No Death Knight defect to fix in phase 1. Phase 2: the session calls `update_viewport_dimensions` only under Grow. |
| Which Skodrak tests pin the startup policy that Decision 1 changes? | `grep -n "def test" tests/unit/test_fullscreen_toggle.py` → three tests pinning SCALED preservation and base-size fullscreen (unchanged by the plan). `test_bug_fixes.py:101 test_fullscreen_default_is_off` and `test_settings_manager_roundtrip.py:107` pin `UserSettings.fullscreen` default False; nothing pins the force-windowed block at `main.py:126-129`. | Phase 5 lists the two default pins to change; the v1 "grep at execution" placeholder is replaced. |
| How many live `set_mode` calls does Broken Moon have? | `grep -rn "set_mode(" src/broken_moon --include='*.py'` → 8 lines: 6 live calls (`settings_menu.py:476, :484`; `app_shell.py:78, :209`; `display_manager.py:105` headless, `:140`) + 2 comments (`settings_menu.py:455`, `sprite_sheet_loader.py:188`). | Phase 6 target list corrected (v1 said four). |
| Which Broken Moon test pins "windowed on large monitors"? | `tests/regression/test_auto_fullscreen_at_startup.py:69 test_1440p_display_stays_windowed` (asserts only the heuristic returns False; also `:59` carries a stale "1600x1200_design" name). | Phase 6: the heuristic test stays valid (the rule is unchanged); the Decision 1 behaviour gets a new test against `session.open()`. Rename the stale test. |
| Is F11 free in Broken Moon? | `input_manager._handle_debug_keys` binds F3 and F9 only. | Phase 6 uses F11 unchanged. |
| How many SP tests depend on `display.py` names? | 80 test files call `init_display` (same signature kept); five import helpers: `test_display.py`, `test_display_options_state.py`, `test_init_display_with_preferences.py`, `test_set_display_mode_resync.py`, `test_text_scale.py` (`render_scaled`, `set_display_mode`, `sync_config_to_window`, `window_sizes`, `keep_window_readable`). | Phase 4 keeps `display.py` as a thin façade with those names re-exported; v1's "seven other test files" corrected. `prefer_window` has one caller (`main.py:203`). |
| `session.reopen()` used in phase 6 without being defined | — | Phase 2 API: `open()` is re-entrant (re-applies the current preference); `reopen` dropped. |
| Callers of `SettingsManager.toggle_fullscreen` | `main.py:461` and `options_state.py:185` only (`grep -rn "toggle_fullscreen()" skodrak`). | Phase 1 removes the Options call; phase 5 deletes the method. Safe. |
| `WINDOWRESIZED` availability | pygame-ce ≥ 2.5 in all four `pyproject.toml`s; SP already handles it (`main.py:259`). | None. |

**Source:** [Skodrak/docs/analysis/display_scaling_comparison_2026-10-19.md](../../../Skodrak/docs/analysis/display_scaling_comparison_2026-10-19.md).
**Goal (user, 2026-10-19):** every game can go fullscreen and works on screens from laptops to large monitors.
**Lives here** because five of the eight phases change `pygame_display_kit`; the per-game phases each land in their own repository and bump the kit pin.

## Decisions (user, 2026-10-19)

1. **First launch on a monitor larger than the design opens fullscreen** (SP_Adventure's behaviour becomes the family's). Small monitors auto-fullscreen as today. The player's later choice is saved and honoured.
2. **F11 toggles fullscreen in all four games**, in addition to each game's menu entry.
3. **The kit defines the saved preference** (`WindowPreferences`: fullscreen flag + windowed size) **and each game supplies the store** (Skodrak `SettingsManager`, SP `settings_io`, new entries for Death Knight and Broken Moon).
4. **Skodrak's DRS is out of scope** (measured 2026-10-19: ≤ 1.3 ms/frame saving at 0.5× against a 3.6 ms draw; decide after a run on the slowest target laptop).

## What the code does today (verified 2026-10-19; file:line)

- Kit v0.4.0 (`pygame_display_kit/`, tag `v0.4.0`, 118 tests): `ResolutionConfig` (base, strategy, native detection, `set_resolution`, `get_display_flags` = RESIZABLE-when-windowed | FULLSCREEN | SCALED-for-ScaledStrategy; `resizable` and `vsync` default True and no game sets them), `FullscreenManager.toggle()` (stashes windowed dims, SCALED-aware size swap, resyncs `current_*`), strategies Grow / Letterbox / Scaled, `should_auto_fullscreen`, `adjust_for_platform`, `select_best_resolution`, per-element helpers. No persistence, no startup policy, no present helper, no event handling, no CLI. Packaging: `[tool.setuptools.packages.find] include = ["pygame_display_kit*"]`; tests run headless on the dummy driver (synthetic 1024×768 native).
- **Skodrak** `skodrak/main.py:95-157`: detect → chrome-adjust → `should_auto_fullscreen` → **forces `fullscreen = False` otherwise** (`:126-129`) → `set_mode((1920,1080), DOUBLEBUF|SCALED[|FULLSCREEN])` → builds `ResolutionConfig(ScaledStrategy, auto_detect=False)` + `FullscreenManager`. F11 `:326-328` → `_toggle_fullscreen` `:444-468` (kit toggle, `SettingsManager.toggle_fullscreen`, `DisplayManager.set_screen`, DRS reset, font cache reset). Options menu `states/options_state.py:165-186`: raw `set_mode(..., DOUBLEBUF|SCALED[|FULLSCREEN])` + `SettingsManager.toggle_fullscreen` — never touches the kit config. `UserSettings.fullscreen` persisted (`settings_manager.py:27`). Tests: `tests/unit/test_fullscreen_toggle.py`, `tests/unit/test_bug_fixes.py`, `tests/integration/test_settings_manager_roundtrip.py`. No argv parsing in `main.py` / `__main__.py`.
- **Death Knight** `dk_modules/core/resolution.py` (facade over kit Letterbox config, 205 `resolution_config.*` read sites in `dk_modules/`; `update_viewport_dimensions` once at `:113`, sufficient because `set_resolution` recomputes scale), `dk_modules/game/renderer.py:38-59` (`set_mode(current, FULLSCREEN|0)`; kit `FullscreenManager`; "session-local, no persistence"), `Death_Knight.py:258-270` (auto-fullscreen on small monitors, else windowed at the chrome-adjusted desktop size), `event_handler.py:99-100` (F11). `ConfigManager` persists only `controls_config.json` under `ResourceManager.get_user_data_dir()`. Test: `tests/regression/test_fullscreen_toggle.py`. No argv parsing.
- **Broken Moon** `src/broken_moon/config/display.py:103-108` (module singleton kit config, Scaled, `auto_detect=True`), `core/game/display_manager.py:912-935` (`set_mode(base, add_scaled_flag(flags))`, `present()` = flip, `toggle_fullscreen` via kit `:972-986`, `handle_window_resize` **has no caller**), `ui/settings_menu.py:441-490` (in-game toggle via `DisplayManager`; **standalone path `:472-484` calls `set_mode((0,0), FULLSCREEN)` without SCALED**), `_apply_resolution` is a documented no-op (resolution rows inert), `cli.py:306-333` (auto-fullscreen + first-launch auto-fit), `core/app_shell.py:78, :209` (two more raw `set_mode` calls with `get_display_flags()` — SCALED-correct; six live `set_mode` calls in three files in all). No fullscreen hotkey in game (`input_manager._handle_debug_keys` has none; the caption's "Press 1" is stale). Persistence: JSON stores exist for `display_features`, keyboard bindings, feature toggles; nothing for fullscreen/resolution. Tests: `tests/unit/core/test_display_manager.py`, `test_display_manager_fullscreen_centering.py`, `tests/integration/test_display_facade.py`, `tests/regression/test_auto_fullscreen_at_startup.py`, `tests/test_ui_buttons.py`. CLI has a `--verify-assets` flag pattern (`cli.py:457`).
- **SP_Adventure** `sp_adventure/core/display.py`: `init_display` (fullscreen at desktop res unless saved window; `prefer_window` for the editor), `window_sizes` / `largest_window` / `fit_window` (16:9 presets under a 100 px chrome allowance), `set_display_mode` (double `set_mode` on macOS leaving fullscreen; `sync_config_to_window` resync), `keep_window_readable` (min 960×540 on `WINDOWRESIZED`, `main.py:259-260`), `render_scaled` (per-frame `smoothscale` + letterbox blit, `main.py:279`). `states/display_options_state.py` toggles/cycles and persists `WindowPreferences` via `config/settings_io.py` (versioned `settings.json`, `window` key, `None` when unset). No hotkey. Tests: 80 files call `init_display`; five import the helpers (`test_display.py`, `test_display_options_state.py`, `test_init_display_with_preferences.py`, `test_set_display_mode_resync.py`, `test_text_scale.py`).

## Phases

| # | Phase | Repo | Risk | Payoff |
| --- | --- | --- | --- | --- |
| 1 | Fix the two toggle defects in place | Skodrak, Broken Moon | low | fullscreen works from every entry point today, independent of the kit release |
| 2 | Kit v0.5.0: `WindowPreferences` + `DisplaySession` | kit | medium (new public API) | startup policy, one toggle, F11, resize, present, persistence hooks — once |
| 3 | Kit v0.5.0: display check (`python -m pygame_display_kit.check` and a callable) | kit | low | the evidence tool for phase 8 |
| 4 | SP_Adventure adopts the session | SP | low (its logic is the model) | proves the API; gains F11 |
| 5 | Skodrak adopts the session | Skodrak | medium | saved preference honoured; Options and F11 share one path; `compute_windowed_size` deleted |
| 6 | Broken Moon adopts the session | BMR | medium (four `set_mode` sites, metaclass facade) | splash path fixed for good; persistence; F11 |
| 7 | Death Knight adopts the session | DKA | low | persistence; unchanged per-element scaling |
| 8 | Screen matrix verification | all | none (evidence) | the goal, demonstrated |

Phase 1 ships first because both defects are user-visible now and the fixes are three lines each; phases 5 and 6 later replace that code wholesale. Phases 4–7 are independent of each other once phase 3 is tagged; the order is by how much each game's code already matches the session.

---

## Phase 1 — fix the toggle defects in place

### Target
- Skodrak `skodrak/states/options_state.py:165-186`, `skodrak/main.py:444-468`, `skodrak/tests/unit/test_fullscreen_toggle.py`.
- Broken Moon `src/broken_moon/ui/settings_menu.py:472-484`, `tests/unit/core/test_display_manager.py` (or a new regression file).

### Change
- Skodrak: `main.py` exposes `self._state_machine.toggle_fullscreen = self._toggle_fullscreen`; `OptionsState._toggle_fullscreen` becomes `self._state_machine.toggle_fullscreen()` and reads its `_fullscreen` display value back from `settings_manager.settings.fullscreen`. The raw `set_mode` and the second `SettingsManager.toggle_fullscreen()` call go.
- Broken Moon: the standalone branch of `SettingsMenu._toggle_fullscreen` builds a `FullscreenManager(_config)` (held on the menu instance, so the windowed-size stash survives) and calls `toggle()`; the `set_mode((0,0), FULLSCREEN)`, the preceding `DisplayConfig.set_resolution(..., self.fullscreen)` and the manual `CURRENT_*` sync go. **Direction:** `toggle()` decides from `_config.fullscreen`, so the method must not flip `self.fullscreen` or `DisplayConfig.FULLSCREEN` before the call; `self.fullscreen` is read back from `DisplayConfig.FULLSCREEN` after it.

### Side effects
- Skodrak: after an Options toggle, `_pdk_config.fullscreen`, `UserSettings.fullscreen` and the real surface agree (today they diverge). The F11 path gains nothing new. The window becomes RESIZABLE after a toggle (kit default) — already true via F11 today; phase 5 sets `resizable = False` explicitly.
- Broken Moon: the splash fullscreen keeps the 1920×1080 logical surface under SCALED instead of a desktop-resolution one. `DisplayConfig.set_resolution(width, height, ...)` before the toggle is dropped on the fullscreen branch (the manager resyncs `current_*` itself); the windowed branch keeps it.

### Tests / acceptance
- Skodrak: `test_fullscreen_toggle.py` gains a case that toggles via `OptionsState` then via the F11 handler and asserts, after each step, `game._pdk_config.fullscreen == settings.fullscreen == bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)` (the FULLSCREEN bit is reported under the dummy driver; verified), and — following the file's existing pattern of patching `pygame.display.set_mode` — that every `set_mode` call carried `SCALED` (the SCALED bit is never reported on the surface, so it must be read from the call args); a grep pin that `options_state.py` contains no `set_mode(`.
- Broken Moon: a regression test that runs the standalone toggle with `pygame.display.set_mode` patched (the `test_display_manager_fullscreen_centering.py` pattern) and asserts the call carried `SCALED | FULLSCREEN` with size `(1920, 1080)`, and that `DisplayConfig.FULLSCREEN` flipped once; the in-game branch unchanged.
- Both suites green; commit per repo.

### Rollback
`git revert <sha>` in each repo (two independent commits).

## Phase 2 — kit v0.5.0: `WindowPreferences` and `DisplaySession`

### Target
New `pygame_display_kit/session.py`, `pygame_display_kit/preferences.py`; `__init__.py` exports; `pyproject.toml` version 0.5.0; `README.md`; new `tests/test_preferences.py`, `tests/test_session.py`. Nothing existing changes except exports (the v0.4.0 API stays byte-for-byte; `FullscreenManager` is used by the session, not replaced).

### Change
`preferences.py`:
```python
@dataclass(frozen=True)
class WindowPreferences:
    fullscreen: bool = True            # Decision 1
    window_width: int = 0              # Letterbox / Grow only: 0 = "largest offered window" at open(); ignored under Scaled
    window_height: int = 0
    def to_dict(self) -> dict; @classmethod def from_dict(cls, data, default=...) -> WindowPreferences  # tolerant: bad shapes -> default
```
`session.py` — one object per game process:
```python
class DisplaySession:
    def __init__(self, config: ResolutionConfig, *, preferences: WindowPreferences | None = None,
                 on_preferences_changed: Callable[[WindowPreferences], None] | None = None,
                 window_sizes: Sequence[tuple[int,int]] = WINDOW_SIZES, chrome_allowance: int = 100,
                 min_window: tuple[int,int] | None = (960, 540), hotkey: int | None = pygame.K_F11,
                 extra_flags: int = 0, resizable: bool | None = None)
    def open(self) -> pygame.Surface            # re-entrant: re-applies the current preference (Broken Moon's resume after a game)
    def toggle_fullscreen(self) -> pygame.Surface
    def set_window_size(self, width, height) -> pygame.Surface
    def handle_event(self, event) -> bool          # F11 KEYDOWN -> toggle; WINDOWRESIZED -> resync + min size (non-SCALED); returns True when consumed
    def present(self, render_surface: pygame.Surface | None = None, *, smooth: bool = True) -> None
    @property screen, preferences, offered_window_sizes
```
Policy in `open()`: if `should_auto_fullscreen(native, chrome-adjusted)` → fullscreen; else `preferences.fullscreen` (None → fullscreen, Decision 1). Fullscreen size: `(base)` under Scaled (SDL scales to the desktop; measured: logical 1920×1080, window 2560×1440), else `(native)` — never a mode switch (SP's rule). Windowed size: **under Scaled always the base size** — the `set_mode` size *is* the window size (measured), so any other size would change the design resolution; `window_width/height` are ignored, `offered_window_sizes` is empty and `set_window_size` raises `NotImplementedError` for that strategy. A panel smaller than base relies on the auto-fullscreen rule (SCALED does not shrink an oversized window, measured). Under Letterbox / Grow: `fit_window(saved)` or the largest offered size, exactly SP's rules. `toggle_fullscreen` = `FullscreenManager.toggle()` + preference update + callback. `set_resolution` already recomputes `scale*`; the session calls `update_viewport_dimensions` only under `GrowStrategy`. `present`: Scaled → `pygame.display.flip()` only (Broken Moon's trip-wire semantics); Letterbox → scale (`smoothscale` or `scale` by `smooth`) + centered blit + flip, with SP's `sync_config_to_window` first; Grow → blit at offset + flip. `set_display_mode`'s macOS double-call and the granted-size resync move here verbatim from SP (`display.py:743-796`), with SP's docstrings' measurements kept.

### Side effects
None on v0.4.0 consumers (additive). The kit now imports `pygame.K_F11` and handles events — documented as opt-in (`hotkey=None` disables).

### Tests / acceptance
Ported from SP's `display.py` behaviours and `tests/unit/test_render_scaled.py`, run on the dummy driver with `pygame.display.Info` mocked where the native size matters: open() picks fullscreen on a 1366×768 and on a 2560×1440 native with no preferences; picks the saved window when it fits and the largest offered when it does not; Scaled fullscreen asks for base size with SCALED; Letterbox fullscreen asks for native; toggle round-trip restores the windowed size and calls the callback with the new preferences; `handle_event(F11)` toggles and returns True, other keys False; `WINDOWRESIZED` below `min_window` re-opens at the minimum (Letterbox) and is a no-op under Scaled; `present` under Letterbox centers a 1920×1080 surface in 2560×1440 at offset (0, 180) with a (2560, 1440) scale, and under Scaled calls no transform; `from_dict` on garbage returns the default. Kit suite ≥ 118 + new tests green; tag `v0.5.0`.

### Rollback
`git revert`; no consumer moves until phase 4.

## Phase 3 — kit v0.5.0: display check

### Target
New `pygame_display_kit/check.py` (+ `__main__` entry `python -m pygame_display_kit.check --strategy scaled|letterbox --base 1920x1080 [--windowed WxH] --out PATH`), `tests/test_check.py`.

### Change
`run_display_check(session, out_path, *, smallest_text_px, seconds=0)`: opens the session (fullscreen by default), draws a calibration frame onto the strategy's render surface — 1 px border, corner markers with their design coordinates, centre cross, a 16:9 frame, three text lines at `smallest_text_px`, 2× and 4×, and a caption with design size, requested size, granted size (`pygame.display.get_surface().get_size()`, `get_window_size()`), flags and platform — presents it, saves `pygame.image.save(screen, out_path)` and prints the caption as one JSON line. `seconds > 0` keeps the frame up for a human look. Games call it from a `--display-check [PATH]` flag with their own strategy, base and smallest text size (phases 4–7).

### Side effects
None at runtime; a new optional entry point.

### Tests / acceptance
Under the dummy driver: the PNG is written at the granted size; the JSON line parses and carries `requested`, `granted`, `fullscreen`, `strategy`; the border pixels at all four corners of the *granted* surface are the border colour under Letterbox (proves no clipping — the SP bug) and under Scaled. Suite green; tag `v0.5.0` after phases 2 and 3 together.

### Rollback
`git revert`.

## Phase 4 — SP_Adventure adopts the session

### Target
`sp_adventure/core/display.py`, `main.py:190-290`, `states/display_options_state.py`, `config/settings_io.py` (`WindowPreferences` becomes the kit's; same JSON shape), `pyproject.toml:38` (pin v0.5.0), `tests/unit/test_render_scaled.py`, `test_set_display_mode_resync.py`, `test_init_display_with_preferences.py`, `test_display.py`, `test_display_options_state.py`, `test_text_scale.py`. `init_display`'s signature is kept: 80 test files call it.

### Change
`init_display` builds `DisplaySession(config, preferences=saved, on_preferences_changed=save_window, window_sizes=WINDOW_SIZES, chrome_allowance=WINDOW_CHROME_ALLOWANCE, min_window=MIN_WINDOW_SIZE, resizable=True)` and returns `session.open(), config`; `prefer_window` passes a preference with `fullscreen=False` and the largest size. `render_scaled` → `session.present(render_surface)`; `keep_window_readable` and the `WINDOWRESIZED` branch → `session.handle_event(event)` placed before `machine.handle_event` (F11 arrives too). `DisplayOptionsState` calls `session.toggle_fullscreen()` / `session.set_window_size()`; persistence stays in `settings_io` through the callback. `display.py` stays as a façade: `init_display`, `set_display_mode`, `sync_config_to_window`, `window_sizes`, `fit_window`, `keep_window_readable`, `render_scaled` keep their names and delegate to the session, so the five helper-importing test files and the 80 `init_display` callers need no edit; their logic lives in the kit from here on.

### Side effects
First-launch behaviour unchanged (already fullscreen). New: F11. Per-frame `smoothscale` unchanged (Letterbox stays; `smooth=True`). `WindowPreferences` default `fullscreen` flips from False to True in the dataclass, but SP never persisted a default (it stores `None` when unset), so saved files read the same.

### Tests / acceptance
`test_render_scaled.py` cases pass against `session.present` (moved or re-pointed); a new test that an F11 `KEYDOWN` through `main`'s loop toggles `config.fullscreen` and triggers one `save_settings`; `--display-check` flag added to `main.py` writing `reports/display_check_<platform>.png`. Suite green.

### Rollback
`git revert`, pin back to v0.4.0.

## Phase 5 — Skodrak adopts the session

### Target
`skodrak/main.py:95-200, :326-328, :444-468`, `states/options_state.py:165-186`, `systems/persistence/settings_manager.py` (`UserSettings.fullscreen` is the whole preference under Scaled — no window size is stored, see v3 audit; `to_dict`/`from_dict` pass it to `WindowPreferences`), `systems/rendering/display_manager.py` (`compute_windowed_size` deleted; docstring 14:9 → 16:9; `set_screen` stays for DRS), `pyproject.toml:17` (pin), tests: `test_fullscreen_toggle.py`, `test_bug_fixes.py`, `test_settings_manager_roundtrip.py`, `test_display_manager.py`, `test_drs_integration.py::test_fullscreen_toggle_rebuilds_surfaces`.

### Change
`Game.__init__`: `self._session = DisplaySession(ResolutionConfig(base, ScaledStrategy, auto_detect=True, platform_adjust=True), preferences=WindowPreferences(fullscreen=settings.fullscreen), on_preferences_changed=self._save_display_prefs, extra_flags=pygame.DOUBLEBUF, resizable=False, min_window=None)`; `self._screen = self._session.open()`. The hand-written detect/adjust/auto-fullscreen/`force windowed` block (`:95-129`) goes — the session applies the small-monitor rule and otherwise honours the saved choice (Decision 1 fixes the "saved fullscreen never survives a relaunch" defect). `_toggle_fullscreen` → `self._screen = self._session.toggle_fullscreen()` + the existing `DisplayManager.set_screen` / DRS reset / font reset; F11 handled by `self._session.handle_event(event)` in `_handle_events` before the hotkey block (`continue` when consumed). `OptionsState` calls the same `toggle_fullscreen` from phase 1. `SettingsManager.toggle_fullscreen` deleted (the session owns the flag; the manager stores what the callback gives it).

### Side effects
- On a large monitor the first launch is now fullscreen, and "F11, quit, relaunch" comes back fullscreen — both are the decided behaviour and a change from today.
- `UserSettings.fullscreen` default flips to True; existing settings files keep their saved value.
- Two pins of the old default change: `test_bug_fixes.py:101 test_fullscreen_default_is_off` → `_is_on`, and `test_settings_manager_roundtrip.py:107` (compares to `GameSettings().fullscreen`, which must flip with it or the comparison is to the wrong source). `test_fullscreen_toggle.py` (SCALED preservation, base-size fullscreen) is unchanged and must stay green through the session.
- DRS untouched: `DisplayManager` still wraps the screen the session returns.

### Tests / acceptance
The phase 1 two-path test still passes with the session underneath; a startup test with `pygame.display.Info` mocked to 2560×1440 and no saved file opens fullscreen, with a saved windowed preference opens that window, with 1366×768 opens fullscreen regardless; `--display-check` flag in `main.py` (no argparse today — a `sys.argv` check like Broken Moon's `--verify-assets`). Full suite green (≈ 26.5 k).

### Rollback
`git revert`, pin back to v0.4.0.

## Phase 6 — Broken Moon adopts the session

### Target
`src/broken_moon/config/display.py` (singleton config stays; a module-level `session` beside it), `core/game/display_manager.py:912-1015` (`_initialize_normal_display`, `toggle_fullscreen`, `handle_window_resize` deleted, `present`), `core/app_shell.py:78, :209`, `cli.py:306-333`, `ui/settings_menu.py:441-490` (both branches → `session.toggle_fullscreen()`), `core/game/input_manager.py` (F11 via `session.handle_event` in the event sweep; `VIDEORESIZE` collection dropped), a new `config/display_preferences.py` store modelled on `display_features.py:54` (JSON under the same directory), `pyproject.toml:29` (pin), `CLAUDE.md:95` and `cli.py:315` (1600×1200 → 1920×1080), caption text. Tests listed in "today".

### Change
One `DisplaySession` created at import next to `_config`, preferences (fullscreen flag only — Scaled, see v3 audit) loaded from the new store, `resizable=False` (today's RESIZABLE is unhandled), `extra_flags=0`. `ApplicationShell.__init__` and `_resume_front_end` both call `session.open()` instead of raw `set_mode`. `_ensure_resolution_initialized`'s first-launch auto-fit (`select_best_resolution`) is deleted: under Scaled the window is always the base size and a preset "resolution" would change the logical size (measured), so the auto-fit has had no effect since the ScaledStrategy switch; the auto-fullscreen half moves into the session's policy. `DisplayManager.toggle_fullscreen` → session; `present()` → `session.present()` (still a flip under Scaled; the trip-wire test keeps it that way).

### Side effects
- First launch on a large monitor becomes fullscreen (Decision 1); fullscreen choice persists.
- The inert resolution rows in the settings menu stay inert (Out of scope: delete or repurpose).
- `DisplayConfig.FULLSCREEN = ...` writes from tests keep working through the metaclass (the session reads `_config.fullscreen`).

### Tests / acceptance
Phase 1's splash regression test passes through the session; `test_auto_fullscreen_at_startup.py` keeps its heuristic tests (the rule is unchanged; rename `test_1080p_display_forces_fullscreen_on_1600x1200_design` to the real design) and gains a `session.open()` test for Decision 1 (2560×1440 native, no saved file → fullscreen; saved window → that window); an F11 test through `InputManager`; `--display-check` flag beside `--verify-assets`. Suite green.

### Rollback
`git revert`, pin back.

## Phase 7 — Death Knight adopts the session

### Target
`dk_modules/game/renderer.py:38-59`, `Death_Knight.py:258-270`, `event_handler.py:99-100`, `dk_modules/core/config_manager.py` (a `display_config.json` beside `controls_config.json` via `ResourceManager.get_user_data_dir()`), `pyproject.toml:28` (pin), `tests/regression/test_fullscreen_toggle.py`.

### Change
`GameRenderer.__init__` builds `DisplaySession(resolution_config.pdk_config, preferences=ConfigManager.load_display(), on_preferences_changed=ConfigManager.save_display, resizable=False, min_window=None)` and opens it; `toggle_fullscreen` → session; `event_handler` F11 → `session.handle_event`. Windowed size: the saved size, else the largest offered 16:9 window under the chrome allowance (today: the whole chrome-adjusted desktop). After any size change the facade's `update_viewport_dimensions` runs (the session calls `set_resolution`, which the facade's properties already read).

### Side effects
- First launch on a large monitor: fullscreen (today: a desktop-sized window). Saved choice honoured across launches (today: none).
- Per-element scaling unchanged; the 205 read sites are untouched.

### Tests / acceptance
`test_fullscreen_toggle.py` extended with persistence (toggle → file written → new session opens in that mode); `--display-check` flag (no argv parsing today — `sys.argv` check). Suite green.

### Rollback
`git revert`, pin back.

## Phase 8 — screen matrix verification

### Target
`pygame_display_kit/docs/display_matrix_2026-10.md` plus the PNGs each game's `--display-check` writes (`<game>/reports/display_check_<platform>_<WxH>.png`).

### Change
Run every game's `--display-check` on: the macOS laptop panel (Retina), an external 1080p, the largest monitor available, a Windows machine if available, and a sub-1080p panel if one can be borrowed (a small panel cannot be simulated: under SCALED an oversized window is not shrunk, measured, so only real hardware exercises the auto-fullscreen rule). Each run also exercises F11 once and relaunches to confirm the saved mode. Record requested/granted sizes, flags and the four corner checks per cell.

### Acceptance
Every cell of the table has a screenshot and a granted size; no cell shows clipping or a wrong logical size; relaunch returns to the chosen mode in all four games. Cells that cannot be run (no hardware) are marked, not inferred.

### Rollback
None (documentation).

---

## Out of scope
- Skodrak DRS (Decision 4): measure on the slowest target laptop; a separate plan removes it or gives it one scale pass and a menu entry.
- Broken Moon's inert resolution rows in the settings menu (delete or repurpose) and its `GrowStrategy` history.
- Death Knight's per-element scaling (205 sites): correct and crisp; converting it to a render surface is a different project.
- A shared settings store across games (each keeps its own file; the kit only defines the record).
- The kit's `resizable`/`vsync` defaults: the session passes them explicitly, so changing the defaults is left alone to keep v0.4.0 behaviour for anyone not on the session.
- SP_Adventure's per-frame `smoothscale` cost (2.2 ms at 1440p): keep until a measurement on a slow machine says otherwise.

---

## Execution notes (2026-10-19)

| Phase | Commit(s) | Deviations and findings |
| --- | --- | --- |
| 1 | Skodrak `737dc749`; Broken Moon `83f9ff8e` | As planned. Broken Moon's settings-menu test mock now flips the shared config like the real DisplayManager. |
| 2 | kit `986ac6a`, `9cbb507`, `3f13209` | The session restores the *preferred* window on toggle-back, so it does not use `FullscreenManager` (which restores the last size); the manager stays for v0.4.0 callers. Added beyond the plan, for SP's façade: `set_fullscreen`, `set_window_size(fit=False)`, public `sync_to_granted` / `keep_window_readable` (reading `pygame.display.get_window_size()` as SP does), `present(screen=…, flip=False)`, a `desktop` argument. **The small-monitor rule is per strategy**: Scaled/Grow use the chrome-adjusted `should_auto_fullscreen`; Letterbox forces fullscreen only when the largest fitting window is below `min_window` or the config's `min_size` — SP's tests pin a fitted window on 1366×768, and Death Knight's 1280×720 clamp still forces fullscreen there. `open()` reads the desktop once (after `set_mode`, `pygame.display.Info()` reports the window's mode). |
| 3 | kit `4380c9e`, `478018d` | The 16:9 frame coincides with the border on a 16:9 design, so the border is drawn last. Screenshots are saved as RGB: macOS desktop-fullscreen surfaces carry an alpha channel left at 0. |
| 4 | SP `96655fb` | `display.py` stays as a façade over a per-config session registry (`session_for`), so all 80 `init_display` callers and the five helper-importing test files pass unchanged. F11 persistence is done in `main`'s loop via `save_window_preferences` (not a session callback), so the Display options screen keeps its own save. Suite: 2 pre-existing failures (`test_build_data_files`, `test_gamepad_dpad_and_stick`; a third, `test_flying_enemy_placement[third_level-0]`, is flaky — it failed once in the baseline and passed after). |
| 5 | Skodrak `726a471b` | `build_display_session` is a module-level factory so startup policy is tested on the real path; `test_main_auto_fullscreen.py` was a mirror of the old composition and now tests that factory. `detect_monitor_resolution` / `should_auto_fullscreen` facades in `display_manager.py` remain (tests use them) but have no production caller — dead-code sweep candidates. |
| 6 | Broken Moon `ee53f5bf` | The session is built on first use (`get_session`) so importing `config.display` reads no settings file. `_ensure_resolution_initialized` deleted (auto-fit was a no-op under SCALED). The render-surface propagation moved from the settings menu into `DisplayManager.toggle_fullscreen` so F11 and the menu share it. A facade test that accepted only RESIZABLE/FULLSCREEN/0 flags now expects SCALED. **A suite run wrote the player's real `display_preferences.json`**; an autouse conftest fixture now routes it to `tmp_path` and the stray file was deleted. |
| 7 | Death Knight `abb6a83` | The session's hotkey is off (F11 stays in `GameEventHandler`, pinned by its test). Renderer tests return real surfaces from the mocked `set_mode` (a `Mock()` has no size). Same autouse guard for `display_config.json`. Suite 7,051 passed, coverage 91 %. |
| 8 | kit `docs/display_matrix_2026-10.md` | Run on this machine only (macOS, 2560×1440): all four fullscreen, `corners_ok`. Other screens listed as not run. |

Pins: every game's `pyproject.toml` now points at `pygame_display_kit.git@v0.5.0`; the tag exists locally and resolves only once the kit branch and tag are pushed. The kit is installed editable on this machine, so the games import the local checkout.

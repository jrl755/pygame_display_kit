"""Heuristic for auto-engaging fullscreen on undersized displays.

Extracted from Skodrak's ``display_manager.should_auto_fullscreen`` —
when the user's monitor is at-or-below the game's design resolution,
windowed mode is a broken state (the OS chrome eats pixels even on
exact-match displays), not a meaningful preference. Consumers call
this before deciding whether to honor a saved windowed preference.

The check is intentionally per-axis (`<=` on either width OR height),
not aspect-ratio aware: a 1920×1080 monitor on a 1920×1080 design is
"exact match" → fullscreen; a 2560×1080 ultrawide on 1920×1080 design
is "wider than design but same height" → also fullscreen (the height
budget is gone). This is the verbatim Skodrak rule, lifted into the
shared library so all three games can apply the same logic without
duplication.
"""


def should_auto_fullscreen(
    monitor_width: int,
    monitor_height: int,
    design_width: int,
    design_height: int,
) -> bool:
    """Return True when the monitor can't comfortably fit a windowed design-resolution surface.

    Triggers on either dimension being ``<=`` the design value — an
    exact-match display loses pixels to the OS chrome (title bar /
    taskbar) so windowed mode is unusable there too. Used by game
    startup paths to override a saved windowed preference when the
    user's display is small enough that windowed mode is a broken
    state, not a meaningful preference.

    Args:
        monitor_width: Detected monitor width in pixels.
        monitor_height: Detected monitor height in pixels.
        design_width: Design-resolution width.
        design_height: Design-resolution height.

    Returns:
        ``True`` if either monitor dimension is ``<=`` the
        corresponding design dimension; ``False`` otherwise.

    Example::

        from pygame_display_kit import detect_native, should_auto_fullscreen

        monitor_w, monitor_h = detect_native()
        if should_auto_fullscreen(monitor_w, monitor_h, 1920, 1080):
            # User saved windowed=True but their display is too small;
            # force fullscreen to avoid a broken windowed state.
            fullscreen = True
    """
    return monitor_width <= design_width or monitor_height <= design_height

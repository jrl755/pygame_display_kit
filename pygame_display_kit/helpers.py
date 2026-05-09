"""Per-element scale helpers — extracted from Death_Knight_Arena.

These helpers convert BASE-coordinate values (the design-time pixel
positions/sizes the developer authored) into display-coordinate values
(scaled + offset by the strategy's letterbox/grow math). They take a
:class:`ResolutionConfig` argument so they're stateless module functions
— callers pass the active config explicitly.

The pattern works best with :class:`LetterboxStrategy` because that
strategy uses uniform scaling and centered offset — every UI widget,
sprite size, font size scales by the same factor and lands in the
correct screen position regardless of display aspect ratio. Under
:class:`GrowStrategy` these helpers still work (scale = 1.0, offset =
0, 0) but the per-element scale is implicit (the whole render surface
is uniformly scaled to the display).
"""

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .config import ResolutionConfig


def scale_value(config: "ResolutionConfig", value: float) -> float:
    """Scale a single BASE-coordinate value to display coordinates.

    Args:
        config: Active resolution config.
        value: A pixel count, distance, or size in BASE coordinates.

    Returns:
        ``value * config.scale``.
    """
    return value * config.scale


def scale_position(
    config: "ResolutionConfig", x: float, y: float
) -> Tuple[float, float]:
    """Scale a BASE-coordinate position + add the strategy's offset.

    Under :class:`LetterboxStrategy`, the offset centers the rendered
    area inside the display (letterbox/pillarbox bars on the un-grown
    axis). Under :class:`GrowStrategy`, offset is (0, 0).

    Args:
        config: Active resolution config.
        x, y: Position in BASE coordinates.

    Returns:
        ``(x * scale + offset_x, y * scale + offset_y)``.
    """
    offset_x, offset_y = config.strategy.compute_viewport_offset(
        config, (config.current_width, config.current_height)
    )
    return (x * config.scale + offset_x, y * config.scale + offset_y)


def scale_size(
    config: "ResolutionConfig", width: float, height: float
) -> Tuple[float, float]:
    """Scale BASE-coordinate dimensions (no offset).

    Use for widget/sprite sizes — sizes don't need centering offset
    (they're width/height, not absolute positions).

    Args:
        config: Active resolution config.
        width, height: Dimensions in BASE coordinates.

    Returns:
        ``(width * scale, height * scale)``.
    """
    return (width * config.scale, height * config.scale)


def get_font_size(config: "ResolutionConfig", base_size: int, minimum: int = 12) -> int:
    """Return scaled font size with readability floor.

    Pygame fonts at sub-12px are unreadable on most displays.
    The minimum prevents tiny text on small windows / scaled-down
    resolutions.

    Args:
        config: Active resolution config.
        base_size: Font size in BASE coordinates (typically 16, 24, etc.).
        minimum: Lower bound on returned size. Default 12 px.

    Returns:
        ``max(int(base_size * scale), minimum)``.
    """
    scaled = int(base_size * config.scale)
    return max(scaled, minimum)

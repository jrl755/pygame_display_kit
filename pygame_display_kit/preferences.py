"""WindowPreferences — the player's saved display choice.

The kit defines the record and its validation; each game stores it in
its own settings file (``to_dict`` / ``from_dict``). A game that has no
saved choice passes ``None`` to :class:`DisplaySession`, which then
applies the family default: fullscreen.

``window_width`` / ``window_height`` only mean something under the
Letterbox and Grow strategies. Under ``pygame.SCALED`` the size passed
to ``set_mode`` *is* the window size (measured 2026-10-19: a 1600x900
request gave a 1600x900 window with a 1600x900 logical surface), so a
window size would change the design resolution; Scaled sessions ignore
these fields and always open a base-sized window.
"""

from dataclasses import asdict, dataclass
from typing import Any, Optional

_INT_FIELDS = ("window_width", "window_height")


@dataclass(frozen=True)
class WindowPreferences:
    """Saved display choice.

    Attributes:
        fullscreen: Open fullscreen. The default is True: fullscreen at
            the desktop's own resolution behaves the same on every OS
            and screen size, with no title bar or taskbar hiding part
            of the picture.
        window_width, window_height: The windowed size to restore
            (Letterbox / Grow). 0 means "the largest offered window".
    """

    fullscreen: bool = True
    window_width: int = 0
    window_height: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Plain dict for the game's settings file."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: object, default: Optional["WindowPreferences"] = None) -> "WindowPreferences":
        """Build from a settings-file mapping, tolerating any bad shape.

        A missing key, wrong type or non-mapping ``data`` yields
        ``default`` (or the class default) for that field, so a corrupt
        or old settings file can never stop a game from opening.
        """
        base = default if default is not None else cls()
        if not isinstance(data, dict):
            return base
        fullscreen = data.get("fullscreen", base.fullscreen)
        if not isinstance(fullscreen, bool):
            fullscreen = base.fullscreen
        sizes = {}
        for name in _INT_FIELDS:
            value = data.get(name, getattr(base, name))
            sizes[name] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else getattr(base, name)
        return cls(fullscreen=fullscreen, **sizes)

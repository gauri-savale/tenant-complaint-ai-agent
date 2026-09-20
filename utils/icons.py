"""
utils/icons.py
----------------
A small set of minimal, professional stroke-icons (Feather/Lucide-style,
24x24, stroke=currentColor) as inline SVG strings. Using inline SVG instead
of emoji or an external icon-font CDN keeps the app fully self-contained
(consistent with the project's offline-first design) and reads as a real
product UI rather than a demo sprinkled with emoji.

Each icon is a bare <svg>...</svg> string; wrap it in a span with the
desired size/color via CSS (color is inherited through `currentColor`).
"""

_STROKE = 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'


def _svg(paths: str) -> str:
    return f'<svg viewBox="0 0 24 24" {_STROKE} xmlns="http://www.w3.org/2000/svg">{paths}</svg>'


ICONS = {
    "complaint": _svg(
        '<path d="M14 3v4a1 1 0 0 0 1 1h4"/>'
        '<path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z"/>'
        '<path d="M9 13h6M9 17h4"/>'
    ),
    "agent": _svg(
        '<path d="M12 3a4 4 0 0 1 4 4v1h.5A2.5 2.5 0 0 1 19 10.5v3A2.5 2.5 0 0 1 16.5 16H16v1a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-1h-.5A2.5 2.5 0 0 1 5 13.5v-3A2.5 2.5 0 0 1 7.5 8H8V7a4 4 0 0 1 4-4Z"/>'
        '<circle cx="9.5" cy="12" r="1"/><circle cx="14.5" cy="12" r="1"/>'
        '<path d="M9 19v1a1 1 0 0 0 1 1h1M15 19v1a1 1 0 0 1-1 1h-1"/>'
    ),
    "management": _svg(
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>'
    ),
    "dashboard": _svg(
        '<rect x="3" y="12" width="4" height="9" rx="1"/>'
        '<rect x="10" y="7" width="4" height="14" rx="1"/>'
        '<rect x="17" y="3" width="4" height="18" rx="1"/>'
    ),
    "insights": _svg(
        '<path d="M12 3a5 5 0 0 0-3 9c.4.3.6.8.6 1.3V14h4.8v-.7c0-.5.2-1 .6-1.3a5 5 0 0 0-3-9Z"/>'
        '<path d="M9.5 17h5M10 20h4"/>'
    ),
    "history": _svg(
        '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v4l3 2"/>'
    ),
    "search": _svg('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
    "refresh": _svg(
        '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 4v5h-5"/>'
    ),
    "save": _svg(
        '<path d="M5 4h11l3 3v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"/>'
        '<path d="M8 4v5h7V4M8 14h8v6H8z"/>'
    ),
    "check": _svg('<path d="M20 6 9 17l-5-5"/>'),
    "alert": _svg(
        '<path d="M10.3 4.3 2.6 18a1 1 0 0 0 .9 1.5h17a1 1 0 0 0 .9-1.5L13.7 4.3a1 1 0 0 0-1.7 0Z"/>'
        '<path d="M12 9.5v4M12 16.5h.01"/>'
    ),
    "sparkle": _svg(
        '<path d="M12 3v3M12 18v3M4 12h3M17 12h3M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2"/>'
        '<circle cx="12" cy="12" r="2.5"/>'
    ),
    "send": _svg('<path d="m3 11 18-8-8 18-2-8-8-2Z"/>'),
    "clear": _svg('<path d="M6 6l12 12M18 6 6 18"/>'),
}


def icon(name: str, size: int = 18) -> str:
    svg = ICONS.get(name, "")
    return f'<span class="tc-icon" style="width:{size}px;height:{size}px;display:inline-flex;">{svg}</span>'

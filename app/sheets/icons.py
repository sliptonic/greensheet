"""
The mark with a character on it. The requester may put one character or
emoji on a greensheet's mark so its tab and its row on the desk stand out.
Green stays; only the glyph changes.
"""

from urllib.parse import quote
from xml.sax.saxutils import escape

GREEN = "#3E8E4E"
PAPER = "#F3F7EF"
MAX_ICON_CODEPOINTS = 16


def clean_icon(raw):
    """One glyph. Whitespace stripped; a long paste is cut, never rejected."""
    raw = (raw or "").strip()
    return raw[:MAX_ICON_CODEPOINTS]


def favicon_svg(icon):
    """A 32x32 SVG of the mark, with the glyph in paper on the green if set."""
    body = (
        f'<path fill="{GREEN}" d="M3.5 0h15.5L28.5 10.8V32H3.5z"/>'
        f'<path fill="{PAPER}" fill-opacity=".85" d="M19 0v10.8h9.5z"/>'
    )
    if icon:
        body += (
            f'<text x="16" y="24.5" text-anchor="middle" font-size="15" '
            f'font-family="system-ui,-apple-system,\'Segoe UI\',\'Apple Color Emoji\',\'Segoe UI Emoji\',sans-serif" '
            f'fill="{PAPER}">{escape(icon)}</text>'
        )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{body}</svg>'


def favicon_data_uri(icon):
    return "data:image/svg+xml;charset=utf-8," + quote(favicon_svg(icon), safe="")

"""
Home-screen icons: the mark on paper, as PNG, without any image library.
Run from app/: python tools/make_icons.py
"""

import struct
import zlib
from pathlib import Path

GREEN = (0x3E, 0x8E, 0x4E)
PAPER = (0xF3, 0xF7, 0xEF)
FOLD = (0xD9, 0xE6, 0xD6)  # paper at 85% over green, as the SVG draws it

OUT = Path(__file__).resolve().parent.parent / "static"


def png(width, height, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def render(size, scale, ss=4):
    """The mark, 14x18 units, centred and scaled to `scale` of the shorter side.
    Supersampled ss times per axis for smooth edges."""
    mark_h = size * scale
    unit = mark_h / 18.0
    mark_w = 14 * unit
    x0 = (size - mark_w) / 2.0
    y0 = (size - mark_h) / 2.0

    def colour_at(px, py):
        u = (px - x0) / unit
        v = (py - y0) / unit
        if not (0 <= u <= 14 and 0 <= v <= 18):
            return PAPER
        # the cut corner, top right: outside the sheet
        if u > 8.7 and v < 6.1 and (u - 8.7) / (14 - 8.7) > v / 6.1:
            return PAPER
        # the fold: the triangle under that corner
        if u >= 8.7 and v <= 6.1:
            return FOLD
        return GREEN

    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            acc = [0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    c = colour_at(x + (sx + 0.5) / ss, y + (sy + 0.5) / ss)
                    acc[0] += c[0]
                    acc[1] += c[1]
                    acc[2] += c[2]
            n = ss * ss
            row += [acc[0] // n, acc[1] // n, acc[2] // n]
        rows.append(row)
    return rows


def main():
    for name, size, scale in (
        ("icon-180.png", 180, 0.62),
        ("icon-192.png", 192, 0.62),
        ("icon-512.png", 512, 0.62),
        ("icon-512-maskable.png", 512, 0.50),
    ):
        (OUT / name).write_bytes(png(size, size, render(size, scale)))
        print("wrote", name)


if __name__ == "__main__":
    main()

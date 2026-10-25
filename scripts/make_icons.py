#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""make_icons.py — draws the face's app icons (two glowing eyes on black) as PNG, standard library only.

    python3 scripts/make_icons.py      writes ros2/atl_phone/web/icons/eye-192.png and eye-512.png
"""
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ros2/atl_phone/web/icons"
EYE = (63, 216, 255)


def inside(x, y, cx, cy, w, h, r):
    """Is (x, y) in the rounded rectangle centred at cx, cy?"""
    dx, dy = max(abs(x - cx) - (w / 2 - r), 0), max(abs(y - cy) - (h / 2 - r), 0)
    return dx * dx + dy * dy <= r * r


def icon(n: int) -> bytes:
    rows = []
    w, h, r = 0.2 * n, 0.3 * n, 0.07 * n   # each eye; the safe zone of a maskable icon is the middle 80 %
    for y in range(n):
        row = bytearray([0])
        for x in range(n):
            px, py = x + 0.5, y + 0.5
            on = any(inside(px, py, cx * n, 0.5 * n, w, h, r) for cx in (0.33, 0.67))
            row += bytes(EYE) if on else b"\0\0\0"
        rows.append(bytes(row))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for n in (192, 512):
        (OUT / f"eye-{n}.png").write_bytes(icon(n))
        print(OUT / f"eye-{n}.png")

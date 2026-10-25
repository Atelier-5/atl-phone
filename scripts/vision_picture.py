#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""vision_picture — a test picture for the camera's finders: ArUco 4x4 marker 7 in the middle, a red square on the left.

    python3 scripts/vision_picture.py out.ppm [--marker-px 160]

640x480, grey. The marker's black square is --marker-px wide (its id cells as js-aruco2's dictionary draws them);
the red square is 80 px, its centre at x 100, y 240. browser_check plays it through Chrome's fake camera.
Standard library only (a binary PPM).
"""
import argparse

W, H = 640, 480
MARKER_7 = {(2, 2), (3, 2), (3, 3), (2, 4), (3, 4), (4, 4), (5, 4), (4, 5)}  # white cells of id 7, on the 8x8 grid (border 1)


def picture(marker_px: int) -> bytearray:
    px = bytearray([150, 150, 150] * W * H)

    def fill(x0, y0, x1, y1, rgb):
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                px[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(rgb)

    cell = marker_px // 6
    x0, y0 = W // 2 - 4 * cell, H // 2 - 4 * cell
    fill(x0, y0, x0 + 8 * cell, y0 + 8 * cell, (255, 255, 255))  # the quiet zone
    fill(x0 + cell, y0 + cell, x0 + 7 * cell, y0 + 7 * cell, (0, 0, 0))
    for cx, cy in MARKER_7:
        fill(x0 + cx * cell, y0 + cy * cell, x0 + (cx + 1) * cell, y0 + (cy + 1) * cell, (255, 255, 255))
    fill(60, 200, 140, 280, (230, 30, 30))
    return px


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("out")
    a.add_argument("--marker-px", type=int, default=160)
    args = a.parse_args()
    with open(args.out, "wb") as f:
        f.write(b"P6 %d %d 255\n" % (W, H) + picture(args.marker_px))


if __name__ == "__main__":
    main()

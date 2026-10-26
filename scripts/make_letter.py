#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""make_letter.py — draws the letter the Webots twin reads aloud (Omi Assist's demo) as a PNG, with Pillow.

    python3 scripts/make_letter.py      writes webots/textures/letter_de.png from webots/letter.json

A made-up letter, no real names: its text is in webots/letter.json, which the twin's controller says when the letter is
in front of the back camera. Run it again after changing the text (the PNG is kept in the repository).
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
W, H = 724, 1024   # A5's shape; saved as 512 x 1024 (Webots wants powers of two), which the sheet stretches back


def main():
    letter = json.loads((HERE / "webots" / "letter.json").read_text())
    img = Image.new("RGB", (W, H), (250, 248, 240))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 46)
    y = 110
    for line in letter["lines"]:
        d.text((68, y), line, fill=(20, 20, 30), font=font)
        y += 76 if line else 48
    out = HERE / "webots" / "textures" / "letter_de.png"
    out.parent.mkdir(exist_ok=True)
    img.resize((512, 1024), Image.LANCZOS).save(out, optimize=True)
    print(out)


if __name__ == "__main__":
    main()

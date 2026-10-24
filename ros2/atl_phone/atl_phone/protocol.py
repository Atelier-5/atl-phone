# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""protocol.py — the JSON messages between the phone page and the bridge, checked both ways (no ROS here).

Phone -> bridge: {"t": "hello" | "imu" | "heading" | "touch" | "battery", ...}
Bridge -> phone: {"t": "face" | "gaze" | "color" | "say" | "torch" | "vibrate" | "open", ...}

A phone is not trusted: parse() returns a clean message or raises ValueError,
and every number is finite and clamped.
"""
import json
import math

from . import contract as c

ZONES = ("left", "centre", "right")
TOUCHES = ("tap", "long", "swipe")
DIRS = ("left", "right", "up", "down")
PAGES = ("face.html", "check.html")   # where the setup page may send the phone


def _num(v, lo=-1e6, hi=1e6) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"not a number: {v!r}")
    return float(min(max(float(v), lo), hi))  # float(): min() hands back an int bound as is, and ROS wants floats


def _vec3(v, lo, hi) -> tuple:
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise ValueError(f"not three numbers: {v!r}")
    return tuple(_num(x, lo, hi) for x in v)


def _one_of(v, allowed):
    if v not in allowed:
        raise ValueError(f"{v!r} is not one of {', '.join(allowed)}")
    return v


def _text(v, n=200) -> str:
    if not isinstance(v, str):
        raise ValueError("not text")
    return v[:n]


def parse(raw: str) -> dict:
    """A message from the phone, checked."""
    try:
        m = json.loads(raw)
    except ValueError:
        raise ValueError("not JSON") from None
    if not isinstance(m, dict):
        raise ValueError("not an object")
    t = m.get("t")
    if t == "hello":
        caps = m.get("caps") if isinstance(m.get("caps"), dict) else {}
        screen = m.get("screen") if isinstance(m.get("screen"), (list, tuple)) else [0, 0]
        return {"t": "hello", "ua": _text(m.get("ua", ""), 300),
                "caps": {_text(k, 40): bool(v) for k, v in list(caps.items())[:40]},
                "screen": [int(_num(x, 0, 10000)) for x in screen[:2]]}
    if t == "imu":
        return {"t": "imu", "acc": _vec3(m.get("acc"), -200, 200), "gyro": _vec3(m.get("gyro"), -100, 100)}
    if t == "heading":
        return {"t": "heading", "deg": _num(m.get("deg")) % 360}
    if t == "touch":
        out = {"t": "touch", "kind": _one_of(m.get("kind"), TOUCHES), "zone": _one_of(m.get("zone"), ZONES)}
        if out["kind"] == "swipe":
            out["dir"] = _one_of(m.get("dir"), DIRS)
        return out
    if t == "battery":
        return {"t": "battery", "level": _num(m.get("level"), 0, 1), "charging": bool(m.get("charging"))}
    raise ValueError(f"unknown message {t!r}")


# bridge -> phone

def face(expression: str) -> dict:
    return {"t": "face", "expression": _one_of(expression, c.EXPRESSIONS)}


def gaze(x: float, y: float) -> dict:
    return {"t": "gaze", "x": _num(x, -1, 1), "y": _num(y, -1, 1)}


def color(r: float, g: float, b: float) -> dict:
    return {"t": "color", "rgb": [round(_num(v, 0, 1) * 255) for v in (r, g, b)]}


def say(data: str, default_lang: str = "en") -> dict:
    """Plain text, or JSON {"text", "lang"}."""
    text, lang = data, default_lang
    if data.lstrip().startswith("{"):
        try:
            m = json.loads(data)
        except ValueError:
            raise ValueError("say: not JSON") from None
        text, lang = m.get("text", ""), m.get("lang", default_lang)
    text = _text(text, c.MAX_SAY).strip()
    if not text:
        raise ValueError("say: nothing to say")
    return {"t": "say", "text": text, "lang": _one_of(lang, c.LANGS)}


def torch(on: bool) -> dict:
    return {"t": "torch", "on": bool(on)}


def vibrate(ms: int) -> dict:
    return {"t": "vibrate", "ms": int(_num(ms, 0, c.MAX_VIBRATE))}


def open_page(page: str) -> dict:
    return {"t": "open", "page": _one_of(page, PAGES)}

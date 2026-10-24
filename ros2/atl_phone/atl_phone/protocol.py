# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""protocol.py — the JSON messages between the phone page and the bridge, checked both ways (no ROS here).

Phone -> bridge: {"t": "hello" | "imu" | "heading" | "touch" | "battery" | "camera", ...}
Bridge -> phone: {"t": "face" | "gaze" | "color" | "say" | "torch" | "vibrate" | "open" | "camera", ...}

"camera" is the setup page's camera test: the phone shows the picture on its own screen and says
whether it works and which codes it read; pictures never leave the phone.

A phone is not trusted: parse() returns a clean message or raises ValueError,
and every number is finite and clamped.
"""
import json
import math
import re

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


def phone_id(v) -> str:
    """The page's random id for this browser (16 hex digits), or "" when it has none or sends something else."""
    return v if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{16}", v) else ""


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
        return {"t": "hello", "id": phone_id(m.get("id")), "ua": _text(m.get("ua", ""), 300),
                "model": _text(m.get("model") or "", 40).strip(),   # from client hints: the UA may hide it ("K")
                "secure": bool(m.get("secure", True)),              # a page that is not secure: no camera, motion, battery
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
    if t == "camera":
        out = {"t": "camera", "on": bool(m.get("on")), "ok": bool(m.get("ok"))}
        if m.get("ok") and isinstance(m.get("size"), (list, tuple)):
            out["size"] = [int(_num(x, 0, 10000)) for x in m["size"][:2]]
        for k, n in (("error", 80), ("code", c.MAX_SAY)):
            if m.get(k):
                out[k] = _text(m[k], n)
        if "torch" in m:
            out["torch"] = bool(m["torch"])
        return out
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


def camera(on: bool) -> dict:
    return {"t": "camera", "on": bool(on)}


def vibrate(ms: int) -> dict:
    return {"t": "vibrate", "ms": int(_num(ms, 0, c.MAX_VIBRATE))}


def open_page(page: str) -> dict:
    return {"t": "open", "page": _one_of(page, PAGES)}

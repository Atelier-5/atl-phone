# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""protocol.py — the JSON messages between the phone page and the bridge, checked both ways (no ROS here).

Phone -> bridge: {"t": "hello" | "imu" | "heading" | "touch" | "battery" | "camera" | "look" | "faces" | "code" | "pad" | "panel"
                       | "see" | "markers" | "blobs" | "objects" | "hands" | "menu" | "answer" | "read" | "what" | "show"
                       | "frame" | "screen", ...}
Bridge -> phone: {"t": "face" | "gaze" | "color" | "say" | "torch" | "vibrate" | "open" | "camera" | "look" | "forget" | "panel"
                       | "see" | "note" | "read" | "what" | "show" | "tour", ...}

"show" and "frame" are the one exception to pictures staying on the phone, for Omi Assist: only while the person presses
"show" on the phone, and only when the facilitator allowed it, the phone sends small JPEG frames; the bridge hands them
to the setup page on this PC only (never a topic, never a file). The bridge says whether it is allowed.

"camera" is the setup page's camera test: the phone shows the picture on its own screen and says
whether it works and which codes it read; pictures never leave the phone.
"look" turns the front camera on: the phone finds faces itself and sends only where they are ("faces");
with "familiar" it also tells them apart, by a signature it keeps in its memory for this session.
Neither pictures nor signatures leave the phone, and a "faces" message cannot carry them.

"screen" says what the phone's screen shows (mode, expression, the tiles, the words as keys of texts.js): the bridge
passes it on to the mirrors (its Webots twin), with a copy of all it sends the phone, so the twin's screen follows the
real one. Keys only: a sentence the phone reads aloud is never in it.

A phone is not trusted: parse() returns a clean message or raises ValueError,
and every number is finite and clamped.
"""
import base64
import json
import math
import re

from . import contract as c

ZONES = ("left", "centre", "right")
TOUCHES = ("tap", "long", "swipe")
DIRS = ("left", "right", "up", "down")
PAGES = ("face.html", "check.html")   # where the setup page may send the phone
LAYOUTS = ("landscape", "portrait", "auto")   # face.html?layout=...
BUTTON_ID = re.compile(r"[A-Za-z0-9_-]{1,20}")
MAX_FRAME = 96 * 1024       # bytes of a show frame, as base64 (a 320 px JPEG is about 15-30 KB)


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


def _id(v, what) -> str:
    if not isinstance(v, str) or not BUTTON_ID.fullmatch(v):
        raise ValueError(f"{what}: an id is letters, digits, - and _")
    return v


def _label(v, n=16):
    """A label: text, or {"en", "fr", "de"} (each optional)."""
    if isinstance(v, dict):
        out = {k: _text(v[k], n) for k in c.LANGS if isinstance(v.get(k), str)}
        if not out:
            raise ValueError("a label needs a text")
        return out
    return _text(v, n)


VISION = ("markers", "blobs", "objects", "hands")


def _vision(t: str, m: dict) -> dict:
    """markers, blobs, objects, hands: only their own fields, each clamped, at most MAX_ITEMS."""
    items = m.get(t)
    if not isinstance(items, list):
        raise ValueError(f"{t}: not a list")
    out = []
    for it in items[:c.MAX_ITEMS]:
        if not isinstance(it, dict):
            raise ValueError(f"{t}: not an object")
        o = {"x": _num(it.get("x"), -1, 1), "y": _num(it.get("y"), -1, 1)}
        if t == "markers":
            o.update(id=int(_num(it.get("id"), 0, 999)), size=_num(it.get("size", 0), 0, 1),
                     distance_m=None if it.get("distance_m") is None else _num(it["distance_m"], 0, 100),
                     yaw_deg=None if it.get("yaw_deg") is None else _num(it["yaw_deg"], -180, 180))
        elif t == "blobs":
            o["size"] = _num(it.get("size"), 0, 1)
        elif t == "objects":
            o.update(label=_one_of(it.get("label"), c.OBJECTS), score=_num(it.get("score"), 0, 1),
                     w=_num(it.get("w"), 0, 2), h=_num(it.get("h"), 0, 2),
                     distance_m=None if it.get("distance_m") is None else _num(it["distance_m"], 0, 100))
        else:
            o["gesture"] = _one_of(it.get("gesture", "none"), c.GESTURES)
        out.append(o)
    return {"t": t, "camera": _one_of(m.get("camera", "front"), c.CAMERAS), t: out}


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
    if t == "look":  # what the front camera does now
        out = {"t": "look", "on": bool(m.get("on")), "ok": bool(m.get("ok")), "familiar": bool(m.get("familiar"))}
        if m.get("error"):
            out["error"] = _text(m["error"], 80)
        return out
    if t == "faces":  # only these fields, each clamped: nothing else of a face can pass
        fs = m.get("faces")
        if not isinstance(fs, list):
            raise ValueError("faces: not a list")
        faces = []
        for f in fs[:c.MAX_FACES]:
            if not isinstance(f, dict):
                raise ValueError("faces: not an object")
            fam = f.get("familiar")
            faces.append({"x": _num(f.get("x"), -1, 1), "y": _num(f.get("y"), -1, 1), "size": _num(f.get("size"), 0, 1),
                          "familiar": None if fam is None else int(_num(fam, 1, c.MAX_FACES))})
        out = {"t": "faces", "n": len(faces), "faces": faces}
        if "period" in m:  # ms between two searches: how fast this phone finds faces
            out["period"] = int(_num(m["period"], 0, 60000))
        return out
    if t in VISION:
        return _vision(t, m)
    if t == "panel":  # the person picked another mode in the menu
        return {"t": "panel", "mode": _one_of(m.get("mode"), c.PANEL_MODES)}
    if t == "menu":  # the person picked a tile or a chip (a mode, a TILE, or a program's own entry)
        return {"t": "menu", "id": _id(m.get("id"), "menu")}
    if t == "answer":  # a note card's button
        return {"t": "answer", "note": _id(m.get("note", "note"), "answer"), "id": _id(m.get("id"), "answer")}
    if t == "read":  # read aloud on the phone: how it went, never the text
        out = {"t": "read", "ok": bool(m.get("ok")), "lines": int(_num(m.get("lines", 0), 0, 1000)),
               "chars": int(_num(m.get("chars", 0), 0, 100000)), "ms": int(_num(m.get("ms", 0), 0, 600000))}
        if m.get("error"):
            out["error"] = _text(m["error"], 80)
        return out
    if t == "what":  # what the phone said it sees
        ok = bool(m.get("ok"))
        label = m.get("label")  # None: it looked and knew nothing there
        return {"t": "what", "ok": ok, "label": _one_of(label, c.OBJECTS) if ok and label is not None else None,
                "score": _num(m.get("score", 0), 0, 1), "ms": int(_num(m.get("ms", 0), 0, 600000))}
    if t == "show":  # the person started or stopped showing
        return {"t": "show", "on": bool(m.get("on"))}
    if t == "frame":  # a show frame: a JPEG, and nothing else
        data = m.get("jpeg")
        if not isinstance(data, str) or len(data) > MAX_FRAME:
            raise ValueError("frame: not a small JPEG")
        try:
            jpeg = base64.b64decode(data, validate=True)
        except ValueError:
            raise ValueError("frame: not base64") from None
        if not (jpeg.startswith(b"\xff\xd8") and jpeg.rstrip(b"\0").endswith(b"\xff\xd9")):
            raise ValueError("frame: not a JPEG")
        return {"t": "frame", "jpeg": jpeg}
    if t == "see":  # what the camera finds now, and how long each finder takes
        out = {"t": "see", "on": bool(m.get("on")), "ok": bool(m.get("ok")),
               "camera": _one_of(m.get("camera", "front"), c.CAMERAS),
               "find": [f for f in m.get("find", []) if f in c.FINDERS][:len(c.FINDERS)] if isinstance(m.get("find"), list) else [],
               "ms": {k: int(_num(v, 0, 60000)) for k, v in (m.get("ms") or {}).items() if k in c.FINDERS}
               if isinstance(m.get("ms"), dict) else {}}
        if m.get("backend"):
            out["backend"] = _text(m["backend"], 60)
        if "follow" in m:
            out["follow"] = bool(m["follow"])
        tg = m.get("target")
        if isinstance(tg, dict) and tg.get("kind") in ("faces", "hands", "markers", "objects"):  # what the eyes follow
            out["target"] = {"kind": tg["kind"], "x": _num(tg.get("x"), -1, 1), "y": _num(tg.get("y"), -1, 1)}
        if m.get("error"):
            out["error"] = _text(m["error"], 80)
        return out
    if t == "screen":  # what the screen shows: keys and ids only, for the mirrors
        return screen_report(m)
    if t == "pad":
        if not isinstance(m.get("id"), str) or not BUTTON_ID.fullmatch(m["id"]):
            raise ValueError("pad: not a button id")
        return {"t": "pad", "id": m["id"]}
    if t == "code":
        text = _text(m.get("text"), c.MAX_SAY).strip()
        if not text:
            raise ValueError("code: empty")
        return {"t": "code", "text": text}
    raise ValueError(f"unknown message {t!r}")


def screen_report(m: dict) -> dict:
    """The phone's screen report, checked: an unknown key is dropped (""), so no free text can pass."""
    toast = m.get("toast") or ""
    ok_toast = toast in c.SCREEN_TOASTS or (toast.startswith("tour.") and toast[5:] in c.TOUR_STEPS) if isinstance(toast, str) else False
    ids = lambda v: v if isinstance(v, str) and BUTTON_ID.fullmatch(v) else ""
    tiles = m.get("tiles") if isinstance(m.get("tiles"), list) else []
    return {"t": "screen", "lang": m.get("lang") if m.get("lang") in c.LANGS else "en",
            "mode": m.get("mode") if m.get("mode") in c.PANEL_MODES else "mouth",
            "expression": m.get("expression") if m.get("expression") in c.EXPRESSIONS else "neutral",
            "style": m.get("style") if m.get("style") in c.PANEL_STYLES else "chips",
            "menu": bool(m.get("menu")), "tiles": [i for i in map(ids, tiles[:c.MAX_MENU + 1]) if i],
            "hi": ids(m.get("hi")), "toast": toast if ok_toast else "",
            "arg": m.get("arg") if ok_toast and toast in ("is", "think") and m.get("arg") in c.OBJECTS else "",
            "note": ids(m.get("note")), "badge": bool(m.get("badge")), "allowed": bool(m.get("allowed")),
            "speaking": bool(m.get("speaking")),
            "sensors": sensor_report(m.get("sensors"))}


def sensor_report(s) -> dict:
    """What the sensors panel shows, as numbers (the battery, the tilt, the compass): only while it shows. Never the
    location, which the phone keeps on its own screen."""
    if not isinstance(s, dict):
        return {}
    try:
        return _sensors(s)
    except ValueError:  # a number that is none: the panel's numbers are left out, the report stays
        return {}


def _sensors(s: dict) -> dict:
    out = {}
    if s.get("battery") is not None:
        out["battery"] = round(_num(s["battery"], 0, 1), 2)
        out["charging"] = bool(s.get("charging"))
    if s.get("heading") is not None:
        out["heading"] = round(_num(s["heading"], 0, 360))
    acc = s.get("acc")
    if isinstance(acc, list) and len(acc) == 3:
        out["acc"] = [round(_num(v, -40, 40), 1) for v in acc]
    return out


def prop(name) -> dict:
    """A prop for the Webots twin's demo (the mirror socket only: a real phone never gets one)."""
    return {"t": "prop", "name": _one_of(name, c.PROPS)}


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


def look(on: bool, familiar: bool = False) -> dict:
    return {"t": "look", "on": bool(on), "familiar": bool(on and familiar)}


def forget() -> dict:
    return {"t": "forget"}


def vibrate(ms: int) -> dict:
    return {"t": "vibrate", "ms": int(_num(ms, 0, c.MAX_VIBRATE))}


def open_page(page: str, layout: str = "") -> dict:
    out = {"t": "open", "page": _one_of(page, PAGES)}
    if layout:
        out["layout"] = _one_of(layout, LAYOUTS)
    return out


def panel(data: str) -> dict:
    """JSON {"mode", "buttons"?}: the lower half of the face in portrait. Buttons: id, label (≤12), color 0..1."""
    try:
        m = json.loads(data)
    except ValueError:
        raise ValueError("panel: not JSON") from None
    if not isinstance(m, dict):
        raise ValueError("panel: not an object")
    out = {"t": "panel", "mode": _one_of(m.get("mode"), c.PANEL_MODES)}
    if "style" in m:
        out["style"] = _one_of(m["style"], c.PANEL_STYLES)
    if "lang" in m:  # the face's words and voice (Omi Assist: German, whatever the phone's own); auto: the phone's again
        out["lang"] = _one_of(m["lang"], c.LANGS + ("auto",))
    if "menu" in m:
        if not isinstance(m["menu"], list) or not m["menu"]:
            raise ValueError("panel: menu is a list of modes and tiles")
        menu, seen = [], set()
        for x in m["menu"][:4 * c.MAX_MENU]:
            if isinstance(x, str):  # a mode, or one of the phone's own tiles
                e = _one_of(x, c.PANEL_MODES + c.TILES)
                key = e
            elif isinstance(x, dict):  # a program's own tile: its pick goes to ROS (menu)
                e = {"id": _id(x.get("id"), "panel: menu"), "label": _label(x.get("label", x.get("id")))}
                if x.get("icon"):
                    e["icon"] = _text(x["icon"], 4)
                key = e["id"]
            else:
                raise ValueError("panel: a menu entry is a mode, a tile or {id, label, icon}")
            if key not in seen and len(menu) < c.MAX_MENU:  # the same twice: once; at most MAX_MENU
                seen.add(key)
                menu.append(e)
        out["menu"] = menu
    if "buttons" in m:
        if not isinstance(m["buttons"], list):
            raise ValueError("panel: buttons is not a list")
        out["buttons"] = []
        for b in m["buttons"][:c.MAX_BUTTONS]:
            if not isinstance(b, dict) or not isinstance(b.get("id"), str) or not BUTTON_ID.fullmatch(b["id"]):
                raise ValueError("panel: a button needs an id (letters, digits, - and _)")
            rgb = b.get("color", [0.25, 0.85, 1.0])
            if not isinstance(rgb, (list, tuple)) or len(rgb) != 3:
                raise ValueError("panel: color is [r, g, b]")
            out["buttons"].append({"id": b["id"], "label": _text(b.get("label", b["id"]), 12),
                                   "rgb": [round(_num(v, 0, 1) * 255) for v in rgb]})
    return out


def see(data: str) -> dict:
    """JSON {"camera", "find", "blob": {"hue", "tol"}, "marker_cm", "fov_deg"}: what the phone's camera should find."""
    try:
        m = json.loads(data)
    except ValueError:
        raise ValueError("see: not JSON") from None
    if not isinstance(m, dict):
        raise ValueError("see: not an object")
    find = m.get("find", [])
    if not isinstance(find, list):
        raise ValueError("see: find is a list")
    out = {"t": "see", "camera": _one_of(m.get("camera", "front"), c.CAMERAS),
           "find": list(dict.fromkeys(_one_of(f, c.FINDERS) for f in find))}
    blob = m.get("blob") or {}
    if not isinstance(blob, dict):
        raise ValueError("see: blob is {hue, tol}")
    out["blob"] = {"hue": _num(blob.get("hue", 0)) % 360, "tol": _num(blob.get("tol", 20), 1, 90)}
    out["marker_cm"] = _num(m.get("marker_cm", 5), 0.5, 100)
    if m.get("follow"):
        out["follow"] = True
    if m.get("fov_deg") is not None:
        out["fov_deg"] = _num(m["fov_deg"], 20, 140)
    return out


def note(data: str) -> dict:
    """JSON {"id", "text", "buttons": [{"id", "label"}], "say"}: a card over the face; an empty text takes it away."""
    try:
        m = json.loads(data)
    except ValueError:
        raise ValueError("note: not JSON") from None
    if not isinstance(m, dict):
        raise ValueError("note: not an object")
    out = {"t": "note", "id": _id(m.get("id", "note"), "note"), "text": _text(m.get("text", ""), c.MAX_SAY).strip(),
           "say": bool(m.get("say", True)), "buttons": []}
    bs = m.get("buttons", [])
    if not isinstance(bs, list):
        raise ValueError("note: buttons is a list")
    for b in bs[:c.MAX_NOTE_BUTTONS]:
        if not isinstance(b, dict):
            raise ValueError("note: a button is {id, label}")
        out["buttons"].append({"id": _id(b.get("id"), "note"), "label": _label(b.get("label", b.get("id")), 20)})
    return out


def ask(kind: str, data: str = "", default_lang: str = "en") -> dict:
    """read or what: JSON {"lang"} (or nothing): the phone does it with its back camera, and speaks."""
    lang = default_lang
    if data and data.strip():
        try:
            m = json.loads(data)
        except ValueError:
            raise ValueError(f"{kind}: not JSON") from None
        lang = m.get("lang", default_lang) if isinstance(m, dict) else default_lang
    return {"t": _one_of(kind, ("read", "what")), "lang": _one_of(lang, c.LANGS)}


def tour(lang: str) -> dict:
    """Omi Assist's presentation: the phone says what it can, tile by tile (the setup page's "Introduce")."""
    return {"t": "tour", "lang": _one_of(lang, c.LANGS)}


def show(allowed: bool, on: bool = False) -> dict:
    """Whether the phone may show its picture to this PC (the facilitator's choice), and whether to stop now."""
    return {"t": "show", "allowed": bool(allowed), "on": bool(allowed and on)}

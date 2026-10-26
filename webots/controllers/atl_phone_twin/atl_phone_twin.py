#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""atl_phone_twin — the phone's Webots twin: an AtlPhone in Webots that speaks the face page's protocol to the bridge.

    (in the atl-phone-twin image, Webots on the host; see the README)
    WEBOTS_CONTROLLER_URL=tcp://127.0.0.1:1240/PH5v0001 python3 atl_phone_twin.py --bridge ws://127.0.0.1:8782/ws [--model ANE-LX1]
    ... python3 atl_phone_twin.py --mirror ws://127.0.0.1:8782/ws/mirror

Two ways to run (contract atl-phone/0.6):
- as the phone (--bridge): the bridge cannot tell it from a real phone, so ROS sees the same topics and a program (the
  Desk Guardian) runs unchanged against the real phone and against this twin;
- as a mirror (--mirror): the real phone is in charge, and the twin's screen follows it: the bridge sends the twin a
  copy of all it sends the phone, and the phone's screen report (the mode, the expression, the tiles, which words show,
  as keys of texts.js, the sensors panel's numbers: never a sentence read aloud, and no picture, except while she
  shows one with Zeigen: then the bridge also sends it the frames, on this computer only, the setup page's consent).
  The twin then sends nothing and says nothing.
Either way it listens on the mirror socket for the demo's props (webots/props.json): a cup, a letter on an easel, a
letter held in a hand, a visitor, flown in and away (the setup page, or keys 1-4 and 0 in Webots).
What the twin does:
- it rides on its holder (AtlPhone follow: a DEF path), as the supervisor of itself, so it moves with the robot;
- imu: from its own motion (the specific force and the turn rate, in the phone frame), heading from its yaw;
- see and look: Webots' Recognition on its cameras gives "ground truth" vision: a Solid whose model is "face" is a
  face, "aruco:<n>" a marker (its distance from the 3D position), a COCO label an object, and any recognised
  colour within the asked hue a blob. Hands are not simulated;
- face, gaze, color, panel, note: drawn on its screen (a Display) like the page draws them, simpler: the eyes, the
  mouth, the pad, the tiles (the one spoken of in yellow), the words, a card, the red badge; the words come from the
  page's own texts.js; say: its Speaker; torch: its LED; vibrate: shown on the screen; touch: a click on its screen in
  Webots (left, centre or right); the camera views: as the phone, its own Webots camera; mirroring, the real phone's
  frames while Zeigen is on, else a camera symbol; the sensors panel: the phone's numbers (never the location);
- what and read (as the phone): simulated and said so (backend "webots"): the nearest thing the back camera's
  Recognition knows, and the letter's text (webots/letter.json) when the letter is in front of it.
Webots' controller library, numpy for the camera pictures and Pillow for the frames (both in the atl-phone-twin image);
the bridge's MockPhone is the WebSocket client.
"""
import argparse
import json
import math
import os
import queue
import sys
import time
from pathlib import Path
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit

import numpy as np

from controller import Display, Supervisor

try:
    from atl_phone.mock_phone import MockPhone
    from atl_phone import contract as c
except ImportError:  # run from the repository
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ros2", "atl_phone"))
    from atl_phone.mock_phone import MockPhone
    from atl_phone import contract as c

G = 9.81
TWIN_ID = "7717717717717717"            # the page's per-browser id: a fixed one for the twin
SEE_EVERY = 0.1                          # s: vision at 10 Hz, like the page
IMU_EVERY = 1 / 30
EYE = {"w": 0.8, "h": 1.0, "top": 0.0, "bottom": 0.0, "dy": 0.0, "heart": 0}
EXPRESSIONS = {"neutral": {}, "happy": {"bottom": 0.6, "h": 0.9}, "sad": {"top": 0.4, "dy": 0.12, "h": 0.85},
               "angry": {"top": 0.4, "h": 0.85}, "surprised": {"w": 0.95, "h": 1.2}, "sleepy": {"top": 0.62, "dy": 0.1},
               "curious": {"w": 0.85, "h": 1.1}, "wink": {}, "scared": {"w": 0.6, "h": 0.75}, "love": {"heart": 1, "w": 0.9, "h": 0.9}}
MOUTHS = {"neutral": 0.15, "happy": 0.6, "sad": -0.45, "angry": -0.2, "surprised": 0.0, "sleepy": 0.05, "curious": 0.1,
          "wink": 0.4, "scared": -0.15, "love": 0.7}
LANGS = {"en": "en-UK", "fr": "fr-FR", "de": "de-DE"}
WEBOTS_DIR = Path(__file__).resolve().parents[2]       # webots/: props.json, letter.json
PICTURE = {"camera": "front", "camera_back": "back", "magnify": "back"}   # a camera view, and its camera
CAM_BUTTONS = [("minus", "-", ("magnify",)), ("plus", "+", ("magnify",)), ("torch", "*", ("magnify",)), ("hold", "||", ("magnify",)),
               ("what", "?", ("camera_back",)), ("show", "", ("camera", "camera_back", "magnify"))]   # as omi.js's CAM_BUTTONS
NOTE_WORDS = {"en": ["Done", "Later"], "fr": ["Fait", "Plus tard"], "de": ["Erledigt", "Später"]}   # the sample card's (omi.py's)


def load_texts() -> dict:
    """The page's words (web/texts.js, strict JSON after "var TEXTS ="): installed with the package, or the repo's."""
    places = [Path(os.environ.get("ATL_PHONE_WEB", "/nonexistent")), Path("/ws/install/share/atl_phone/web"),
              WEBOTS_DIR.parent / "ros2" / "atl_phone" / "web"]
    for d in places:
        if (d / "texts.js").exists():
            js = (d / "texts.js").read_text()
            return json.loads(js[js.index("var TEXTS = {") + 12:js.rindex("}") + 1])
    return {"icon": {}, "mode": {"en": {}}, "omi": {"en": {}}, "tour": {"en": {}}, "what": {}}


def wrap(text: str, width: int) -> list:
    """Words in lines of at most width characters."""
    out, line = [], ""
    for w in text.split():
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return out + ([line] if line else [])


def seat_of(holder) -> list:
    """Where the phone's screen rests on its holder, in the holder's frame: the old block (12 mm up), or the Omi stack's
    clamp (AtlOmiStack: the Pi's box, the riser, the clamp's neck; the same numbers as the PROTO)."""
    if holder is None or holder.getField("riser") is None:
        return [0.0, 0.0, 0.012]
    pi_h = 0.032 if holder.getField("pi").getSFString() == "5" else 0.0256
    return [0.02, 0.0, pi_h + 0.0032 * max(1, holder.getField("riser").getSFInt32()) + 0.0017 + holder.getField("neck").getSFFloat()]


def mat(rot):
    """Webots' axis-angle -> a 3x3 rotation matrix (rows)."""
    x, y, z, a = rot
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    x, y, z = x / n, y / n, z / n
    c_, s, t = math.cos(a), math.sin(a), 1 - math.cos(a)
    return [[t * x * x + c_, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c_, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c_]]


def axis_angle(R):
    tr = R[0][0] + R[1][1] + R[2][2]
    a = math.acos(max(-1.0, min(1.0, (tr - 1) / 2)))
    if a < 1e-9:
        return [0.0, 0.0, 1.0, 0.0]
    if abs(a - math.pi) < 1e-6:
        x = math.sqrt(max(0.0, (R[0][0] + 1) / 2))
        y = math.copysign(math.sqrt(max(0.0, (R[1][1] + 1) / 2)), R[0][1] or 1)
        z = math.copysign(math.sqrt(max(0.0, (R[2][2] + 1) / 2)), R[0][2] or 1)
        return [x, y, z, a]
    s = 2 * math.sin(a)
    return [(R[2][1] - R[1][2]) / s, (R[0][2] - R[2][0]) / s, (R[1][0] - R[0][1]) / s, a]


def mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(R, v):
    return [sum(R[i][k] * v[k] for k in range(3)) for i in range(3)]


def transpose(R):
    return [[R[j][i] for j in range(3)] for i in range(3)]


def mount(upright: bool, tilt: float, size, seat=(0.0, 0.0, 0.012)):
    """Where the phone's centre sits on its holder, and how it is turned (columns: the phone's x, y, z), in the
    holder's frame: the screen's bottom edge on the seat, the screen to the robot's front (+x), leaning back by tilt."""
    s, co = math.sin(tilt), math.cos(tilt)
    z = [co, 0.0, s]
    if upright:   # portrait: y up the screen, leaning back
        y, half = [-s, 0.0, co], size[1] / 2
    else:         # landscape: the phone's top to the robot's right (seen from the front: to the left)
        y, half = [0.0, -1.0, 0.0], size[0] / 2
    x = [y[1] * z[2] - y[2] * z[1], y[2] * z[0] - y[0] * z[2], y[0] * z[1] - y[1] * z[0]]
    up = [-s, 0.0, co] if not upright else y
    at = [seat[0] + up[0] * half - z[0] * size[2] / 2, seat[1], seat[2] + up[2] * half]
    return at, [[x[i], y[i], z[i]] for i in range(3)]


class Twin:
    def __init__(self, bridge: str, mirror: str, model: str, snap: str = ""):
        self.robot = Supervisor()
        self.snap, self.next_snap = snap, 0.0
        self.dt = self.robot.getBasicTimeStep() / 1000.0
        self.me = self.robot.getSelf()
        self.size = self.me.getField("size").getSFVec3f() if self.me.getField("size") else [0.0747, 0.1585, 0.0077]
        follow = self.robot.getCustomData()  # AtlPhone's follow
        self.holder = self.robot.getFromDef(follow) if follow else None
        self.seat = seat_of(self.holder)
        self.body = self.robot.getFromDef(follow.split(".")[0]) if follow else None   # the robot it rides on
        print(f"{self.robot.getName()}: " + (f"rides on {follow}" if self.holder else f"stands alone (no {follow!r} to ride on)"), flush=True)
        self.screen = self.robot.getDevice("screen")
        self.cams = {"front": self.robot.getDevice("camera_front"), "back": self.robot.getDevice("camera_back")}
        self.speaker = self.robot.getDevice("speaker")
        self.torch = self.robot.getDevice("torch")
        self.mouse = self.robot.getMouse()
        self.mouse.enable(int(self.robot.getBasicTimeStep()))
        self.mouse.enable3dPosition()
        self.keyboard = self.robot.getKeyboard()
        self.keyboard.enable(int(self.robot.getBasicTimeStep()) * 4)
        self.texts = load_texts()
        self.model = model
        self.mirroring = not bridge                     # the real phone is in charge: follow its screen, send nothing
        self.phone = MockPhone(bridge) if bridge else None
        self.mirror = None
        if mirror:
            try:
                self.mirror = MockPhone(mirror)
            except OSError as e:
                if self.mirroring:
                    raise
                print(f"no mirror socket at {mirror} ({e}): no props from the setup page (keys 1-4 still work)", flush=True)
        self.expression, self.color, self.gaze = "neutral", [63, 216, 255], (0.0, 0.0)
        self.panel = {"mode": "mouth", "buttons": [], "menu": list(c.PANEL_MODES)}
        self.shown = None          # mirroring: the phone's last screen report
        self.note = None           # the card over the face (a reminder), as the bridge sent it
        self.toast = ("", "", 0.0)  # simulated helpers (as the phone): key, arg, until
        self.real = {"connected": False, "model": ""}
        self.look, self.familiar, self.see, self.seeing = False, False, {"find": [], "camera": "front"}, False
        self.say_until, self.buzz_until, self.drawn, self.first_picture = 0.0, 0.0, None, 0.0
        self.acc, self.heading = None, None   # its own motion sensors (the sensors panel, as the phone)
        self.frame = (b"", -1.0)  # mirroring: the last frame she showed (Zeigen), and when; never kept on disk
        self.ask = None            # (kind, lang, since): a what or read the twin answers from its back camera
        self.poses = []           # (t, position, R): the last three, for the IMU
        self.t = 0.0
        self.next_see = self.next_draw = 0.0
        self.next_imu = 0.2       # s: after the jump onto the holder, which is no motion
        self.last_click = False
        self.props = json.loads((WEBOTS_DIR / "props.json").read_text())
        self.flying = []           # (node, from, to, t0, seconds, yaw)
        self.prop = ""
        if self.phone:
            w, h = self.cams["front"].getWidth(), self.cams["front"].getHeight()
            self.hello(w, h)

    def hello(self, w, h):
        self.phone.send(t="hello", id=TWIN_ID, ua="Webots twin (atl-phone)", model=f"{self.model} twin", secure=True,
                        caps={"motion": True, "compass": True, "tts": True, "vibrate": False, "battery": True, "wakelock": True,
                              "camera": True, "barcode": False}, screen=[self.screen.getWidth() * 4, self.screen.getHeight() * 4])
        self.phone.send(t="battery", level=0.8, charging=True)

    def send(self, **m):
        if self.phone:
            self.phone.send(**m)

    def lang(self) -> str:
        l = (self.shown or {}).get("lang") if self.mirroring else self.panel.get("lang")
        return l if l in LANGS else "de" if self.mirroring else "en"

    def word(self, table: str, key: str) -> str:
        t = self.texts.get(table, {})
        return (t.get(self.lang()) or t.get("en") or {}).get(key, "")

    # ---- the body: ride on the holder; the IMU from the motion ---------------------------------------------------
    def ride(self):
        if not self.holder:
            return
        hp, hR = self.holder.getPosition(), [self.holder.getOrientation()[i * 3:i * 3 + 3] for i in range(3)]
        up = self.holder.getField("upright").getSFBool() if self.holder.getField("upright") else True
        tilt = self.holder.getField("tilt").getSFFloat() if self.holder.getField("tilt") else 0.2
        at, M = mount(up, tilt, self.size, self.seat)
        p = [hp[i] + apply(hR, at)[i] for i in range(3)]
        R = mul(hR, M)
        self.me.getField("translation").setSFVec3f(p)
        self.me.getField("rotation").setSFRotation(axis_angle(R))

    def imu(self):
        p = self.me.getPosition()
        R = [self.me.getOrientation()[i * 3:i * 3 + 3] for i in range(3)]
        self.poses = (self.poses + [(self.t, p, R)])[-3:]
        if len(self.poses) < 3:
            return
        (t0, p0, _), (t1, p1, R1), (t2, p2, R2) = self.poses
        d1, d2 = max(t1 - t0, 1e-3), max(t2 - t1, 1e-3)
        a = [((p2[i] - p1[i]) / d2 - (p1[i] - p0[i]) / d1) / ((d1 + d2) / 2) for i in range(3)]
        f = apply(transpose(R2), [a[0], a[1], a[2] + G])   # what an accelerometer feels, in the phone frame
        dR = mul(transpose(R1), R2)                         # the turn since the last pose, in the phone frame
        aa = axis_angle(dR)
        w = [aa[i] * aa[3] / d2 for i in range(3)]
        self.send(t="imu", acc=[max(-150.0, min(150.0, v)) for v in f], gyro=w)
        yaw = math.degrees(math.atan2(R2[1][2], R2[0][2]))   # where the screen faces, from +x; north is +y in the table
        self.send(t="heading", deg=(90.0 - yaw) % 360)
        self.acc, self.heading = [round(v, 1) for v in f], round((90.0 - yaw) % 360)

    # ---- what and read, as the phone: from the back camera's Recognition (simulated, and said so) ------------------
    def answer(self):
        kind, l, since = self.ask
        cam = self.cams["back"]
        if self.t < since + 0.4 or not cam.getSamplingPeriod():
            return
        self.ask = None
        objs = cam.getRecognitionObjects() or []
        ms = int((self.t - since) * 1000)
        w = self.texts.get("omi", {}).get(l) or {}
        if kind == "read":
            letter = json.loads((WEBOTS_DIR / "letter.json").read_text())
            if any(o.getModel() == "letter" for o in objs):
                lines = [x for x in letter["lines"] if x]
                self.say(" ".join(lines), letter.get("lang", l))
                self.toast = ("reading", "", self.say_until)
                self.send(t="read", ok=True, lines=len(lines), chars=sum(len(x.replace(" ", "")) for x in lines), ms=ms)
            else:
                self.say(w.get("notext", ""), l)
                self.toast = ("notext", "", self.t + 8)
                self.send(t="read", ok=True, lines=0, chars=0, ms=ms)
            return
        things = [o for o in objs if o.getModel() in c.OBJECTS]
        best = max(things, key=lambda o: o.getSizeOnImage()[0] * o.getSizeOnImage()[1], default=None)
        label = best.getModel() if best else None
        key = "nothing" if not label else "person" if label == "person" else "is"
        name = (self.texts.get("what", {}).get(label) or [label] * 3)[("en", "fr", "de").index(l)] if label else ""
        self.say(w.get(key, "").replace("{x}", name), l)
        self.toast = (key, label if key == "is" else "", self.t + 8)
        self.send(t="what", ok=True, label=label, score=0.99 if label else 0.0, ms=ms)

    def say(self, text: str, l: str):
        if not text or self.mirroring:   # mirroring: the real phone speaks
            return
        self.speaker.setLanguage(LANGS.get(l, "en-UK"))
        self.speaker.speak(text, 1.0)
        self.say_until = self.t + 0.07 * len(text) + 0.5

    # ---- seeing: Recognition, as the page's finders report ---------------------------------------------------
    def finders(self):
        f = list(self.see.get("find", []))
        if self.look and "faces" not in f:
            f.append("faces")
        return f

    def vision(self):
        if self.mirroring:   # the real phone sees
            return
        f = self.finders()
        side = self.see.get("camera", "front") if self.see.get("find") else "front"
        if self.ask:         # a what or a read: the back camera, for a moment
            side = "back"
        pic = PICTURE.get(self.panel.get("mode"))   # a camera view on the screen: that camera's picture
        for name, cam in self.cams.items():
            on = ((bool(f) or bool(self.ask)) and name == side) or name == pic
            if on and cam.getSamplingPeriod() == 0:
                cam.enable(100)
                cam.recognitionEnable(100)
                self.first_picture = self.t + 0.25   # like a phone: nothing to say before the first picture
            elif not on and cam.getSamplingPeriod():
                cam.recognitionDisable()
                cam.disable()
        if self.ask:
            return self.answer()
        if not f:
            if self.seeing:
                self.seeing = False
                self.send(t="see", on=False, ok=True, camera=side, find=[])
            return
        self.seeing = True
        if self.t < self.first_picture:
            return
        cam = self.cams[side]
        w, h, front = cam.getWidth(), cam.getHeight(), side == "front"
        fov = cam.getFov()
        objs = cam.getRecognitionObjects() or []
        faces, markers, objects, blobs = [], [], [], []
        for o in objs:
            model = o.getModel()
            px, py = o.getPositionOnImage()
            sw, sh = o.getSizeOnImage()
            x = (1 - 2 * px / w) if front else (2 * px / w - 1)
            y = 1 - 2 * py / h
            pos = o.getPosition()
            dist = round(math.sqrt(sum(v * v for v in pos)), 3)
            if model == "face":
                faces.append({"x": x, "y": y, "size": min(1.0, sh / h), "familiar": None})
            elif model.startswith("aruco:") and model[6:].isdigit():
                ori = o.getOrientation()
                Rm = mat(ori) if len(ori) == 4 else [ori[0:3], ori[3:6], ori[6:9]]
                n = [Rm[0][0], Rm[1][0]]           # the marker's face (its local x), in the camera's frame (x ahead)
                if n[0] > 0:                        # the side we see
                    n = [-n[0], -n[1]]
                yaw = math.degrees(math.atan2(n[1], -n[0]))   # 0: square on; > 0: it faces the camera's left
                markers.append({"id": int(model[6:]), "x": x, "y": y, "size": min(1.0, sh / h), "distance_m": dist,
                                "yaw_deg": round(yaw, 1)})
            elif model in c.OBJECTS:
                objects.append({"label": model, "score": 0.99, "x": x, "y": y, "w": sw / w, "h": sh / h, "distance_m": dist})
            if "blobs" in f and o.getNumberOfColors():
                colours = o.getColors()
                r, g, b = colours[0], colours[1], colours[2]
                mx, mn = max(r, g, b), min(r, g, b)
                if mx > 0.2 and mx - mn > 0.3 * mx:
                    hh = (((g - b) / (mx - mn)) % 6 if mx == r else (b - r) / (mx - mn) + 2 if mx == g else (r - g) / (mx - mn) + 4) * 60
                    want = self.see.get("blob", {"hue": 0, "tol": 20})
                    dh = abs(hh - want["hue"]) % 360
                    if min(dh, 360 - dh) <= want["tol"]:
                        blobs.append({"x": x, "y": y, "size": min(1.0, sh / h)})
        size = lambda v: -v.get("size", v.get("h", 0))
        if "faces" in f:
            self.send(t="faces", faces=sorted(faces, key=size)[:8], period=int(SEE_EVERY * 1000))
        if "markers" in f:
            self.send(t="markers", camera=side, markers=markers[:8])
        if "objects" in f:
            self.send(t="objects", camera=side, objects=sorted(objects, key=size)[:8])
        if "blobs" in f:
            self.send(t="blobs", camera=side, blobs=sorted(blobs, key=size)[:8])
        if "hands" in f:
            self.send(t="hands", camera=side, hands=[])
        if math.isfinite(fov):
            self.send(t="see", on=True, ok=True, camera=side, find=f, ms={k: 1 for k in f}, backend="webots")

    # ---- what the bridge asks (as the phone), and what the mirror socket brings ----------------------------------
    def handle(self, m, mirrored=False):
        t = m.get("t")
        if t == "prop":
            return self.fly(m.get("name", ""))
        if t == "phone":
            self.real = {"connected": bool(m.get("connected")), "model": str(m.get("model", ""))[:40]}
            return
        if mirrored and not self.mirroring:   # the twin is the phone: the copies are what it was sent already
            return
        if t == "screen":
            self.shown = m
            self.expression = m.get("expression", self.expression)
        elif t == "frame":   # she shows (Zeigen): the bridge sends it to mirrors on this computer only
            try:
                import base64
                self.frame = (base64.b64decode(m.get("jpeg", ""), validate=True), self.t)
            except ValueError:
                pass
        elif t == "face":
            self.expression = m["expression"]
        elif t == "gaze":
            self.gaze = (m["x"], m["y"])
        elif t == "color":
            self.color = m["rgb"]
        elif t == "say":
            self.say(m["text"], m.get("lang"))
        elif t == "torch":
            self.torch.set(1 if m["on"] else 0)
            self.send(t="camera", on=False, ok=True, torch=bool(m["on"]))
        elif t == "camera":
            self.send(t="camera", on=bool(m["on"]), ok=True, size=[self.cams["back"].getWidth(), self.cams["back"].getHeight()])
        elif t == "vibrate":
            self.buzz_until = self.t + m["ms"] / 1000.0
        elif t == "look":
            self.look, self.familiar = m["on"], m.get("familiar", False)
            self.send(t="look", on=self.look, ok=True, familiar=False)  # the twin tells no faces apart
            if not self.look:
                self.send(t="faces", faces=[])
        elif t == "see":
            self.see = m
        elif t == "panel":
            self.panel.update({k: v for k, v in m.items() if k in ("mode", "buttons", "menu", "style", "lang")})
        elif t == "note":
            self.note = m if m.get("text") else None
        elif t in ("what", "read") and not self.mirroring:
            self.ask = (t, m.get("lang") if m.get("lang") in LANGS else self.lang(), self.t)
            self.say(self.word("omi", "wait" if t == "what" else "reading"), self.ask[1])

    # ---- the props: flown in where the robot's cameras look, and away ---------------------------------------------
    def fly(self, name: str):
        pr = self.props
        if name != "away" and not isinstance(pr.get(name), dict):
            return
        park = pr["park"]
        for k, v in pr.items():  # one at a time: the others go
            if isinstance(v, dict) and k != name:
                node = self.robot.getFromDef(v["def"])
                if node and node.getPosition()[2] > park[2] + 0.5:
                    self.flying.append((node, node.getPosition(), [node.getPosition()[0], node.getPosition()[1], node.getPosition()[2] + 0.6], self.t, 0.8, None, True))
        self.prop = "" if name == "away" else name
        if name == "away":
            return
        v = pr[name]
        node = self.robot.getFromDef(v["def"])
        if not node or not self.body:
            return
        bp = self.body.getPosition()
        bR = [self.body.getOrientation()[i * 3:i * 3 + 3] for i in range(3)]
        yaw = math.atan2(bR[1][0], bR[0][0])
        where = lambda a: [bp[0] + math.cos(yaw) * a[0] - math.sin(yaw) * a[1], bp[1] + math.sin(yaw) * a[0] + math.cos(yaw) * a[1], bp[2] - 0.0005 + a[2]]
        to = where(v["at"])
        start = where(v["from"]) if "from" in v else [to[0], to[1], to[2] + 0.6]
        print(f"prop: {name}", flush=True)
        self.flying.append((node, start, to, self.t, float(pr.get("fly_s", 1.5)), yaw, False))

    def animate(self):
        left = []
        for node, a, b, t0, dur, yaw, park in self.flying:
            k = min(1.0, (self.t - t0) / dur)
            e = k * k * (3 - 2 * k)
            node.getField("translation").setSFVec3f([a[i] + (b[i] - a[i]) * e for i in range(3)])
            if yaw is not None:
                node.getField("rotation").setSFRotation([0, 0, 1, yaw])
            if k < 1:
                left.append((node, a, b, t0, dur, yaw, park))
            elif park:
                node.getField("translation").setSFVec3f(self.props["park"])
        self.flying = left

    def keys(self):
        k = self.keyboard.getKey()
        while k != -1:
            ch = chr(k & 0xFFFF) if 0 < (k & 0xFFFF) < 0x110000 else ""
            if ch == "0":
                self.fly("away")
            for name, v in self.props.items():
                if isinstance(v, dict) and v.get("key") == ch:
                    self.fly(name)
            k = self.keyboard.getKey()

    def click(self):
        st = self.mouse.getState()
        down = st.left
        if down and not self.last_click and st.x == st.x:  # NaN when the click is not on a 3D point
            p = [st.x, st.y, st.z]
            me, R = self.me.getPosition(), [self.me.getOrientation()[i * 3:i * 3 + 3] for i in range(3)]
            q = apply(transpose(R), [p[i] - me[i] for i in range(3)])
            if abs(q[0]) < self.size[0] / 2 and abs(q[1]) < self.size[1] / 2 and q[2] > 0:
                zone = "left" if q[0] < -self.size[0] / 6 else "right" if q[0] > self.size[0] / 6 else "centre"
                self.send(t="touch", kind="tap", zone=zone)
        self.last_click = down

    # ---- the screen: the eyes, and the panel's mouth, pad, tiles, words and card, simpler than the page -----------
    def state(self) -> dict:
        """What the screen shows: the real phone's report when mirroring, else the twin's own."""
        if self.mirroring:
            sh = dict(self.shown or {"mode": "mouth", "expression": self.expression, "menu": False})
            if not self.real["connected"]:
                sh.update(menu=False, toast="", note="", badge=False)
            return sh
        key, arg, until = self.toast
        return {"mode": self.panel.get("mode", "mouth"), "expression": self.expression, "style": self.panel.get("style", "chips"),
                "menu": False, "tiles": [], "hi": "", "toast": key if self.t < until else "", "arg": arg,
                "note": (self.note or {}).get("id", ""), "badge": False, "speaking": self.t < self.say_until,
                "sensors": {"acc": self.acc, "heading": self.heading} if self.panel.get("mode") == "sensors" else {}}

    def toast_text(self, key: str, arg: str) -> str:
        if key == "time":
            l, d = self.lang(), time.localtime()
            return {"en": f"It is {d.tm_hour}:{d.tm_min:02d}.", "fr": f"Il est {d.tm_hour} h {d.tm_min:02d}.",
                    "de": f"Es ist {d.tm_hour}:{d.tm_min:02d} Uhr."}[l]
        if key.startswith("tour."):
            return self.word("tour", key[5:])
        text = self.word("omi", key)
        if arg:
            name = (self.texts.get("what", {}).get(arg) or [arg] * 3)[("en", "fr", "de").index(self.lang())]
            text = text.replace("{x}", name)
        return text

    def card(self, note_id: str):
        """The card's text and buttons: the reminder the bridge sent, or the presentation's sample."""
        if note_id == "tour":
            return self.word("tour", "card"), NOTE_WORDS[self.lang()]
        if self.note and self.note.get("id") == note_id:
            l = self.lang()
            labels = [b.get("label") for b in self.note.get("buttons", [])]
            return self.note.get("text", ""), [x.get(l) or next(iter(x.values()), "") if isinstance(x, dict) else str(x) for x in labels]
        return "", []

    def text(self, s: str, x: int, y: int, size: int, rgb: int = 0xffffff):
        d = self.screen
        d.setFont("Arial", size, True)
        d.setColor(rgb)
        d.drawText(s, x, y)

    def draw(self):
        st = self.state()
        speaking = bool(st.get("speaking")) if self.mirroring else self.t < self.say_until
        blink = 0.1 if (self.t % 4) < 0.15 else 1.0
        key = (json.dumps(st, sort_keys=True), tuple(self.color), round(self.gaze[0], 1), round(self.gaze[1], 1), json.dumps(self.panel),
               json.dumps(self.note), speaking and int(self.t * 10), self.t < self.buzz_until, blink, self.real["connected"],
               st.get("mode") in PICTURE and int(self.t * 10))
        if key == self.drawn:
            return
        self.drawn = key
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        rgb = (self.color[0] << 16) | (self.color[1] << 8) | self.color[2]
        expression = st.get("expression", self.expression)
        d.setAlpha(1.0)
        d.setColor(0x000000)
        d.fillRectangle(0, 0, W, H)
        mode = st.get("mode", "mouth")
        split = mode != "off"
        tiles_up = st.get("menu") and st.get("style") == "tiles"
        eye_h = int(H * 0.25) if tiles_up else int(H * 0.54) if split else H
        base = min(W * 0.32, eye_h * 0.55)
        e = dict(EYE, **EXPRESSIONS.get(expression, {}))
        for side in (-1, 1):
            cx = W / 2 + side * W * 0.22 + self.gaze[0] * base * 0.35
            cy = eye_h / 2 - self.gaze[1] * base * 0.25 + e["dy"] * base
            w, h = e["w"] * base, e["h"] * base * blink
            if expression == "wink" and side == 1:
                h = e["h"] * base * 0.25
            if e["heart"]:
                d.setColor(0xff5a96)
                r = int(base * 0.27)
                d.fillOval(int(cx - r * 0.9), int(cy - r * 0.5), r, r)
                d.fillOval(int(cx + r * 0.9), int(cy - r * 0.5), r, r)
                d.fillPolygon([int(cx - r * 1.85), int(cx + r * 1.85), int(cx)], [int(cy - r * 0.2), int(cy - r * 0.2), int(cy + base * 0.5)])
                continue
            d.setColor(rgb)
            r = int(min(w, h) * 0.28)
            x0, y0 = int(cx - w / 2), int(cy - h / 2)
            d.fillRectangle(x0 + r, y0, int(w) - 2 * r, int(h))
            d.fillRectangle(x0, y0 + r, int(w), max(1, int(h) - 2 * r))
            for ox, oy in ((x0 + r, y0 + r), (x0 + int(w) - r, y0 + r), (x0 + r, y0 + int(h) - r), (x0 + int(w) - r, y0 + int(h) - r)):
                d.fillOval(ox, oy, r, r)
            d.setColor(0x000000)
            if e["top"] > 0.01:
                d.fillRectangle(x0 - 4, y0 - 4, int(w) + 8, int(e["top"] * h) + 4)
            if e["bottom"] > 0.01:
                d.fillOval(int(cx), int(y0 + h + h * 0.55 - e["bottom"] * h * 0.8), int(w / 2 + 6), int(h * 0.6))
        top = eye_h
        if tiles_up:
            self.draw_tiles(st, top)
        elif split:
            self.draw_panel(mode, top, speaking, rgb, expression, st)
        note_id = st.get("note") or ""
        if note_id:
            self.draw_card(note_id)
        if st.get("toast"):
            self.draw_toast(self.toast_text(st["toast"], st.get("arg", "")), top_of_screen=bool(tiles_up))
        if st.get("badge"):
            d.setColor(0xd0302a)
            d.fillRectangle(W // 2 - 50, 4, 100, 22)
            self.text("● " + (self.word("mode", "showing") or "SHOWING"), W // 2 - 44, 7, 14)
        if self.mirroring and not self.real["connected"]:
            self.text("…", W - 24, 6, 16, 0x808080)   # no real phone to follow
        if self.t < self.buzz_until:
            self.text("bzz", W - 40, 8, 12, 0xe0b341)

    def draw_panel(self, mode, top, speaking, rgb, expression, st):
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        d.setColor(rgb)
        if mode == "mouth":
            cy, mw = top + (H - top) * 0.45, W * 0.42
            if speaking:  # the sound wave, as the page draws it
                xs = [int(W * 0.1 + W * 0.8 * i / 31) for i in range(32)]
                ys = [int(cy + math.sin(i * 1.7 + self.t * 22) * (H - top) * 0.15 * math.sin(math.pi * i / 31)) for i in range(32)]
                for i in range(31):
                    d.drawLine(xs[i], ys[i], xs[i + 1], ys[i + 1])
            else:
                bend = MOUTHS.get(expression, 0.15) * (H - top) * 0.18
                pts = [(W / 2 - mw / 2 + mw * i / 20, cy - bend / 2 + bend * 2 * (1 - (2 * i / 20 - 1) ** 2)) for i in range(21)]
                for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                    for k in range(-2, 3):
                        d.drawLine(int(ax), int(ay) + k, int(bx), int(by) + k)
        elif mode == "pad":
            bs = self.panel.get("buttons") or [{"id": k, "label": k.upper()} for k in "abcd"]
            cols = 2 if len(bs) <= 4 else 3 if len(bs) <= 6 else 4
            rows = (len(bs) + cols - 1) // cols
            bw, bh = (W - 16) / cols, (H - top - 16) / rows
            for i, b in enumerate(bs):
                x, y = int(8 + (i % cols) * bw), int(top + 8 + (i // cols) * bh)
                col = b.get("rgb") or self.color
                d.setColor((col[0] << 16) | (col[1] << 8) | col[2])
                d.drawRectangle(x + 3, y + 3, int(bw) - 6, int(bh) - 6)
                d.drawText(str(b.get("label", b["id"]))[:12], x + 10, y + int(bh / 2) - 4)
        elif mode == "sensors":
            self.draw_sensors(st.get("sensors") or {}, top)
        elif mode in PICTURE:
            if not self.draw_picture(mode, top, st):   # no picture to show: a camera symbol, as the picture stays on the phone
                d.drawRectangle(8, top + 8, W - 16, H - top - 16)
                cx, cy = W // 2, top + (H - top) // 2
                d.fillRectangle(cx - 34, cy - 18, 68, 44)
                d.fillRectangle(cx - 12, cy - 26, 24, 10)
                d.setColor(0x000000)
                d.fillOval(cx, cy + 4, 14, 14)
                word = {"camera": "front", "camera_back": "back", "magnify": "magnify"}[mode]
                self.text(self.word("mode", word), 16, top + 16, 14, rgb)
            self.draw_cam_buttons(mode, st)

    def draw_sensors(self, s: dict, top: int):
        """The sensors panel's tiles, as the page draws them: two across. The location stays on the phone."""
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        none = self.word("mode", "none") or "-"
        b = s.get("battery")
        acc, hd = s.get("acc"), s.get("heading")
        link = ("● " if self.real["connected"] else "○ ") if self.mirroring else "● twin"
        vision = "" if self.mirroring else ",".join(self.finders())
        tiles = [("battery", f"{round(b * 100)}%" + (" +" if s.get("charging") else "") if b is not None else none),
                 ("tilt", " ".join(f"{v:.1f}" for v in acc) if acc else none),
                 ("compass", f"{hd}°" if hd is not None else none),
                 ("location", none), ("link", link), ("vision", vision or none), ("pressed", none)]
        rows = (len(tiles) + 1) // 2
        tw, th = (W - 12) / 2, (H - top - 8) / rows
        for i, (k, v) in enumerate(tiles):
            x, y = int(6 + (i % 2) * tw), int(top + 4 + (i // 2) * th)
            d.setColor(0x1d5d6e)
            d.drawRectangle(x + 2, y + 2, int(tw) - 4, int(th) - 4)
            self.text(self.word("mode", k) or k, x + 8, y + 6, 11, 0x7fb7c4)
            self.text(v[:14], x + 8, y + int(th / 2), 15, 0x3fd8ff)
        if acc:   # the tilt's bubble, in the tile's right
            cx, cy = int(6 + 2 * tw) - 18, int(top + 4 + 16)   # beside its label, clear of the numbers (ovals: centre, radii)
            d.setColor(0x1d5d6e)
            d.drawOval(cx, cy, 9, 9)
            d.setColor(0x3fd8ff)
            d.fillOval(int(cx + max(-1, min(1, -acc[0] / 9.81)) * 6), int(cy + max(-1, min(1, acc[1] / 9.81)) * 6), 3, 3)

    def draw_picture(self, mode: str, top: int, st: dict) -> bool:
        """The camera view's picture in the panel: as the phone, its own Webots camera; mirroring, the frame she shows
        (Zeigen, fresh within 3 s). False when there is none."""
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        pw, ph = W, H - top
        if self.mirroring:
            jpeg, at = self.frame
            if not (st.get("badge") and jpeg and self.t - at < 3.0):
                return False
            try:
                from PIL import Image
                im = Image.open(BytesIO(jpeg)).convert("RGB")
            except Exception:   # noqa: BLE001 (a frame that does not decode is left out)
                return False
            k = max(pw / im.width, ph / im.height)   # cover the panel, cut the rest
            im = im.resize((max(pw, round(im.width * k)), max(ph, round(im.height * k))))
            x0, y0 = (im.width - pw) // 2, (im.height - ph) // 2
            rgb = np.asarray(im.crop((x0, y0, x0 + pw, y0 + ph)))
            px = np.dstack([rgb[:, :, 2], rgb[:, :, 1], rgb[:, :, 0], np.full(rgb.shape[:2], 255, np.uint8)])
        else:
            cam = self.cams[PICTURE[mode]]
            try:
                raw = cam.getImage() if cam.getSamplingPeriod() else None
            except ValueError:    # just switched on: no picture yet
                raw = None
            if not raw:
                return False
            w, h = cam.getWidth(), cam.getHeight()
            px = np.frombuffer(raw, np.uint8).reshape(h, w, 4)
            if mode == "camera":
                px = px[:, ::-1]                    # the front camera as a mirror, as on the phone
            if mode == "magnify":                   # the middle, twice as big
                px = px[h // 4:h // 4 + h // 2, w // 4:w // 4 + w // 2].repeat(2, 0).repeat(2, 1)
            k = max(pw / px.shape[1], ph / px.shape[0])
            ys = (np.arange(ph) / k + (px.shape[0] - ph / k) / 2).astype(int).clip(0, px.shape[0] - 1)
            xs = (np.arange(pw) / k + (px.shape[1] - pw / k) / 2).astype(int).clip(0, px.shape[1] - 1)
            px = px[ys][:, xs]
        img = d.imageNew(np.ascontiguousarray(px).tobytes(), Display.BGRA, pw, ph)
        d.imagePaste(img, 0, top, False)
        d.imageDelete(img)
        return True

    def draw_cam_buttons(self, mode: str, st: dict):
        """The camera view's buttons, as omi.js puts them over the picture: zoom, torch, hold in the magnifier; "what is
        this?" on the back camera; Zeigen in every view, when allowed."""
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        allowed = st.get("allowed") if self.mirroring else False
        bs = [(k, lab) for k, lab, modes in CAM_BUTTONS if mode in modes and (k != "show" or allowed)]
        if not bs:
            return
        bw, y = (W - 24) / len(bs), H - 48
        for i, (k, lab) in enumerate(bs):
            x = int(12 + i * bw)
            on = k == "show" and st.get("badge")
            d.setColor(0xe0b341 if on else 0x202020)
            d.fillRectangle(x + 2, y, int(bw) - 4, 38)
            d.setColor(0x3fd8ff)
            d.drawRectangle(x + 2, y, int(bw) - 4, 38)
            label = self.word("mode", "show") if k == "show" else f"? {self.word('mode', 'what')}" if k == "what" else lab
            self.text(label, x + 6, y + 12, 15 if len(label) < 10 else 12, 0x101010 if on else 0xffffff)

    def draw_tiles(self, st, top):
        """The tiles, three across, as the page lays them out upright (the eyes keep the top quarter)."""
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        ids = st.get("tiles") or []
        if not ids:
            return
        cols, rows = 3, (len(ids) + 2) // 3
        tw, th = W / cols, (H - top) / rows
        own = {x.get("id"): x for x in self.panel.get("menu", []) if isinstance(x, dict)}
        for i, k in enumerate(ids):
            x, y = int((i % cols) * tw) + 3, int(top + (i // cols) * th) + 3
            hi, face = k == st.get("hi"), k == "face"
            d.setColor(0xe0b341 if hi else 0x3a3210 if face else 0x1b2a33)
            d.fillRectangle(x, y, int(tw) - 6, int(th) - 6)
            d.setColor(0xffe066 if hi or face else 0x3fd8ff)
            d.drawRectangle(x, y, int(tw) - 6, int(th) - 6)
            label = own[k].get("label", {}).get(self.lang(), k) if k in own and isinstance(own[k].get("label"), dict) else self.word("mode", k) or k
            lines = wrap(label, 9)[:3]
            for j, line in enumerate(lines):
                self.text(line, x + 6, int(y + th / 2 - 9 * len(lines) + 18 * j), 15, 0x101010 if hi else 0xffffff)

    def draw_toast(self, text: str, top_of_screen: bool):
        if not text:
            return
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        lines = wrap(text, 26)[:6]
        h = 20 * len(lines) + 12
        y0 = 4 if top_of_screen else round(40 * H / 730)   # as the page: 40 px from the top (6 above the tiles)
        d.setColor(0x101010)
        d.fillRectangle(6, y0, W - 12, h)
        d.setColor(0x3fd8ff)                               # its cyan frame
        for k in range(3):
            d.drawRectangle(6 + k, y0 + k, W - 12 - 2 * k, h - 2 * k)
        for j, line in enumerate(lines):
            self.text(line, 12, y0 + 6 + 20 * j, 16)

    def draw_card(self, note_id: str):
        text, buttons = self.card(note_id)
        if not text:
            return
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        y0 = int(H * 0.3)
        d.setColor(0xf5f1e6)
        d.fillRectangle(10, y0, W - 20, int(H * 0.45))
        for j, line in enumerate(wrap(text, 20)[:5]):
            self.text(line, 22, y0 + 16 + 24 * j, 19, 0x101010)
        bw = (W - 40) // max(1, len(buttons))
        for i, b in enumerate(buttons):
            x = 20 + i * bw
            d.setColor(0x2e7d32 if i == 0 else 0x6d6d6d)
            d.fillRectangle(x + 2, y0 + int(H * 0.45) - 56, bw - 4, 44)
            self.text(str(b)[:10], x + 10, y0 + int(H * 0.45) - 42, 16)

    def pump(self, link, mirrored):
        if not link:
            return
        try:
            while True:
                self.handle(link.got.get_nowait(), mirrored)
        except queue.Empty:
            pass

    def run(self):
        step = int(self.robot.getBasicTimeStep())
        while self.robot.step(step) != -1:
            self.t += self.dt
            self.ride()
            self.pump(self.phone, False)
            self.pump(self.mirror, True)
            if self.phone and self.phone.closed.is_set():
                print("the bridge closed the link (another phone?); the twin stops", flush=True)
                return
            if self.mirroring and self.mirror.closed.is_set():
                print("the bridge closed the mirror; the twin stops", flush=True)
                return
            if self.t >= self.next_imu:
                self.next_imu = self.t + IMU_EVERY
                if self.phone:
                    self.imu()
            if self.t >= self.next_see:
                self.next_see = self.t + SEE_EVERY
                self.vision()
            if self.t >= self.next_draw:
                self.next_draw = self.t + 0.1
                self.draw()
                if self.snap and self.t >= self.next_snap:   # --snap: the screen as a picture, for a check to read
                    self.next_snap = self.t + 1.0
                    self.screen.imageSave(None, self.snap)
            if self.flying:
                self.animate()
            self.keys()
            if self.phone:
                self.click()


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--bridge", default=None, help=f"be the phone: the bridge's WebSocket (default ws://127.0.0.1:{c.PORT}/ws; add ?key=...)")
    a.add_argument("--mirror", default=None, help=f"follow the real phone: the bridge's mirror socket (ws://127.0.0.1:{c.PORT}{c.MIRROR})")
    a.add_argument("--model", default="A50", help="the phone it plays (webots/phones.json): its hello says '<model> twin'")
    a.add_argument("--snap", default="", help="save the twin's screen as this PNG every second (for checks)")
    args = a.parse_args()
    if args.bridge and args.mirror:
        sys.exit("--bridge or --mirror, not both")
    bridge = None if args.mirror else (args.bridge or f"ws://127.0.0.1:{c.PORT}/ws")
    if not args.mirror:   # as the phone: the mirror socket brings the props (same host, same key)
        u = urlsplit(bridge)
        args.mirror = urlunsplit((u.scheme, u.netloc, c.MIRROR, u.query, ""))
    mirror = args.mirror
    for _ in range(30):  # the bridge may still be starting
        try:
            twin = Twin(bridge, mirror, args.model, args.snap)
            break
        except OSError:
            time.sleep(1)
    else:
        sys.exit(f"no bridge at {bridge or mirror}")
    twin.run()


if __name__ == "__main__":
    main()

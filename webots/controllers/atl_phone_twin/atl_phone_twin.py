#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""atl_phone_twin — the phone's Webots twin: an AtlPhone in Webots that speaks the face page's protocol to the bridge.

    (in the atl-phone-twin image, Webots on the host; see the README)
    WEBOTS_CONTROLLER_URL=tcp://127.0.0.1:1240/PH5v0001 python3 atl_phone_twin.py --bridge ws://127.0.0.1:8782/ws

The bridge cannot tell it from a real phone, so ROS sees the same topics (contract atl-phone/0.4) and a program
(the Desk Guardian) runs unchanged against the real phone and against this twin. What the twin does:
- it rides on its holder (AtlPhone follow: a DEF path), as the supervisor of itself, so it moves with the robot;
- imu: from its own motion (the specific force and the turn rate, in the phone frame), heading from its yaw;
- see and look: Webots' Recognition on its cameras gives "ground truth" vision: a Solid whose model is "face" is a
  face, "aruco:<n>" a marker (its distance from the 3D position), a COCO label an object, and any recognised
  colour within the asked hue a blob. Hands are not simulated;
- face, gaze, color, panel: drawn on its screen (a Display) like the page draws them, simpler; say: its Speaker;
  torch: its LED; vibrate: shown on the screen; touch: a click on its screen in Webots (left, centre or right).
Standard library and Webots' controller library only (the bridge's MockPhone is the WebSocket client).
"""
import argparse
import json
import math
import os
import queue
import sys
import time

from controller import Supervisor

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


def mount(upright: bool, tilt: float, size):
    """Where the phone's centre sits on its holder, and how it is turned (columns: the phone's x, y, z), in the
    holder's frame: the bottom edge on the block (12 mm), the screen to the robot's front (+x), leaning back by tilt."""
    s, co = math.sin(tilt), math.cos(tilt)
    z = [co, 0.0, s]
    if upright:   # portrait: y up the screen, leaning back
        y, half = [-s, 0.0, co], size[1] / 2
    else:         # landscape: the phone's top to the robot's right (seen from the front: to the left)
        y, half = [0.0, -1.0, 0.0], size[0] / 2
    x = [y[1] * z[2] - y[2] * z[1], y[2] * z[0] - y[0] * z[2], y[0] * z[1] - y[1] * z[0]]
    up = [-s, 0.0, co] if not upright else y
    at = [up[0] * half - z[0] * size[2] / 2, 0.0, 0.012 + up[2] * half]
    return at, [[x[i], y[i], z[i]] for i in range(3)]


class Twin:
    def __init__(self, bridge: str):
        self.robot = Supervisor()
        self.dt = self.robot.getBasicTimeStep() / 1000.0
        self.me = self.robot.getSelf()
        self.size = self.me.getField("size").getSFVec3f() if self.me.getField("size") else [0.0747, 0.1585, 0.0077]
        follow = self.robot.getCustomData()  # AtlPhone's follow
        self.holder = self.robot.getFromDef(follow) if follow else None
        print(f"{self.robot.getName()}: " + (f"rides on {follow}" if self.holder else f"stands alone (no {follow!r} to ride on)"), flush=True)
        self.screen = self.robot.getDevice("screen")
        self.cams = {"front": self.robot.getDevice("camera_front"), "back": self.robot.getDevice("camera_back")}
        self.speaker = self.robot.getDevice("speaker")
        self.torch = self.robot.getDevice("torch")
        self.mouse = self.robot.getMouse()
        self.mouse.enable(int(self.robot.getBasicTimeStep()))
        self.mouse.enable3dPosition()
        self.phone = MockPhone(bridge)
        self.expression, self.color, self.gaze = "neutral", [63, 216, 255], (0.0, 0.0)
        self.panel = {"mode": "mouth", "buttons": [], "menu": list(c.PANEL_MODES)}
        self.look, self.familiar, self.see, self.seeing = False, False, {"find": [], "camera": "front"}, False
        self.say_until, self.buzz_until, self.drawn, self.first_picture = 0.0, 0.0, None, 0.0
        self.poses = []           # (t, position, R): the last three, for the IMU
        self.t = 0.0
        self.next_see = self.next_draw = 0.0
        self.next_imu = 0.2       # s: after the jump onto the holder, which is no motion
        self.last_click = False
        w, h = self.cams["front"].getWidth(), self.cams["front"].getHeight()
        self.hello(w, h)

    def hello(self, w, h):
        self.phone.send(t="hello", id=TWIN_ID, ua="Webots twin (atl-phone)", model="A50 twin", secure=True,
                        caps={"motion": True, "compass": True, "tts": True, "vibrate": False, "battery": True, "wakelock": True,
                              "camera": True, "barcode": False}, screen=[self.screen.getWidth() * 4, self.screen.getHeight() * 4])
        self.phone.send(t="battery", level=0.8, charging=True)

    # ---- the body: ride on the holder; the IMU from the motion ---------------------------------------------------
    def ride(self):
        if not self.holder:
            return
        hp, hR = self.holder.getPosition(), [self.holder.getOrientation()[i * 3:i * 3 + 3] for i in range(3)]
        up = self.holder.getField("upright").getSFBool() if self.holder.getField("upright") else True
        tilt = self.holder.getField("tilt").getSFFloat() if self.holder.getField("tilt") else 0.2
        at, M = mount(up, tilt, self.size)
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
        self.phone.send(t="imu", acc=[max(-150.0, min(150.0, v)) for v in f], gyro=w)
        yaw = math.degrees(math.atan2(R2[1][2], R2[0][2]))   # where the screen faces, from +x; north is +y in the table
        self.phone.send(t="heading", deg=(90.0 - yaw) % 360)

    # ---- seeing: Recognition, as the page's finders report ---------------------------------------------------
    def finders(self):
        f = list(self.see.get("find", []))
        if self.look and "faces" not in f:
            f.append("faces")
        return f

    def vision(self):
        f = self.finders()
        side = self.see.get("camera", "front") if self.see.get("find") else "front"
        for name, cam in self.cams.items():
            on = bool(f) and name == side
            if on and cam.getSamplingPeriod() == 0:
                cam.enable(100)
                cam.recognitionEnable(100)
                self.first_picture = self.t + 0.25   # like a phone: nothing to say before the first picture
            elif not on and cam.getSamplingPeriod():
                cam.recognitionDisable()
                cam.disable()
        if not f:
            if self.seeing:
                self.seeing = False
                self.phone.send(t="see", on=False, ok=True, camera=side, find=[])
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
            self.phone.send(t="faces", faces=sorted(faces, key=size)[:8], period=int(SEE_EVERY * 1000))
        if "markers" in f:
            self.phone.send(t="markers", camera=side, markers=markers[:8])
        if "objects" in f:
            self.phone.send(t="objects", camera=side, objects=sorted(objects, key=size)[:8])
        if "blobs" in f:
            self.phone.send(t="blobs", camera=side, blobs=sorted(blobs, key=size)[:8])
        if "hands" in f:
            self.phone.send(t="hands", camera=side, hands=[])
        if math.isfinite(fov):
            self.phone.send(t="see", on=True, ok=True, camera=side, find=f, ms={k: 1 for k in f}, backend="webots")

    # ---- what the bridge asks --------------------------------------------------------------------------------
    def handle(self, m):
        t = m.get("t")
        if t == "face":
            self.expression = m["expression"]
        elif t == "gaze":
            self.gaze = (m["x"], m["y"])
        elif t == "color":
            self.color = m["rgb"]
        elif t == "say":
            self.speaker.setLanguage(LANGS.get(m.get("lang"), "en-UK"))
            self.speaker.speak(m["text"], 1.0)
            self.say_until = self.t + 0.07 * len(m["text"]) + 0.5
        elif t == "torch":
            self.torch.set(1 if m["on"] else 0)
            self.phone.send(t="camera", on=False, ok=True, torch=bool(m["on"]))
        elif t == "camera":
            self.phone.send(t="camera", on=bool(m["on"]), ok=True, size=[self.cams["back"].getWidth(), self.cams["back"].getHeight()])
        elif t == "vibrate":
            self.buzz_until = self.t + m["ms"] / 1000.0
        elif t == "look":
            self.look, self.familiar = m["on"], m.get("familiar", False)
            self.phone.send(t="look", on=self.look, ok=True, familiar=False)  # the twin tells no faces apart
            if not self.look:
                self.phone.send(t="faces", faces=[])
        elif t == "see":
            self.see = m
        elif t == "panel":
            self.panel.update({k: v for k, v in m.items() if k in ("mode", "buttons", "menu")})

    def click(self):
        st = self.mouse.getState()
        down = st.left
        if down and not self.last_click and st.x == st.x:  # NaN when the click is not on a 3D point
            p = [st.x, st.y, st.z]
            me, R = self.me.getPosition(), [self.me.getOrientation()[i * 3:i * 3 + 3] for i in range(3)]
            q = apply(transpose(R), [p[i] - me[i] for i in range(3)])
            if abs(q[0]) < self.size[0] / 2 and abs(q[1]) < self.size[1] / 2 and q[2] > 0:
                zone = "left" if q[0] < -self.size[0] / 6 else "right" if q[0] > self.size[0] / 6 else "centre"
                self.phone.send(t="touch", kind="tap", zone=zone)
        self.last_click = down

    # ---- the screen: the eyes, and the panel's mouth or pad, simpler than the page --------------------------
    def draw(self):
        speaking = self.t < self.say_until
        blink = 0.1 if (self.t % 4) < 0.15 else 1.0
        key = (self.expression, tuple(self.color), round(self.gaze[0], 1), round(self.gaze[1], 1), json.dumps(self.panel),
               speaking and int(self.t * 10), self.t < self.buzz_until, blink)
        if key == self.drawn:
            return
        self.drawn = key
        d, W, H = self.screen, self.screen.getWidth(), self.screen.getHeight()
        rgb = (self.color[0] << 16) | (self.color[1] << 8) | self.color[2]
        d.setAlpha(1.0)
        d.setColor(0x000000)
        d.fillRectangle(0, 0, W, H)
        split = self.panel.get("mode") != "off"
        eye_h = int(H * 0.54) if split else H
        base = min(W * 0.32, eye_h * 0.55)
        e = dict(EYE, **EXPRESSIONS.get(self.expression, {}))
        for side in (-1, 1):
            cx = W / 2 + side * W * 0.22 + self.gaze[0] * base * 0.35
            cy = eye_h / 2 - self.gaze[1] * base * 0.25 + e["dy"] * base
            w, h = e["w"] * base, e["h"] * base * blink
            if self.expression == "wink" and side == 1:
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
        if not split:
            return
        mode, top = self.panel.get("mode"), eye_h
        d.setColor(rgb)
        if mode == "mouth":
            cy, mw = top + (H - top) * 0.45, W * 0.42
            if speaking:  # the sound wave, as the page draws it
                xs = [int(W * 0.1 + W * 0.8 * i / 31) for i in range(32)]
                ys = [int(cy + math.sin(i * 1.7 + self.t * 22) * (H - top) * 0.15 * math.sin(math.pi * i / 31)) for i in range(32)]
                for i in range(31):
                    d.drawLine(xs[i], ys[i], xs[i + 1], ys[i + 1])
            else:
                bend = MOUTHS.get(self.expression, 0.15) * (H - top) * 0.18
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
            d.drawText("A50 twin", 10, top + 10)
            d.drawText("look: " + ("on" if self.look else "off"), 10, top + 30)
            d.drawText("see: " + ",".join(self.see.get("find", [])), 10, top + 50)
        elif mode in ("camera", "camera_back"):
            d.drawRectangle(8, top + 8, W - 16, H - top - 16)
            d.drawText("camera", 16, top + 16)
        if self.t < self.buzz_until:
            d.setColor(0xe0b341)
            d.drawText("bzz", W - 40, 8)

    def run(self):
        step = int(self.robot.getBasicTimeStep())
        while self.robot.step(step) != -1:
            self.t += self.dt
            self.ride()
            try:
                while True:
                    self.handle(self.phone.got.get_nowait())
            except queue.Empty:
                pass
            if self.phone.closed.is_set():
                print("the bridge closed the link (another phone?); the twin stops", flush=True)
                return
            if self.t >= self.next_imu:
                self.next_imu = self.t + IMU_EVERY
                self.imu()
            if self.t >= self.next_see:
                self.next_see = self.t + SEE_EVERY
                self.vision()
            if self.t >= self.next_draw:
                self.next_draw = self.t + 0.1
                self.draw()
            self.click()


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--bridge", default=f"ws://127.0.0.1:{c.PORT}/ws", help="the bridge's WebSocket (add ?key=... when it has one)")
    args = a.parse_args()
    for _ in range(30):  # the bridge may still be starting
        try:
            twin = Twin(args.bridge)
            break
        except OSError:
            time.sleep(1)
    else:
        sys.exit(f"no bridge at {args.bridge}")
    twin.run()


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""contract_check — does a running bridge keep the contract (contract.py)? A mock phone plays the phone.

    python3 -m atl_phone.contract_check [--robot thymio_1] [--port 8782] [--key ...] [--wav speech.wav]

--wav: a clip of German speech (16 kHz mono WAV) for Übersetzen, to be heard and translated; without it, a second of
silence goes the same way and must come back as "nothing heard". Either way it needs the bridge's models.

Prints one line per check (PASS/FAIL) and exits 1 if any failed. Also the setup page's API (on this PC). Run it with no real
phone on the bridge: the mock phone takes over, and a real one would be closed.
"""
import argparse
import base64
import json
import math
import sys
import time
import wave
import urllib.error
import urllib.request

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile
from geometry_msgs.msg import Point
from sensor_msgs.msg import BatteryState, Imu
from std_msgs.msg import Bool, ColorRGBA, Empty, Float32, Int32, String

from . import contract as c
from .mock_phone import ID as MOCK_ID, MockPhone


class Check:
    def __init__(self, robot: str):
        rclpy.init()
        self.n = rclpy.create_node("phone_contract_check")
        self.t = c.topics(robot)
        self.robot = robot
        self.got = {}
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        for name, kind, qos in [("status", String, latched), ("imu", Imu, 10), ("heading", Float32, 10),
                                ("touch", String, 10), ("battery", BatteryState, latched), ("faces", String, 10), ("codes", String, 10), ("pad", String, 10),
                                ("panel_mode", String, latched), ("markers", String, 10), ("blobs", String, 10),
                                ("objects", String, 10), ("hands", String, 10), ("menu", String, 10), ("note_answer", String, 10),
                                ("read_result", String, 10), ("what_result", String, 10), ("translate_result", String, 10)]:
            self.n.create_subscription(kind, self.t[name], lambda m, k=name: self.got.setdefault(k, []).append(m), qos)
        self.pub = {name: self.n.create_publisher(kind, self.t[name], 10) for name, kind in
                    [("expression", String), ("gaze", Point), ("color", ColorRGBA), ("say", String),
                     ("torch", Bool), ("vibrate", Int32), ("look", Bool), ("familiar", Bool), ("forget", Empty), ("panel", String), ("see", String),
                     ("note", String), ("read", String), ("what", String)]}
        self.n.create_subscription(String, f"/{robot}/omi/state", lambda m: self.got.setdefault("omi/state", []).append(m), 10)
        for k in ("run", "drive"):  # the Desk Guardian's own topics, which the setup page starts it with
            self.n.create_subscription(Bool, f"/{robot}/guardian/{k}", lambda m, k=k: self.got.setdefault("guardian/" + k, []).append(m), 10)
        self.failed = 0

    def ok(self, name: str, good: bool, detail=""):
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
        self.failed += not good

    def wait(self, key: str, pred=lambda m: True, timeout=3.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self.n, timeout_sec=0.05)
            for m in self.got.get(key, []):
                if pred(m):
                    return m
        return None

    def status(self, connected: bool):
        return self.wait("status", lambda m: json.loads(m.data).get("connected") is connected)

    def run(self, url: str, wav=None) -> int:
        phone = MockPhone(url)
        phone.hello()
        s = self.wait("status", lambda m: json.loads(m.data).get("model") == "MOCK-PHONE")  # (after hello: a status may come before it)
        detail = json.loads(s.data) if s else {}
        self.ok("status: connected, with the phone's model and contract", bool(s) and detail.get("model") == "MOCK-PHONE"
                and detail.get("contract") == c.CONTRACT, json.dumps(detail)[:120])
        try:
            w = phone.expect("web")   # the first thing the bridge sends after hello
        except TimeoutError:
            w = None
        self.ok("web: the pages' fingerprint on hello, so a page from an older bridge reloads",
                bool(w) and len(w.get("id", "")) == 16 and w["id"] == json.load(urllib.request.urlopen(
                    url.replace("ws://", "http://").split("/ws")[0] + "/api/state", timeout=5)).get("web"), w)

        for _ in range(5):
            phone.send(t="imu", acc=[0.1, 0.2, 9.81], gyro=[0.0, 0.0, 0.5])
            time.sleep(0.03)
        m = self.wait("imu")
        self.ok("imu: m/s2 with gravity, rad/s, phone frame, no orientation", bool(m)
                and abs(m.linear_acceleration.z - 9.81) < 1e-6 and abs(m.angular_velocity.z - 0.5) < 1e-6
                and m.header.frame_id == f"{self.robot}/phone" and m.orientation_covariance[0] == -1.0)

        phone.send(t="heading", deg=370)
        m = self.wait("heading")
        self.ok("heading: degrees, wrapped to 0..360", bool(m) and math.isclose(m.data, 10.0, abs_tol=1e-4), m and m.data)

        phone.send(t="touch", kind="swipe", zone="left", dir="up")
        m = self.wait("touch")
        self.ok("touch: kind, zone, direction", bool(m) and json.loads(m.data) == {"kind": "swipe", "zone": "left", "dir": "up"}, m and m.data)

        phone.send(t="battery", level=0.42, charging=True)
        m = self.wait("battery", lambda m: abs(m.percentage - 0.42) < 1e-6)
        self.ok("battery: level and charging", bool(m) and m.power_supply_status == BatteryState.POWER_SUPPLY_STATUS_CHARGING)

        phone.send(t="imu", acc=["NaN", 0, 0], gyro=[0, 0, 0])
        phone.send(t="touch", kind="tap", zone="elsewhere")
        before = len(self.got.get("touch", []))
        self.wait("touch", lambda m: False, timeout=0.5)
        self.ok("bad messages from the phone are dropped", len(self.got.get("touch", [])) == before)

        def to_phone(name, msg, t):
            self.pub[name].publish(msg)
            try:
                return phone.expect(t)
            except TimeoutError:
                return None

        m = to_phone("expression", String(data="happy"), "face")
        self.ok("face/expression reaches the phone", m == {"t": "face", "expression": "happy"}, m)
        self.pub["expression"].publish(String(data="grumpy"))
        m = to_phone("gaze", Point(x=2.0, y=-0.5), "gaze")
        self.ok("face/gaze reaches the phone, clamped (and an unknown expression does not)", m == {"t": "gaze", "x": 1.0, "y": -0.5}, m)
        m = to_phone("color", ColorRGBA(r=1.0, g=0.5, b=0.0, a=1.0), "color")
        self.ok("face/color reaches the phone as 0..255", m == {"t": "color", "rgb": [255, 128, 0]}, m)
        m = to_phone("say", String(data='{"text": "Bonjour", "lang": "fr"}'), "say")
        self.ok("say reaches the phone, with its language", m == {"t": "say", "text": "Bonjour", "lang": "fr"}, m)
        m = to_phone("torch", Bool(data=True), "torch")
        self.ok("torch reaches the phone", m == {"t": "torch", "on": True}, m)
        m = to_phone("vibrate", Int32(data=99999), "vibrate")
        self.ok("vibrate reaches the phone, at most MAX_VIBRATE", m == {"t": "vibrate", "ms": c.MAX_VIBRATE}, m)

        m = to_phone("look", Bool(data=True), "look")
        self.ok("look reaches the phone (familiar off: not allowed)", m == {"t": "look", "on": True, "familiar": False}, m)
        self.pub["familiar"].publish(Bool(data=True))
        phone.send(t="faces", faces=[{"x": 0.5, "y": 0.1, "size": 0.3, "familiar": 2, "descriptor": [0.5] * 128}])
        f = self.wait("faces")
        self.ok("faces reach ROS: where they are, nothing else, no numbers while familiar is not allowed",
                bool(f) and json.loads(f.data) == {"n": 1, "faces": [{"x": 0.5, "y": 0.1, "size": 0.3, "familiar": None}]}, f and f.data)
        phone.send(t="code", text="atl-guardian:owner")
        f = self.wait("codes")
        self.ok("a code the front camera read reaches ROS", bool(f) and json.loads(f.data) == {"text": "atl-guardian:owner"}, f and f.data)
        m = to_phone("forget", Empty(), "forget")
        self.ok("look/forget reaches the phone", m == {"t": "forget"}, m)
        m = to_phone("look", Bool(data=False), "look")
        self.ok("look off reaches the phone", m == {"t": "look", "on": False, "familiar": False}, m)

        self.pub["panel"].publish(String(data='{"mode": "pad", "buttons": [{"id": "../x"}]}'))
        m = to_phone("panel", String(data=json.dumps({"mode": "pad", "buttons": [{"id": "go", "label": "Go!", "color": [0, 1, 2]}],
                                                       "script": "alert(1)"})), "panel")
        self.ok("panel reaches the phone: checked, colours 0..255, nothing else (and a bad button id does not)",
                m == {"t": "panel", "mode": "pad", "buttons": [{"id": "go", "label": "Go!", "rgb": [0, 255, 255]}]}, m)
        phone.send(t="pad", id="go")
        phone.send(t="pad", id="<script>")
        f = self.wait("pad")
        self.wait("pad", lambda m: False, timeout=0.3)
        self.ok("a press on the panel's pad reaches ROS (a bad id does not)",
                [json.loads(x.data) for x in self.got.get("pad", [])] == [{"id": "go"}], [x.data for x in self.got.get("pad", [])])

        pm = self.wait("panel_mode", lambda m: m.data == "pad")  # (a latched one from a run before may come first)
        self.ok("panel/mode (latched) says what the panel shows: as the program set it", bool(pm) and pm.data == "pad", pm and pm.data)
        phone.send(t="panel", mode="sensors")
        pm = self.wait("panel_mode", lambda m: m.data == "sensors")
        self.ok("panel/mode: the person picked another mode in the phone's menu", bool(pm))

        self.pub["see"].publish(String(data='{"find": ["x-ray"]}'))
        m = to_phone("see", String(data=json.dumps({"camera": "back", "find": ["markers", "blobs"], "blob": {"hue": 120}})), "see")
        self.ok("see reaches the phone, checked (and an unknown finder does not)",
                m == {"t": "see", "camera": "back", "find": ["markers", "blobs"], "blob": {"hue": 120.0, "tol": 20.0}, "marker_cm": 5.0}, m)
        phone.send(t="markers", camera="back", markers=[{"id": 7, "x": 0.1, "y": 0, "size": 0.3, "distance_m": 0.42, "yaw_deg": 10, "picture": "x"}])
        phone.send(t="objects", camera="back", objects=[{"label": "a child's name", "score": 1, "x": 0, "y": 0, "w": 1, "h": 1}])
        phone.send(t="objects", camera="back", objects=[{"label": "cup", "score": 0.8, "x": 0, "y": 0, "w": 0.1, "h": 0.2, "distance_m": 0.5}])
        phone.send(t="hands", camera="back", hands=[{"x": 0, "y": 0, "gesture": "thumbs_up"}])
        phone.send(t="blobs", camera="back", blobs=[{"x": -0.5, "y": 0.5, "size": 0.1}])
        mk, ob, hd, bl = self.wait("markers"), self.wait("objects"), self.wait("hands"), self.wait("blobs")
        self.wait("objects", lambda m: False, timeout=0.3)
        self.ok("markers, objects, hands and blobs reach ROS: their own fields only (an unknown label does not)",
                bool(mk and ob and hd and bl) and json.loads(mk.data) == {"camera": "back", "markers": [
                    {"x": 0.1, "y": 0.0, "id": 7, "size": 0.3, "distance_m": 0.42, "yaw_deg": 10.0}]}
                and [json.loads(x.data)["objects"][0]["label"] for x in self.got["objects"]] == ["cup"]
                and json.loads(hd.data)["hands"][0]["gesture"] == "thumbs_up" and json.loads(bl.data)["blobs"][0]["size"] == 0.1,
                [x and x.data for x in (mk, ob, hd, bl)])
        phone.send(t="faces", faces=[], period=1500)
        f = self.wait("faces", lambda m: json.loads(m.data).get("period") == 1500)
        self.ok("faces say how fast the phone searches (period, ms)", bool(f), f and f.data)

        base = url.split("/ws")[0].replace("ws:", "http:")

        def api(path, body=None):
            req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body else None,
                                         headers={"Content-Type": "application/json"})
            return urllib.request.urlopen(req, timeout=5)

        api("/api/act", {"topic": "expression", "value": "wink"})
        try:
            m = phone.expect("face")
        except TimeoutError:
            m = None
        self.ok("setup page: a test goes through ROS to the phone", m == {"t": "face", "expression": "wink"}, m)
        st = json.load(api("/api/state"))
        self.ok("setup page: the state shows the phone and what it sensed", st.get("connected") is True
                and st["phone"].get("model") == "MOCK-PHONE" and st["seen"]["touch"][-1]["dir"] == "up"
                and st["seen"]["battery"]["level"] == 0.42 and st["seen"]["imu"]["n"] >= 1)
        api("/api/act", {"camera": True})
        try:
            m = phone.expect("camera")
        except TimeoutError:
            m = None
        phone.send(t="camera", on=True, ok=True, size=[1280, 720], code="atl-phone camera test")
        time.sleep(0.2)
        cam = json.load(api("/api/state"))["seen"].get("camera", {})
        self.ok("setup page: the camera test reaches the phone, and its report comes back", m == {"t": "camera", "on": True}
                and cam.get("size") == [1280, 720] and cam.get("codes") == ["atl-phone camera test"], (m, cam))
        api("/report", {"userAgent": "(Linux; Android 10; K)", "model": "SM-A505FN", "phone_id": MOCK_ID,
                         "checks": {"camera": {"ok": False, "need": "core"}}})
        st = json.load(api("/api/state"))
        r = st["reports"][-1]
        self.ok("setup page: a phone check report is kept, with the page's model and the phone's id",
                r["model"] == "SM-A505FN" and r["checks"]["camera"]["ok"] is False
                and r["id"] == st["phone"].get("id") == MOCK_ID, (r["id"], st["phone"].get("id"), r["model"]))

        api("/api/act", {"open": "face.html", "layout": "portrait"})
        try:
            m = phone.expect("open")
        except TimeoutError:
            m = None
        self.ok("setup page: the face opens in portrait", m == {"t": "open", "page": "face.html", "layout": "portrait"}, m)

        api("/api/act", {"guardian": True, "drive": False})
        run = self.wait("guardian/run")
        drive = self.wait("guardian/drive")
        g, end = {}, time.monotonic() + 3.0
        while time.monotonic() < end and g.get("state") in (None, "off"):
            self.wait("status", lambda m: False, timeout=0.3)
            g = json.load(api("/api/state")).get("guardian", {})
        api("/api/act", {"guardian": False})
        self.ok("setup page: the Desk Guardian starts (guardian/run, drive off) and its state comes back",
                bool(run) and run.data is True and bool(drive) and drive.data is False and g.get("state") not in (None, "off")
                and g.get("drive") is False, g)
        stopped = self.wait("guardian/run", lambda m: m.data is False)
        m, end = None, time.monotonic() + 3.0
        while m != {"t": "face", "expression": "neutral"} and time.monotonic() < end:
            try:
                m = phone.expect("face", timeout=end - time.monotonic())
            except TimeoutError:
                break
        self.ok("setup page: stopped, the guardian puts the face back to neutral", bool(stopped) and m == {"t": "face", "expression": "neutral"}, m)

        second = MockPhone(url)
        second.hello()
        self.ok("a second phone takes over and the first is closed", phone.closed.wait(3.0))
        try:
            m = second.expect("panel")
        except TimeoutError:
            m = None
        self.ok("the phone that comes gets the panel a program set (as the person left it)", bool(m) and m["buttons"][0]["id"] == "go"
                and m["mode"] == "sensors", m)
        try:
            m = second.expect("see")
        except TimeoutError:
            m = None
        self.ok("... and what a program asked its camera to find", bool(m) and m["find"] == ["markers", "blobs"], m)
        second.close()
        self.ok("status: disconnected when the phone is gone", bool(self.status(False)))
        try:
            api("/api/act", {"topic": "expression", "value": "happy"})
            refused = None
        except urllib.error.HTTPError as e:
            refused = (e.code, json.load(e).get("error"))
        self.ok("setup page: with no phone, an output test is refused", refused == (400, "no phone"), refused)
        api("/api/act", {"topic": "see", "value": {"camera": "front", "find": []}})  # a test left on: cleared with no phone there
        third = MockPhone(url)
        third.hello()
        try:
            m = third.expect("see", 1.5)
        except TimeoutError:
            m = None
        kept = (json.load(api("/api/state")).get("see") or {}).get("find")
        self.ok("setup page: with no phone, see can still be turned off: the phone that comes gets none", m is None and kept == [], (m, kept))
        third.close()
        self.omi(url, api)
        self.mirror(url, api)
        self.translate(url, api, wav)

        print(f"{'all passed' if not self.failed else f'{self.failed} failed'}")
        self.n.destroy_node()
        rclpy.shutdown()
        return 1 if self.failed else 0


    def omi(self, url, api):
        """0.5, Omi Assist: tiles and their picks, notes, read and what, showing (only when allowed, never on a topic)."""
        import base64
        phone = MockPhone(url)
        phone.hello()
        self.status(True)

        def get(t, timeout=3.0):
            try:
                return phone.expect(t, timeout)
            except TimeoutError:
                return None

        self.pub["panel"].publish(String(data=json.dumps({"mode": "mouth", "style": "tiles", "menu": c.OMI_MENU})))
        m, end = get("panel"), time.monotonic() + 3.0
        while m and m.get("style") != "tiles" and time.monotonic() < end:  # first, the panel kept from before, sent on hello
            m = get("panel")
        self.ok("0.5: panel tiles reach the phone, with the phone's own tiles", bool(m) and m.get("style") == "tiles"
                and m.get("menu") == c.OMI_MENU, m)
        phone.send(t="menu", id="time")
        k = self.wait("menu")
        self.ok("0.5: a tile picked reaches ROS (menu)", bool(k) and json.loads(k.data) == {"id": "time"}, k and k.data)
        self.pub["note"].publish(String(data=json.dumps({"id": "r1", "text": "Tabletten", "buttons": [{"id": "done", "label": "Erledigt"}]})))
        m = get("note")
        phone.send(t="answer", note="r1", id="done")
        a = self.wait("note_answer")
        self.ok("0.5: a note reaches the phone and its answer comes back (note/answer)", bool(m) and m.get("text") == "Tabletten"
                and bool(a) and json.loads(a.data) == {"note": "r1", "id": "done"}, (m, a and a.data))
        self.pub["read"].publish(String(data=""))
        m = get("read")
        phone.send(t="read", ok=True, lines=2, chars=40, ms=3100, text="the text stays on the phone")
        r = self.wait("read_result")
        self.ok("0.5: read reaches the phone; only how it went comes back (never the text)", bool(m) and m.get("lang") in c.LANGS
                and bool(r) and json.loads(r.data) == {"ok": True, "lines": 2, "chars": 40, "ms": 3100}, (m, r and r.data))
        self.pub["what"].publish(String(data='{"lang": "de"}'))
        m = get("what")
        phone.send(t="what", ok=True, label="cup", score=0.8, ms=1500)
        w = self.wait("what_result")
        self.ok("0.5: what reaches the phone and the label comes back", m == {"t": "what", "lang": "de"}
                and bool(w) and json.loads(w.data)["label"] == "cup", (m, w and w.data))

        jpeg = b"\xff\xd8" + b"\x11" * 200 + b"\xff\xd9"
        frame = base64.b64encode(jpeg).decode()

        def shown():
            try:
                return api("/api/show.jpg").read()
            except urllib.error.HTTPError as e:
                return e.code
        api("/api/act", {"allow_show": False})
        get("show", 1.0)
        phone.send(t="show", on=True)
        refused = get("show")
        phone.send(t="frame", jpeg=frame)
        time.sleep(0.3)
        self.ok("0.5: show is refused unless allowed: the phone is told, no frame reaches the PC",
                refused == {"t": "show", "allowed": False, "on": False} and shown() == 404, refused)
        api("/api/act", {"allow_show": True})
        allowed = get("show")
        phone.send(t="show", on=True)
        phone.send(t="frame", jpeg=frame)
        time.sleep(0.3)
        st = json.load(api("/api/state")).get("show", {})
        got = shown()
        topics = [n for n, _ in self.n.get_topic_names_and_types() if "show" in n or "frame" in n]
        self.ok("0.5: allowed, what she shows reaches the setup page only (/api/show.jpg), on no topic",
                bool(allowed) and allowed.get("allowed") is True and got == jpeg and st.get("on") is True and topics == [], (allowed, st, topics))
        api("/api/act", {"show": False})
        stop = get("show")
        time.sleep(0.2)
        self.ok("0.5: the setup page stops the showing: the phone is told, the frame is dropped",
                stop == {"t": "show", "allowed": True, "on": False} and shown() == 404, stop)
        api("/api/act", {"allow_show": False})

        try:
            api("/api/act", {"reminders": [{"text": "", "at": "9"}]})
            bad = None
        except urllib.error.HTTPError as e:
            bad = e.code
        api("/api/act", {"omi": True, "reminders": [{"id": "pill", "text": "Tabletten", "at": "09:00"}]})
        m, s = get("panel"), get("see")
        o, end = {}, time.monotonic() + 4.0
        while time.monotonic() < end and not (o.get("state") == "on" and o.get("reminders")):
            self.wait("status", lambda m: False, timeout=0.3)
            o = json.load(api("/api/state")).get("omi", {})
        self.ok("0.5: setup page: Omi Assist starts: the tiles, the eyes following, its reminders (a bad one refused)",
                bad == 400 and bool(m) and m.get("style") == "tiles" and bool(s) and s.get("follow") is True
                and o.get("state") == "on" and [r["id"] for r in o.get("reminders", [])] == ["pill"], (bad, m, s, o))
        api("/api/act", {"omi_tour": True})
        tour = get("tour")
        api("/api/act", {"omi": False})
        m = get("panel")
        self.ok("0.5: the setup page's Introduce: the phone is asked for the presentation, in Omi's language",
                tour == {"t": "tour", "lang": o.get("lang")} and m.get("lang") == "auto" if m else False, (tour, m))
        end = time.monotonic() + 4.0
        while time.monotonic() < end and json.load(api("/api/state")).get("omi", {}).get("state") == "on":
            time.sleep(0.2)
        try:
            api("/api/act", {"omi_tour": True})
            late = None
        except urllib.error.HTTPError as e:
            late = e.code
        self.ok("0.5: stopped, Omi Assist puts the chips back (the phone's own language); no presentation then",
                bool(m) and m.get("style") == "chips" and late == 400, (m, late))
        api("/api/act", {"reminders": []})
        phone.close()

    def mirror(self, url, api):
        """0.6: the mirror socket (the phone's Webots twin): a copy of what the phone gets, its screen report, the props."""
        from urllib.parse import urlsplit, urlunsplit
        u = urlsplit(url)

        def code(body):
            try:
                api("/api/act", body)
                return 204
            except urllib.error.HTTPError as e:
                return e.code

        def get(link, t, timeout=3.0):
            try:
                return link.expect(t, timeout)
            except TimeoutError:
                return None

        none = code({"prop": "cup"})
        twin = MockPhone(urlunsplit((u.scheme, u.netloc, c.MIRROR, u.query, "")))
        first = get(twin, "phone")
        phone = MockPhone(url)
        phone.hello()
        self.status(True)
        hello, end = None, time.monotonic() + 3.0
        while time.monotonic() < end and not (hello and hello.get("connected")):   # the step before's phone may still be
            hello = get(twin, "phone", max(0.1, end - time.monotonic()))           # going: its "gone" can come first
        self.ok("0.6: a mirror connects beside the phone, and hears when the phone comes",
                none == 400 and first is not None and bool(hello) and hello.get("connected") is True
                and json.load(api("/api/state")).get("mirrors") == 1, (none, first, hello))
        self.pub["expression"].publish(String(data="love"))
        a, b = get(phone, "face"), get(twin, "face")
        self.ok("0.6: the mirror gets a copy of what the phone is sent", a == b == {"t": "face", "expression": "love"}, (a, b))
        phone.send(t="screen", lang="de", mode="mouth", expression="love", style="tiles", menu=True, tiles=["time", "face"],
                   hi="time", toast="Lieber Herr Muster, Ihre Rechnung", note="", badge=False, speaking=True)
        sneak = get(twin, "screen")
        phone.send(t="screen", lang="de", mode="mouth", expression="love", style="tiles", menu=True, tiles=["time", "face"],
                   hi="time", toast="tour.time", note="", badge=False, speaking=True)
        good = get(twin, "screen")
        self.ok("0.6: the phone's screen report reaches the mirror as keys only (free text dropped), not ROS",
                bool(sneak) and sneak["toast"] == "" and bool(good) and good["toast"] == "tour.time" and good["tiles"] == ["time", "face"]
                and json.load(api("/api/state")).get("screen", {}).get("hi") == "time", (sneak, good))
        sent = code({"prop": "cup"})
        prop = get(twin, "prop")
        on_phone = get(phone, "prop", 0.5)
        before = len(self.got.get("touch", []))
        twin.send(t="touch", kind="tap", zone="left")
        self.wait("touch", lambda m: False, timeout=0.5)
        self.ok("0.6: a prop goes to the mirror only; a mirror cannot drive the phone (its frames are dropped)",
                sent == 204 and prop == {"t": "prop", "name": "cup"} and on_phone is None
                and len(self.got.get("touch", [])) == before and code({"prop": "cake"}) == 400, (sent, prop, on_phone))
        jpeg = base64.b64encode(b"\xff\xd8" + b"\x22" * 200 + b"\xff\xd9").decode()
        phone.send(t="frame", jpeg=jpeg)                   # not showing: dropped, the mirror gets nothing
        unshown = get(twin, "frame", 0.5)
        api("/api/act", {"allow_show": True})
        get(phone, "show", 1.0)
        phone.send(t="show", on=True)
        time.sleep(0.2)
        phone.send(t="frame", jpeg=jpeg)
        shown = get(twin, "frame")
        api("/api/act", {"show": False})
        api("/api/act", {"allow_show": False})
        self.ok("0.6: a picture reaches the mirror on this computer only while she shows it (Zeigen), never otherwise",
                unshown is None and bool(shown) and shown.get("jpeg") == jpeg, (unshown, bool(shown)))
        phone.close()
        gone = get(twin, "phone")
        self.ok("0.6: the mirror hears when the phone goes", bool(gone) and gone.get("connected") is False, gone)
        twin.close()


    def translate(self, url, api, wav):
        """0.7, Übersetzen: the sound only when allowed; the words back to the phone alone; ROS gets counts only."""
        from urllib.parse import urlsplit, urlunsplit
        u = urlsplit(url)

        def get(link, t, timeout=3.0):
            try:
                return link.expect(t, timeout)
            except TimeoutError:
                return None

        if wav:
            with wave.open(wav, "rb") as w:
                if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, 16000):
                    raise SystemExit(f"{wav}: not 16 kHz mono PCM16")
                pcm = w.readframes(w.getnframes())
        else:
            pcm = b"\0" * 32000   # a second of silence
        chunks = [base64.b64encode(pcm[i:i + 8000]).decode() for i in range(0, len(pcm), 8000)]

        twin = MockPhone(urlunsplit((u.scheme, u.netloc, c.MIRROR, u.query, "")))
        phone = MockPhone(url)
        phone.hello()
        self.status(True)
        api("/api/act", {"allow_translate": False})
        get(phone, "translate", 1.0)
        before = len(self.got.get("translate_result", []))
        phone.send(t="audio", lang="de", seq=0, pcm=chunks[0])
        refused = get(phone, "translate")
        phone.send(t="audio", lang="de", end=True)
        self.wait("translate_result", lambda m: False, timeout=0.5)
        self.ok("0.7: Übersetzen's sound is refused unless allowed: the phone is told, nothing is heard",
                refused == {"t": "translate", "allowed": False, "ready": False}
                and len(self.got.get("translate_result", [])) == before and get(phone, "heard", 0.3) is None, refused)
        st = json.load(api("/api/state")).get("translate", {})
        api("/api/act", {"allow_translate": True})
        allowed = get(phone, "translate")
        self.ok("0.7: allowed from the setup page, the phone hears that it may talk, with the models ready",
                bool(allowed) and (allowed["allowed"], allowed["ready"]) == (True, True) and st.get("ready") is True
                and st.get("link_ok") is True, (allowed, st))
        for i, b in enumerate(chunks):   # as the phone sends them while a half is held
            phone.send(t="audio", lang="de", seq=i, pcm=b)
        phone.send(t="audio", lang="de", end=True)
        heard = get(phone, "heard", 30.0)   # the first one waits for the models to load
        said = get(phone, "translated", 10.0) if heard and heard.get("text") else None
        r = self.wait("translate_result", timeout=5.0)
        counts = json.loads(r.data) if r else {}
        if wav:
            good = bool(heard) and len(heard["text"]) > 3 and bool(said) and said["lang"] == "fr" and len(said["text"]) > 3 \
                and counts.get("ok") is True and counts.get("words", 0) > 0
        else:
            good = heard == {"t": "heard", "lang": "de", "text": "", "error": "nothing", "who": "robot"} and counts.get("ok") is False
        self.ok("0.7: held and let go, the phone gets what was heard" + (" and its French" if wav else " (nothing, for silence)"),
                good, (heard, said and said.get("text"), counts))
        words = set(((heard or {}).get("text", "") + " " + ((said or {}).get("text", ""))).lower().split()) - {""}
        mirrored = list(twin.got.queue)
        st = json.load(api("/api/state"))
        leaked = [m for m in mirrored if m.get("t") in ("heard", "translated", "audio")]
        self.ok("0.7: the words reach neither the mirror nor ROS nor the setup page: counts only",
                not leaked and set(counts) <= {"ok", "from", "to", "words", "seconds", "ms"}
                and not any(w in json.dumps(st).lower() for w in words if len(w) > 3)
                and st.get("translate", {}).get("last", {}).get("words") == counts.get("words"), (leaked, counts))
        self.guest(api, phone, twin, chunks, wav)
        api("/api/act", {"allow_translate": False})
        off, end = None, time.monotonic() + 3.0
        while time.monotonic() < end and not (off and off["allowed"] is False):   # (after the guest's: the last one says so)
            off = get(phone, "translate", max(0.1, end - time.monotonic()))
        self.ok("0.7: not allowed any more, the phone is told at once (and no guest link)",
                bool(off) and off["allowed"] is False and not off.get("guest"), off)
        phone.close()
        twin.close()


    def guest(self, api, phone, twin, chunks, wav):
        """0.7, a guest phone on the Wi-Fi (talk.html, the guest port): the robot's phone gets its link for the QR code,
        the mirror never; both phones see what either says; a new code sends the guest away."""
        g = json.load(api("/api/state")).get("translate", {}).get("guest", {})
        if not g.get("port"):
            self.ok("0.7: the guest port (skipped: the bridge has none, guest_port:=)", True)
            return

        def get(link, t, timeout=3.0):
            try:
                return link.expect(t, timeout)
            except TimeoutError:
                return None

        api("/api/act", {"guest_new": True})
        st = get(phone, "translate")
        link = (st or {}).get("guest", "")
        from urllib.parse import parse_qs, urlsplit
        k = parse_qs(urlsplit(link).query).get("k", [""])[0]
        self.ok("0.7: the robot's phone gets the guest page's link with a fresh code, for its QR code",
                link.startswith("https://") and f":{g['port']}/talk.html?k=" in link and len(k) >= 12 and st.get("guest_on") is False, st)
        guest = MockPhone(f"wss://127.0.0.1:{g['port']}/ws/talk?k={k}")
        joined = get(phone, "translate")
        gs = get(guest, "translate")
        self.ok("0.7: a guest phone joins with the code: the robot's phone hears it (its QR code goes), the guest may talk",
                bool(joined) and joined.get("guest_on") is True and bool(gs) and gs.get("allowed") is True
                and gs.get("ready") is True and "guest" not in {k2 for k2, v in gs.items() if v}, (joined, gs))
        for i, b in enumerate(chunks):
            guest.send(t="audio", lang="de", seq=i, pcm=b)
        guest.send(t="audio", lang="de", end=True)
        if wav:
            on_guest, on_robot = get(guest, "translated", 30.0), get(phone, "translated", 5.0)
            good = bool(on_guest) and on_guest == on_robot and on_guest.get("who") == "guest" and len(on_guest.get("text", "")) > 3
        else:
            on_guest, on_robot = get(guest, "heard", 30.0), get(phone, "heard", 1.0)
            good = bool(on_guest) and on_guest.get("error") == "nothing" and on_robot is None   # an error: the speaker only
        self.ok("0.7: what the guest says reaches both phones, marked as the guest's" + ("" if wav else " (silence: the guest alone hears nothing)"),
                good, (on_guest, on_robot))
        for i, b in enumerate(chunks[:4]):
            phone.send(t="audio", lang="de", seq=i, pcm=b)
        phone.send(t="audio", lang="de", end=True)
        if wav:
            back = get(guest, "translated", 15.0) or get(guest, "heard", 1.0)
            self.ok("0.7: what the robot's phone hears reaches the guest too, marked as the robot's",
                    bool(back) and back.get("who") == "robot", back)
        mirrored = json.dumps(list(twin.got.queue))
        self.ok("0.7: the mirror gets neither the guest's link and code nor any words",
                k not in mirrored and "talk.html" not in mirrored and '"heard"' not in mirrored and '"translated"' not in mirrored, len(mirrored))
        api("/api/act", {"guest_new": True})
        gone = guest.closed.wait(3)
        try:
            MockPhone(f"wss://127.0.0.1:{g['port']}/ws/talk?k={k}")
            old = "accepted"
        except ConnectionError as e:
            old = str(e)
        self.ok("0.7: a new guest code sends the guest away; the old code is refused",
                gone and "403" in old and json.load(api("/api/state"))["translate"]["guest"]["connected"] is False, (gone, old))


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--robot", default="thymio_1")
    a.add_argument("--port", type=int, default=c.PORT)
    a.add_argument("--key", default="")
    a.add_argument("--wav", help="German speech, 16 kHz mono, for Übersetzen")
    args = a.parse_args()
    url = f"ws://127.0.0.1:{args.port}/ws" + (f"?key={args.key}" if args.key else "")
    sys.exit(Check(args.robot).run(url, args.wav))


if __name__ == "__main__":
    main()

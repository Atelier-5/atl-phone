# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""contract_check — does a running bridge keep the contract (contract.py)? A mock phone plays the phone.

    python3 -m atl_phone.contract_check [--robot thymio_1] [--port 8782] [--key ...]

Prints one line per check (PASS/FAIL) and exits 1 if any failed. Also the setup page's API (on this PC). Run it with no real
phone on the bridge: the mock phone takes over, and a real one would be closed.
"""
import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile
from geometry_msgs.msg import Point
from sensor_msgs.msg import BatteryState, Imu
from std_msgs.msg import Bool, ColorRGBA, Float32, Int32, String

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
                                ("touch", String, 10), ("battery", BatteryState, latched)]:
            self.n.create_subscription(kind, self.t[name], lambda m, k=name: self.got.setdefault(k, []).append(m), qos)
        self.pub = {name: self.n.create_publisher(kind, self.t[name], 10) for name, kind in
                    [("expression", String), ("gaze", Point), ("color", ColorRGBA), ("say", String),
                     ("torch", Bool), ("vibrate", Int32)]}
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

    def run(self, url: str) -> int:
        phone = MockPhone(url)
        phone.hello()
        s = self.status(True)
        detail = json.loads(s.data) if s else {}
        self.ok("status: connected, with the phone's model and contract", bool(s) and detail.get("model") == "MOCK-PHONE"
                and detail.get("contract") == c.CONTRACT, json.dumps(detail)[:120])

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

        second = MockPhone(url)
        second.hello()
        self.ok("a second phone takes over and the first is closed", phone.closed.wait(3.0))
        second.close()
        self.ok("status: disconnected when the phone is gone", bool(self.status(False)))
        try:
            api("/api/act", {"topic": "expression", "value": "happy"})
            refused = None
        except urllib.error.HTTPError as e:
            refused = (e.code, json.load(e).get("error"))
        self.ok("setup page: with no phone, an output test is refused", refused == (400, "no phone"), refused)

        print(f"{'all passed' if not self.failed else f'{self.failed} failed'}")
        self.n.destroy_node()
        rclpy.shutdown()
        return 1 if self.failed else 0


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--robot", default="thymio_1")
    a.add_argument("--port", type=int, default=c.PORT)
    a.add_argument("--key", default="")
    args = a.parse_args()
    url = f"ws://127.0.0.1:{args.port}/ws" + (f"?key={args.key}" if args.key else "")
    sys.exit(Check(args.robot).run(url))


if __name__ == "__main__":
    main()

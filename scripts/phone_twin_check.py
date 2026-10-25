#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""phone_twin_check — the phone's Webots twin on the Thymio twin: does the bridge see it as a phone, and does it see?

    (the bridge with the guardian, atl-bot-thymio's container and the twin, on ROS_DOMAIN_ID 77; see README)
    python3 scripts/phone_twin_world.py ~/atl/atl-ide/mydocs/twin --things     # then Webots on webots/worlds/table_phone.wbt
    python3 scripts/phone_twin_check.py [--port 8792] [--gateway http://127.0.0.1:8781]

Only the bridge's setup API and the Thymio's gateway: the twin is a phone like any other (contract atl-phone/0.4).
It checks that it rides on the Thymio (gravity in the phone's frame, leaning back), the heading, the vision against
the world's geometry (a marker's distance within 2 cm, a cup, a red ball, a face), and that the Desk Guardian, unchanged,
turns the robot to the face it sees through the twin's camera. Standard library only.
"""
import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from phone_twin_world import THINGS  # noqa: E402

TILT, PHONE, FRONT_AT = 0.2, (0.0747, 0.1585, 0.0077), 0.074   # the holder's default, the A50 (phones.json)
HOLDER, TOP = (0.02, 0.0, 0.053), 0.7505                         # the holder on the Thymio, the Thymio on the table


def front_camera(x, y, yaw):
    """Where the front camera is, in the world, for the Thymio at x, y, yaw (the holder's mount, portrait)."""
    s, c = math.sin(TILT), math.cos(TILT)
    up = PHONE[1] / 2 + FRONT_AT                    # from the phone's bottom edge to the camera, up the screen
    back = -s * up - c * PHONE[2] / 2 + HOLDER[0]   # ahead of the Thymio's centre (negative: behind the holder)
    return (x + back * math.cos(yaw), y + back * math.sin(yaw), TOP + HOLDER[2] + 0.012 + c * up - s * PHONE[2] / 2)


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--port", type=int, default=8792)
    a.add_argument("--gateway", default="http://127.0.0.1:8781")
    args = a.parse_args()
    bridge = f"http://127.0.0.1:{args.port}"
    failed = 0

    def ok(name, good, detail=""):
        nonlocal failed
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
        failed += not good

    def call(url, body=None):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.load(r) if r.headers.get("Content-Type", "").startswith("application/json") else None

    state = lambda: call(bridge + "/api/state")
    act = lambda body: call(bridge + "/api/act", body)
    gw = lambda path, body=None: call(args.gateway + path, body)

    def fresh(kind, since, timeout=3.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            v = state()["seen"].get(kind)
            if v and v.get("at", 0) > since:
                return v
            time.sleep(0.1)
        return None

    act({"guardian": False})
    gw("/behaviour", {"name": "none"})
    gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
    time.sleep(1.5)
    s = state()
    ph = s.get("phone") or {}
    ok("the twin is connected as a phone", s["connected"] and ph.get("model") == "A50 twin", f"{ph.get('model')}, {ph.get('ua')}")

    t0 = time.time()
    imu, head = fresh("imu", t0), fresh("heading", t0)
    want = (0.0, 9.81 * math.cos(TILT), 9.81 * math.sin(TILT))
    ok("it rides on the Thymio, leaning back: gravity along the screen and a little out of it",
       imu and all(abs(imu["acc"][i] - want[i]) < 0.3 for i in range(3)) and max(map(abs, imu["gyro"])) < 0.05,
       f"acc {[round(v, 2) for v in imu['acc']] if imu else None}, want {[round(v, 2) for v in want]}")
    ok("its heading: east (90°) for the Thymio along the table", head and abs(head["deg"] - 90) < 2, f"{head and round(head['deg'], 1)}")

    t0 = time.time()
    act({"topic": "see", "value": {"camera": "front", "find": ["markers", "objects", "blobs", "faces"],
                                   "blob": {"hue": 0, "tol": 25}, "marker_cm": 6}})
    markers, objects, blobs, faces = (fresh(k, t0) for k in ("markers", "objects", "blobs", "faces"))
    cam = front_camera(0.0, 0.0, 0.0)
    at = {t[0]: t[2] for t in THINGS}
    dist = math.dist(cam, at["MARKER"])
    m = next((m for m in (markers or {}).get("markers", []) if m["id"] == 3), None)
    ok("marker 3: its distance within 2 cm, square on, to the right", m and abs(m["distance_m"] - dist) < 0.02 and abs(m["yaw_deg"]) < 5
       and m["x"] < 0, f"{m and m['distance_m']} m, want {dist:.3f}; yaw {m and m['yaw_deg']}, x {m and round(m['x'], 2)}")
    cup = next((o for o in (objects or {}).get("objects", []) if o["label"] == "cup"), None)
    ok("a cup, on the left", cup and cup["x"] > 0 and abs(cup["distance_m"] - math.dist(cam, at["CUP"])) < 0.02,
       f"{cup and (round(cup['x'], 2), cup['distance_m'])}")
    bl = (blobs or {}).get("blobs", [])
    ok("the red ball: a blob on the right", len(bl) == 1 and bl[0]["x"] < 0, f"{bl}")
    fa = (faces or {}).get("faces", [])
    ok("a face beyond the table, on the left", len(fa) == 1 and fa[0]["x"] > 0.3, f"{fa}")
    act({"topic": "see", "value": {"camera": "back", "find": ["markers", "objects"]}})
    time.sleep(1.0)
    t0 = time.time()
    back = fresh("objects", t0)
    ok("the back camera sees none of them (they are ahead)", back and back["camera"] == "back" and not back["objects"], f"{back}")
    act({"topic": "see", "value": {"camera": "front", "find": []}})
    time.sleep(0.5)
    ok("see nothing: vision off", state()["seen"].get("see", {}).get("on") is False, f"{state()['seen'].get('see')}")

    # the Desk Guardian, unchanged: it asks for look, the twin's Recognition finds the face, the guardian turns to it
    y0 = gw("/state")["pose"]["yaw"]
    act({"guardian": True, "drive": True})
    turning, states, gyro = [], set(), 0.0
    end = time.monotonic() + 8.0
    while time.monotonic() < end:
        time.sleep(0.25)
        s = state()
        states.add(s["guardian"].get("state"))
        gyro = max(gyro, max(map(abs, s["seen"].get("imu", {}).get("gyro", [0]))))
        turning.append(gw("/state")["pose"]["yaw"])
    face_yaw = math.atan2(at["FACE"][1] - cam[1], at["FACE"][0] - cam[0])
    ok("the guardian sees the face through the twin and turns the Thymio to it",
       {"alert", "intruder"} & states and max(turning) - y0 > 0.2 and abs(turning[-1] - face_yaw) < 0.25,
       f"states {sorted(s for s in states if s)}, yaw {y0:.2f} -> {turning[-1]:.2f} (the face at {face_yaw:.2f})")
    ok("turning, the twin's gyro moves", gyro > 0.2, f"max |gyro| {gyro:.2f} rad/s")
    act({"guardian": False})
    time.sleep(1.0)
    gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        sys.exit(f"no bridge or gateway: {e}")

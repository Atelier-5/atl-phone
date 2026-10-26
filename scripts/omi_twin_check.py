#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""omi_twin_check — Omi Assist's Webots twin (the robot alone on the table, with its props): does it work as the robot will?

    python3 scripts/phone_twin_world.py ~/atl/atl-ide/mydocs/twin --scene omi    # then Webots on webots/worlds/table_omi.wbt,
    # atl-bot-thymio's launch with table:=webots/worlds/table_omi.json and the twin (--model ANE-LX1) on the test bridge
    python3 scripts/omi_twin_check.py [--port 8792] [--gateway http://127.0.0.1:8781]

Only the bridge's setup API and the Thymio's gateway, as the setup page uses them. It checks: the twin is the ANE-LX1 in
its clamp (gravity in its frame: the clamp's 15 degrees back) and listens for props; the table is empty (neither camera
finds anything); the cup flies in and "what is this?" names it; the letter on its easel behind the robot is read (its
line count), and the letter held in a hand too (so the back camera's view is free of the Pi and the riser); a visitor's
face is seen by the front camera; "away" leaves the table empty again; and the robot stays on its wheels when it starts,
turns and stops as the guardian does (it tips at the Thymio's full 0.2 m/s: printed as INFO, a known limit). Standard library only.
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TILT = 0.26          # AtlOmiStack's default
SAFE = 0.1           # m/s: above the guardian's 0.06, under the 0.12 where the stack starts to rock (measured)
TURN = 1.5           # rad/s: the guardian's turn away from an edge


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--port", type=int, default=8792)
    a.add_argument("--gateway", default="http://127.0.0.1:8781")
    args = a.parse_args()
    bridge = f"http://127.0.0.1:{args.port}"
    letter = [x for x in json.loads((HERE / "webots" / "letter.json").read_text())["lines"] if x]
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

    def fresh(kind, since, timeout=4.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            v = state()["seen"].get(kind)
            if v and v.get("at", 0) > since:
                return v
            time.sleep(0.1)
        return None

    def finds(camera, settle=1.2):
        """What the camera finds now: faces, objects, markers (vision on for a moment)."""
        t0 = time.time()
        act({"topic": "see", "value": {"camera": camera, "find": ["faces", "objects", "markers"]}})
        time.sleep(settle)
        got = {k: (fresh(k, t0, 2.0) or {}).get(k, []) for k in ("faces", "objects", "markers")}
        act({"topic": "see", "value": {"find": []}})
        return got

    def ask(kind):
        t0 = time.time()
        act({"topic": kind, "value": {"lang": "de"}})
        return fresh(kind, t0, 5.0)

    act({"guardian": False})
    act({"omi": False})
    act({"prop": "away"})
    gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
    time.sleep(2.0)
    s = state()
    ph = s.get("phone") or {}
    ok("the twin is the ANE-LX1, and listens for props (a mirror)", s["connected"] and ph.get("model") == "ANE-LX1 twin"
       and s.get("mirrors", 0) >= 1, f"{ph.get('model')}, mirrors {s.get('mirrors')}")
    t0 = time.time()
    imu = fresh("imu", t0)
    want = (0.0, 9.81 * math.cos(TILT), 9.81 * math.sin(TILT))
    acc = imu["acc"] if imu else [0, 0, 0]
    ok("it stands in the clamp, leaning back 15 degrees (gravity in the phone's frame)",
       bool(imu) and all(abs(acc[i] - want[i]) < 0.3 for i in range(3)), [round(v, 2) for v in acc])

    front, back = finds("front"), finds("back")
    ok("the table is empty: neither camera finds a face, an object or a marker",
       not any(front.values()) and not any(back.values()), (front, back))

    act({"prop": "cup"})
    time.sleep(2.5)
    w = ask("what")
    ok("the cup flies in behind the robot, and \"what is this?\" names it", bool(w) and w.get("label") == "cup", w)

    act({"prop": "letter"})
    time.sleep(2.5)
    r = ask("read")
    ok(f"the letter on its easel behind the robot is read: {len(letter)} lines", bool(r) and r.get("lines") == len(letter), r)

    act({"prop": "hand"})
    time.sleep(2.5)
    r = ask("read")
    ok("the letter held in a hand is read too: the back camera's view is free", bool(r) and r.get("lines") == len(letter), r)

    act({"prop": "visitor"})
    time.sleep(2.5)
    seen = finds("front")
    ok("a visitor comes: the front camera finds the face", len(seen["faces"]) == 1, seen["faces"])

    act({"prop": "away"})
    time.sleep(1.5)
    front, back = finds("front"), finds("back")
    ok("\"away\": the props go, the table is empty again", not any(front.values()) and not any(back.values()), (front, back))

    def upright(linear, angular, secs=1.5):
        """Drive, stop suddenly, and say how far the phone's gravity moved (degrees) and the pose's z change."""
        gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
        time.sleep(1.5)
        rest = (fresh("imu", time.time()) or {}).get("acc", acc)
        z0 = gw("/state")["pose"]["z"]
        worst, end = 0.0, time.monotonic() + secs + 1.5
        while time.monotonic() < end:
            on = time.monotonic() < end - 1.5
            gw("/drive", {"linear": linear if on else 0.0, "angular": angular if on else 0.0})
            worst = max(worst, abs(gw("/state")["pose"]["z"] - z0))
            time.sleep(0.1)
        time.sleep(0.5)
        after = (fresh("imu", time.time()) or {}).get("acc", [0, 0, 0])
        n = (math.sqrt(sum(v * v for v in rest)) * math.sqrt(sum(v * v for v in after))) or 1
        angle = math.degrees(math.acos(max(-1.0, min(1.0, sum(rest[i] * after[i] for i in range(3)) / n))))
        return angle, worst

    angle, lift = upright(SAFE, 0.0)
    ok(f"a start and a sudden stop at {SAFE} m/s (the guardian drives at most 0.06): the robot stays on its wheels",
       angle < 1.0 and lift < 0.003, f"{angle:.2f} degrees after, the body rose {lift * 1000:.1f} mm at most")
    angle, lift = upright(0.0, TURN)
    ok(f"a turn at {TURN} rad/s (the guardian's turn away from an edge) and a stop: it stays on its wheels",
       angle < 1.0 and lift < 0.003, f"{angle:.2f} degrees after, the body rose {lift * 1000:.1f} mm at most")
    angle, lift = upright(0.2, 0.0)
    print(f"INFO  the Thymio's full speed (0.2 m/s) with the stack: the body rose {lift * 1000:.0f} mm, {angle:.0f} degrees "
          "after (a known limit: keep the stack under 0.12 m/s; see webots/omi_robot.ttl)", flush=True)
    gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as e:
        sys.exit(f"no bridge or gateway: {e}")

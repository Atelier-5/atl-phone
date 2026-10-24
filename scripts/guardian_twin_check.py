#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""guardian_twin_check — the Desk Guardian on the Thymio twin in Webots, with a mock phone: does the body follow?

    (Webots with an atl-ide table, and atl-bot-thymio's container, on ROS_DOMAIN_ID 77; see README)
    docker run -d --name atl-phone-check --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp -e ROS_DOMAIN_ID=77 \\
        atl-phone:kilted ros2 launch atl_phone phone.launch.py port:=8792 guardian:=true
    python3 scripts/guardian_twin_check.py [--port 8792] [--gateway http://127.0.0.1:8781]

The mock phone shows a face on the left, then nothing; the gateway (atl-bot-thymio) lifts the robot and puts it
at the table's edge, as a hand would. The checks read the twin's pose and wheels: the guardian, a ROS node that
knows only topics, drives the simulated Thymio as it will a real one. Standard library only.
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ros2" / "atl_phone"))
from atl_phone.mock_phone import MockPhone  # noqa: E402


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--port", type=int, default=8792)
    a.add_argument("--gateway", default="http://127.0.0.1:8781")
    args = a.parse_args()
    failed = 0

    def ok(name, good, detail=""):
        nonlocal failed
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
        failed += not good

    def gw(path, body=None):
        req = urllib.request.Request(args.gateway + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.load(r) if r.headers.get("Content-Type", "").startswith("application/json") else None

    phone = MockPhone(f"ws://127.0.0.1:{args.port}/ws")
    phone.hello()
    faces, said = [], []

    def world(seconds):
        """The mock phone's camera sees `faces` 20 times a second; what the phone is told to say is kept."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            phone.faces(*faces)
            phone.imu()
            time.sleep(0.05)
            while not phone.got.empty():
                m = phone.got.get()
                if m.get("t") == "say":
                    said.append(m["text"])

    def yaw():
        return gw("/state")["pose"]["yaw"]

    gw("/behaviour", {"name": "none"})
    gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
    world(1.0)
    y0, seen = yaw(), []
    for _ in range(16):  # a whole look-around (8 s)
        world(0.5)
        seen.append(yaw())
    ok("guarding: the guardian turns the twin to look around", max(abs(v - y0) for v in seen) > 0.2,
       f"yaw {y0:.2f} -> {min(seen):.2f}..{max(seen):.2f}")

    faces[:] = [{"x": 0.7, "size": 0.2}]
    y0 = yaw()
    world(1.5)
    y1 = yaw()
    ok("a face on its left: the twin turns left, towards it", y1 - y0 > 0.4 and "Who's there?" in said, f"yaw {y0:.2f} -> {y1:.2f}, said {said}")
    faces[:] = []

    gw("/lift", {"up": True})
    world(1.0)
    st = gw("/state")
    ok("lifted (the ground sensors see nothing): scared, and the wheels stop",
       "Put me down!" in said and all(abs(w) < 0.05 for w in st["wheels"]), f"wheels {st['wheels']}")
    gw("/lift", {"up": False})
    world(1.5)

    # at the table's right edge (x 0.6), turned so that its right ground sensor is over it and the left one is not
    # (measured on the twin); turned further (yaw 1.2) a wheel goes over first and the twin tips onto its nose
    x0 = 0.53
    gw("/place", {"name": "thymio_1", "x": x0, "y": 0.0, "yaw": 0.4})
    world(3.0)
    st = gw("/state")
    p = st["pose"]
    ok("at the edge: \"Whoa, the edge!\", it backs off and stays on the table",
       "Whoa, the edge!" in said and p["x"] < x0 - 0.02 and p["z"] > -0.002, f"pose x {p['x']:.3f} z {p['z']:.4f}, ground {st['ground']}, said {said[-2:]}")

    gw("/place", {"name": "thymio_1", "x": 0.0, "y": 0.0, "yaw": 0.0})
    phone.close()
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""guardian_check — the Desk Guardian's story, played against a running bridge and guardian, with no phone and no Webots.

    ros2 launch atl_phone phone.launch.py port:=8792 guardian:=true      (ROS_DOMAIN_ID of its own, e.g. 77)
    python3 -m atl_phone.guardian_check [--robot thymio_1] [--port 8792]

A mock phone plays the phone (faces, a card, a lift, a long touch) and a fake Thymio the body (its ground
sensors; it records cmd_vel). The guardian only sees topics, so this is the same run as with the real phone on
the Thymio twin: the backend's test scenario. One PASS/FAIL line per step; exits 1 if any failed.
"""
import argparse
import json
import queue
import sys
import time
import urllib.request

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, String

from . import contract as c
from . import guardian as gd
from .guardian_node import thymio_topics
from .mock_phone import MockPhone

DESK = [700.0, 700.0]           # the Thymio's ground sensors on a white desk


class Story:
    def __init__(self, robot: str, port: int):
        rclpy.init()
        self.n = rclpy.create_node("guardian_check")
        self.base = f"http://127.0.0.1:{port}"
        self.url = f"ws://127.0.0.1:{port}/ws"
        th = thymio_topics(robot)
        self.ground = self.n.create_publisher(Float32MultiArray, th["ground"], 10)
        self.cmds, self.faces, self.states = [], [], []
        self.n.create_subscription(Twist, th["cmd_vel"], lambda m: self.cmds.append((time.monotonic(), m.linear.x, m.angular.z)), 10)
        self.n.create_subscription(String, c.topics(robot)["faces"], lambda m: self.faces.append(json.loads(m.data)), 10)
        self.n.create_subscription(String, f"/{robot}/guardian/state", lambda m: self.states.append(json.loads(m.data)["state"]), 10)
        self.got = []               # what the phone was sent: (time, message)
        self.now_faces = []         # what the mock phone's front camera "sees"
        self.acc = (0.0, 0.0, 9.81)
        self.desk = list(DESK)
        self.failed = 0

    def ok(self, name: str, good: bool, detail=""):
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
        self.failed += not good

    def api(self, body):
        req = urllib.request.Request(self.base + "/api/act", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=5)

    def run_for(self, seconds: float, until=None):
        """The world goes on: the camera sees now_faces, the IMU feels acc, the Thymio stands on desk, 20 times a second.
        Returns the first message to the phone that until() accepts (from now on), or None."""
        start, end, next_at = time.monotonic(), time.monotonic() + seconds, 0.0
        while time.monotonic() < end:
            if time.monotonic() >= next_at:
                next_at = time.monotonic() + 0.05
                self.phone.faces(*self.now_faces)
                self.phone.imu(self.acc)
                self.ground.publish(Float32MultiArray(data=self.desk))
            rclpy.spin_once(self.n, timeout_sec=0.01)
            try:
                while True:
                    self.got.append((time.monotonic(), self.phone.got.get_nowait()))
            except queue.Empty:
                pass
            if until:
                for at, m in self.got:
                    if at >= start and until(m):
                        return m
        return None

    def to_phone(self, t, seconds=4.0, **want):
        return self.run_for(seconds, lambda m: m.get("t") == t and all(m.get(k) == v for k, v in want.items()))

    def cmds_since(self, t0):
        return [(lin, ang) for at, lin, ang in self.cmds if at >= t0]

    def run(self) -> int:
        self.phone = MockPhone(self.url)
        self.phone.hello()
        en = gd.SAY["en"]

        m = self.to_phone("look", on=True)
        self.ok("the guardian asks the phone to look; telling faces apart is refused (not allowed yet)",
                bool(m) and m.get("familiar") is False, m)

        t0 = time.monotonic()
        m = self.to_phone("face", expression="sleepy")
        self.run_for(3.0)
        turns = [a for _, a in self.cmds_since(t0)]
        self.ok("nobody there: sleepy eyes, and it looks around (cmd_vel)", bool(m) and turns and max(abs(a) for a in turns) > 0.1,
                f"{len(turns)} cmd_vel")

        self.api({"allow_familiar": True})
        m = self.to_phone("look", on=True, familiar=True)
        self.ok("the facilitator allows familiar (setup page): the phone is asked to tell faces apart", bool(m), m)

        self.now_faces = [{"x": 0.6, "size": 0.2, "familiar": 1}]
        t0 = time.monotonic()
        m = self.to_phone("say", text=en["alert"])
        face = [x for at, x in self.got if at >= t0 and x.get("t") == "face"]
        turns = [a for _, a in self.cmds_since(t0)]
        self.ok("a face appears on its left: surprised, \"Who's there?\", it turns left to it",
                bool(m) and any(x["expression"] == "surprised" for x in face) and turns and max(turns) > 0.5,
                f"max turn {max(turns) if turns else None}")

        self.phone.send(t="code", text=gd.OWNER_CARD)
        m = self.to_phone("say", text=en["owner"])
        self.ok("the owner card with that face: happy, and it says it will remember", bool(m)
                and any(x.get("expression") == "happy" for _, x in self.got[-40:] if x.get("t") == "face"))
        self.now_faces = [{"x": 0.0, "size": 0.2, "familiar": 1}]
        self.run_for(1.0)
        self.ok("the same face (number 1) stays a friend", self.states[-1:] == ["friend"], self.states[-1:])

        self.now_faces = [{"x": 0.0, "size": 0.5, "familiar": 2}]
        t0 = time.monotonic()
        m = self.to_phone("face", seconds=2.0, expression="surprised")
        self.ok("another face (number 2), close: alert, not a friend", bool(m), m)
        m = self.to_phone("say", seconds=gd.INTRUDER_AFTER + 3, text=en["intruder"])
        self.run_for(0.6)
        sent = [x for at, x in self.got if at >= t0]
        self.ok(f"still close after {gd.INTRUDER_AFTER:.0f} s: an intruder: angry, buzz, backs off",
                bool(m) and any(x.get("expression") == "angry" for x in sent) and any(x.get("t") == "vibrate" for x in sent)
                and min(lin for lin, _ in self.cmds_since(t0)) < 0)

        self.now_faces = []
        self.acc = (0.0, 0.0, 16.0)
        t0 = time.monotonic()
        m = self.to_phone("say", text=en["scared"])
        self.run_for(0.5)
        last = self.cmds_since(time.monotonic() - 0.3)
        self.ok("picked up (the phone's IMU): scared, \"Put me down!\", the wheels stop",
                bool(m) and last and all(lin == 0 and ang == 0 for lin, ang in last), last[-1:])
        self.acc = (0.0, 0.0, 9.81)
        self.run_for(1.5)

        self.desk = [50.0, 700.0]
        t0 = time.monotonic()
        m = self.to_phone("say", seconds=2.0, text=en["edge"])
        self.desk = list(DESK)
        self.run_for(gd.EDGE_BACK + gd.EDGE_TURN + 0.3)
        moves = self.cmds_since(t0)
        self.ok("the left ground sensor over the edge: it backs off and turns right",
                bool(m) and min(lin for lin, _ in moves) < 0 and min(ang for _, ang in moves) < -1.0)

        self.phone.send(t="touch", kind="long", zone="centre")
        m = self.to_phone("face", expression="love")
        self.ok("a long touch: love", bool(m))
        self.run_for(0.5)  # guardian/state comes at 5 Hz

        seen = set(self.states)
        want = set(gd.FACES)
        self.ok("guardian/state went through every state", want <= seen, f"missing: {sorted(want - seen)}" if want - seen else "")

        self.api({"allow_familiar": False})
        self.now_faces = [{"x": 0.0, "size": 0.05, "familiar": 4}]  # the phone sends a number anyway
        self.run_for(0.5)
        self.ok("familiar taken back: faces reach ROS without their numbers again",
                bool(self.faces) and all(f["familiar"] is None for f in self.faces[-1]["faces"]), self.faces[-1:] or None)
        self.phone.close()
        print(f"{'all passed' if not self.failed else f'{self.failed} failed'}")
        self.n.destroy_node()
        rclpy.shutdown()
        return 1 if self.failed else 0


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--robot", default="thymio_1")
    a.add_argument("--port", type=int, default=c.PORT)
    args = a.parse_args()
    sys.exit(Story(args.robot, args.port).run())


if __name__ == "__main__":
    main()

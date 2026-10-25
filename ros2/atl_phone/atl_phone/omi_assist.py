# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""omi_assist — Omi Assist: the phone on a stand as a helper, with big spoken tiles, eyes that follow, and reminders.

    ros2 run atl_phone omi_assist --ros-args -p robot:=thymio_1 [-p lang:=de] [-p folder:=/omi] [-p run:=true]

    out: /<robot>/phone/panel (the tiles), see (the eyes follow), say, note; /<robot>/omi/state (String JSON, 1 Hz)
    in:  /<robot>/phone/status, faces, menu, note/answer; /<robot>/omi/run (Bool), /<robot>/omi/reminders (String JSON list)

The helpers themselves (the time, the magnifier, reading, "what is this?", the cameras, showing) run on the phone
(web/omi.js): a picture needs no trip to the PC. This node sets the phone up for them, greets a face that comes after a
while, and brings the assistant's reminders at their time (omi.py), as a card she answers on the phone.
Stopped, it puts the panel back to the chips and the eyes' following off.
"""
import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, String

from . import contract as c
from . import omi

GREET_AFTER = 300.0     # s without a face: the next face is greeted
CHECK_EVERY = 5.0       # s between two looks at the reminders
PANEL = {"mode": "mouth", "style": "tiles", "menu": c.OMI_MENU}
SEE = {"camera": "front", "find": ["faces", "hands"], "follow": True}


class OmiAssist(Node):
    def __init__(self):
        super().__init__("omi_assist")
        robot = self.declare_parameter("robot", "thymio_1").value
        self.lang = self.declare_parameter("lang", "de").value
        self.running = bool(self.declare_parameter("run", False).value)
        self.reminders = omi.Reminders(self.declare_parameter("folder", "").value or None)
        t = c.topics(robot)
        self.pub = {k: self.create_publisher(String, t[k], 10) for k in ("panel", "see", "say", "note")}
        self.state_pub = self.create_publisher(String, f"/{robot}/omi/state", 10)
        self.connected, self.face_seen, self.picks, self.open_note = False, 0.0, [], None
        self.create_subscription(String, t["status"], self.on_status, QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(String, t["faces"], self.on_faces, 10)
        self.create_subscription(String, t["menu"], self.on_menu, 10)
        self.create_subscription(String, t["note_answer"], self.on_answer, 10)
        self.create_subscription(Bool, f"/{robot}/omi/run", lambda m: self.run(m.data), 10)
        self.create_subscription(String, f"/{robot}/omi/reminders", self.on_reminders, 10)
        self.create_timer(CHECK_EVERY, self.check)
        self.create_timer(1.0, self.publish_state)
        self.panel = dict(PANEL, lang=self.lang)   # the tiles in Omi's language, whatever the phone's own
        if self.running:
            self.set_up()
        self.get_logger().info(f"Omi Assist on /{robot}: {'running' if self.running else 'waiting to be started'},"
                               f" {len(self.reminders.items)} reminders")

    def send(self, k, body):
        self.pub[k].publish(String(data=json.dumps(body)))

    def set_up(self):
        """The phone as Omi wants it: the tiles, the eyes following; sent again when a phone comes."""
        self.send("panel", self.panel)
        self.send("see", SEE)

    def run(self, on: bool):
        if on == self.running:
            return
        self.running = on
        if on:
            self.set_up()
        else:  # as it was before: the chips, no following, no card
            self.send("panel", {"mode": "mouth", "style": "chips", "menu": list(c.PANEL_MODES), "lang": "auto"})
            self.send("see", {"camera": "front", "find": []})
            if self.open_note:
                self.send("note", {"id": self.open_note, "text": ""})
                self.open_note = None
        self.get_logger().info(f"Omi Assist {'started' if on else 'stopped'}")

    def on_status(self, m):
        connected = bool(json.loads(m.data).get("connected"))
        if connected and not self.connected and self.running:
            self.set_up()
        self.connected = connected

    def on_faces(self, m):
        if not json.loads(m.data).get("faces"):
            return
        now = time.monotonic()
        if self.running and now - self.face_seen > GREET_AFTER:
            self.send("say", {"text": omi.TEXT.get(self.lang, omi.TEXT["en"])["hello"], "lang": self.lang})
        self.face_seen = now

    def on_menu(self, m):
        self.picks = (self.picks + [{"id": json.loads(m.data).get("id"), "at": time.time()}])[-5:]

    def on_answer(self, m):
        a = json.loads(m.data)
        self.reminders.answer(a.get("note", ""), a.get("id", ""), omi.now_local())
        if a.get("note") == self.open_note:
            self.open_note = None

    def on_reminders(self, m):
        try:
            self.reminders.set(json.loads(m.data))
            self.get_logger().info(f"{len(self.reminders.items)} reminders")
        except ValueError as e:
            self.get_logger().warning(f"reminders not taken: {e}")

    def check(self):
        if not self.running:
            return
        for r in self.reminders.due(omi.now_local()):
            n = omi.note_for(r, self.lang)
            self.send("say", {"text": n.pop("_say"), "lang": self.lang})
            self.send("note", n)
            self.open_note = r["id"]
            self.get_logger().info(f"reminder: {r['text']}")

    def publish_state(self):
        now = omi.now_local()
        self.state_pub.publish(String(data=json.dumps({
            "state": "on" if self.running else "off", "lang": self.lang, "reminders": self.reminders.items,
            "next": self.reminders.next(now), "answers": self.reminders.log[-5:], "picks": self.picks, "note": self.open_note})))

    def destroy_node(self):
        if self.running:
            self.run(False)
        super().destroy_node()


def main():
    rclpy.init()
    node = OmiAssist()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

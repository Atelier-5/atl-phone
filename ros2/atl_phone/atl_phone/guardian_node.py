# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""guardian_node — runs the Desk Guardian (guardian.py) on the phone's topics and, when there is one, a Thymio's.

    ros2 run atl_phone guardian --ros-args -p robot:=thymio_1 [-p lang:=fr] [-p drive:=true]

    in:  /<robot>/phone/faces, touch, imu, codes;  /<robot>/prox/ground (atl-thymio, optional)
    out: /<robot>/phone/face/expression, face/color, face/gaze, say, vibrate, look, look/familiar
         /<robot>/cmd_vel, leds/top (atl-thymio; only with drive, and only while the Thymio answers)
         /<robot>/guardian/state (String JSON, 5 Hz)

It knows nothing of the phone's page or of Webots: only the topics. The same node runs
against guardian_check's mock phone and fake Thymio, and against the real ones.
It asks for look and familiar; the bridge decides whether faces get their numbers. When the phone forgets
its faces (familiar off, another page or phone: the bridge's status), the guardian forgets its friends too.
"""
import json
import time

import rclpy
from geometry_msgs.msg import Point, Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool, ColorRGBA, Float32MultiArray, Int32, String

from . import contract as c
from . import guardian as gd

RATE = 20.0                 # Hz
STATE_EVERY = 4             # ticks: 5 Hz
ASK_EVERY = 40              # ticks: look and familiar again every 2 s (the bridge passes on only changes)
THYMIO_QUIET = 1.0          # s without prox/ground: no Thymio


def thymio_topics(robot: str) -> dict:  # atl-thymio/0.1 (atl-bot-thymio thymio_twin/contract.py)
    return {"ground": f"/{robot}/prox/ground", "cmd_vel": f"/{robot}/cmd_vel", "led": f"/{robot}/leds/top"}


class GuardianNode(Node):
    def __init__(self):
        super().__init__("guardian")
        robot = self.declare_parameter("robot", "thymio_1").value
        self.drive = bool(self.declare_parameter("drive", True).value)
        self.guardian = gd.Guardian(self.declare_parameter("lang", "en").value)
        self.lang = self.guardian.lang
        self.t, th = c.topics(robot), thymio_topics(robot)
        self.sensors, self.events = gd.Sensors(), gd.Events()
        self.faces_at = -1e9
        self.ground_at = -1e9
        self.last = {}
        self.ticks = 0
        self.pub = {k: self.create_publisher(kind, self.t[k], 10) for k, kind in
                    [("expression", String), ("color", ColorRGBA), ("gaze", Point), ("say", String), ("vibrate", Int32),
                     ("look", Bool), ("familiar", Bool)]}
        self.cmd = self.create_publisher(Twist, th["cmd_vel"], 10)
        self.led = self.create_publisher(ColorRGBA, th["led"], 10)
        self.state_pub = self.create_publisher(String, f"/{robot}/guardian/state", 10)
        self.create_subscription(String, self.t["faces"], self.on_faces, 10)
        self.create_subscription(String, self.t["touch"], lambda m: self.events.touches.append(json.loads(m.data)), 10)
        self.create_subscription(String, self.t["codes"], lambda m: self.events.codes.append(json.loads(m.data).get("text", "")), 10)
        self.create_subscription(Imu, self.t["imu"], self.on_imu, 10)
        self.create_subscription(Float32MultiArray, th["ground"], self.on_ground, 10)
        self.phone = None
        self.create_subscription(String, self.t["status"], self.on_status, QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_timer(1.0 / RATE, self.tick)
        self.get_logger().info(f"Desk Guardian on /{robot} ({'with' if self.drive else 'without'} the Thymio's wheels)")

    def on_faces(self, m):
        f = json.loads(m.data)
        self.sensors.faces = sorted(f.get("faces", []), key=lambda x: -x.get("size", 0))
        self.faces_at = time.monotonic()

    def on_status(self, m):
        s = json.loads(m.data)
        phone = (s.get("connected"), s.get("familiar"), s.get("id"), s.get("peer"))
        if self.phone is not None and phone != self.phone and self.guardian.friends | self.guardian.met:
            self.get_logger().info("the phone forgot its faces: so does the guardian")
            self.guardian.forget()
        self.phone = phone

    def on_imu(self, m):
        a, w = m.linear_acceleration, m.angular_velocity
        self.sensors.acc, self.sensors.gyro = (a.x, a.y, a.z), (w.x, w.y, w.z)

    def on_ground(self, m):
        self.sensors.ground = list(m.data)
        self.ground_at = time.monotonic()

    def changed(self, key, value) -> bool:
        if self.last.get(key) == value:
            return False
        self.last[key] = value
        return True

    def tick(self):
        now = time.monotonic()
        self.sensors.faces_age = now - self.faces_at
        thymio = now - self.ground_at < THYMIO_QUIET
        if not thymio:
            self.sensors.ground = None
        out = self.guardian.step(self.sensors, self.events, 1.0 / RATE)
        self.events = gd.Events()
        if self.ticks % ASK_EVERY == 0:  # again now and then: a phone that comes back gets the face as it is
            self.pub["look"].publish(Bool(data=True))
            self.pub["familiar"].publish(Bool(data=True))
            self.last.clear()
        if self.changed("expression", out.expression):
            self.pub["expression"].publish(String(data=out.expression))
        r, g, b = (float(v) for v in out.colour)
        if self.changed("colour", out.colour):
            self.pub["color"].publish(ColorRGBA(r=r, g=g, b=b, a=1.0))
            if thymio and self.drive:
                self.led.publish(ColorRGBA(r=r, g=g, b=b, a=1.0))
        if out.gaze is not None:
            self.pub["gaze"].publish(Point(x=float(out.gaze[0]), y=float(out.gaze[1])))
        if out.say:
            self.pub["say"].publish(String(data=json.dumps({"text": out.say, "lang": self.lang})))
        if out.vibrate:
            self.pub["vibrate"].publish(Int32(data=int(out.vibrate)))
        if thymio and self.drive:
            tw = Twist()
            tw.linear.x, tw.angular.z = float(out.linear), float(out.angular)
            self.cmd.publish(tw)
        if self.ticks % STATE_EVERY == 0:
            self.state_pub.publish(String(data=json.dumps({"state": out.state, "doing": out.doing, "faces": len(self.sensors.faces)
                                                           if self.sensors.faces_age < 1.0 else 0, "thymio": thymio,
                                                           "friends": sorted(self.guardian.friends)})))
        self.ticks += 1

    def destroy_node(self):
        if self.drive:
            self.cmd.publish(Twist())  # stop the wheels
        self.pub["look"].publish(Bool(data=False))
        super().destroy_node()


def main():
    rclpy.init()
    node = GuardianNode()
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

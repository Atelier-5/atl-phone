# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""thymio_pad — a sample program: the phone's pad becomes the Thymio's five buttons, and they drive it.

    ros2 run atl_phone thymio_pad --ros-args -p robot:=thymio_1

It sets the panel (/<robot>/phone/panel: the buttons ▲ ◀ ● ▶ ▼, and a menu without the cameras), then listens to
/<robot>/phone/pad: ▲ and ▼ speed up and slow down (or back up), ◀ and ▶ turn, ● stops, as on a Thymio in its
"explorer" mode. It drives /<robot>/cmd_vel ten times a second. A program of some forty lines: copy it.
"""
import json

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String

from . import contract as c

STEP = 0.04         # m/s per press of ▲ or ▼
TOP = 0.14          # m/s, the Thymio's top speed is about 0.2
TURN = 1.2          # rad/s while ◀ or ▶ was pressed last
TURN_FOR = 0.5      # s a turn lasts


class ThymioPad(Node):
    def __init__(self):
        super().__init__("thymio_pad")
        robot = self.declare_parameter("robot", "thymio_1").value
        t = c.topics(robot)
        self.speed, self.turn_until, self.turn = 0.0, 0.0, 0.0
        self.cmd = self.create_publisher(Twist, f"/{robot}/cmd_vel", 10)
        panel = self.create_publisher(String, t["panel"], 10)
        self.create_subscription(String, t["pad"], self.pressed, 10)
        self.create_timer(0.1, self.drive)
        show = {"mode": "pad", "buttons": c.THYMIO_PAD, "menu": ["pad", "mouth", "sensors", "off"]}
        self.create_timer(1.0, lambda: panel.publish(String(data=json.dumps(show))))  # again each second: a phone may come later
        self.get_logger().info(f"the phone's pad drives /{robot}/cmd_vel")

    def now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def pressed(self, m):
        button = json.loads(m.data).get("id")
        if button == "forward":
            self.speed = min(TOP, self.speed + STEP)
        elif button == "backward":
            self.speed = max(-TOP, self.speed - STEP)
        elif button in ("left", "right"):
            self.turn, self.turn_until = (TURN if button == "left" else -TURN), self.now() + TURN_FOR
        elif button == "centre":
            self.speed, self.turn_until = 0.0, 0.0

    def drive(self):
        tw = Twist()
        tw.linear.x = float(self.speed)
        tw.angular.z = float(self.turn if self.now() < self.turn_until else 0.0)
        self.cmd.publish(tw)


def main():
    rclpy.init()
    node = ThymioPad()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

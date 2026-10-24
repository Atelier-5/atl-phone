# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""bridge — the phone on ROS 2: serves the face page, and maps its WebSocket to the contract's topics.

    ros2 run atl_phone bridge --ros-args -p robot:=thymio_1 [-p port:=8782] [-p key:=...] [-p cert:=c.pem -p cert_key:=k.pem]

Over USB (adb reverse) the phone opens http://localhost:8782; over Wi-Fi it needs
https (cert), or the camera and microphone stay blocked.
"""
import json
import re
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import BatteryState, Imu
from std_msgs.msg import Bool, ColorRGBA, Float32, Int32, String

from . import contract as c
from . import protocol as p
from .wsserver import PhoneServer


class Bridge(Node):
    def __init__(self):
        super().__init__("phone_bridge")
        self.robot = self.declare_parameter("robot", "thymio_1").value
        port = self.declare_parameter("port", c.PORT).value
        bind = self.declare_parameter("bind", "0.0.0.0").value
        key = self.declare_parameter("key", "").value
        cert = self.declare_parameter("cert", "").value or None
        cert_key = self.declare_parameter("cert_key", "").value or None
        self.lang = self.declare_parameter("lang", "en").value
        web = self.declare_parameter("web", get_package_share_directory("atl_phone") + "/web").value
        self.t = c.topics(self.robot)
        self.frame_id = f"{self.robot}/phone"
        self.phone = {}
        self.last_imu = 0.0

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = {
            "status": self.create_publisher(String, self.t["status"], latched),
            "imu": self.create_publisher(Imu, self.t["imu"], 10),
            "heading": self.create_publisher(Float32, self.t["heading"], 10),
            "touch": self.create_publisher(String, self.t["touch"], 10),
            "battery": self.create_publisher(BatteryState, self.t["battery"], latched),
        }
        self.create_subscription(String, self.t["expression"], lambda m: self.out(p.face, m.data), 10)
        self.create_subscription(Point, self.t["gaze"], lambda m: self.out(p.gaze, m.x, m.y), 10)
        self.create_subscription(ColorRGBA, self.t["color"], lambda m: self.out(p.color, m.r, m.g, m.b), 10)
        self.create_subscription(String, self.t["say"], lambda m: self.out(p.say, m.data, self.lang), 10)
        self.create_subscription(Bool, self.t["torch"], lambda m: self.out(p.torch, m.data), 10)
        self.create_subscription(Int32, self.t["vibrate"], lambda m: self.out(p.vibrate, m.data), 10)

        self.server = PhoneServer(web, port, bind, key, on_open=self.opened, on_text=self.text, on_close=self.closed,
                                  cert=cert, cert_key=cert_key).start()
        self.status()
        q = f"?key={key}" if key else ""
        self.get_logger().info(f"{c.CONTRACT} for /{self.robot}: {self.server.scheme}://<this PC>:{self.server.port}/{q}"
                               f" (USB: adb reverse tcp:{port} tcp:{port}, then http://localhost:{port}/{q})")

    def out(self, make, *args):
        try:
            msg = make(*args)
        except ValueError as e:
            self.get_logger().warning(f"not sent to the phone: {e}")
            return
        self.server.send(json.dumps(msg))

    def status(self):
        s = {"contract": c.CONTRACT, "connected": self.server.connected}
        if s["connected"]:
            s.update(self.phone)
        self.pub["status"].publish(String(data=json.dumps(s)))

    def opened(self, link):
        self.phone = {"peer": link.peer}
        self.get_logger().info(f"phone at {link.peer}")
        self.status()

    def closed(self, link):
        self.get_logger().info(f"phone at {link.peer} gone")
        self.phone = {}
        self.status()

    def text(self, raw: str):
        try:
            m = p.parse(raw)
        except ValueError as e:
            self.get_logger().warning(f"from the phone: {e}", throttle_duration_sec=5.0)
            return
        t = m["t"]
        if t == "hello":
            self.phone.update(model=model_of(m["ua"]), ua=m["ua"], caps=m["caps"], screen=m["screen"])
            self.get_logger().info(f"phone says hello: {self.phone['model']}")
            self.status()
        elif t == "imu":
            now = time.monotonic()
            if now - self.last_imu < 1.0 / c.MAX_IMU_RATE:
                return
            self.last_imu = now
            imu = Imu()
            imu.header.stamp = self.get_clock().now().to_msg()
            imu.header.frame_id = self.frame_id
            imu.orientation_covariance[0] = -1.0  # no orientation
            imu.linear_acceleration.x, imu.linear_acceleration.y, imu.linear_acceleration.z = m["acc"]
            imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z = m["gyro"]
            self.pub["imu"].publish(imu)
        elif t == "heading":
            self.pub["heading"].publish(Float32(data=m["deg"]))
        elif t == "touch":
            self.pub["touch"].publish(String(data=json.dumps({k: v for k, v in m.items() if k != "t"})))
        elif t == "battery":
            b = BatteryState()
            b.header.stamp = self.get_clock().now().to_msg()
            b.header.frame_id = self.frame_id
            b.percentage = m["level"]
            b.present = True
            b.power_supply_status = (BatteryState.POWER_SUPPLY_STATUS_CHARGING if m["charging"]
                                     else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING)
            self.pub["battery"].publish(b)

    def destroy_node(self):
        self.server.stop()
        super().destroy_node()


def model_of(ua: str) -> str:
    """'... (Linux; Android 8.0.0; SM-G950F) ...' -> 'SM-G950F'."""
    m = re.search(r"Android [\d.]+; ([^;)]+)", ua)
    return m.group(1).strip()[:40] if m else "unknown"


def main():
    rclpy.init()
    node = Bridge()
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

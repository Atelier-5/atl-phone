# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""contract.py — the phone payload's interface: the topics every phone (real, or later its Webots twin) offers.

The phone is a peripheral: it shows the face, senses and speaks; the robot's
brain runs elsewhere and only sees these topics. They live under the robot
that carries the phone, /<robot>/phone/..., so a robot with a phone keeps its
own contract and gains these. Bump CONTRACT when a topic changes.
"""

CONTRACT = "atl-phone/0.1"
PORT = 8782                 # the bridge's page and WebSocket (atl-ide 8780, the Thymio gateway 8781)


def topics(robot: str) -> dict:
    ns = f"/{robot}/phone"
    return {
        # out: published by the phone (through the bridge)
        "status": f"{ns}/status",           # std_msgs/String JSON {"contract", "connected", "model", "caps", "screen"}, latched
        "imu": f"{ns}/imu",                 # sensor_msgs/Imu, phone frame (x right, y up the screen, z out of it), m/s2 with gravity, rad/s; no orientation
        "heading": f"{ns}/heading",         # std_msgs/Float32, degrees clockwise from magnetic north (compass), when the phone has one
        "touch": f"{ns}/touch",             # std_msgs/String JSON {"kind": "tap"|"long"|"swipe", "zone": "left"|"centre"|"right", "dir"?}
        "battery": f"{ns}/battery",         # sensor_msgs/BatteryState: the phone's own battery
        # in: listened to by the phone
        "expression": f"{ns}/face/expression",  # std_msgs/String, one of EXPRESSIONS
        "gaze": f"{ns}/face/gaze",          # geometry_msgs/Point, x right, y up, each -1..1 (z unused)
        "color": f"{ns}/face/color",        # std_msgs/ColorRGBA 0..1: the eyes' colour
        "say": f"{ns}/say",                 # std_msgs/String: text, or JSON {"text", "lang": "en"|"fr"|"de"}
        "torch": f"{ns}/torch",             # std_msgs/Bool: the headlight (it opens the camera, and the face shows it)
        "vibrate": f"{ns}/vibrate",         # std_msgs/Int32: milliseconds, at most MAX_VIBRATE
    }


EXPRESSIONS = ("neutral", "happy", "sad", "angry", "surprised", "sleepy", "curious", "wink", "scared", "love")
LANGS = ("en", "fr", "de")
MAX_SAY = 200               # characters
MAX_VIBRATE = 2000          # ms
MAX_IMU_RATE = 60.0         # Hz: faster messages from a phone are dropped

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""The phone on a robot: the bridge that serves the face page and maps it to /<robot>/phone/...

    ros2 launch atl_phone phone.launch.py [robot:=thymio_1] [port:=8782] [key:=...] [cert:=c.pem cert_key:=k.pem [ca:=ca.crt]]
        [lang:=en] [familiar:=false] [guardian:=false [drive:=true]]

guardian:=true also runs the Desk Guardian (guardian_node) on the same robot; familiar:=true lets programs
ask the phone to tell faces apart (the setup page can allow it too).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

ARGS = {"robot": "thymio_1", "port": "8782", "key": "", "cert": "", "cert_key": "", "ca": "", "lang": "en", "familiar": "false"}


def generate_launch_description():
    bridge = {k: LaunchConfiguration(k) for k in ARGS}
    return LaunchDescription(
        [DeclareLaunchArgument(k, default_value=v) for k, v in ARGS.items()]
        + [DeclareLaunchArgument("guardian", default_value="false"), DeclareLaunchArgument("drive", default_value="true")]
        + [Node(package="atl_phone", executable="bridge", name="phone_bridge", output="screen", parameters=[bridge]),
           Node(package="atl_phone", executable="guardian", name="guardian", output="screen",
                condition=IfCondition(LaunchConfiguration("guardian")),
                parameters=[{"robot": LaunchConfiguration("robot"), "lang": LaunchConfiguration("lang"),
                             "drive": LaunchConfiguration("drive")}])])

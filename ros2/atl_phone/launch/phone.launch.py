# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""The phone on a robot: the bridge that serves the face page and maps it to /<robot>/phone/...

    ros2 launch atl_phone phone.launch.py [robot:=thymio_1] [port:=8782] [key:=...] [cert:=c.pem cert_key:=k.pem] [lang:=en]
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

ARGS = {"robot": "thymio_1", "port": "8782", "key": "", "cert": "", "cert_key": "", "lang": "en"}


def generate_launch_description():
    return LaunchDescription(
        [DeclareLaunchArgument(k, default_value=v) for k, v in ARGS.items()]
        + [Node(package="atl_phone", executable="bridge", name="phone_bridge", output="screen",
                parameters=[{k: LaunchConfiguration(k) for k in ARGS}])])

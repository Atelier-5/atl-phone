# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""The phone on a robot: the bridge that serves the face page and maps it to /<robot>/phone/...

    ros2 launch atl_phone phone.launch.py [robot:=thymio_1] [port:=8782] [key:=...] [cert:=c.pem cert_key:=k.pem [ca:=ca.crt]]
        [lang:=en] [familiar:=false] [guardian:=false [drive:=true]] [reports:=/reports] [omi:=false [omi_folder:=/omi]] [show:=false]
        [translate:=false] [models:=/models] [guest_port:=8783 guest_cert:=c.pem guest_cert_key:=k.pem [guest_ca:=ca.crt]]

The Desk Guardian (guardian_node) runs beside the bridge, waiting: the setup page's Scenarios step starts it,
or guardian:=true from the start. familiar:=true lets programs ask the phone to tell faces apart (the setup
page can allow it too). Omi Assist (omi_assist) runs beside it too, waiting the same way (omi:=true starts it; its
reminders in omi_folder). show:=true lets the person show the phone's picture to this PC (the setup page can allow it).
translate:=true lets the phone send its sound while a half of Übersetzen is held, to be heard and translated here (the
models in models, scripts/get_models.sh; the setup page can allow it). guest_port: a second phone on the Wi-Fi joins
Übersetzen there (talk.html, https with guest_cert), with the code the robot's phone shows as a QR code.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

ARGS = {"robot": "thymio_1", "port": "8782", "key": "", "cert": "", "cert_key": "", "ca": "", "lang": "en", "familiar": "false",
        "reports": "", "show": "false", "translate": "false", "models": "",
        "guest_port": "0", "guest_cert": "", "guest_cert_key": "", "guest_ca": ""}  # reports: a folder for the registry of phones tested (start.sh: the repository's reports/)


def generate_launch_description():
    bridge = {k: LaunchConfiguration(k) for k in ARGS}
    return LaunchDescription(
        [DeclareLaunchArgument(k, default_value=v) for k, v in ARGS.items()]
        + [DeclareLaunchArgument("guardian", default_value="false"), DeclareLaunchArgument("drive", default_value="true"),
           DeclareLaunchArgument("omi", default_value="false"), DeclareLaunchArgument("omi_folder", default_value="")]
        + [Node(package="atl_phone", executable="bridge", name="phone_bridge", output="screen", parameters=[bridge]),
           Node(package="atl_phone", executable="guardian", name="guardian", output="screen",
                parameters=[{"robot": LaunchConfiguration("robot"), "lang": LaunchConfiguration("lang"),
                             "drive": LaunchConfiguration("drive"), "run": LaunchConfiguration("guardian")}]),
           Node(package="atl_phone", executable="omi_assist", name="omi_assist", output="screen",
                parameters=[{"robot": LaunchConfiguration("robot"), "lang": LaunchConfiguration("lang"),
                             "folder": LaunchConfiguration("omi_folder"), "run": LaunchConfiguration("omi")}])])

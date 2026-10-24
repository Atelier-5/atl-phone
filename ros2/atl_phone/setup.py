# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
from glob import glob

from setuptools import setup

package = "atl_phone"
setup(
    name=package,
    version="0.1.0",
    packages=[package],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package}"]),
        (f"share/{package}", ["package.xml"]),
        (f"share/{package}/web", glob("web/*")),
        (f"share/{package}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    entry_points={"console_scripts": ["bridge = atl_phone.bridge_node:main"]},
    zip_safe=True,
    maintainer="Atelier-5",
    description="An old phone as the robot's face, eyes and ears",
    license="GPL-3.0-or-later",
)

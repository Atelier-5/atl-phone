# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import os
from glob import glob

from setuptools import setup

package = "atl_phone"
setup(
    name=package,
    version="0.2.0",
    packages=[package],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package}"]),
        (f"share/{package}", ["package.xml"]),
        (f"share/{package}/web", [f for f in glob("web/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor", [f for f in glob("web/vendor/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor/face-api", [f for f in glob("web/vendor/face-api/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor/face-api/models", glob("web/vendor/face-api/models/*")),
        (f"share/{package}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    entry_points={"console_scripts": ["bridge = atl_phone.bridge_node:main", "guardian = atl_phone.guardian_node:main"]},
    zip_safe=True,
    maintainer="Atelier-5",
    description="An old phone as the robot's face, eyes and ears",
    license="GPL-3.0-or-later",
)

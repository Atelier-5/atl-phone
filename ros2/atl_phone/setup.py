# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import os
from glob import glob

from setuptools import setup

package = "atl_phone"
setup(
    name=package,
    version="0.5.0",
    packages=[package],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package}"]),
        (f"share/{package}", ["package.xml"]),
        (f"share/{package}/web", [f for f in glob("web/*") if os.path.isfile(f)]),
        (f"share/{package}/web/icons", glob("web/icons/*")),
        (f"share/{package}/web/vendor", [f for f in glob("web/vendor/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor/face-api", [f for f in glob("web/vendor/face-api/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor/face-api/models", glob("web/vendor/face-api/models/*")),
        (f"share/{package}/web/vendor/mediapipe", [f for f in glob("web/vendor/mediapipe/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor/mediapipe/wasm", glob("web/vendor/mediapipe/wasm/*")),
        (f"share/{package}/web/vendor/mediapipe/models", glob("web/vendor/mediapipe/models/*")),
        (f"share/{package}/web/vendor/aruco", glob("web/vendor/aruco/*")),
        (f"share/{package}/web/vendor/tesseract", [f for f in glob("web/vendor/tesseract/*") if os.path.isfile(f)]),
        (f"share/{package}/web/vendor/tesseract/lang", glob("web/vendor/tesseract/lang/*")),
        (f"share/{package}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    entry_points={"console_scripts": ["bridge = atl_phone.bridge_node:main", "guardian = atl_phone.guardian_node:main",
                                      "thymio_pad = atl_phone.thymio_pad:main",
                                      "omi_assist = atl_phone.omi_assist:main"]},
    zip_safe=True,
    maintainer="Atelier-5",
    description="An old phone as the robot's face, eyes and ears",
    license="GPL-3.0-or-later",
)

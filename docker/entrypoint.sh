#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# Source ROS 2 Kilted and the atl_phone workspace, then run the command.
set -e
source /opt/ros/kilted/setup.bash
source /ws/install/setup.bash
exec "$@"

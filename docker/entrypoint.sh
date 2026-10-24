#!/bin/bash
# Source ROS 2 Kilted and the atl_phone workspace, then run the command.
set -e
source /opt/ros/kilted/setup.bash
source /ws/install/setup.bash
exec "$@"

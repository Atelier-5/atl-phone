# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# atl-phone on its own: ROS 2 Kilted (Ubuntu 24.04) with the phone bridge. A robot's image installs
# ros2/atl_phone the same way (copy it into its workspace).
#
#   docker build -f docker/Dockerfile -t atl-phone:kilted .
#   docker run --rm --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp atl-phone:kilted \
#       ros2 launch atl_phone phone.launch.py robot:=thymio_1
FROM ros:kilted-ros-base
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /ws
COPY ros2/ src/
RUN . /opt/ros/kilted/setup.sh && colcon build --merge-install && rm -rf build log
COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]

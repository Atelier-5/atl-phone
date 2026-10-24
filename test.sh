#!/usr/bin/env bash
# The tests: plain Python, no ROS, no phone.
# A workstation's ROS environment (PYTHONPATH, pytest plugins) is kept out of it.
#
#   ./test.sh
#   ./test.sh -k report
set -euo pipefail
cd "$(dirname "$0")"
unset PYTHONPATH
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
exec uv run -q --no-project --python 3.11 --with pytest python -m pytest tests "$@"

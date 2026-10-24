#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# Opens the phone check on a phone plugged in by USB (USB debugging on).
# adb reverse makes the PC's port the phone's localhost, a secure page without certificates.
#
#   ./scripts/usb.sh [page]          default page: check.html (serve.py must be running)
set -euo pipefail
PORT=${ATL_PHONE_PORT:-8782}
PAGE=${1:-check.html}
command -v adb >/dev/null || { echo "adb is missing: sudo apt install adb" >&2; exit 1; }
adb get-state >/dev/null || { echo "no phone: plug it in and allow USB debugging" >&2; exit 1; }
adb reverse "tcp:$PORT" "tcp:$PORT"
adb shell am start -a android.intent.action.VIEW -d "http://localhost:$PORT/$PAGE" >/dev/null
echo "opened http://localhost:$PORT/$PAGE on $(adb shell getprop ro.product.model | tr -d '\r')"

#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# What weighs on the phone (over USB, adb), and lighter on request: free memory, the busiest apps, how many Chrome tabs
# are open, the battery's temperature and the thermal status. It changes nothing unless you type y to each question.
#
#   ./scripts/phone_tidy.sh [--kill] [--stay-on] [--close-tabs]
#
# --kill: stop the apps in the background (am kill-all: they start again when opened; no data is lost).
# --stay-on: keep the screen on while the phone is on its USB cable (for a stand; undo: adb shell svc power stayon false).
# --close-tabs: Chrome's tabs other than atl-phone's (localhost:8782 / the bridge), each shown and closed only on y.
# Without an option it only looks. ANDROID_SERIAL picks the phone when more than one is plugged in.
set -euo pipefail
KILL=0 STAY=0 TABS=0 PORT=${ATL_PORT:-8782} CDP=9229
for a in "$@"; do
  case "$a" in
    --kill) KILL=1 ;; --stay-on) STAY=1 ;; --close-tabs) TABS=1 ;;
    -h|--help) sed -n '4,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $a (see --help)" >&2; exit 2 ;;
  esac
done
command -v adb >/dev/null || { echo "adb is missing (sudo apt install adb)" >&2; exit 1; }
[ "$(adb get-state 2>/dev/null || true)" = device ] || { echo "no phone over USB (adb devices; allow USB debugging on the phone)" >&2; exit 1; }
sh_() { adb shell "$@" 2>/dev/null | tr -d '\r'; }
yes_() { local r; read -r -p "$1 [y/N] " r; [ "$r" = y ] || [ "$r" = Y ]; }

free_mb() { sh_ cat /proc/meminfo | awk '/MemAvailable/ {print int($2/1024)}'; }
total_mb() { sh_ cat /proc/meminfo | awk '/MemTotal/ {print int($2/1024)}'; }
load() { sh_ uptime | sed -n 's/.*load average: *//p'; }
tabs() {  # how many tabs Chrome has open: a count only, nothing about what is in them
  adb forward tcp:$CDP localabstract:chrome_devtools_remote >/dev/null 2>&1 || { echo "?"; return; }
  curl -s --max-time 3 "http://localhost:$CDP/json/list" | python3 -c 'import json,sys
try: print(sum(t.get("type") == "page" for t in json.load(sys.stdin)))
except ValueError: print("?")'
}
line() { echo "  free memory $(free_mb) of $(total_mb) MB · load $(load) · Chrome tabs $(tabs)"; }

echo "$(sh_ getprop ro.product.model) · Android $(sh_ getprop ro.build.version.release)"
echo "before:"; line
t=$(sh_ dumpsys battery | awk '/temperature/ {print $2/10; exit}')
th=$(sh_ dumpsys thermalservice | awk -F': ' '/Thermal Status/ {print $2; exit}')
echo "  battery ${t:-?} °C · thermal status ${th:-?} (0 none … 3 severe: the phone slows itself down)"
echo "the busiest apps now (CPU %):"
# head and awk stop reading early, and adb then ends on a broken pipe: not an error here (pipefail would end the script)
busy=$(set +o pipefail; sh_ top -b -n 1 -o %CPU,RES,NAME -s 1 | awk '$1 ~ /^[0-9.]+$/ && $1+0 > 0.5' | head -6)
[ -n "$busy" ] || busy=$(set +o pipefail; sh_ top -n 1 -m 6 | tail -n +5)   # an older top: its own columns
echo "$busy" | sed 's/^/  /'
echo "the apps that hold most memory (this takes a few seconds):"
mem=$(set +o pipefail; sh_ dumpsys meminfo | awk '/Total (PSS|RSS) by process/ {f=1; next} f && NF==0 {exit} f' | head -6)
echo "$mem" | sed 's/^ */  /'

if [ "$KILL" = 1 ] && yes_ "Stop the apps in the background (no data is lost)?"; then sh_ am kill-all; echo "  stopped"; fi
if [ "$STAY" = 1 ] && yes_ "Keep the screen on while on USB?"; then sh_ svc power stayon usb; echo "  the screen stays on while on USB"; fi
if [ "$TABS" = 1 ]; then
  adb forward tcp:$CDP localabstract:chrome_devtools_remote >/dev/null
  curl -s "http://localhost:$CDP/json/list" | python3 -c 'import json,sys
for t in json.load(sys.stdin):
    if t.get("type") == "page" and ":'"$PORT"'/" not in t.get("url", ""):
        print(t["id"] + "\t" + (t.get("title") or t.get("url", ""))[:70])' |
  while IFS=$'\t' read -r id title; do
    if yes_ "Close the tab: $title ?" </dev/tty; then curl -s -o /dev/null "http://localhost:$CDP/json/close/$id"; echo "  closed"; fi
  done
fi
if [ "$KILL$STAY$TABS" != 000 ]; then sleep 2; echo "after:"; line; fi

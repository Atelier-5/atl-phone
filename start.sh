#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# Starts the phone bridge in Docker and opens the setup page, which guides through connecting and testing a phone.
# The image is built when it is missing or the sources changed.
#
#   ./start.sh [--robot thymio_1] [--port 8782] [--lang en|fr|de] [--key KEY] [--make-cert [DIR] | --cert DIR]
#              [--guardian [--no-drive]] [--omi [--show] [--translate [--no-guest]]] [--familiar] [--rebuild] [--no-open]
#   ./start.sh stop | logs
#
# --guardian: start the Desk Guardian at once (else the setup page starts it); it drives the Thymio when one answers
#   (--no-drive: never).
# --omi: Omi Assist at once, in German unless --lang says otherwise (else the setup page starts it); its reminders and
#   their answers are kept in omi/ (git-ignored). --show: the person may show the camera's picture to this PC, while
#   she presses the show tile (else the setup page allows it; agree on it with her first: docs/consent-show.md).
# --translate: Übersetzen, German <-> French: the phone may send its sound while a half of the translate panel is held,
#   heard and translated on this computer and dropped (else the setup page allows it; docs/consent-translate.md). The
#   models: ./scripts/get_models.sh puts them in models/ (git-ignored), mounted read-only. A second phone on the home
#   Wi-Fi can join from the QR code the robot's phone shows: the guest page, https on port GUEST_PORT (8783), with this
#   PC's own certificate (certs/, made or renewed as --make-cert does); the face stays as it is. The port is open
#   whenever the models are there, and answers only while Übersetzen is allowed. --no-guest: not.
# --familiar: programs may ask the phone to tell faces apart, this session only (ask the people at the table first).
#
# --make-cert [DIR]: Wi-Fi over HTTPS with this PC's own certificate authority (DIR default certs/): made the first
#   time, renewed when this PC's address changes. Each phone installs the authority once (the setup page offers it).
# --cert DIR: DIR/cert.pem and DIR/key.pem (and DIR/ca.crt, offered to the phones, if there is one).
# ROS_DOMAIN_ID is passed on.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
IMAGE=atl-phone:kilted
NAME=atl-phone
ROBOT=thymio_1 PORT=8782 LANG_=en KEY="" CERT="" MAKE_CERT="" REBUILD=0 OPEN=1 GUARDIAN=false DRIVE=true FAMILIAR=false OMI=false SHOW=false TRANSLATE=false GUEST=true GUEST_PORT=8783 LANG_SET=0

case "${1:-}" in
  stop) docker rm -f "$NAME" >/dev/null 2>&1 && echo "stopped" || echo "not running"; exit 0 ;;
  logs) exec docker logs -f "$NAME" ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    --robot) ROBOT=$2; shift 2 ;;
    --port) PORT=$2; shift 2 ;;
    --lang) LANG_=$2; LANG_SET=1; shift 2 ;;
    --key) KEY=$2; shift 2 ;;
    --cert) CERT=$(cd "$2" && pwd); shift 2 ;;
    --make-cert) if [ -n "${2:-}" ] && [ "${2#--}" = "$2" ]; then MAKE_CERT=$2; shift; else MAKE_CERT=certs; fi; shift ;;
    --guardian) GUARDIAN=true; shift ;;
    --no-drive) DRIVE=false; shift ;;
    --familiar) FAMILIAR=true; shift ;;
    --omi) OMI=true; shift ;;
    --show) SHOW=true; shift ;;
    --translate) TRANSLATE=true; shift ;;
    --no-guest) GUEST=false; shift ;;
    --rebuild) REBUILD=1; shift ;;
    --no-open) OPEN=0; shift ;;
    -h|--help) sed -n '4,21p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
done

if [ -n "$MAKE_CERT" ]; then
  ./scripts/make_cert.sh "$MAKE_CERT"
  CERT=$(cd "$MAKE_CERT" && pwd)
fi

# build when the sources changed: their hash is the image's label
SRC=$( { find ros2 docker -type f -not -path '*/__pycache__/*' -not -path '*/test/*' -print0
         find docs/architecture -maxdepth 1 -type f -name '*.html' -print0; } | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)
HAVE=$(docker image inspect --format '{{index .Config.Labels "atl.src"}}' "$IMAGE" 2>/dev/null || true)
if [ "$REBUILD" = 1 ] || [ "$HAVE" != "$SRC" ]; then
  echo "building $IMAGE…"
  docker build -q --label "atl.src=$SRC" -f docker/Dockerfile -t "$IMAGE" . >/dev/null
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
if ss -ltn "( sport = :$PORT )" | grep -q LISTEN; then
  echo "port $PORT is taken (by: $(ss -ltnp "( sport = :$PORT )" | grep -o 'users:(("[^"]*' | cut -d'"' -f2 | head -1)); try --port" >&2
  exit 1
fi

[ "$OMI" = true ] && [ "$LANG_SET" = 0 ] && LANG_=de
ARGS=(robot:="$ROBOT" port:="$PORT" lang:="$LANG_" familiar:="$FAMILIAR" guardian:="$GUARDIAN" drive:="$DRIVE" omi:="$OMI" show:="$SHOW" translate:="$TRANSLATE")
[ -n "$KEY" ] && ARGS+=(key:="$KEY")
# every phone tested goes into the registry, reports/ in this repository (git-ignored): one folder per model
mkdir -p "$HERE/reports"
MOUNT=(-v "$HERE/reports:/reports")
ARGS+=(reports:=/reports)
# Omi Assist's reminders and the answers to them: omi/ in this repository (git-ignored)
mkdir -p "$HERE/omi"
MOUNT+=(-v "$HERE/omi:/omi")
ARGS+=(omi_folder:=/omi)
# Übersetzen's models (scripts/get_models.sh), read-only
if [ -d "$HERE/models" ]; then
  MOUNT+=(-v "$HERE/models:/models:ro")
  ARGS+=(models:=/models)
fi
# Übersetzen's guest page, for a second phone on the Wi-Fi: its own https port, with this PC's certificate (the
# authority's key stays in certs/)
GUEST_URL=""
if [ -d "$HERE/models" ] && [ "$GUEST" = true ]; then   # ready for when Übersetzen is allowed (it holds no code before)
  ss -ltn "( sport = :$GUEST_PORT )" | grep -q LISTEN && { echo "port $GUEST_PORT (the guest page) is taken: --no-guest" >&2; exit 1; }
  ./scripts/make_cert.sh certs >/dev/null
  MOUNT+=(-v "$HERE/certs/cert.pem:/guest/cert.pem:ro" -v "$HERE/certs/key.pem:/guest/key.pem:ro" -v "$HERE/certs/ca.crt:/guest/ca.crt:ro")
  ARGS+=(guest_port:="$GUEST_PORT" guest_cert:=/guest/cert.pem guest_cert_key:=/guest/key.pem guest_ca:=/guest/ca.crt)
  GUEST_URL=yes
fi
if [ -n "$CERT" ]; then
  [ -f "$CERT/cert.pem" ] && [ -f "$CERT/key.pem" ] || { echo "$CERT needs cert.pem and key.pem" >&2; exit 1; }
  # the files the bridge needs, one by one: an authority's key next to them stays on this PC
  MOUNT+=(-v "$CERT/cert.pem:/certs/cert.pem:ro" -v "$CERT/key.pem:/certs/key.pem:ro")
  ARGS+=(cert:=/certs/cert.pem cert_key:=/certs/key.pem)
  if [ -f "$CERT/ca.crt" ]; then
    MOUNT+=(-v "$CERT/ca.crt:/certs/ca.crt:ro")
    ARGS+=(ca:=/certs/ca.crt)
  fi
fi
# Fast DDS between containers: their shared memory is not shared, so UDP only (else a Thymio's container is not heard)
docker run -d --rm --name "$NAME" --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 "${MOUNT[@]}" "$IMAGE" \
  ros2 launch atl_phone phone.launch.py "${ARGS[@]}" >/dev/null

SCHEME=http; [ -n "$CERT" ] && SCHEME=https
SETUP="$SCHEME://localhost:$PORT/setup.html"
for _ in $(seq 60); do
  curl -sfk -o /dev/null "$SCHEME://localhost:$PORT/api/state" && break
  docker inspect "$NAME" >/dev/null 2>&1 || { echo "the bridge stopped; ./start.sh logs shows why" >&2; exit 1; }
  sleep 0.5
done
curl -sfk -o /dev/null "$SCHEME://localhost:$PORT/api/state" || { echo "the bridge does not answer; see ./start.sh logs" >&2; exit 1; }

echo "bridge for /$ROBOT on port $PORT (container $NAME)"
if [ "$GUARDIAN" = true ]; then echo "  Desk Guardian: on (watch: docker exec $NAME /entrypoint.sh ros2 topic echo --no-daemon /$ROBOT/guardian/state)"
else echo "  Desk Guardian: waiting (start it on the setup page: Desk Guard)"; fi
if [ "$OMI" = true ]; then echo "  Omi Assist: on, $LANG_ (reminders in omi/)"; SETUP="$SETUP#omi"
else echo "  Omi Assist: waiting (start it on the setup page: Omi Assist)"; fi
[ "$SHOW" = true ] && echo "  showing the picture to this PC: allowed (only while she presses the show tile)"
if [ "$TRANSLATE" = true ]; then
  if ./scripts/get_models.sh --check >/dev/null 2>&1; then echo "  Übersetzen: allowed (the sound only while a half is held, heard here and dropped)"
  else echo "  Übersetzen: allowed, but the models are missing: ./scripts/get_models.sh"; fi
  [ -n "$GUEST_URL" ] && echo "  a second phone: scans the QR code the robot's phone shows in Übersetzen (https, port $GUEST_PORT)"
fi
echo "  setup:  $SETUP"
[ -n "$CERT" ] && echo "  phones: install $CERT/ca.crt once each (the setup page's Wi-Fi tab shows how)"
echo "  logs:   ./start.sh logs      stop: ./start.sh stop"
if [ "$OPEN" = 1 ] && command -v xdg-open >/dev/null && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  xdg-open "$SETUP" >/dev/null 2>&1 &
fi

#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
# Starts the phone bridge in Docker and opens the setup page, which guides through connecting and testing a phone.
# The image is built when it is missing or the sources changed.
#
#   ./start.sh [--robot thymio_1] [--port 8782] [--lang en|fr|de] [--key KEY] [--make-cert [DIR] | --cert DIR]
#              [--rebuild] [--no-open]
#   ./start.sh stop | logs
#
# --make-cert [DIR]: Wi-Fi over HTTPS with this PC's own certificate authority (DIR default certs/): made the first
#   time, renewed when this PC's address changes. Each phone installs the authority once (the setup page offers it).
# --cert DIR: DIR/cert.pem and DIR/key.pem (and DIR/ca.crt, offered to the phones, if there is one).
# ROS_DOMAIN_ID is passed on.
set -euo pipefail
cd "$(dirname "$0")"
IMAGE=atl-phone:kilted
NAME=atl-phone
ROBOT=thymio_1 PORT=8782 LANG_=en KEY="" CERT="" MAKE_CERT="" REBUILD=0 OPEN=1

case "${1:-}" in
  stop) docker rm -f "$NAME" >/dev/null 2>&1 && echo "stopped" || echo "not running"; exit 0 ;;
  logs) exec docker logs -f "$NAME" ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    --robot) ROBOT=$2; shift 2 ;;
    --port) PORT=$2; shift 2 ;;
    --lang) LANG_=$2; shift 2 ;;
    --key) KEY=$2; shift 2 ;;
    --cert) CERT=$(cd "$2" && pwd); shift 2 ;;
    --make-cert) if [ -n "${2:-}" ] && [ "${2#--}" = "$2" ]; then MAKE_CERT=$2; shift; else MAKE_CERT=certs; fi; shift ;;
    --rebuild) REBUILD=1; shift ;;
    --no-open) OPEN=0; shift ;;
    -h|--help) sed -n '4,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
done

if [ -n "$MAKE_CERT" ]; then
  ./scripts/make_cert.sh "$MAKE_CERT"
  CERT=$(cd "$MAKE_CERT" && pwd)
fi

# build when the sources changed: their hash is the image's label
SRC=$(find ros2 docker -type f -not -path '*/__pycache__/*' -not -path '*/test/*' -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)
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

ARGS=(robot:="$ROBOT" port:="$PORT" lang:="$LANG_")
[ -n "$KEY" ] && ARGS+=(key:="$KEY")
MOUNT=()
if [ -n "$CERT" ]; then
  [ -f "$CERT/cert.pem" ] && [ -f "$CERT/key.pem" ] || { echo "$CERT needs cert.pem and key.pem" >&2; exit 1; }
  # the files the bridge needs, one by one: an authority's key next to them stays on this PC
  MOUNT=(-v "$CERT/cert.pem:/certs/cert.pem:ro" -v "$CERT/key.pem:/certs/key.pem:ro")
  ARGS+=(cert:=/certs/cert.pem cert_key:=/certs/key.pem)
  if [ -f "$CERT/ca.crt" ]; then
    MOUNT+=(-v "$CERT/ca.crt:/certs/ca.crt:ro")
    ARGS+=(ca:=/certs/ca.crt)
  fi
fi
docker run -d --rm --name "$NAME" --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" "${MOUNT[@]}" "$IMAGE" \
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
echo "  setup:  $SETUP"
[ -n "$CERT" ] && echo "  phones: install $CERT/ca.crt once each (the setup page's Wi-Fi tab shows how)"
echo "  logs:   ./start.sh logs      stop: ./start.sh stop"
if [ "$OPEN" = 1 ] && command -v xdg-open >/dev/null && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  xdg-open "$SETUP" >/dev/null 2>&1 &
fi

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""serve — serves the phone pages (web/) and keeps the reports phones send back (standard library only).

    python3 scripts/serve.py                      http on :8782, for USB (adb reverse makes it localhost)
    python3 scripts/serve.py --cert c.pem --key k.pem    https, for Wi-Fi (camera and microphone need it)

Reports land in reports/<when>-<model>.json; each one is summed up on the terminal.
"""
import argparse
import json
import re
import socket
import ssl
import sys
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "ros2" / "atl_phone" / "web"
REPORTS = ROOT / "reports"
MAX_REPORT = 64 * 1024


def model_of(user_agent: str) -> str:
    """The phone's model from its user agent, e.g. 'Android 8.0.0; SM-G950F' -> 'SM-G950F'."""
    m = re.search(r"Android [\d.]+; ([^;)]+)", user_agent or "")
    name = m.group(1).strip() if m else "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:40] or "unknown"


def model_in(report: dict) -> str:
    """The model the check page found (client hints), else the one in its user agent; safe as a file name."""
    m = report.get("model")
    if isinstance(m, str) and m.strip():
        return re.sub(r"[^A-Za-z0-9._-]+", "_", m.strip())[:40]
    return model_of(report.get("userAgent", ""))


def summary(report: dict) -> str:
    checks = report.get("checks", {})
    yes = sorted(k for k, v in checks.items() if v.get("ok") is True)
    no = sorted(k for k, v in checks.items() if v.get("ok") is False)
    core_missing = sorted(k for k, v in checks.items() if v.get("ok") is False and v.get("need") == "core")
    return (f"{model_in(report)}: {len(yes)} yes, {len(no)} no"
            + (f"; core missing: {', '.join(core_missing)}" if core_missing else "; core complete"))


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/report":
            return self.send_error(404)
        size = int(self.headers.get("Content-Length") or 0)
        if not 0 < size <= MAX_REPORT:
            return self.send_error(413)
        try:
            report = json.loads(self.rfile.read(size))
            if not isinstance(report, dict) or not isinstance(report.get("checks"), dict):
                raise ValueError("not a phone check report")
        except ValueError as e:
            return self.send_error(400, str(e))
        REPORTS.mkdir(exist_ok=True)
        when = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = REPORTS / f"{when}-{model_in(report)}.json"
        path.write_text(json.dumps(report, indent=2) + "\n")
        print("report:", summary(report), "->", path.relative_to(ROOT), flush=True)
        self.send_response(204)
        self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def lan_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))  # no packet is sent; it only picks the outgoing interface
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--port", type=int, default=8782)
    p.add_argument("--bind", default="0.0.0.0")
    p.add_argument("--cert")
    p.add_argument("--key")
    a = p.parse_args(argv)
    server = ThreadingHTTPServer((a.bind, a.port), partial(Handler, directory=str(WEB)))
    scheme = "http"
    if a.cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(a.cert, a.key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    print(f"USB:   adb reverse tcp:{a.port} tcp:{a.port}, then http://localhost:{a.port}/check.html")
    print(f"Wi-Fi: {scheme}://{lan_address()}:{a.port}/check.html"
          + ("" if a.cert else "   (http: camera and microphone stay blocked)"), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

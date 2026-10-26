# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""mock_adb — a fake adb server (adb's own text protocol) and a fake phone Chrome's DevTools, for phone_health's tests
and the browser check's "a lighter phone" card: no phone, no adb, and never the person's real tabs.

    adb, chrome = start()           # both on free ports of 127.0.0.1; adb.shells: what was run; chrome.closed: closed ids
    ... ADB_SERVER_PORT=adb.server_address[1] ATL_CDP_PORT=chrome.server_address[1] ...
    stop(adb, chrome)
"""
import json
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERIAL = "PHONE1"
SHELL = {
    "getprop": "ANE-LX1\n9\nMemTotal:        3874144 kB\nMemAvailable:    1030000 kB\n"
               " 22:01:02 up 3 days,  load average: 41.80, 43.08, 42.62\n  temperature: 352\nThermal Status: 0\n",
    "top": "  %CPU  RES NAME\r\n   100  91M com.android.chrome\r\n  27.7 2.4M top\r\n  69.4 267M com.android.chrome:privileged_process0\r\n",
    "dumpsys meminfo": "Applications Memory Usage\n\nTotal PSS by process:\n    262,409K: com.huawei.hiai (pid 26719)\n"
                       "    159,291K: com.facebook.orca (pid 22151)\n\nTotal PSS by OOM adjustment:\n    1K: x\n",
}
PAGES = [{"id": "A", "type": "page", "title": "Omi", "url": "http://localhost:{port}/face.html"},
         {"id": "B", "type": "page", "title": "Some news", "url": "https://example.org/"},
         {"id": "C", "type": "page", "title": "", "url": "https://example.com/x"},
         {"id": "W", "type": "service_worker", "url": "https://example.org/sw.js"}]


class FakeAdb(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, port=0):
        self.shells = []
        super().__init__(("127.0.0.1", port), _AdbHandler)


class _AdbHandler(socketserver.BaseRequestHandler):
    def cmd(self):
        n = int(self.request.recv(4), 16)
        return self.request.recv(n).decode()

    def handle(self):
        c = self.cmd()
        if c == "host:devices":
            body = f"{SERIAL}\tdevice\n".encode()
            self.request.sendall(b"OKAY" + b"%04x" % len(body) + body)
        elif c.startswith(f"host-serial:{SERIAL}:forward:"):
            self.request.sendall(b"OKAYOKAY")
        elif c == f"host:transport:{SERIAL}":
            self.request.sendall(b"OKAY")
            sh = self.cmd()[len("shell:"):]
            self.server.shells.append(sh)
            out = next((v for k, v in SHELL.items() if sh.startswith(k)), "")
            self.request.sendall(b"OKAY" + out.encode())
        else:
            msg = b"unknown command"
            self.request.sendall(b"FAIL" + b"%04x" % len(msg) + msg)


class FakeChrome(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, bridge_port=8782, port=0):
        self.pages = [dict(p, url=p["url"].replace("{port}", str(bridge_port))) for p in PAGES]
        self.closed = []
        super().__init__(("127.0.0.1", port), _ChromeHandler)


class _ChromeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        srv = self.server
        if self.path == "/json/list":
            body = json.dumps([p for p in srv.pages if p["id"] not in srv.closed]).encode()
        elif self.path.startswith("/json/close/"):
            srv.closed.append(self.path.rsplit("/", 1)[1])
            body = b"Target is closing"
        else:
            body = b""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def start(bridge_port=8782, adb_port=0, cdp_port=0):
    adb, chrome = FakeAdb(adb_port), FakeChrome(bridge_port, cdp_port)
    for srv in (adb, chrome):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return adb, chrome


def stop(*servers):
    for srv in servers:
        srv.shutdown()
        srv.server_close()

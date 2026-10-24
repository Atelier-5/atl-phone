#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""browser_check — the face page in a real (headless) Chrome as the phone, against a bridge in Docker.

    docker run -d --name atl-phone-check --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp atl-phone:kilted \\
        ros2 launch atl_phone phone.launch.py port:=8792
    python3 scripts/browser_check.py --container atl-phone-check --port 8792 [--shots <dir>]

ROS -> page: expressions published on the topic show on the face (read back from the page).
Page -> ROS: the page says hello (status) and a tap reaches the touch topic.
The setup page can send the phone to the check.
Prints PASS/FAIL per check and exits 1 if any failed. Standard library only.
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ros2" / "atl_phone"))
from atl_phone.mock_phone import MockPhone  # noqa: E402  (a WebSocket client is all CDP needs)

DEBUG_PORT = 9333


class Page:
    def __init__(self, url: str):
        self.profile = tempfile.mkdtemp(prefix="atl-phone-chrome-", dir=os.environ.get("ATL_SCRATCH"))
        self.chrome = subprocess.Popen(
            ["google-chrome", "--headless=new", "--no-sandbox", f"--user-data-dir={self.profile}",
             f"--remote-debugging-port={DEBUG_PORT}", "--remote-allow-origins=*", "--window-size=800,450",
             "--use-angle=swiftshader", "--enable-unsafe-swiftshader", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/list", timeout=1))
                ws = next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page")
                break
            except (OSError, StopIteration, ValueError):
                time.sleep(0.2)
        else:
            raise RuntimeError("Chrome did not start")
        self.cdp, self.id = MockPhone(ws), 0

    def call(self, method: str, **params):
        self.id += 1
        self.cdp.send(id=self.id, method=method, params=params)
        end = time.monotonic() + 10
        while time.monotonic() < end:
            m = self.cdp.got.get(timeout=10)
            if m.get("id") == self.id:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})
        raise TimeoutError(method)

    def js(self, expr: str):
        return self.call("Runtime.evaluate", expression=expr, returnByValue=True)["result"].get("value")

    def tap(self, x: int, y: int):
        for kind in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)

    def shot(self, path: Path):
        path.write_bytes(base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"]))

    def close(self):
        self.cdp.close()
        self.chrome.terminate()
        self.chrome.wait(10)
        shutil.rmtree(self.profile, ignore_errors=True)


def ros(container: str, *args, wait=True, timeout=20):
    cmd = ["docker", "exec", "-e", f"ROS_DOMAIN_ID={os.environ.get('ROS_DOMAIN_ID', '0')}", container, "/entrypoint.sh", "ros2", *args]
    if not wait:
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--container", required=True)
    a.add_argument("--port", type=int, default=8792)
    a.add_argument("--robot", default="thymio_1")
    a.add_argument("--shots", type=Path)
    args = a.parse_args()
    ns = f"/{args.robot}/phone"
    failed = 0

    def ok(name, good, detail=""):
        nonlocal failed
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
        failed += not good

    page = Page(f"http://localhost:{args.port}/face.html?autostart=1")
    try:
        connected = False
        for _ in range(30):
            if page.js("ws && ws.readyState") == 1:
                connected = True
                break
            time.sleep(0.3)
        ok("the page connects to the bridge", connected)
        status = ros(args.container, "topic", "echo", "--once", "--no-daemon", "--qos-durability", "transient_local", "--qos-reliability", "reliable", "--full-length", f"{ns}/status", "std_msgs/msg/String")
        ok("status: the page said hello (caps, screen)", '"caps"' in status and '"connected": true' in status, status.strip()[:100])

        for e in ("angry", "love", "happy"):
            ros(args.container, "topic", "pub", "--once", "-w", "1", f"{ns}/face/expression", "std_msgs/msg/String", f"{{data: {e}}}")
            shown = None
            for _ in range(20):
                shown = page.js("expression")
                if shown == e:
                    break
                time.sleep(0.2)
            ok(f"face/expression {e} shows on the face", shown == e, shown)
            if args.shots:
                args.shots.mkdir(parents=True, exist_ok=True)
                time.sleep(0.6)  # let the eyes ease into it
                page.shot(args.shots / f"live-{e}.png")

        echo = ros(args.container, "topic", "echo", "--once", "--no-daemon", f"{ns}/touch", "std_msgs/msg/String", wait=False)
        time.sleep(3)  # the echo must be subscribed before the tap
        page.tap(700, 225)
        try:
            out, _ = echo.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            echo.kill()
            out = ""
        ok("a tap on the right third reaches the touch topic", '"kind": "tap"' in out and '"zone": "right"' in out, out.strip()[:100])

        def act(body):
            req = urllib.request.Request(f"http://127.0.0.1:{args.port}/api/act", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            return urllib.request.urlopen(req, timeout=5).status

        act({"open": "check.html"})
        where = None
        for _ in range(30):
            time.sleep(0.3)
            try:
                where = page.js("location.pathname")
            except (RuntimeError, TimeoutError):
                continue  # the page is changing
            if where == "/check.html":
                break
        ok("setup page: 'open the check' sends the phone to check.html", where == "/check.html", where)
    finally:
        page.close()
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

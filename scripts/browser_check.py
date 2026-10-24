#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""browser_check — the face page in a real (headless) Chrome as the phone, against a bridge in Docker.

    docker run -d --name atl-phone-check --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp atl-phone:kilted \\
        ros2 launch atl_phone phone.launch.py port:=8792
    python3 scripts/browser_check.py --container atl-phone-check --port 8792 [--shots <dir>] [--face <picture>]

ROS -> page: expressions published on the topic show on the face (read back from the page).
Page -> ROS: the page says hello (status) and a tap reaches the touch topic.
Look: the front camera (Chrome's fake one) runs the face finder on the page and faces reach the bridge;
with --face, the fake camera shows that picture (of an adult, kept out of the repo) and the face is found.
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
    def __init__(self, url: str, extra=()):
        self.profile = tempfile.mkdtemp(prefix="atl-phone-chrome-", dir=os.environ.get("ATL_SCRATCH"))
        self.chrome = subprocess.Popen(
            ["google-chrome", "--headless=new", "--no-sandbox", f"--user-data-dir={self.profile}",
             f"--remote-debugging-port={DEBUG_PORT}", "--remote-allow-origins=*", "--window-size=800,450",
             "--use-angle=swiftshader", "--enable-unsafe-swiftshader", *extra, url],
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
    a.add_argument("--face", type=Path, help="a picture with one face, for the fake front camera")
    args = a.parse_args()
    ns = f"/{args.robot}/phone"
    failed = 0

    def ok(name, good, detail=""):
        nonlocal failed
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
        failed += not good

    camera = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
    tmp = None
    if args.face:  # Chrome's fake camera plays a .y4m (or .mjpeg) file
        tmp = tempfile.mkdtemp(prefix="atl-phone-face-", dir=os.environ.get("ATL_SCRATCH"))
        y4m = os.path.join(tmp, "face.y4m")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(args.face), "-t", "2", "-r", "10",
                        "-vf", "scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2", "-pix_fmt", "yuv420p", y4m], check=True)
        camera.append(f"--use-file-for-fake-video-capture={y4m}")
    page = Page(f"http://localhost:{args.port}/face.html?autostart=1", camera)
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
        # the echo must be subscribed before a tap reaches it, and starting it takes long on a busy PC:
        # tap once a second until it has one
        for _ in range(15):
            page.tap(700, 225)
            try:
                echo.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                pass
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

        def seen():
            return json.load(urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/state", timeout=5))["seen"]

        act({"topic": "look", "value": True})  # through ROS, as a program would
        look, faces = {}, {}
        for _ in range(100):  # loading the face finder takes a while on a CPU-only Chrome
            time.sleep(0.3)
            s = seen()
            look, faces = s.get("look", {}), s.get("faces", {})
            if look.get("ok") and faces and (faces["n"] or not args.face):
                break
        ok("look: the front camera opens and the face finder runs on the page", look.get("ok") is True and "n" in faces
           and page.js("document.getElementById('eye').textContent") == "● look", (look, faces))
        if args.face:
            f = (faces.get("faces") or [{}])[0]
            ok("look: the face in the picture is found, in the middle", faces.get("n") == 1 and abs(f.get("x", 9)) < 0.4
               and abs(f.get("y", 9)) < 0.5 and f.get("size", 0) > 0.1, faces)
            if args.shots:
                page.shot(args.shots / "look.png")
            act({"allow_familiar": True})
            act({"topic": "familiar", "value": True})
            for _ in range(100):  # the recognition net is 6 MB
                time.sleep(0.3)
                faces = seen().get("faces", {})
                if faces.get("n") and faces["faces"][0]["familiar"]:
                    break
            n = page.js("seeing.known.length")
            ok("familiar (allowed): the face gets number 1, and the page keeps one signature, in memory",
               faces.get("n") == 1 and faces["faces"][0]["familiar"] == 1 and n == 1, (faces, n))
            act({"allow_familiar": False})
            time.sleep(1.0)
            ok("familiar taken back: the page forgets the signatures", page.js("seeing.known.length") == 0 and not page.js("seeing.familiar"))
        act({"topic": "look", "value": False})
        time.sleep(1.0)
        ok("look off: the camera closes", page.js("cam === null && document.getElementById('eye').style.display") == "none")

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
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

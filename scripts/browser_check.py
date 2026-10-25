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
Portrait: the setup page turns the face upright; the panel under the eyes shows the mouth (a sound wave while it
speaks), the pad (a press reaches ROS), the sensors, or a camera's picture, as a program sets it or the person picks it
(a tap on the eyes opens the menu, a swipe steps through it). Vision: a test picture (scripts/vision_picture.py) through
the fake camera: marker 7 and its distance, a red blob on either camera, and MediaPipe's faces, objects and hands running.
The setup page's Scenarios step starts the Desk Guardian and shows its state. The setup page can send the phone to the check.
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

    def wait_for(self, expr: str, tries=30):
        """Polls a JS expression until it is truthy (a page that reloads meanwhile is retried); returns its last value."""
        v = None
        for _ in range(tries):
            try:
                v = self.js(expr)
            except (RuntimeError, TimeoutError):
                v = None
            if v:
                return v
            time.sleep(0.3)
        return v

    def size(self, w: int, h: int, mobile=False):
        self.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=mobile)

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

        def state():
            return json.load(urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/state", timeout=5))

        def seen():
            return state()["seen"]

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

        def shoot(name):
            if args.shots:
                time.sleep(0.6)
                page.shot(args.shots / name)

        page.size(360, 760, mobile=True)  # a narrow phone, upright (the ANE-LX1's 360×760)
        # the bridge keeps the last panel for the phone that comes (a rerun gets this run's last): start from the default
        act({"topic": "panel", "value": {"mode": "mouth", "buttons": [{"id": k, "label": k.upper()} for k in "abcd"]}})
        act({"open": "face.html", "layout": "portrait"})
        up = page.wait_for("location.search.indexOf('layout=portrait') >= 0 && ws && ws.readyState === 1 && split() && "
                           "panel.mode === 'mouth' && document.getElementById('panel').style.display === 'none'")
        ok("portrait: the face reloads upright, eyes on top and the mouth below", bool(up))
        shoot("portrait-mouth-default.png")
        page.tap(200, 150)  # a tap on the eyes
        chips = page.wait_for("document.getElementById('menu').style.display === 'flex' && "
                              "[].map.call(document.querySelectorAll('#menu button'), function (b) { return b.dataset.mode; }).join()")
        ok("a tap on the eyes opens the menu: six modes", chips == "mouth,pad,off,camera,camera_back,sensors", chips)
        fit = page.js("(function () { var y = splitY(), r = [].map.call(document.querySelectorAll('#menu button'), function (b) { return b.getBoundingClientRect(); });"
                      " return r.every(function (b) { return b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= y; }) &&"
                      " parseFloat(canvas.style.height) === innerHeight && Math.abs(parseFloat(document.getElementById('panel').style.top) - y) < 1; })()")
        ok("on a narrow phone every chip shows whole, above the panel, which starts where the eyes end", fit is True, fit)
        shoot("portrait-menu.png")
        r = page.js("(function () { var b = document.querySelector('#menu button[data-mode=pad]').getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()")
        page.tap(int(r[0]), int(r[1]))
        n = page.wait_for("getComputedStyle(document.getElementById('pad')).display === 'grid' && document.querySelectorAll('#pad button').length")
        told = None
        for _ in range(20):
            time.sleep(0.2)
            told = (state().get("panel") or {}).get("mode")
            if told == "pad":
                break
        ok("the menu's Buttons: the pad of 4, and the bridge is told (panel/mode)", n == 4 and told == "pad", (n, told))
        shoot("portrait-pad.png")
        r = page.js("(function () { var b = document.querySelectorAll('#pad button')[1].getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()")
        page.tap(int(r[0]), int(r[1]))
        pads = []
        for _ in range(20):
            time.sleep(0.2)
            pads = [x["id"] for x in seen().get("pad", [])]
            if pads:
                break
        ok("portrait: a press on pad button B reaches ROS (pad)", pads[-1:] == ["b"], pads)

        act({"topic": "panel", "value": {"mode": "pad", "buttons": [{"id": k, "label": k.title(), "color": [1, 0.5 * i / 5, 0]} for i, k in
                                                                     enumerate(["go", "stop", "left", "right", "dance", "sing"])]}})
        n = page.wait_for("document.querySelectorAll('#pad button').length === 6 && document.querySelectorAll('#pad button').length")
        ok("panel: a program sets six buttons of its own", n == 6, n)
        shoot("portrait-pad6.png")
        act({"topic": "panel", "value": {"mode": "mouth"}})
        act({"topic": "expression", "value": "happy"})
        m = page.wait_for("panel.mode === 'mouth' && expression === 'happy' && document.getElementById('panel').style.display === 'none'")
        ok("panel: the mouth instead, drawn under the eyes (no buttons)", bool(m))
        shoot("portrait-mouth.png")
        page.js("speaking = true; word()")
        w = page.wait_for("wave.amp.filter(function (a) { return a > 0.1; }).length > 5")
        shoot("portrait-wave.png")
        page.js("speaking = false")
        ok("speaking: the mouth turns into a sound wave", bool(w))
        page.wait_for("!wave.amp.some(function (a) { return a > 0.02; })")
        for kind, x in (("mousePressed", 320), ("mouseMoved", 200), ("mouseReleased", 80)):  # a swipe to the left, on the eyes
            page.call("Input.dispatchMouseEvent", type=kind, x=x, y=200, button="left", buttons=1, clickCount=1)
        sw = page.wait_for("panel.mode === 'pad' && panel.mode")
        ok("a swipe left on the eyes: the next mode (mouth -> buttons)", sw == "pad", sw)
        act({"topic": "panel", "value": {"mode": "sensors"}})
        tiles = page.wait_for("getComputedStyle(document.getElementById('sensors')).display === 'grid' && "
                              "document.querySelectorAll('#sensors .tile').length")
        ok("panel: the sensors, six tiles drawn on the phone", tiles == 6, tiles)
        shoot("portrait-sensors.png")
        act({"topic": "panel", "value": {"mode": "camera_back"}})
        c = page.wait_for("camFacing === 'environment' && document.getElementById('pcam').videoWidth > 0 && "
                          "document.getElementById('pcam').style.transform === 'none'")
        ok("panel: the back camera's picture (not mirrored)", bool(c))
        act({"topic": "panel", "value": {"mode": "camera"}})
        c = page.wait_for("camFacing === 'user' && document.getElementById('pcam').style.display === 'block' && "
                          "document.getElementById('pcam').videoWidth > 0 && document.getElementById('eye').textContent")
        ok("panel: the front camera's picture, on the page only, and the face says a camera is on", c == "● cam", c)
        shoot("portrait-camera.png")
        act({"topic": "panel", "value": {"mode": "off"}})
        off = page.wait_for("cam === null && !split() && eyeH === H")
        ok("panel off: the camera closes and the eyes take the whole screen", bool(off))
        shoot("portrait-off.png")
        act({"topic": "panel", "value": {"mode": "pad"}})
        act({"topic": "expression", "value": "neutral"})
        page.size(800, 450)
        act({"open": "face.html", "layout": "landscape"})
        back = page.wait_for("location.search.indexOf('layout=landscape') >= 0 && ws && ws.readyState === 1 && !split()")
        ok("landscape again: the eyes alone, as before", bool(back))

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
        before = len(state().get("reports", []))
        page.wait_for("typeof sendReport === 'function'")
        page.js("sendReport()")  # what Test everything ends with: the report to the PC, then the face, turned as held
        where = None
        for _ in range(40):
            time.sleep(0.3)
            try:
                where = page.js("location.pathname + location.search")
            except (RuntimeError, TimeoutError):
                continue
            if where.startswith("/face.html"):
                break
        r = state().get("reports", [])
        ok("check page: the report goes to the PC, then on to the face (layout=auto)",
           len(r) > before and where == "/face.html?layout=auto", (len(r), where))
    finally:
        page.close()

    # vision: a test picture (marker 7 in the middle, a red square on the left) through the fake camera
    vtmp = tempfile.mkdtemp(prefix="atl-phone-vision-", dir=os.environ.get("ATL_SCRATCH"))
    subprocess.run([sys.executable, str(Path(__file__).with_name("vision_picture.py")), os.path.join(vtmp, "v.ppm")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", os.path.join(vtmp, "v.ppm"), "-t", "2", "-r", "10",
                    "-pix_fmt", "yuv420p", os.path.join(vtmp, "v.y4m")], check=True)
    page = Page(f"http://localhost:{args.port}/face.html?autostart=1",
                ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-video-capture={vtmp}/v.y4m"])
    try:
        page.wait_for("ws && ws.readyState === 1")

        def found(kind, test, tries=60):
            v = None
            for _ in range(tries):
                time.sleep(0.5)
                v = seen().get(kind)
                if v and test(v):
                    return v
            return v

        act({"topic": "see", "value": {"camera": "front", "find": ["markers", "blobs"], "blob": {"hue": 0, "tol": 15}, "marker_cm": 5, "fov_deg": 60}})
        mk = found("markers", lambda v: v["markers"])
        m = (mk or {}).get("markers", [{}])[0] if mk and mk["markers"] else {}
        ok("see markers: marker 7 in the middle, 18 cm away (5 cm, 156 px of 640, 60 degrees)", m.get("id") == 7 and abs(m.get("x", 9)) < 0.05
           and 0.16 < (m.get("distance_m") or 0) < 0.20 and m.get("yaw_deg") is not None and abs(m["yaw_deg"]) < 10, m)
        bl = found("blobs", lambda v: v["blobs"])
        b = (bl or {}).get("blobs", [{}])[0] if bl and bl["blobs"] else {}
        ok("see blobs: the red square, on the face's right (the front camera is a mirror)", 0.6 < b.get("x", 0) < 0.8 and 0.12 < b.get("size", 0) < 0.22, b)
        act({"topic": "see", "value": {"camera": "back", "find": ["blobs"], "blob": {"hue": 0, "tol": 15}}})
        bl = found("blobs", lambda v: v["camera"] == "back" and v["blobs"] and v["blobs"][0]["x"] < 0)
        ok("see on the back camera: the red square on the left, as the camera sees it", bool(bl) and -0.8 < bl["blobs"][0]["x"] < -0.6, bl)
        act({"topic": "see", "value": {"camera": "front", "find": ["faces", "objects", "hands"]}})
        sr = found("see", lambda v: v.get("ok") and {"faces", "objects", "hands"} <= set(v.get("ms", {})), tries=120)
        ok("see faces, objects, hands: MediaPipe runs on the page, and the phone says how long each takes", bool(sr), sr)
        act({"topic": "see", "value": {"find": []}})
        off = page.wait_for("cam === null")
        ok("see nothing: the camera closes", bool(off))
    finally:
        page.close()
        shutil.rmtree(vtmp, ignore_errors=True)

    # Omi Assist: the tiles, the note, the helpers, the follower, showing; a printed page through the fake camera
    otmp = tempfile.mkdtemp(prefix="atl-phone-omi-", dir=os.environ.get("ATL_SCRATCH"))
    font = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans:bold"], capture_output=True, text=True).stdout.strip()
    lines = ["Hallo Oma", "Der Arzt kommt um zehn Uhr.", "Bitte die Tabletten nehmen."]
    draw = ",".join(f"drawtext=fontfile={font}:text='{t}':fontsize=40:fontcolor=black:x=40:y={90 + 110 * i}" for i, t in enumerate(lines))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=white:s=1280x480:d=2:r=10", "-vf", draw,
                    "-pix_fmt", "yuv420p", os.path.join(otmp, "text.y4m")], check=True)
    page = Page(f"http://localhost:{args.port}/face.html?autostart=1&layout=portrait&lang=de",
                ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-video-capture={otmp}/text.y4m"])
    try:
        page.size(360, 760, mobile=True)
        page.wait_for("ws && ws.readyState === 1")
        act({"topic": "see", "value": {"find": []}})
        act({"topic": "panel", "value": {"mode": "mouth", "style": "tiles", "menu": ["time", "front", "back", "magnify", "read", "what", "follow", "show"]}})
        page.wait_for("panel.style === 'tiles'")
        page.tap(180, 100)
        fit = page.wait_for("document.getElementById('menu').style.display === 'grid' && (function () {"
                            " var bs = [].slice.call(document.querySelectorAll('#menu button'));"
                            " return bs.length === 9 && bs.every(function (b) { var r = b.getBoundingClientRect(), s = b.querySelector('span');"
                            " return r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight && r.height >= 90 && s.scrollWidth <= b.clientWidth"
                            " && parseFloat(getComputedStyle(b).fontSize) >= 17; }) && bs.length; })()")
        ok("Omi: a tap on the eyes opens nine big tiles (eight and Gesicht), each whole on a 360 px phone", fit == 9, fit)
        shoot("omi-tiles.png")
        r = page.js("(function () { var b = document.querySelector('#menu button[data-mode=time]').getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()")
        page.tap(int(r[0]), int(r[1]))
        said = page.wait_for("document.getElementById('toast').style.display === 'block' && document.getElementById('toast').textContent")
        picked = [x["id"] for x in seen().get("menu", [])]
        ok("Omi: the time tile says the time and the day, in German, and ROS hears the pick (menu)",
           bool(said) and said.startswith("Es ist") and "Heute ist" in said and picked[-1:] == ["time"], (said, picked[-1:]))
        act({"topic": "note", "value": {"id": "r1", "text": "Tabletten nehmen", "buttons": [{"id": "done", "label": {"de": "Erledigt"}},
                                                                                           {"id": "later", "label": {"de": "Später"}}]}})
        b = page.wait_for("document.getElementById('card').style.display === 'flex' && document.querySelector('#card button').textContent")
        shoot("omi-note.png")
        r = page.js("(function () { var b = document.querySelector('#card button').getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()")
        page.tap(int(r[0]), int(r[1]))
        ans = None
        for _ in range(20):
            time.sleep(0.2)
            ans = seen().get("answer")
            if ans:
                break
        ok("Omi: a reminder's card shows big; Erledigt answers it (note/answer)", b == "Erledigt" and bool(ans) and ans["id"] == "done"
           and page.js("document.getElementById('card').style.display") == "none", (b, ans))
        act({"topic": "read", "value": ""})
        rd = None
        for _ in range(240):  # Tesseract loads its German the first time
            time.sleep(0.5)
            rd = seen().get("read")
            if rd:
                break
        spoken = page.js("document.getElementById('toast').textContent")
        ok("Omi: read: the printed page is read on the phone, three lines; only the counts reach ROS",
           bool(rd) and rd.get("ok") is True and rd.get("lines") == 3 and "text" not in rd, (rd, spoken))
        page.js("stopReading()")
        act({"topic": "what", "value": {"lang": "de"}})
        wt = None
        for _ in range(120):
            time.sleep(0.5)
            wt = seen().get("what")
            if wt:
                break
        phrase = page.js("whatPhrase('cup', 0.8, 'de') + ' / ' + whatPhrase('cup', 0.5, 'fr') + ' / ' + whatPhrase(null, 0, 'en')")
        ok("Omi: what: one look of the object finder at the back camera; a cup is said with its article",
           bool(wt) and wt.get("ok") is True and phrase.startswith("Das ist eine Tasse. / Je crois que c’est une tasse."), (wt, phrase))
        follow = page.js("(function () { vision.follow = true; seeing.follow = { cur: null, cand: null, candAt: 0 };"
                         " var a = { kind: 'markers', x: 0.5, y: 0, d: 0.5 }, b = { kind: 'faces', x: -0.5, y: 0, d: 0.3 }, out = [];"
                         " out.push(followPick([a, b], 0).kind);"                                       # the nearer
                         " out.push(followPick([{ kind: 'markers', x: 0.5, y: 0, d: 0.24 }, b], 100).kind);"  # only 20 % nearer: held
                         " out.push(followPick([{ kind: 'markers', x: 0.5, y: 0, d: 0.2 }, b], 200).kind);"   # 33 % nearer, not yet 0.5 s
                         " out.push(followPick([{ kind: 'markers', x: 0.5, y: 0, d: 0.2 }, b], 750).kind);"   # 0.55 s: it takes over
                         " out.push(followPick([], 1500).kind);"                                         # lost: held 1 s
                         " out.push(String(followPick([], 1800)));"                                      # then let go
                         " vision.follow = false; return out.join(); })()")
        ok("Omi: the follower holds the nearest; another takes over only when 25 % nearer for 0.5 s; a lost one is held 1 s",
           follow == "faces,faces,faces,markers,markers,null", follow)
        act({"allow_show": False})
        page.wait_for("!omi.showAllowed")
        page.js("omiTile('show')")
        refused = page.js("omi.showing === false && document.getElementById('showing').style.display !== 'block'")
        act({"allow_show": True})
        page.wait_for("omi.showAllowed")
        page.js("omiTile('show')")
        badge = page.wait_for("omi.showing && document.getElementById('showing').style.display === 'block' && document.getElementById('showing').textContent")
        pic = None
        for _ in range(20):
            time.sleep(0.3)
            try:
                rsp = urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/show.jpg", timeout=5)
                pic = (rsp.headers.get("Content-Type"), len(rsp.read()))
                break
            except urllib.error.HTTPError:
                continue
        shoot("omi-show.png")
        act({"show": False})
        stopped = page.wait_for("!omi.showing && document.getElementById('showing').style.display === 'none'")
        act({"allow_show": False})
        ok("Omi: show is refused unless allowed; allowed, the red badge is on and the PC gets the picture; stopped from the PC",
           refused is True and badge == "● ZEIGEN" and bool(pic) and pic[0] == "image/jpeg" and pic[1] > 1000 and bool(stopped), (refused, badge, pic))
        page.js("setPanel({ mode: 'magnify' }, true)")
        mag = page.wait_for("getComputedStyle(document.getElementById('mag')).display === 'flex' && pcam.style.display === 'block' && camFacing === 'environment'")
        page.js("magnify('plus')")
        shoot("omi-magnify.png")
        ok("Omi: the magnifier: the back camera big in the panel, with zoom, torch and hold", bool(mag) and page.js("omi.zoom") > 1, page.js("omi.zoom"))
        page.tap(180, 100)
        r = page.wait_for("document.getElementById('menu').style.display === 'grid' && (function () { var b = document.querySelector('#menu button[data-mode=face]');"
                          " if (!b || b !== document.querySelector('#menu').lastElementChild) return null; b = b.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()")
        page.js("window.__said = []; (function () { var sp = speak; speak = function (t, l, a, d) { if (!a) window.__said.push(t); return sp(t, l, a, d); }; })()")
        page.tap(int(r[0]), int(r[1]))
        home = page.wait_for("panel.mode === 'mouth' && document.getElementById('menu').style.display === 'none' && pcam.style.display === 'none' && expression === 'love' && 'home'")
        said = page.js("window.__said.join(' / ')")
        after = page.wait_for("expression !== 'love' && expression")
        ok("Omi: the last tile, Gesicht, goes back to the face from the magnifier: „Hier bin ich wieder!“ once, a short love face",
           home == "home" and bool(r) and said == "Hier bin ich wieder!" and after == "neutral", (r, home, said, after))
        alive = page.js("(function () { ripples.push({ x: 10, y: 10, t: performance.now() + 400 }); window.__drawn = 0;"
                        " var d = draw; draw = function (n) { window.__drawn++; d(n); }; return 1; })()")
        time.sleep(1.5)
        drawn = page.js("(function () { var n = window.__drawn; return n; })()")  # (the old face: one frame, then none)
        ok("the face keeps drawing after a tap newer than the frame (the ANE-LX1's black screen)", bool(alive) and drawn >= 3, drawn)
        page.js("delete Q.lang")
        act({"topic": "panel", "value": {"mode": "mouth", "style": "tiles", "lang": "fr", "menu": ["time", "front"]}})
        fr = page.wait_for("lang === 'fr' && document.documentElement.lang === 'fr' && lang")
        kept = page.js("(function () { try { return localStorage.getItem('atl-phone-lang'); } catch (e) { return 'none'; } })()")
        act({"topic": "panel", "value": {"mode": "mouth", "style": "tiles", "lang": "auto", "menu": ["time", "front"]}})
        auto = page.wait_for("lang === PHONE_LANG && lang")
        gone = page.js("(function () { try { return localStorage.getItem('atl-phone-lang'); } catch (e) { return 'none'; } })()")
        fr = fr if kept == "fr" and gone is None else (fr, kept, gone)
        page.js("Q.lang = 'de'; setLang('de')")
        ok("Omi: a panel's lang sets the face's words and voice (Omi: German on a French phone), kept for the start screen; auto: the phone's own again",
           fr == "fr" and bool(auto), (fr, auto))
        page.js("tour('de')")
        hello = page.wait_for("omi.touring && document.getElementById('toast').textContent")
        menu = page.wait_for("omi.touring && document.getElementById('menu').style.display === 'grid' && 'menu'", 80)
        shoot("omi-tour.png")
        page.tap(180, 60)
        ended = page.wait_for("!omi.touring && !document.querySelector('#menu .tour') && 'ended'")  # (the tap on the eyes: the menu)
        ok("Omi: the presentation says hello in German, opens the tiles, and a tap ends it",
           bool(hello) and hello.startswith("Hallo Omi! Ich bin Omi Assist") and menu == "menu" and ended == "ended", (hello, menu, ended))
        act({"topic": "panel", "value": {"mode": "mouth", "style": "chips", "menu": ["mouth", "pad", "off", "camera", "camera_back", "sensors"]}})
        page.wait_for("panel.style === 'chips' && cam === null")
    finally:
        page.close()
        shutil.rmtree(otmp, ignore_errors=True)

    page = Page(f"http://localhost:{args.port}/setup.html")
    try:
        page.wait_for("typeof go === 'function' && S !== null")
        views = page.js("[].map.call(document.querySelectorAll('#views button'), function (b) { return b.getAttribute('data-v'); }).join()")
        page.js("showView('guard')")
        ok("setup page: a menu at the top: Connect and Test, Desk Guard, Omi Assist", views == "setup,guard,omi"
           and page.js("document.getElementById('v-guard').className === 'on' && document.querySelector('.wrap').classList.contains('solo')"
                       " && getComputedStyle(document.querySelector('.wrap nav')).display === 'none'"), views)
        off = page.wait_for("live.guard && live.guard.textContent === t('g_off') && live.guard.textContent")
        act({"guardian": True, "drive": False})
        on = page.wait_for("guardianOn() && live.guard.textContent")
        ok("setup page, Desk Guard: the guardian waits, then starts on Start and shows its state", bool(off) and bool(on), (off, on))
        if args.shots:
            for w, h in ((1100, 900), (390, 1400)):
                for scheme in ("light", "dark"):
                    page.size(w, h)
                    page.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": scheme}])
                    time.sleep(0.5)
                    page.shot(args.shots / f"setup-guard-{w}-{scheme}.png")
        page.js("showView('omi')")
        page.js("[].filter.call(document.querySelectorAll('#omi-cards button'), function (b) { return b.textContent.indexOf('▶') === 0; })[0].click()")
        omi_on = page.wait_for("omiOn() && !guardianOn() && live.omi.textContent", tries=40)
        stopped = page.wait_for("!guardianOn() && live.guard.textContent === t('g_off')")
        ok("setup page, Omi Assist: Start runs it, and stops the Desk Guardian (they share the face)", bool(omi_on) and bool(stopped), omi_on)
        page.js("[].filter.call(document.querySelectorAll('#omi-cards button'), function (b) { return b.textContent === t('rem_test'); })[0].click()")
        rem = page.wait_for("S.omi && S.omi.reminders && S.omi.reminders.length === 1 && S.omi.next && S.omi.next.text", tries=40)
        if args.shots:
            for w, h in ((1100, 1100), (390, 1900)):
                for scheme in ("light", "dark"):
                    page.size(w, h)
                    page.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": scheme}])
                    time.sleep(0.5)
                    page.shot(args.shots / f"setup-omi-{w}-{scheme}.png")
        ok("setup page, Omi Assist: a reminder in a minute is kept by Omi Assist and shown as the next", rem == "Drink a glass of water", rem)
        act({"reminders": []})
        act({"omi": False})
        off = page.wait_for("!omiOn() && live.omi.textContent.indexOf(t('omi_off')) === 0", tries=40)
        ok("setup page, Omi Assist: Stop stops it", bool(off))
    finally:
        page.close()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

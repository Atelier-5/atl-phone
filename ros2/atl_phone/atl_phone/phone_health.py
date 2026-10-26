# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""phone_health — what weighs on the phone, and lighter on request, for the setup page (scripts/phone_tidy.sh's twin).

It speaks to the adb server already running on this computer (127.0.0.1:5037, the one that holds the phone's USB link
and its adb reverse), with adb's own text protocol: no adb in the container, whose version would not match the host's
(adb then kills the other server, and the phone's link with it). With --net=host the container reaches it as is.

look(): the model, free memory, the load, how many Chrome tabs are open (a count), the battery's temperature, the
thermal status, the busiest apps and the ones holding most memory. kill(): am kill-all (background apps stop; they start
again when opened, no data is lost). stay_on(on): the screen stays on while on USB. tabs(port): Chrome's tabs other than
the bridge's own (their id and title, for the setup page on this PC only); close(port, ids): closes those, never one of
the bridge's pages. Nothing here runs unless the person at the setup page asks.
"""
import json
import os
import re
import socket
import urllib.request

ADB = (os.environ.get("ADB_SERVER_HOST", "127.0.0.1"), int(os.environ.get("ADB_SERVER_PORT", "5037")))
CDP = int(os.environ.get("ATL_CDP_PORT", "9229"))   # the phone's Chrome DevTools, forwarded here (as phone_tidy.sh; browser_check: 9333)
TIMEOUT = 20.0               # s: dumpsys meminfo takes about 8 s on a busy phone


class AdbError(RuntimeError):
    pass


def _send(s: socket.socket, cmd: str):
    data = cmd.encode()
    s.sendall(b"%04x" % len(data) + data)
    status = _read(s, 4)
    if status != b"OKAY":
        n = int(_read(s, 4) or b"0", 16) if status == b"FAIL" else 0
        raise AdbError((_read(s, n).decode(errors="replace") if n else status.decode(errors="replace")) or "adb refused")


def _read(s: socket.socket, n: int) -> bytes:
    out = b""
    while len(out) < n:
        chunk = s.recv(n - len(out))
        if not chunk:
            break
        out += chunk
    return out


def _connect() -> socket.socket:
    try:
        return socket.create_connection(ADB, timeout=TIMEOUT)
    except OSError as e:
        raise AdbError(f"no adb server on this computer ({e}): run adb devices once") from e


def serial() -> str:
    """The phone on USB: ANDROID_SERIAL, else the one device adb has."""
    with _connect() as s:
        _send(s, "host:devices")
        listing = _read(s, int(_read(s, 4) or b"0", 16)).decode()
    devices = [ln.split("\t")[0] for ln in listing.splitlines() if ln.endswith("\tdevice")]
    want = os.environ.get("ANDROID_SERIAL")
    if want:
        if want not in devices:
            raise AdbError(f"no phone {want} on USB")
        return want
    if len(devices) != 1:
        raise AdbError("no phone on USB" if not devices else "more than one phone on USB: set ANDROID_SERIAL")
    return devices[0]


def shell(cmd: str, dev: str = "") -> str:
    with _connect() as s:
        _send(s, f"host:transport:{dev or serial()}")
        _send(s, f"shell:{cmd}")
        out = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    return out.decode(errors="replace").replace("\r", "")


def forward(local: int, remote: str, dev: str = ""):
    with _connect() as s:
        _send(s, f"host-serial:{dev or serial()}:forward:tcp:{local};{remote}")
        _read(s, 4)   # a second OKAY, once the forward is set


def _pages(dev: str) -> list:
    forward(CDP, "localabstract:chrome_devtools_remote", dev)
    with urllib.request.urlopen(f"http://127.0.0.1:{CDP}/json/list", timeout=5) as r:
        return [t for t in json.load(r) if t.get("type") == "page"]


def _ours(t: dict, port: int) -> bool:
    return f":{port}/" in t.get("url", "")


def look() -> dict:
    """The phone's load, as numbers and app names (nothing about what the apps or tabs hold)."""
    dev = serial()
    info = shell("getprop ro.product.model; getprop ro.build.version.release; cat /proc/meminfo; uptime; "
                 "dumpsys battery; dumpsys thermalservice", dev)
    lines = info.splitlines()
    mem = {k: int(v) for k, v in re.findall(r"^(MemAvailable|MemTotal):\s+(\d+)", info, re.M)}
    load = re.search(r"load average:\s*([\d.]+),?\s*([\d.]+),?\s*([\d.]+)", info)
    temp = re.search(r"^\s*temperature:\s*(\d+)", info, re.M)
    thermal = re.search(r"Thermal Status:\s*(\d+)", info)
    try:
        tabs = len(_pages(dev))
    except (OSError, ValueError, AdbError):
        tabs = None
    busy = []
    for ln in shell("top -b -n 1 -o %CPU,RES,NAME -s 1", dev).splitlines():
        f = ln.split()
        if len(f) >= 3 and re.fullmatch(r"[\d.]+", f[0]) and float(f[0]) > 0.5 and f[2] != "top":
            busy.append({"cpu": float(f[0]), "res": f[1], "name": f[2]})
    held, on = [], False
    for ln in shell("dumpsys meminfo", dev).splitlines():
        if re.search(r"Total (PSS|RSS) by process", ln):
            on = True
            continue
        if on and not ln.strip():
            break
        m = re.match(r"\s*([\d,]+)K: (\S+)", ln) if on else None
        if m:
            held.append({"mb": round(int(m.group(1).replace(",", "")) / 1024), "name": m.group(2)})
    return {"model": lines[0].strip() if lines else "", "android": lines[1].strip() if len(lines) > 1 else "",
            "free_mb": mem.get("MemAvailable", 0) // 1024, "total_mb": mem.get("MemTotal", 0) // 1024,
            "load": [float(x) for x in load.groups()] if load else None, "tabs": tabs,
            "battery_c": int(temp.group(1)) / 10 if temp else None, "thermal": int(thermal.group(1)) if thermal else None,
            "busy": busy[:6], "memory": held[:6]}


def kill():
    shell("am kill-all")


def stay_on(on: bool):
    shell("svc power stayon " + ("usb" if on else "false"))


def tabs(port: int) -> list:
    """Chrome's tabs other than the bridge's: what the person at the setup page may close."""
    return [{"id": t["id"], "title": (t.get("title") or t.get("url", ""))[:80]} for t in _pages(serial()) if not _ours(t, port)]


def close(port: int, ids: list) -> int:
    """Closes these tabs, if they are still open and not the bridge's: how many closed."""
    pages = {t["id"]: t for t in _pages(serial())}
    n = 0
    for i in ids if isinstance(ids, list) else []:
        t = pages.get(i) if isinstance(i, str) else None
        if t and not _ours(t, port):
            urllib.request.urlopen(f"http://127.0.0.1:{CDP}/json/close/{i}", timeout=5).read()
            n += 1
    return n

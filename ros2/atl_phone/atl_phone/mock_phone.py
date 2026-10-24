# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""mock_phone — a phone without a phone: a WebSocket client that talks like the face page (standard library only).

    python3 -m atl_phone.mock_phone [--url ws://127.0.0.1:8782/ws]     says hello, sends a still IMU, prints what comes

The tests and contract_check use MockPhone directly.
"""
import argparse
import base64
import json
import os
import queue
import socket
import threading
import time
from urllib.parse import urlsplit

from .wsserver import accept_key, frame, read_frame

ID = "0123456789abcdef"  # the page's random per-browser id
UA = "Mozilla/5.0 (Linux; Android 8.0.0; MOCK-PHONE) AppleWebKit/537.36 Chrome/119.0 Mobile Safari/537.36"


class MockPhone:
    def __init__(self, url: str, timeout: float = 5.0):
        u = urlsplit(url)
        self.sock = socket.create_connection((u.hostname, u.port or 80), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        path = u.path + (f"?{u.query}" if u.query else "")
        host = f"{u.hostname}:{u.port or 80}"
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: http://{host}\r\n\r\n").encode())
        self.rfile = self.sock.makefile("rb")
        status = self.rfile.readline().decode()
        headers = {}
        while True:
            line = self.rfile.readline().decode().strip()
            if not line:
                break
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()
        if " 101 " not in status or headers.get("sec-websocket-accept") != accept_key(key):
            raise ConnectionError(status.strip())
        self.sock.settimeout(None)  # the timeout was for connecting; an idle link is no error
        self.got = queue.Queue()
        self.closed = threading.Event()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            while True:
                opcode, data = read_frame(self.rfile, limit=1 << 24)
                if opcode == 8:
                    break
                if opcode == 1:
                    self.got.put(json.loads(data))
        except (OSError, ValueError):
            pass
        self.closed.set()

    def send(self, **msg):
        self.sock.sendall(frame(json.dumps(msg).encode(), mask=True))

    def hello(self):
        self.send(t="hello", id=ID, ua=UA, caps={"motion": True, "tts": True, "vibrate": True}, screen=[1280, 720])

    def expect(self, t: str, timeout: float = 3.0) -> dict:
        """The next message of kind t (others are skipped)."""
        end = time.monotonic() + timeout
        while True:
            left = end - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"no {t!r} message")
            try:
                m = self.got.get(timeout=left)
            except queue.Empty:
                continue
            if m.get("t") == t:
                return m

    def close(self):
        try:
            self.sock.sendall(frame(b"\x03\xe8", opcode=8, mask=True))
        except OSError:
            pass
        self.sock.close()


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--url", default="ws://127.0.0.1:8782/ws")
    a = p.parse_args()
    phone = MockPhone(a.url)
    phone.hello()
    print("connected; Ctrl-C to stop")
    try:
        while True:
            phone.send(t="imu", acc=[0.0, 0.0, 9.81], gyro=[0.0, 0.0, 0.0])
            try:
                while True:
                    print(phone.got.get_nowait())
            except queue.Empty:
                pass
            time.sleep(0.05)
    except KeyboardInterrupt:
        phone.close()


if __name__ == "__main__":
    main()

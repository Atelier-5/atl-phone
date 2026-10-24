# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""wsserver.py — the phone's page and its WebSocket on one port (standard library only, no ROS here).

GET /        -> face.html (any file of web/ is served as is)
GET /ws      -> the WebSocket (RFC 6455, text frames only); ?key=... when the bridge has a pairing key

One phone at a time: a new phone takes over and the old one is closed.
A browser on another site is refused (Origin must match Host).
"""
import base64
import hashlib
import hmac
import os
import socket
import ssl
import struct
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 64 * 1024


def accept_key(key: str) -> str:
    return base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()


def frame(payload: bytes, opcode: int = 1, mask: bool = False) -> bytes:
    """One final frame. A server never masks; a client always does."""
    head = bytes([0x80 | opcode])
    n = len(payload)
    bit = 0x80 if mask else 0
    if n < 126:
        head += bytes([bit | n])
    elif n < 1 << 16:
        head += bytes([bit | 126]) + struct.pack(">H", n)
    else:
        head += bytes([bit | 127]) + struct.pack(">Q", n)
    if not mask:
        return head + payload
    key = os.urandom(4)
    return head + key + bytes(b ^ key[i % 4] for i, b in enumerate(payload))


def read_frame(rfile, limit: int = MAX_FRAME) -> tuple:
    """(opcode, payload) of the next frame; (8, b"") when the peer is gone. A phone's frames stay under MAX_FRAME."""
    head = rfile.read(2)
    if len(head) < 2:
        return 8, b""
    fin, opcode = head[0] & 0x80, head[0] & 0x0F
    masked, n = head[1] & 0x80, head[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", rfile.read(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", rfile.read(8))[0]
    if n > limit or not fin:
        raise ValueError("frame too big or fragmented")
    key = rfile.read(4) if masked else b""
    data = rfile.read(n)
    if masked:
        data = bytes(b ^ key[i % 4] for i, b in enumerate(data))
    return opcode, data


class Link:
    """The phone's connection, as the bridge sees it."""

    def __init__(self, wfile, peer):
        self.wfile, self.peer = wfile, peer
        self.lock = threading.Lock()
        self.open = True

    def send(self, text: str) -> bool:
        with self.lock:
            if not self.open:
                return False
            try:
                self.wfile.write(frame(text.encode()))
                self.wfile.flush()
                return True
            except OSError:
                self.open = False
                return False

    def close(self, code: int = 1000):
        with self.lock:
            if self.open:
                self.open = False
                try:
                    self.wfile.write(frame(struct.pack(">H", code), opcode=8))
                    self.wfile.flush()
                except OSError:
                    pass


class PhoneServer:
    """Serves web_dir and one phone. Callbacks run on the connection's thread:
    on_open(link), on_text(text), on_close(link)."""

    def __init__(self, web_dir, port, bind="0.0.0.0", key="", on_open=None, on_text=None, on_close=None,
                 cert=None, cert_key=None):
        self.key = key
        self.on_open = on_open or (lambda link: None)
        self.on_text = on_text or (lambda text: None)
        self.on_close = on_close or (lambda link: None)
        self.link = None
        self.lock = threading.Lock()
        self.httpd = ThreadingHTTPServer((bind, port), partial(make_handler(self), directory=str(web_dir)))
        self.httpd.daemon_threads = True
        self.scheme = "http"
        if cert:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert, cert_key)
            self.httpd.socket = ctx.wrap_socket(self.httpd.socket, server_side=True)
            self.scheme = "https"
        self.port = self.httpd.server_port

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True, name="phone-server").start()
        return self

    def stop(self):
        with self.lock:
            if self.link:
                self.link.close(1001)
        self.httpd.shutdown()
        self.httpd.server_close()

    def send(self, text: str) -> bool:
        link = self.link
        return bool(link and link.send(text))

    @property
    def connected(self) -> bool:
        return bool(self.link and self.link.open)

    def take_over(self, link):
        with self.lock:
            old, self.link = self.link, link
        if old:
            old.close(4000)  # another phone took over

    def release(self, link) -> bool:
        with self.lock:
            if self.link is not link:
                return False
            self.link = None
            return True


def make_handler(server: PhoneServer):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):  # quiet: the bridge logs what matters
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/":
                self.send_response(302)
                self.send_header("Location", "/face.html" + (f"?{url.query}" if url.query else ""))
                self.end_headers()
                return
            if url.path != "/ws":
                return super().do_GET()
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                return self.send_error(403, "foreign origin")
            given = parse_qs(url.query).get("key", [""])[0]
            if server.key and not hmac.compare_digest(given, server.key):
                return self.send_error(403, "wrong key")
            ws_key = self.headers.get("Sec-WebSocket-Key")
            if self.headers.get("Upgrade", "").lower() != "websocket" or not ws_key:
                return self.send_error(400, "not a WebSocket")
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept_key(ws_key))
            super(SimpleHTTPRequestHandler, self).end_headers()  # no Cache-Control on a 101
            self.wfile.flush()
            self.close_connection = True
            self.serve_ws()

        def serve_ws(self):
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            link = Link(self.wfile, self.client_address[0])
            server.take_over(link)
            server.on_open(link)
            try:
                while link.open:
                    opcode, data = read_frame(self.rfile)
                    if opcode == 1:
                        server.on_text(data.decode("utf-8", "replace"))
                    elif opcode == 9:
                        with link.lock:
                            self.wfile.write(frame(data, opcode=10))
                    elif opcode == 8:
                        break
            except (OSError, ValueError):
                pass
            finally:
                link.close()
                if server.release(link):
                    server.on_close(link)

    return Handler

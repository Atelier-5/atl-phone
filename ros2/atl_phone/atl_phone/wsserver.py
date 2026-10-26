# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""wsserver.py — the phone's page and its WebSocket on one port (standard library only, no ROS here).

GET /        -> face.html (any file of web/ is served as is)
GET /ws      -> the WebSocket (RFC 6455, text frames only); ?key=... when the bridge has a pairing key
GET /ws/mirror -> a mirror (the phone's Webots twin): it gets a copy of all the phone is sent, and what the bridge
                passes on (the phone's screen report); it only listens. This PC only, or with the pairing key
POST /report -> a phone check's report (check.html), from any phone; kept in the registry when the bridge has one
POST /api/summary -> the setup page's summary, into the registry: this PC only
GET /api/show.jpg -> the picture the person shows right now (Omi Assist, opt-in): this PC only, kept in memory only
GET /ca.crt  -> this PC's certificate authority, for a phone to install once (when the bridge has one)
GET /docs/   -> the architecture pack (docs/architecture: its landing page and diagrams), when the bridge has it
GET /api/state, POST /api/act -> the setup page's view of the phone and its tests: this PC only (loopback;
                a phone on USB is loopback too, through adb reverse, and it is the robot's own phone)

GuestServer, on its own https port: Übersetzen's guest page (talk.html) for a second phone on the home Wi-Fi, and its
WebSocket /ws/talk with the guest key (the robot's phone shows it as a QR code). Nothing else: no face, no API.

One phone at a time: a new phone takes over and the old one is closed; a frame the old one had already sent is dropped.
Mirrors: any number, beside the phone.
A browser on another site is refused (Origin must match Host).
"""
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import socket
import ssl
import struct
import threading
from functools import partial
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MIRROR = "/ws/mirror"   # contract.MIRROR (this module imports no ROS and nothing of the package)
GUEST_WS = "/ws/talk"   # the guest phone's WebSocket (GuestServer)
GUEST_FILES = ("talk.html", "guest.js", "talk.js", "texts.js")   # all a guest phone may load
MAX_MIRRORS = 4

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 128 * 1024   # a show frame (Omi) is the largest: a 320 px JPEG as base64 (protocol.MAX_FRAME)
MAX_POST = 64 * 1024


class Server(ThreadingHTTPServer):
    """A threading HTTP server whose TLS handshake happens in each request's own thread, with a time limit: done in
    accept(), on the only accepting thread, one silent connection would keep every other phone out."""
    daemon_threads = True
    HANDSHAKE_S = 10

    def use_tls(self, cert, cert_key):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, cert_key)
        self.socket = ctx.wrap_socket(self.socket, server_side=True, do_handshake_on_connect=False)

    def finish_request(self, request, client_address):
        if isinstance(request, ssl.SSLSocket):
            try:
                request.settimeout(self.HANDSHAKE_S)
                request.do_handshake()
                request.settimeout(None)
            except (OSError, ValueError):   # silent, too slow, or not TLS: this connection only (closed after)
                return
        super().finish_request(request, client_address)


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


def web_id(web_dir) -> str:
    """A fingerprint of the pages this bridge serves: a page loaded from an older bridge sees it change, and reloads.
    The files' bytes, except vendor/ (fixed versions, some 30 MB), where the names and sizes are enough."""
    h = hashlib.sha256()
    root = Path(web_dir)
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = f.relative_to(root).as_posix()
        h.update(rel.encode() + b"\0")
        h.update(str(f.stat().st_size).encode() if rel.startswith("vendor/") else f.read_bytes())
    return h.hexdigest()[:16]


def lan_address() -> str:
    """This PC's address on the local network (the phones' Wi-Fi), or 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))  # no packet is sent; it only picks the outgoing interface
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


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
                 cert=None, cert_key=None, api=None, ca=None, on_mirror=None, docs=None):
        """api, for the setup page: state() -> dict, act(dict) -> None (ValueError refuses it), report(dict) and
        summary(dict) -> None or what to answer (where it was kept).
        ca: the authority that signed cert, offered at /ca.crt (public: it is what a phone needs to trust the bridge).
        on_mirror(link): a mirror came; what it should know already (the panel, the last screen) goes to link.
        docs: the architecture pack's folder, served at /docs/ (static pages, as web_dir)."""
        self.key = key
        self.docs = str(docs) if docs and Path(docs).is_dir() else None
        self.ca = ca
        self.api = api
        self.on_open = on_open or (lambda link: None)
        self.on_text = on_text or (lambda text: None)
        self.on_close = on_close or (lambda link: None)
        self.on_mirror = on_mirror or (lambda link: None)
        self.link = None
        self.mirrors, self.mlock = [], threading.Lock()   # its own lock: the phone's is held while a message is delivered
        self.lock = threading.Lock()
        self.httpd = Server((bind, port), partial(make_handler(self), directory=str(web_dir)))
        self.scheme = "http"
        if cert:
            self.httpd.use_tls(cert, cert_key)
            self.scheme = "https"
        self.port = self.httpd.server_port

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True, name="phone-server").start()
        return self

    def stop(self):
        with self.lock:
            if self.link:
                self.link.close(1001)
        with self.mlock:
            for m in self.mirrors:
                m.close(1001)
        self.httpd.shutdown()
        self.httpd.server_close()

    def send(self, text: str) -> bool:
        """To the phone, and a copy to each mirror. True when the phone got it."""
        link = self.link
        self.send_mirrors(text)
        return bool(link and link.send(text))

    def send_phone(self, text: str) -> bool:
        """To the phone alone, no copy to the mirrors: Übersetzen's words (heard, translated)."""
        link = self.link
        return bool(link and link.send(text))

    @property
    def phone_local(self) -> bool:
        """The phone's link is this computer (USB with adb reverse, or the Pi's own USB) or https: its sound may come."""
        link = self.link
        return bool(link and link.open) and (self.scheme == "https" or ipaddress.ip_address(link.peer).is_loopback)

    def send_mirrors(self, text: str, local_only: bool = False) -> int:
        """To the mirrors only (the screen report, a prop): how many got it. local_only: to the mirrors on this computer
        only (loopback), as the setup page: a picture the person shows never goes further."""
        with self.mlock:
            self.mirrors = [m for m in self.mirrors if m.open]
            mirrors = [m for m in self.mirrors if not local_only or ipaddress.ip_address(m.peer).is_loopback]
        return sum(m.send(text) for m in mirrors)

    @property
    def mirror_count(self) -> int:
        return sum(1 for m in self.mirrors if m.open)

    @property
    def connected(self) -> bool:
        return bool(self.link and self.link.open)

    def take_over(self, link):
        with self.lock:  # waits for a message being delivered (deliver), so none of the old phone's lands after this
            old, self.link = self.link, link
        if old:
            old.close(4000)  # another phone took over

    def deliver(self, link, text: str) -> bool:
        """on_text, if link is still the phone. A frame read after a takeover is the old phone's: dropped."""
        with self.lock:
            if self.link is not link:
                return False
            self.on_text(text)
            return True

    def release(self, link) -> bool:
        with self.lock:
            if self.link is not link:
                return False
            self.link = None
            return True


def make_handler(server: PhoneServer):
    class Handler(SimpleHTTPRequestHandler):
        # vision's libraries: a module, and WebAssembly (which the browser compiles while it loads only with its own type)
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript",
                          ".wasm": "application/wasm", ".webmanifest": "application/manifest+json", ".tflite": "application/octet-stream", ".task": "application/octet-stream"}

        def log_message(self, *args):  # quiet: the bridge logs what matters
            pass

        def end_headers(self):
            # vendor/ holds fixed versions (some 30 MB): a phone keeps them a day; the rest is never cached
            self.send_header("Cache-Control", "max-age=86400" if self.path.startswith("/vendor/") else "no-store")
            super().end_headers()

        def translate_path(self, path):
            p = urlsplit(path).path
            if server.docs and (p == "/docs" or p.startswith("/docs/")):   # the pack, from its own folder
                web, self.directory = self.directory, server.docs
                try:
                    return super().translate_path(path[len("/docs"):])
                finally:
                    self.directory = web
            return super().translate_path(path)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/":
                self.send_response(302)
                self.send_header("Location", "/face.html" + (f"?{url.query}" if url.query else ""))
                self.end_headers()
                return
            if url.path == "/ca.crt":
                if not server.ca:
                    return self.send_error(404)
                with open(server.ca, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-x509-ca-cert")
                self.send_header("Content-Disposition", 'attachment; filename="atl-phone-ca.crt"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if url.path == "/api/state":
                if self.refused(local=True):
                    return
                return self.answer(200, server.api.state())
            if url.path == "/api/show.jpg":  # what the person shows (Omi): this PC only, while showing, never stored
                if self.refused(local=True):
                    return
                jpeg = server.api.show_frame() if hasattr(server.api, "show_frame") else None
                if not jpeg:
                    return self.send_error(404, "nothing shown")
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpeg)))
                self.end_headers()
                self.wfile.write(jpeg)
                return
            if url.path not in ("/ws", MIRROR):
                return super().do_GET()
            if self.refused():
                return
            given = parse_qs(url.query).get("key", [""])[0]
            if server.key and not hmac.compare_digest(given, server.key):
                return self.send_error(403, "wrong key")
            if url.path == MIRROR and not (server.key or ipaddress.ip_address(self.client_address[0]).is_loopback):
                return self.send_error(403, "this PC only")
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
            self.serve_mirror() if url.path == MIRROR else self.serve_ws()

        def refused(self, local=False) -> bool:
            """A browser on another site, or (local) someone not on this PC: refused, with the answer sent."""
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                self.send_error(403, "foreign origin")
                return True
            if local and not (server.api and ipaddress.ip_address(self.client_address[0]).is_loopback):
                self.send_error(403, "this PC only")
                return True
            return False

        def answer(self, status, payload=None):
            body = json.dumps(payload).encode() if payload is not None else b""
            self.send_response(status)
            if body:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in ("/report", "/api/act", "/api/summary") or not server.api:
                return self.send_error(404)
            if self.refused(local=path.startswith("/api/")):
                return
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= MAX_POST:
                return self.send_error(413)
            try:
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("not an object")
                if path == "/report":
                    if not isinstance(body.get("checks"), dict):
                        raise ValueError("not a phone check report")
                    saved = server.api.report(body)
                elif path == "/api/summary":
                    if not isinstance(body.get("text"), str):
                        raise ValueError("not a setup summary")
                    saved = server.api.summary(body)
                else:
                    saved = server.api.act(body)
            except ValueError as e:
                return self.answer(400, {"error": str(e)})
            self.answer(200, saved) if saved else self.answer(204)

        def serve_ws(self):
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            link = Link(self.wfile, self.client_address[0])
            server.take_over(link)
            server.on_open(link)
            try:
                while link.open:
                    opcode, data = read_frame(self.rfile)
                    if opcode == 1:
                        server.deliver(link, data.decode("utf-8", "replace"))
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

        def serve_mirror(self):
            """A mirror only listens: its frames are read and dropped (pings answered), so it cannot drive the phone."""
            link = Link(self.wfile, self.client_address[0])
            with server.mlock:
                server.mirrors = [m for m in server.mirrors if m.open]
                full = len(server.mirrors) >= MAX_MIRRORS
                if not full:
                    server.mirrors.append(link)
            if full:
                link.close(4001)
                return
            server.on_mirror(link)
            try:
                while link.open:
                    opcode, data = read_frame(self.rfile)
                    if opcode == 9:
                        with link.lock:
                            self.wfile.write(frame(data, opcode=10))
                    elif opcode == 8:
                        break
            except (OSError, ValueError):
                pass
            finally:
                link.close()

    return Handler


class GuestServer:
    """Übersetzen's guest phone, on its own https port (a phone's microphone needs a secure page, and the guest is on
    Wi-Fi): GUEST_FILES and the WebSocket GUEST_WS, with the guest key (key() gives it, "" while guests are not
    allowed). One guest at a time: a new one takes over. The guest only talks: on_text gets what it sends."""

    def __init__(self, web_dir, port, cert, cert_key, key, on_open=None, on_text=None, on_close=None, ca=None, bind="0.0.0.0"):
        self.key = key
        self.ca = ca
        self.on_open = on_open or (lambda link: None)
        self.on_text = on_text or (lambda text: None)
        self.on_close = on_close or (lambda link: None)
        self.link, self.lock = None, threading.Lock()
        self.httpd = Server((bind, port), partial(make_guest_handler(self), directory=str(web_dir)))
        if cert:   # always, from the bridge (a guest's microphone needs https); the tests go without
            self.httpd.use_tls(cert, cert_key)
        self.port = self.httpd.server_port

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True, name="guest-server").start()
        return self

    def stop(self):
        self.drop(1001)
        self.httpd.shutdown()
        self.httpd.server_close()

    def drop(self, code=4002):
        """The guest goes (a new guest key, guests no longer allowed)."""
        with self.lock:
            link, self.link = self.link, None
        if link:
            link.close(code)
            self.on_close(link)

    @property
    def connected(self) -> bool:
        return bool(self.link and self.link.open)

    def send(self, text: str) -> bool:
        link = self.link
        return bool(link and link.send(text))


def make_guest_handler(server: GuestServer):
    class Handler(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

        def log_message(self, *args):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_HEAD(self):
            self.send_error(405)

        def do_POST(self):
            self.send_error(404)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/":
                self.send_response(302)
                self.send_header("Location", "/talk.html" + (f"?{url.query}" if url.query else ""))
                self.end_headers()
                return
            if url.path == "/ca.crt" and server.ca:   # the authority, to trust this page once (no warning after)
                with open(server.ca, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-x509-ca-cert")
                self.send_header("Content-Disposition", 'attachment; filename="atl-phone-ca.crt"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if url.path.lstrip("/") in GUEST_FILES:
                return super().do_GET()
            if url.path != GUEST_WS:
                return self.send_error(404)
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                return self.send_error(403, "foreign origin")
            key, given = server.key(), parse_qs(url.query).get("k", [""])[0]
            if not key or not hmac.compare_digest(given, key):
                return self.send_error(403, "no guest now, or an old code")
            ws_key = self.headers.get("Sec-WebSocket-Key")
            if self.headers.get("Upgrade", "").lower() != "websocket" or not ws_key:
                return self.send_error(400, "not a WebSocket")
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept_key(ws_key))
            super(SimpleHTTPRequestHandler, self).end_headers()
            self.wfile.flush()
            self.close_connection = True
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            link = Link(self.wfile, self.client_address[0])
            with server.lock:
                old, server.link = server.link, link
            if old:
                old.close(4000)   # another guest took over
            server.on_open(link)
            try:
                while link.open:
                    opcode, data = read_frame(self.rfile)
                    if opcode == 1:
                        if server.link is link:
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
                with server.lock:
                    mine = server.link is link
                    if mine:
                        server.link = None
                if mine:
                    server.on_close(link)

    return Handler

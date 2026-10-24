# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import json
import queue
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from atl_phone.mock_phone import MockPhone
from atl_phone.wsserver import PhoneServer, accept_key

WEB = Path(__file__).resolve().parent.parent / "web"


@pytest.fixture
def server():
    events = queue.Queue()
    s = PhoneServer(WEB, 0, "127.0.0.1", key="k3y", on_open=lambda l: events.put("open"),
                    on_text=lambda t: events.put(json.loads(t)), on_close=lambda l: events.put("close")).start()
    s.events = events
    yield s
    s.stop()


def url(s, key="k3y"):
    return f"ws://127.0.0.1:{s.port}/ws?key={key}"


def test_accept_key():
    assert accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="  # RFC 6455, 1.3


def test_serves_the_pages(server):
    base = f"http://127.0.0.1:{server.port}"
    assert "face.js" in urllib.request.urlopen(base + "/?key=k3y", timeout=5).read().decode()  # / -> face.html
    assert "atl-phone-check" in urllib.request.urlopen(base + "/check.html", timeout=5).read().decode()


def test_both_ways(server):
    phone = MockPhone(url(server))
    assert server.events.get(timeout=3) == "open"
    phone.hello()
    assert server.events.get(timeout=3)["t"] == "hello"
    assert server.send(json.dumps({"t": "face", "expression": "happy"}))
    assert phone.expect("face") == {"t": "face", "expression": "happy"}
    big = "x" * 70000  # needs a 64-bit length
    assert server.send(json.dumps({"t": "say", "text": big}))
    assert phone.expect("say")["text"] == big
    phone.close()
    assert server.events.get(timeout=3) == "close"
    assert not server.connected


def test_an_idle_link_stays_open(server):
    phone = MockPhone(url(server), timeout=0.5)
    time.sleep(1.0)
    assert not phone.closed.is_set()
    assert server.send('{"t": "torch", "on": true}')
    assert phone.expect("torch")["on"] is True
    phone.close()


def test_a_new_phone_takes_over(server):
    first = MockPhone(url(server))
    second = MockPhone(url(server))
    assert first.closed.wait(3)
    assert server.connected
    assert server.send('{"t": "torch", "on": false}')
    assert second.expect("torch")["on"] is False
    second.close()


def test_wrong_key_is_refused(server):
    with pytest.raises(ConnectionError, match="403"):
        MockPhone(url(server, key="guess"))


def test_foreign_origin_is_refused(server):
    req = urllib.request.Request(url(server).replace("ws:", "http:"), headers={
        "Origin": "http://evil.example", "Upgrade": "websocket", "Connection": "Upgrade",
        "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==", "Sec-WebSocket-Version": "13"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=5)
    assert e.value.code == 403

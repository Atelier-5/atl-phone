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
from atl_phone.wsserver import PhoneServer, accept_key, web_id

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


def test_a_mirror_gets_a_copy_and_cannot_drive_the_phone(server):
    phone = MockPhone(url(server))
    assert server.events.get(timeout=3) == "open"
    twin = MockPhone(f"ws://127.0.0.1:{server.port}/ws/mirror?key=k3y")
    for _ in range(50):
        if server.mirror_count:
            break
        time.sleep(0.05)
    assert server.mirror_count == 1 and server.connected   # beside the phone: no takeover
    assert server.send(json.dumps({"t": "face", "expression": "love"}))
    assert phone.expect("face")["expression"] == "love" and twin.expect("face")["expression"] == "love"
    assert server.send_mirrors(json.dumps({"t": "prop", "name": "cup"})) == 1
    assert twin.expect("prop")["name"] == "cup"
    twin.send(t="touch", kind="tap", zone="left")            # dropped: only the phone is heard
    phone.send(t="battery", level=0.5, charging=False)
    assert server.events.get(timeout=3)["t"] == "battery"
    with pytest.raises(queue.Empty):
        phone.got.get(timeout=0.3)                           # the phone never got the prop
    twin.close()
    phone.close()


def test_a_shown_picture_reaches_only_the_mirrors_on_this_computer(server):
    twin = MockPhone(f"ws://127.0.0.1:{server.port}/ws/mirror?key=k3y")
    for _ in range(50):
        if server.mirror_count:
            break
        time.sleep(0.05)
    assert server.send_mirrors('{"t": "frame", "jpeg": ""}', local_only=True) == 1   # on this computer: as the setup page
    assert twin.expect("frame")["t"] == "frame"
    server.mirrors[0].peer = "192.168.1.20"                                           # a mirror on the Wi-Fi, with the key
    assert server.send_mirrors('{"t": "frame", "jpeg": ""}', local_only=True) == 0
    assert server.send_mirrors('{"t": "prop", "name": "cup"}') == 1                   # it still gets the rest
    twin.close()


def test_a_mirror_needs_the_key(server):
    with pytest.raises(OSError):
        MockPhone(f"ws://127.0.0.1:{server.port}/ws/mirror?key=nope")


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


def test_the_old_phone_is_not_heard_after_a_takeover(server):
    first = MockPhone(url(server))
    assert server.events.get(timeout=3) == "open"
    second = MockPhone(url(server))
    assert server.events.get(timeout=3) == "open"
    assert first.closed.wait(3)
    first.send(t="hello", ua="the old phone")  # sent before it saw the close: its thread is still reading
    second.send(t="hello", ua="the new phone")
    assert server.events.get(timeout=3)["ua"] == "the new phone"
    with pytest.raises(queue.Empty):
        server.events.get(timeout=0.5)
    second.close()


def test_no_authority_no_ca_crt(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"http://127.0.0.1:{server.port}/ca.crt", timeout=5)
    assert e.value.code == 404


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


class FakeApi:
    def __init__(self):
        self.acts, self.reports = [], []

    def state(self):
        return {"connected": False}

    def act(self, body):
        if body.get("topic") == "bad":
            raise ValueError("unknown topic")
        self.acts.append(body)

    def report(self, body):
        self.reports.append(body)
        return {"saved": "reports/X/2026-10-25-check.json"} if body.get("model") == "X" else None

    def summary(self, body):
        self.reports.append(body)
        return {"saved": "reports/X/2026-10-25-summary.txt"}


@pytest.fixture
def api_server():
    api = FakeApi()
    s = PhoneServer(WEB, 0, "127.0.0.1", api=api).start()
    s.fake = api
    yield s
    s.stop()


def http(s, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{s.port}{path}", data=data, headers=dict({"Content-Type": "application/json"}, **(headers or {})))
    return urllib.request.urlopen(req, timeout=5)


def test_setup_api(api_server):
    assert json.load(http(api_server, "/api/state")) == {"connected": False}
    assert http(api_server, "/api/act", {"topic": "expression", "value": "happy"}).status == 204
    assert api_server.fake.acts == [{"topic": "expression", "value": "happy"}]
    with pytest.raises(urllib.error.HTTPError) as e:
        http(api_server, "/api/act", {"topic": "bad"})
    assert e.value.code == 400 and "unknown topic" in e.value.read().decode()


def test_setup_api_refuses_other_sites(api_server):
    # a page on another site, open in this PC's browser, must not drive the robot's phone
    for path, body in [("/api/state", None), ("/api/act", {"topic": "torch", "value": True})]:
        with pytest.raises(urllib.error.HTTPError) as e:
            http(api_server, path, body, {"Origin": "http://evil.example"})
        assert e.value.code == 403
    assert api_server.fake.acts == []


def test_report(api_server):
    assert http(api_server, "/report", {"userAgent": "x", "checks": {"camera": {"ok": True}}}).status == 204
    assert api_server.fake.reports[0]["checks"] == {"camera": {"ok": True}}
    for bad in ([1], {"checks": 3}):
        with pytest.raises(urllib.error.HTTPError) as e:
            http(api_server, "/report", bad)
        assert e.value.code == 400


def test_report_says_where_it_was_kept_and_the_summary_is_this_pcs_only(api_server):
    r = http(api_server, "/report", {"model": "X", "checks": {}})
    assert r.status == 200 and json.load(r) == {"saved": "reports/X/2026-10-25-check.json"}
    r = http(api_server, "/api/summary", {"model": "X", "text": "Phone: X"})
    assert r.status == 200 and json.load(r)["saved"].endswith("summary.txt")
    for body, headers in [({"model": "X"}, None), ({"text": "t"}, {"Origin": "http://evil.example"})]:
        with pytest.raises(urllib.error.HTTPError) as e:
            http(api_server, "/api/summary", body, headers)
        assert e.value.code in (400, 403)


def test_no_api_no_routes(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        http(server, "/api/state")
    assert e.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as e:
        http(server, "/api/act", {"topic": "torch"})
    assert e.value.code == 404


def test_setup_api_is_for_this_pc_only():
    from atl_phone.wsserver import lan_address
    ip = lan_address()
    if ip == "127.0.0.1":
        pytest.skip("no network: nothing but loopback to call from")
    s = PhoneServer(WEB, 0, "0.0.0.0", api=FakeApi()).start()
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(f"http://{ip}:{s.port}/api/state", timeout=5)
        assert e.value.code == 403
        req = urllib.request.Request(f"http://{ip}:{s.port}/report", data=b'{"checks": {}}', headers={"Content-Type": "application/json"})
        assert urllib.request.urlopen(req, timeout=5).status == 204  # a phone on Wi-Fi may send its check
    finally:
        s.stop()


def test_the_pages_fingerprint_changes_with_a_page(tmp_path):
    (tmp_path / "vendor").mkdir()
    (tmp_path / "face.js").write_text("var a = 1;")
    (tmp_path / "vendor" / "big.wasm").write_bytes(b"x" * 100)
    first = web_id(tmp_path)
    assert first == web_id(tmp_path) and len(first) == 16
    (tmp_path / "face.js").write_text("var a = 2;")
    second = web_id(tmp_path)
    assert second != first
    (tmp_path / "vendor" / "big.wasm").write_bytes(b"y" * 100)   # vendor/: names and sizes only
    assert web_id(tmp_path) == second
    (tmp_path / "vendor" / "big.wasm").write_bytes(b"y" * 101)
    assert web_id(tmp_path) != second


def test_the_docs_are_served_beside_the_pages(tmp_path):
    (tmp_path / "index.html").write_text("<title>pack</title>")
    s = PhoneServer(WEB, 0, "127.0.0.1", docs=tmp_path).start()
    try:
        base = f"http://127.0.0.1:{s.port}"
        assert b"pack" in urllib.request.urlopen(base + "/docs/").read()
        assert b"pack" in urllib.request.urlopen(base + "/docs").read()        # redirected to /docs/
        assert b"pack" in urllib.request.urlopen(base + "/docs/index.html").read()
        assert b"<canvas" in urllib.request.urlopen(base + "/face.html").read()  # the pages stay where they were
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/docs/../../etc/passwd")                 # stays in the docs folder
    finally:
        s.stop()


def test_no_docs_folder_no_docs(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"http://127.0.0.1:{server.port}/docs/")
    assert e.value.code == 404

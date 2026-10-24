# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import json
import sys
import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import serve  # noqa: E402

UA = "Mozilla/5.0 (Linux; Android 8.0.0; SM-G950F) AppleWebKit/537.36 Chrome/119.0 Mobile Safari/537.36"


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(serve, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(serve, "ROOT", tmp_path)
    s = ThreadingHTTPServer(("127.0.0.1", 0), partial(serve.Handler, directory=str(serve.WEB)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}", tmp_path / "reports"
    s.shutdown()


def post(url, body: bytes):
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=5)


def test_model_in_prefers_the_client_hint():
    assert serve.model_in({"model": "SM-A505FN", "userAgent": "(Linux; Android 10; K)"}) == "SM-A505FN"
    assert serve.model_in({"model": " ../x ", "userAgent": UA}) == ".._x"
    assert serve.model_in({"userAgent": UA}) == "SM-G950F"


def test_model_of():
    assert serve.model_of(UA) == "SM-G950F"
    assert serve.model_of("Mozilla/5.0 (X11; Linux x86_64)") == "unknown"
    assert serve.model_of("(Linux; Android 9; ../../etc)") == ".._.._etc"


def test_serves_the_check_page(server):
    url, _ = server
    page = urllib.request.urlopen(url + "/check.html", timeout=5).read().decode()
    assert "atl-phone-check/0.1" in page


def test_keeps_a_report(server):
    url, reports = server
    report = {"userAgent": UA, "checks": {"camera": {"ok": True, "need": "core"}, "tts": {"ok": False, "need": "core"}}}
    assert post(url + "/report", json.dumps(report).encode()).status == 204
    (saved,) = reports.glob("*-SM-G950F.json")
    assert json.loads(saved.read_text()) == report
    assert serve.summary(report) == "SM-G950F: 1 yes, 1 no; core missing: tts"


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"checks": 3}'])
def test_refuses_what_is_not_a_report(server, body):
    url, reports = server
    with pytest.raises(urllib.error.HTTPError) as e:
        post(url + "/report", body)
    assert e.value.code == 400
    assert not reports.exists()


def test_refuses_a_huge_report(server):
    url, _ = server
    with pytest.raises(urllib.error.HTTPError) as e:
        post(url + "/report", b"x" * (serve.MAX_REPORT + 1))
    assert e.value.code == 413

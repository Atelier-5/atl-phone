# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""phone_health against a fake adb server (adb's own protocol) and a fake Chrome DevTools: no phone, no adb needed."""
import socket

import pytest

from atl_phone import mock_adb
from atl_phone import phone_health as ph

@pytest.fixture
def phone(monkeypatch):
    adb, chrome = mock_adb.start(8782)
    monkeypatch.setattr(ph, "ADB", adb.server_address)
    monkeypatch.setattr(ph, "CDP", chrome.server_address[1])
    monkeypatch.delenv("ANDROID_SERIAL", raising=False)
    yield adb, chrome
    mock_adb.stop(adb, chrome)


def test_it_reads_the_load_as_numbers_and_app_names(phone):
    h = ph.look()
    assert (h["model"], h["android"], h["free_mb"], h["total_mb"]) == ("ANE-LX1", "9", 1005, 3783)
    assert h["load"] == [41.8, 43.08, 42.62] and h["battery_c"] == 35.2 and h["thermal"] == 0 and h["tabs"] == 3
    assert [b["name"] for b in h["busy"]] == ["com.android.chrome", "com.android.chrome:privileged_process0"]   # not top
    assert h["memory"] == [{"mb": 256, "name": "com.huawei.hiai"}, {"mb": 156, "name": "com.facebook.orca"}]


def test_kill_and_stay_on_are_the_scripts_commands(phone):
    ph.kill()
    ph.stay_on(True)
    ph.stay_on(False)
    assert phone[0].shells == ["am kill-all", "svc power stayon usb", "svc power stayon false"]


def test_the_bridges_own_tab_is_never_offered_nor_closed(phone):
    assert ph.tabs(8782) == [{"id": "B", "title": "Some news"}, {"id": "C", "title": "https://example.com/x"}]
    assert ph.close(8782, ["A", "B", "nope", 7]) == 1 and phone[1].closed == ["B"]


def test_no_adb_server_says_so(monkeypatch):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    monkeypatch.setattr(ph, "ADB", ("127.0.0.1", port))
    with pytest.raises(ph.AdbError, match="no adb server"):
        ph.look()

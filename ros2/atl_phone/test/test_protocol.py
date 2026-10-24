# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import json

import pytest

from atl_phone import contract as c
from atl_phone import protocol as p


def parse(**m):
    return p.parse(json.dumps(m))


def test_hello():
    m = parse(t="hello", ua="x" * 500, caps={"motion": 1, "tts": 0}, screen=[1280, 720, 9])
    assert m == {"t": "hello", "id": "", "ua": "x" * 300, "model": "", "secure": True,
                 "caps": {"motion": True, "tts": False}, "screen": [1280, 720]}
    m = parse(t="hello", ua="", model=" Pixel 3 ", secure=False, id="0123456789abcdef")
    assert (m["model"], m["secure"], m["id"]) == ("Pixel 3", False, "0123456789abcdef")


@pytest.mark.parametrize("v", ["0123456789ABCDEF", "0123", "0123456789abcdef0", "../../etc/passwd!", 7, None])
def test_a_phone_id_is_16_hex_digits_or_nothing(v):
    assert p.phone_id(v) == ""


def test_camera():
    assert parse(t="camera", on=True, ok=True, size=[1280, 720.4]) == {"t": "camera", "on": True, "ok": True, "size": [1280, 720]}
    m = parse(t="camera", on=False, ok=False, error="NotAllowedError", torch=False)
    assert m == {"t": "camera", "on": False, "ok": False, "error": "NotAllowedError", "torch": False}
    assert parse(t="camera", on=True, ok=True, size=[1, 1], code="x" * 999)["code"] == "x" * 200
    assert "size" not in parse(t="camera", on=True, ok=True, torch=True)  # a torch report keeps the picture's size


def test_imu_is_clamped():
    m = parse(t="imu", acc=[0, 0, 1e9], gyro=[0.1, -0.2, 0.3])
    assert m == {"t": "imu", "acc": (0.0, 0.0, 200.0), "gyro": (0.1, -0.2, 0.3)}


def test_heading_wraps():
    assert parse(t="heading", deg=359.5)["deg"] == 359.5
    assert parse(t="heading", deg=360)["deg"] == 0.0
    assert parse(t="heading", deg=370)["deg"] == 10.0
    assert parse(t="heading", deg=-90)["deg"] == 270.0


def test_clamped_numbers_stay_floats():
    # min(max(370.0, 0), 360) is the int 360: rclpy publishes an int in a float field by aborting the process
    m = parse(t="imu", acc=[1e9, -1e9, 3], gyro=[0, 0, 0])
    assert all(type(v) is float for v in m["acc"] + m["gyro"])
    assert type(parse(t="battery", level=7)["level"]) is float
    assert type(p.gaze(5, 0)["x"]) is float


def test_touch():
    assert parse(t="touch", kind="tap", zone="centre") == {"t": "touch", "kind": "tap", "zone": "centre"}
    assert parse(t="touch", kind="swipe", zone="right", dir="down")["dir"] == "down"


@pytest.mark.parametrize("raw", [
    "nope", "[1]", '{"t": "teleport"}',
    '{"t": "imu", "acc": [0, 0], "gyro": [0, 0, 0]}',
    '{"t": "imu", "acc": [0, 0, NaN], "gyro": [0, 0, 0]}',
    '{"t": "imu", "acc": [true, 0, 0], "gyro": [0, 0, 0]}',
    '{"t": "touch", "kind": "tap", "zone": "elsewhere"}',
    '{"t": "touch", "kind": "swipe", "zone": "left"}',
    '{"t": "battery", "level": "full"}',
])
def test_refuses(raw):
    with pytest.raises(ValueError):
        p.parse(raw)


def test_to_the_phone():
    assert p.face("love") == {"t": "face", "expression": "love"}
    assert p.gaze(3, -3) == {"t": "gaze", "x": 1.0, "y": -1.0}
    assert p.color(1, 0.5, 0) == {"t": "color", "rgb": [255, 128, 0]}
    assert p.torch(1) == {"t": "torch", "on": True}
    assert p.camera(0) == {"t": "camera", "on": False}
    assert p.vibrate(-5) == {"t": "vibrate", "ms": 0}
    assert p.vibrate(10 ** 6) == {"t": "vibrate", "ms": c.MAX_VIBRATE}
    with pytest.raises(ValueError):
        p.face("grumpy")


def test_say():
    assert p.say("Hello") == {"t": "say", "text": "Hello", "lang": "en"}
    assert p.say("Hallo", "de")["lang"] == "de"
    assert p.say('{"text": "Salut", "lang": "fr"}') == {"t": "say", "text": "Salut", "lang": "fr"}
    assert len(p.say("a" * 1000)["text"]) == c.MAX_SAY
    for bad in ["   ", '{"text": "Hi", "lang": "xx"}', "{broken"]:
        with pytest.raises(ValueError):
            p.say(bad)


def test_every_expression_is_on_the_page():
    from pathlib import Path
    page = (Path(__file__).resolve().parent.parent / "web" / "face.js").read_text()
    for e in c.EXPRESSIONS:
        assert f"  {e}: " in page, e


def test_open_page():
    assert p.open_page("check.html") == {"t": "open", "page": "check.html"}
    with pytest.raises(ValueError):
        p.open_page("https://evil.example/")

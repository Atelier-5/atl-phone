# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import json
import re
from pathlib import Path

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
    '{"t": "faces", "faces": "two"}',
    '{"t": "faces", "faces": [3]}',
    '{"t": "faces", "faces": [{"x": 0, "y": 0}]}',
    '{"t": "code", "text": "  "}',
])
def test_refuses(raw):
    with pytest.raises(ValueError):
        p.parse(raw)


def test_faces_carry_only_where_they_are():
    m = parse(t="faces", faces=[{"x": 2, "y": -0.5, "size": 0.3, "familiar": 2, "descriptor": [0.1] * 128, "jpeg": "..."}])
    assert m == {"t": "faces", "n": 1, "faces": [{"x": 1.0, "y": -0.5, "size": 0.3, "familiar": 2}]}
    assert parse(t="faces", faces=[])["n"] == 0
    many = parse(t="faces", faces=[{"x": 0, "y": 0, "size": 0.1, "familiar": 99}] * 20)
    assert many["n"] == c.MAX_FACES and many["faces"][0]["familiar"] == c.MAX_FACES
    assert parse(t="faces", faces=[{"x": 0, "y": 0, "size": 0.1}])["faces"][0]["familiar"] is None


def test_look_and_code():
    assert parse(t="look", on=True, ok=False, error="NotAllowedError", familiar=1) == {
        "t": "look", "on": True, "ok": False, "familiar": True, "error": "NotAllowedError"}
    assert parse(t="code", text=" atl-guardian:owner ") == {"t": "code", "text": "atl-guardian:owner"}
    assert p.look(True, True) == {"t": "look", "on": True, "familiar": True}
    assert p.look(False, True) == {"t": "look", "on": False, "familiar": False}
    assert p.forget() == {"t": "forget"}


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


def test_web_fingerprint():
    assert p.web("0123456789abcdef") == {"t": "web", "id": "0123456789abcdef"}
    for bad in ("", "0123", "0123456789ABCDEF", "<script>abcdefgh", None):
        with pytest.raises(ValueError):
            p.web(bad)


def test_the_face_reloads_for_new_pages():
    page = (Path(__file__).resolve().parent.parent / "web" / "face.js").read_text()
    assert "m.t === 'web'" in page and "location.replace" in page


def test_open_page():
    assert p.open_page("check.html") == {"t": "open", "page": "check.html"}
    with pytest.raises(ValueError):
        p.open_page("https://evil.example/")
    assert p.open_page("face.html", "portrait") == {"t": "open", "page": "face.html", "layout": "portrait"}
    with pytest.raises(ValueError):
        p.open_page("face.html", "sideways")


def test_panel():
    assert p.panel('{"mode": "mouth"}') == {"t": "panel", "mode": "mouth"}
    m = p.panel(json.dumps({"mode": "pad", "buttons": [{"id": "fwd", "label": "Forward, quickly!", "color": [2, 0.5, -1]}] * 20}))
    assert len(m["buttons"]) == c.MAX_BUTTONS and m["buttons"][0] == {"id": "fwd", "label": "Forward, qui", "rgb": [255, 128, 0]}
    assert p.panel('{"mode": "pad", "buttons": [{"id": "x"}]}')["buttons"] == [{"id": "x", "label": "x", "rgb": [64, 217, 255]}]
    for bad in ['{"mode": "video"}', "[]", "{broken", '{"mode": "pad", "buttons": [{"id": "a b"}]}',
                '{"mode": "pad", "buttons": [{"id": "a", "color": [1, 0]}]}', '{"mode": "pad", "buttons": "a"}']:
        with pytest.raises(ValueError):
            p.panel(bad)


def test_pad_from_the_phone():
    assert parse(t="pad", id="b") == {"t": "pad", "id": "b"}
    for bad in ["", "a" * 21, "<b>", None, 3]:
        with pytest.raises(ValueError):
            parse(t="pad", id=bad)


def test_the_face_has_the_default_panel():
    from pathlib import Path
    page = (Path(__file__).resolve().parent.parent / "web" / "face.js").read_text()
    for b in p.panel(json.dumps(c.DEFAULT_PANEL))["buttons"]:
        assert f"{{ id: '{b['id']}', label: '{b['label']}', rgb: {b['rgb']} }}" in page, b


def test_see():
    m = p.see('{"camera": "back", "find": ["markers", "blobs", "markers"], "blob": {"hue": 400, "tol": 0}, "marker_cm": 1000}')
    assert m == {"t": "see", "camera": "back", "find": ["markers", "blobs"], "blob": {"hue": 40.0, "tol": 1.0}, "marker_cm": 100.0}
    assert p.see('{"find": []}')["find"] == [] and p.see('{"find": ["faces"], "fov_deg": 5}')["fov_deg"] == 20.0
    for bad in ['{"find": ["x-ray"]}', '{"camera": "side"}', '{"find": "faces"}', "[]", "{broken"]:
        with pytest.raises(ValueError):
            p.see(bad)


def test_vision_from_the_phone():
    m = parse(t="markers", camera="back", markers=[{"id": 7, "x": 3, "y": 0, "size": 0.2, "distance_m": 0.3, "yaw_deg": 400, "img": "..."}] * 20)
    assert len(m["markers"]) == c.MAX_ITEMS and m["markers"][0] == {"x": 1.0, "y": 0.0, "id": 7, "size": 0.2, "distance_m": 0.3, "yaw_deg": 180.0}
    assert parse(t="blobs", blobs=[{"x": 0.5, "y": -0.5, "size": 0.1, "rgb": [1, 2, 3]}]) == {
        "t": "blobs", "camera": "front", "blobs": [{"x": 0.5, "y": -0.5, "size": 0.1}]}
    o = parse(t="objects", camera="front", objects=[{"label": "cup", "score": 0.9, "x": 0, "y": 0, "w": 0.2, "h": 0.3, "distance_m": None}])
    assert o["objects"][0] == {"x": 0.0, "y": 0.0, "label": "cup", "score": 0.9, "w": 0.2, "h": 0.3, "distance_m": None}
    assert parse(t="hands", hands=[{"x": 0, "y": 0, "gesture": "thumbs_up"}])["hands"][0]["gesture"] == "thumbs_up"
    for bad in [dict(t="objects", objects=[{"label": "name: Alice", "score": 1, "x": 0, "y": 0, "w": 0, "h": 0}]),
                dict(t="hands", hands=[{"x": 0, "y": 0, "gesture": "wave"}]), dict(t="markers", markers="7"),
                dict(t="blobs", camera="side", blobs=[])]:
        with pytest.raises(ValueError):
            p.parse(json.dumps(bad))


def test_the_see_report_and_the_panel_mode_from_the_phone():
    m = parse(t="see", on=True, ok=True, camera="back", find=["markers", "x"], ms={"markers": 12.4, "secret": 1}, backend="gpu")
    assert m == {"t": "see", "on": True, "ok": True, "camera": "back", "find": ["markers"], "ms": {"markers": 12}, "backend": "gpu"}
    assert parse(t="panel", mode="sensors") == {"t": "panel", "mode": "sensors"}
    assert parse(t="faces", faces=[], period=250.7)["period"] == 250
    with pytest.raises(ValueError):
        parse(t="panel", mode="disco")


def test_panel_menu():
    m = p.panel('{"mode": "pad", "menu": ["pad", "mouth", "pad"]}')
    assert m["menu"] == ["pad", "mouth"]
    for bad in ['{"mode": "pad", "menu": []}', '{"mode": "pad", "menu": ["tv"]}']:
        with pytest.raises(ValueError):
            p.panel(bad)
    assert p.panel(json.dumps({"mode": "pad", "buttons": c.THYMIO_PAD}))["buttons"][0]["label"] == "▲"


def test_panel_lang_and_the_tour():
    assert p.panel('{"mode": "mouth", "lang": "de"}')["lang"] == "de"
    assert p.panel('{"mode": "mouth", "lang": "auto"}')["lang"] == "auto"
    assert "lang" not in p.panel('{"mode": "mouth"}')
    with pytest.raises(ValueError):
        p.panel('{"mode": "mouth", "lang": "xx"}')
    assert p.tour("de") == {"t": "tour", "lang": "de"}
    with pytest.raises(ValueError):
        p.tour("xx")


def texts() -> dict:
    """web/texts.js: the words of the page and of the Webots twin (strict JSON after "var TEXTS =")."""
    js = (Path(__file__).resolve().parents[1] / "web" / "texts.js").read_text()
    return json.loads(js[js.index("var TEXTS = {") + 12:js.rindex("}") + 1])


def test_the_tour_says_every_step_in_every_language():
    js = (Path(__file__).resolve().parents[1] / "web" / "omi.js").read_text()
    steps = re.findall(r"\{ k: '(\w+)'", js[js.index("var TOUR ="):])
    assert set(steps + ["card"]) == set(c.TOUR_STEPS)
    for lang in ("en", "fr", "de"):
        assert set(texts()["tour"][lang]) == set(c.TOUR_STEPS), lang


def test_every_screen_key_has_its_words_in_every_language():
    t = texts()
    for lang in c.LANGS:
        for k in c.SCREEN_TOASTS:
            assert k == "time" or t["omi"][lang].get(k), (lang, k)
        assert set(t["mode"][lang]) >= set(c.PANEL_MODES) | set(c.TILES) | {"face", "showing"}, lang
    assert set(t["what"]) == set(c.OBJECTS)


def test_the_screen_report_carries_keys_never_free_text():
    m = p.parse(json.dumps({"t": "screen", "lang": "de", "mode": "magnify", "expression": "love", "style": "tiles", "menu": 1,
                            "tiles": ["time", "face", "<b>", 3], "hi": "time", "toast": "is", "arg": "cup", "note": "pill",
                            "badge": True, "speaking": True}))
    assert m == {"t": "screen", "lang": "de", "mode": "magnify", "expression": "love", "style": "tiles", "menu": True,
                 "tiles": ["time", "face"], "hi": "time", "toast": "is", "arg": "cup", "note": "pill", "badge": True,
                 "allowed": False, "speaking": True, "sensors": {}}
    assert p.parse(json.dumps({"t": "screen", "toast": "tour.bye"}))["toast"] == "tour.bye"
    for toast, arg in (("Lieber Herr Muster, Ihre Rechnung", ""), ("tour.nope", ""), ("reading", "cup"), ("is", "Muster")):
        r = p.parse(json.dumps({"t": "screen", "toast": toast, "arg": arg}))
        assert r["arg"] == "" and r["toast"] in ("", "reading", "is"), toast
    bad = p.parse(json.dumps({"t": "screen", "lang": "xx", "mode": "film", "expression": "evil", "hi": "a b", "note": "<i>"}))
    assert (bad["lang"], bad["mode"], bad["expression"], bad["hi"], bad["note"]) == ("en", "mouth", "neutral", "", "")
    assert p.prop("cup") == {"t": "prop", "name": "cup"}
    with pytest.raises(ValueError):
        p.prop("cake")


def test_the_sensors_panel_numbers_go_but_never_a_location():
    s = p.parse(json.dumps({"t": "screen", "mode": "sensors", "sensors": {
        "battery": 0.834, "charging": 1, "heading": 361.4, "acc": [0.04, 9.61, 2.0], "lat": 48.1, "lon": 11.5, "where": "home"}}))
    assert s["sensors"] == {"battery": 0.83, "charging": True, "heading": 360, "acc": [0.0, 9.6, 2.0]}
    assert p.parse(json.dumps({"t": "screen", "sensors": {"battery": "full", "acc": [1, 2]}}))["sensors"] == {}
    assert p.parse(json.dumps({"t": "screen", "sensors": "48.1, 11.5"}))["sensors"] == {}


def test_the_face_knows_every_panel_mode_and_vision_every_gesture():
    from pathlib import Path
    web = Path(__file__).resolve().parent.parent / "web"
    assert f"var MODES = {list(c.PANEL_MODES)};".replace('"', "'") in (web / "face.js").read_text()
    see = (web / "see.js").read_text()
    for g in c.GESTURES:
        assert f"'{g}'" in see, g


def test_tiles_and_a_programs_own_entries():
    m = p.panel(json.dumps({"mode": "mouth", "style": "tiles", "menu": c.OMI_MENU + ["time", {"id": "tea", "label": {"de": "Tee", "xx": 1}, "icon": "🍵🍵🍵🍵🍵"}]}))
    assert m["style"] == "tiles" and m["menu"][:len(c.OMI_MENU)] == c.OMI_MENU
    assert m["menu"][-1] == {"id": "tea", "label": {"de": "Tee"}, "icon": "🍵🍵🍵🍵"} and len(m["menu"]) == len(c.OMI_MENU) + 1
    assert len(p.panel(json.dumps({"mode": "mouth", "menu": [{"id": f"x{i}"} for i in range(20)]}))["menu"]) == c.MAX_MENU
    for bad in [{"mode": "mouth", "style": "big"}, {"mode": "mouth", "menu": [{"id": "a b"}]}, {"mode": "mouth", "menu": [3]},
                {"mode": "mouth", "menu": [{"id": "a", "label": {"xx": "?"}}]}]:
        with pytest.raises(ValueError):
            p.panel(json.dumps(bad))


def test_omi_messages_from_the_phone():
    assert parse(t="menu", id="time") == {"t": "menu", "id": "time"}
    assert parse(t="answer", note="r1", id="done") == {"t": "answer", "note": "r1", "id": "done"}
    assert parse(t="read", ok=True, lines=3.7, chars=-2, ms=900, text="never kept") == {"t": "read", "ok": True, "lines": 3, "chars": 0, "ms": 900}
    assert parse(t="what", ok=True, label="cup", score=0.83, ms=1200)["label"] == "cup"
    assert parse(t="what", ok=False, label="cup")["label"] is None
    assert parse(t="what", ok=True, label=None)["label"] is None   # it looked, and knew nothing there
    assert parse(t="show", on=1) == {"t": "show", "on": True}
    m = parse(t="see", on=True, ok=True, find=["faces"], follow=True, target={"kind": "hands", "x": 3, "y": -0.2})
    assert m["follow"] is True and m["target"] == {"kind": "hands", "x": 1, "y": -0.2}
    assert "target" not in parse(t="see", target={"kind": "blobs", "x": 0, "y": 0})
    for bad in [dict(t="menu", id="no spaces"), dict(t="what", ok=True, label="unicorn")]:
        with pytest.raises(ValueError):
            parse(**bad)


def test_show_frames_are_small_jpegs_only():
    import base64
    jpeg = b"\xff\xd8" + b"\0" * 100 + b"\xff\xd9"
    assert parse(t="frame", jpeg=base64.b64encode(jpeg).decode())["jpeg"] == jpeg
    for bad in [base64.b64encode(b"\x89PNG....").decode(), "not base64!", base64.b64encode(b"\xff\xd8" + b"\0" * p.MAX_FRAME).decode(), 3]:
        with pytest.raises(ValueError):
            parse(t="frame", jpeg=bad)


def test_omi_messages_to_the_phone():
    n = p.note(json.dumps({"id": "r1", "text": " x " * 200, "buttons": [{"id": "done", "label": {"de": "Erledigt"}}, {"id": "b"}, {"id": "c"}, {"id": "d"}]}))
    assert n["id"] == "r1" and len(n["text"]) <= c.MAX_SAY and len(n["buttons"]) == c.MAX_NOTE_BUTTONS and n["say"] is True
    assert n["buttons"][0] == {"id": "done", "label": {"de": "Erledigt"}} and n["buttons"][1]["label"] == "b"
    assert p.note('{"text": ""}') == {"t": "note", "id": "note", "text": "", "say": True, "buttons": []}
    assert p.ask("read", "", "de") == {"t": "read", "lang": "de"}
    assert p.ask("what", '{"lang": "fr"}') == {"t": "what", "lang": "fr"}
    assert p.show(False, True) == {"t": "show", "allowed": False, "on": False}
    assert p.see('{"find": ["faces"], "follow": true}')["follow"] is True and "follow" not in p.see('{"find": []}')
    with pytest.raises(ValueError):
        p.ask("what", '{"lang": "xx"}')


def test_the_phone_knows_every_tile_and_names_every_object():
    from pathlib import Path
    web = Path(__file__).resolve().parent.parent / "web"
    assert f"var TILES = {list(c.TILES)};".replace('"', "'") in (web / "face.js").read_text()
    what = texts()["what"]   # English, French, German, each said with its article
    assert sorted(what) == sorted(c.OBJECTS)
    for label, row in what.items():
        assert len(row) == 3 and all(isinstance(w, str) and w for w in row), label

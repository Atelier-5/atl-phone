# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""The registry of phones tested: one entry per model, one file per model and day, the notes kept."""
import json

from atl_phone.registry import Registry, slug

REPORT = {"phone_id": "ecdaf06c4d54da5f", "userAgent": "Mozilla/5.0 (Linux; Android 10; K) Chrome/125",
          "checks": {"android": {"ok": True, "note": "Android 10", "need": "info"},
                     "screen": {"ok": True, "note": "360×760 @3x", "need": "core", "tested": False},
                     "webgl": {"ok": True, "note": "ANGLE (ARM, Mali-T830)", "need": "nice"},
                     "faces": {"ok": True, "note": "115 ms per search · gpu", "need": "nice", "tested": True},
                     "motion": {"ok": False, "note": "", "need": "core", "tested": True},
                     "light": {"ok": False, "note": "flag", "need": "later"}}}


def test_a_check_and_a_summary_make_one_entry(tmp_path):
    reg = Registry(tmp_path)
    at = 1792913000.0
    p = reg.check(REPORT, "ANE-LX1", at)
    reg.check(REPORT, "ANE-LX1", at + 60)  # Send tapped twice: still one file that day
    assert p.name.endswith("-check.json") and len(list((tmp_path / "ANE-LX1").glob("*-check.json"))) == 1
    data = json.loads((tmp_path / "phones.json").read_text())
    e = data["phones"]["ANE-LX1"]
    assert e["ids"] == ["ecdaf06c4d54da5f"] and e["details"]["gpu"].startswith("ANGLE") and e["details"]["faces"].startswith("115 ms")
    assert e["check"]["verdict"] == "core missing: motion" and e["check"]["missing"]["later"] == ["light"]
    e["notes"] = "less steady than the A50"
    (tmp_path / "phones.json").write_text(json.dumps(data))
    reg.summary({"text": "Phone: ANE-LX1\n[x] face", "results": {"face": True, "look": False, "code": None, "evil": "<x>"}}, "ANE-LX1", at)
    e = json.loads((tmp_path / "phones.json").read_text())["phones"]["ANE-LX1"]
    assert e["notes"] == "less steady than the A50"
    assert e["summary"]["works"] == ["face"] and e["summary"]["fails"] == ["look"] and e["summary"]["untested"] == ["code"]
    assert (tmp_path / "ANE-LX1" / (e["summary"]["day"] + "-summary.txt")).read_text().startswith("Phone: ANE-LX1")
    md = (tmp_path / "phones.md").read_text()
    assert "| ANE-LX1 | Android 10 |" in md and "less steady than the A50" in md and "look / code" in md


def test_a_model_is_a_safe_folder_name(tmp_path):
    assert slug("../../etc") == "etc" and slug("SM-A505FN") == "SM-A505FN" and slug("") == "unknown"
    assert Registry(tmp_path).check({"checks": {}}, "../x").parent == tmp_path / "x"

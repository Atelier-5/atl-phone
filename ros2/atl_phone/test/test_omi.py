# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import json
from datetime import datetime

import pytest

from atl_phone import omi

SUN = datetime(2026, 10, 25, 9, 0)   # a Sunday


def test_clean():
    rs = omi.clean([{"text": " Tabletten ", "at": "09:00"}, {"id": "r1", "text": "Wasser", "at": "10:30", "days": ["sun", "xx"]},
                    {"id": "r1", "text": "again", "at": "11:00"}])
    assert [r["id"] for r in rs] == ["r1", "r2", "r3"] or len({r["id"] for r in rs}) == 3
    assert rs[0]["text"] == "Tabletten" and rs[1]["days"] == ["sun"]
    for bad in ["x", [{"text": "", "at": "09:00"}], [{"text": "a", "at": "25:00"}], [{"text": "a", "at": "9:00"}], [3]]:
        with pytest.raises(ValueError):
            omi.clean(bad)
    assert len(omi.clean([{"text": "a", "at": "09:00"}] * 50)) == omi.MAX_REMINDERS


def test_due_once_on_its_day_within_five_minutes():
    r = omi.Reminders()
    r.set([{"id": "pill", "text": "Tabletten", "at": "09:00"}, {"id": "mon", "text": "Montag", "at": "09:00", "days": ["mon"]}])
    assert r.due(SUN.replace(hour=8, minute=59)) == []
    assert [x["id"] for x in r.due(SUN.replace(minute=2))] == ["pill"]
    assert r.due(SUN.replace(minute=3)) == []                         # once
    r2 = omi.Reminders()
    r2.set([{"id": "pill", "text": "Tabletten", "at": "09:00"}])
    assert r2.due(SUN.replace(minute=6)) == []                        # never hours (or minutes) late
    assert [x["id"] for x in r.due(datetime(2026, 10, 26, 9, 0))] == ["pill", "mon"]   # the next day, Monday


def test_later_comes_again_and_answers_are_logged(tmp_path):
    r = omi.Reminders(tmp_path)
    r.set([{"id": "pill", "text": "Tabletten", "at": "09:00"}])
    assert r.due(SUN)
    r.answer("pill", "later", SUN)
    assert r.due(SUN.replace(minute=9)) == []
    assert [x["id"] for x in r.due(SUN.replace(minute=10))] == ["pill"]
    r.answer("pill", "done", SUN.replace(minute=11))
    r.answer("nobody", "done", SUN)                                   # not a reminder: nothing
    lines = [json.loads(x) for x in (tmp_path / "answers.jsonl").read_text().splitlines()]
    assert [x["answer"] for x in lines] == ["later", "done"] and lines[1]["text"] == "Tabletten"
    assert omi.Reminders(tmp_path).items == r.items                   # kept on disk


def test_next():
    r = omi.Reminders()
    r.set([{"id": "a", "text": "A", "at": "08:00"}, {"id": "b", "text": "B", "at": "20:00", "days": ["mon"]}])
    assert r.next(SUN) == {"id": "a", "text": "A", "at": "2026-10-26T08:00"}
    r.due(SUN.replace(hour=8, minute=0)) and None
    assert omi.Reminders().next(SUN) is None


def test_note_for():
    n = omi.note_for({"id": "pill", "text": "Tabletten"}, "de")
    assert n["_say"] == "Eine Erinnerung: Tabletten" and [b["id"] for b in n["buttons"]] == ["done", "later"]
    assert n["buttons"][0]["label"]["de"] == "Erledigt" and n["say"] is False

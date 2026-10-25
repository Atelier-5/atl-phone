# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""omi — Omi Assist's reminders, in plain Python (no ROS): what is due, done, or put off.

A reminder: {"id", "text", "at": "HH:MM", "days": ["mon", ...] (none: every day)}. At its time on its day it is due
once; the person answers on the phone: "done" (logged), or "later" (due again LATER_MIN minutes on). The assistant sets
them from the PC (the setup page); they are kept in <folder>/reminders.json, the answers in <folder>/answers.jsonl.
"""
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
LATER_MIN = 10
MAX_REMINDERS = 20
TEXT = {  # the note card's buttons, and what is said
    "en": {"done": "Done", "later": "Later", "remind": "A reminder:", "hello": "Nice to see you! How can I help you?"},
    "fr": {"done": "Fait", "later": "Plus tard", "remind": "Un rappel :", "hello": "Ça me fait plaisir de te voir ! Comment puis-je t’aider ?"},
    "de": {"done": "Erledigt", "later": "Später", "remind": "Eine Erinnerung:", "hello": "Schön, dich zu sehen! Wie kann ich dir helfen?"},
}


def clean(items) -> list:
    """The reminders as the setup page sends them, checked: a list of {id, text, at, days}."""
    if not isinstance(items, list):
        raise ValueError("reminders: a list")
    out, ids = [], set()
    for r in items[:MAX_REMINDERS]:
        if not isinstance(r, dict):
            raise ValueError("a reminder is {text, at, days}")
        text = str(r.get("text", "")).strip()[:150]
        at = str(r.get("at", ""))
        if not text or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", at):
            raise ValueError("a reminder needs a text and a time HH:MM")
        days = [d for d in r.get("days") or [] if d in DAYS]
        rid = str(r.get("id") or "") if re.fullmatch(r"[A-Za-z0-9_-]{1,20}", str(r.get("id") or "")) else ""
        n = 1
        while not rid or rid in ids:
            rid, n = f"r{len(out) + n}", n + 1
        ids.add(rid)
        out.append({"id": rid, "text": text, "at": at, "days": days})
    return out


class Reminders:
    def __init__(self, folder=None):
        self.dir = Path(folder) if folder else None
        self.items, self.fired, self.later = [], {}, {}   # fired: id -> the day it was due; later: id -> when again
        self.log = []
        if self.dir and (self.dir / "reminders.json").exists():
            try:
                self.items = clean(json.loads((self.dir / "reminders.json").read_text()))
            except (OSError, ValueError):
                self.items = []

    def set(self, items):
        self.items = clean(items)
        known = {r["id"] for r in self.items}
        self.fired = {k: v for k, v in self.fired.items() if k in known}
        self.later = {k: v for k, v in self.later.items() if k in known}
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / "reminders.json").write_text(json.dumps(self.items, indent=2, ensure_ascii=False) + "\n")

    def due(self, now: datetime) -> list:
        """The reminders due now (each once): their time today, or a later one that came."""
        out, today = [], now.strftime("%Y-%m-%d")
        for r in self.items:
            again = self.later.get(r["id"])
            if again and now >= again:
                del self.later[r["id"]]
                out.append(r)
                continue
            if self.fired.get(r["id"]) == today or (r["days"] and DAYS[now.weekday()] not in r["days"]):
                continue
            h, m = map(int, r["at"].split(":"))
            at = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if at <= now < at + timedelta(minutes=5):   # up to 5 min late (the PC was busy), never hours later
                self.fired[r["id"]] = today
                out.append(r)
        return out

    def answer(self, rid: str, button: str, now: datetime):
        r = next((x for x in self.items if x["id"] == rid), None)
        if not r:
            return
        if button == "later":
            self.later[rid] = now + timedelta(minutes=LATER_MIN)
        entry = {"when": now.isoformat(timespec="seconds"), "id": rid, "text": r["text"], "answer": button}
        self.log = (self.log + [entry])[-20:]
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)
            with open(self.dir / "answers.jsonl", "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def next(self, now: datetime):
        """The next reminder to come, and when."""
        best = None
        for r in self.items:
            again = self.later.get(r["id"])
            cands = [again] if again else []
            h, m = map(int, r["at"].split(":"))
            for d in range(8):
                day = now + timedelta(days=d)
                at = day.replace(hour=h, minute=m, second=0, microsecond=0)
                if (not r["days"] or DAYS[day.weekday()] in r["days"]) and at > now and not (d == 0 and self.fired.get(r["id"]) == now.strftime("%Y-%m-%d")):
                    cands.append(at)
                    break
            for at in cands:
                if best is None or at < best[1]:
                    best = (r, at)
        return {"id": best[0]["id"], "text": best[0]["text"], "at": best[1].isoformat(timespec="minutes")} if best else None


def note_for(r: dict, lang: str) -> dict:
    """The card over the face for a reminder: its text, and the two buttons."""
    t = TEXT.get(lang, TEXT["en"])
    return {"id": r["id"], "text": r["text"], "say": False,   # the node says it first, with "A reminder:"
            "buttons": [{"id": "done", "label": {k: v["done"] for k, v in TEXT.items()}},
                        {"id": "later", "label": {k: v["later"] for k, v in TEXT.items()}}],
            "_say": f"{t['remind']} {r['text']}"}


def now_local() -> datetime:
    return datetime.fromtimestamp(time.time())

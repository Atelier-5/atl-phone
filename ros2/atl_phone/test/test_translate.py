# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""Übersetzen's engine with fake models: sentences at pauses, limits, lazy loading, missing models."""
import threading

import pytest

from atl_phone import translate as tr
from atl_phone.translate import Translator, sentences, split_text

WORDS = [{"word": "ich", "start": 0.1, "end": 0.3}, {"word": "habe", "start": 0.35, "end": 0.6},
         {"word": "kuchen", "start": 0.62, "end": 1.0},
         {"word": "möchtest", "start": 1.6, "end": 2.0}, {"word": "du", "start": 2.05, "end": 2.2}]


class FakeRec:
    def __init__(self, log):
        self.log = log

    def accept(self, pcm):
        self.log.append(len(pcm))

    def final(self):
        return WORDS


class FakeAsr:
    loads = 0

    def __init__(self, path):
        FakeAsr.loads += 1
        self.path, self.fed = path, []

    def recognizer(self):
        return FakeRec(self.fed)


class FakeMt:
    def __init__(self, path, threads):
        self.path, self.seen = path, []

    def translate(self, lines):
        self.seen.append(list(lines))
        return [f"<{s}>" for s in lines]


def folder(tmp_path, *names):
    for n in names:
        (tmp_path / n).mkdir()
    return tmp_path


def test_words_become_sentences_at_pauses():
    assert sentences(WORDS) == ["Ich habe kuchen.", "Möchtest du."]
    assert sentences([]) == []
    assert sentences(WORDS, gap=1.0) == ["Ich habe kuchen möchtest du."]


def test_text_is_split_into_sentences_and_capped():
    assert split_text("Chère maman,  merci.\nNous t'embrassons ! Bises") == ["Chère maman, merci.", "Nous t'embrassons !", "Bises"]
    assert len("".join(split_text("a" * 2000))) == tr.MAX_CHARS
    assert split_text("   ") == [] and split_text(None) == []


def test_which_models_are_there(tmp_path):
    t = Translator(folder(tmp_path, tr.ASR["de"], tr.MT[("de", "fr")]), asr=FakeAsr, mt=FakeMt)
    assert t.models() == {"de": True, "fr": False, "de-fr": True, "fr-de": False} and not t.ready
    assert Translator(None).models() == {"de": False, "fr": False, "de-fr": False, "fr-de": False}
    with pytest.raises(LookupError):
        t.listen("fr")
    with pytest.raises(LookupError):
        t.translate("Bonjour.", "fr", "de")


def test_an_utterance_is_heard_once_and_capped(tmp_path):
    FakeAsr.loads = 0
    t = Translator(folder(tmp_path, *tr.ASR.values(), *tr.MT.values()), asr=FakeAsr, mt=FakeMt)
    assert t.ready
    u = t.listen("de")
    assert u.feed(b"\0" * 8000) and u.seconds == 0.25
    assert not u.feed(b"\0" * tr.MAX_BYTES)  # over 30 s: dropped
    assert u.text() == "Ich habe kuchen. Möchtest du."
    assert u.text() == "" and not u.feed(b"\0" * 10) and u.rec is None  # made once; nothing of it kept
    t.listen("de")
    assert FakeAsr.loads == 1  # the model loads once
    assert t.hear(b"\0" * 20000, "de") == "Ich habe kuchen. Möchtest du."
    with pytest.raises(ValueError):
        t.listen("en")


def test_translation_goes_sentence_by_sentence(tmp_path):
    t = Translator(folder(tmp_path, *tr.MT.values()), asr=FakeAsr, mt=FakeMt)
    assert t.translate("Ich habe Kuchen. Möchtest du?", "de", "fr") == "<Ich habe Kuchen.> <Möchtest du?>"
    assert t.engines[("de", "fr")].seen == [["Ich habe Kuchen.", "Möchtest du?"]]
    assert t.translate("", "de", "fr") == ""
    with pytest.raises(ValueError):
        t.translate("Hallo.", "de", "en")


def test_two_callers_load_a_model_once(tmp_path):
    made = []
    gate = threading.Event()

    def slow(path, threads):
        gate.wait(1)
        made.append(path)
        return FakeMt(path, threads)

    t = Translator(folder(tmp_path, *tr.MT.values()), mt=slow)
    out = []
    ths = [threading.Thread(target=lambda: out.append(t.translate("Salut.", "fr", "de"))) for _ in range(3)]
    for th in ths:
        th.start()
    gate.set()
    for th in ths:
        th.join(5)
    assert out == ["<Salut.>"] * 3 and len(made) == 1


def run(session):
    session.q.join()  # the worker did every job queued


def test_a_session_sends_the_words_to_the_phone_and_counts_to_ros(tmp_path):
    sent, counts, logs = [], [], []
    t = Translator(folder(tmp_path, *tr.ASR.values(), *tr.MT.values()), asr=FakeAsr, mt=FakeMt)
    s = tr.Session(t, sent.append, counts.append, logs.append)
    for seq in range(3):
        s.audio({"t": "audio", "lang": "de", "seq": seq, "pcm": b"\0" * 8000, "end": False})
    s.audio({"t": "audio", "lang": "de", "end": True})
    run(s)
    assert sent[0] == {"t": "heard", "lang": "de", "text": "Ich habe kuchen. Möchtest du."}
    assert sent[1]["t"] == "translated" and sent[1]["lang"] == "fr" and sent[1]["text"] == "<Ich habe kuchen.> <Möchtest du.>"
    assert counts == [{"ok": True, "from": "de", "to": "fr", "words": 5, "ms": counts[0]["ms"], "seconds": 0.8}]
    assert not any("kuchen" in json_text for json_text in map(str, counts + logs))  # ROS and the log: counts only
    s.text("Chère maman. Bises", "fr", "de")
    run(s)
    assert sent[-1]["text"] == "<Chère maman.> <Bises>" and sent[-1]["source"] == "text" and counts[-1]["from"] == "fr"
    s.stop()


def test_a_session_without_models_says_so_and_a_cancel_drops_the_hold(tmp_path):
    sent, counts = [], []
    s = tr.Session(Translator(tmp_path, asr=FakeAsr, mt=FakeMt), sent.append, counts.append)
    s.audio({"t": "audio", "lang": "fr", "seq": 0, "pcm": b"\0" * 800, "end": False})
    s.audio({"t": "audio", "lang": "fr", "seq": 1, "pcm": b"\0" * 800, "end": False})
    s.audio({"t": "audio", "lang": "fr", "end": True})
    run(s)
    assert sent == [{"t": "heard", "lang": "fr", "text": "", "error": "models"}] and counts == []  # said once, not per chunk
    (tmp_path / "m").mkdir()
    sent2 = []
    s2 = tr.Session(Translator(folder(tmp_path / "m", *tr.ASR.values(), *tr.MT.values()), asr=FakeAsr, mt=FakeMt), sent2.append)
    s2.audio({"t": "audio", "lang": "de", "seq": 0, "pcm": b"\0" * 800, "end": False})
    s2.cancel()
    s2.audio({"t": "audio", "lang": "de", "end": True})
    run(s2)
    assert sent2 == []  # the phone went: nothing of that hold is heard
    s.stop(), s2.stop()


def test_a_flooding_phone_fills_the_queue_and_the_rest_is_dropped(tmp_path):
    s = tr.Session(Translator(tmp_path), [].append)
    s.stop()
    s.worker.join(2)
    taken = sum(s.audio({"t": "audio", "lang": "de", "seq": 1, "pcm": b"\0\0", "end": False}) for _ in range(tr.Session.QUEUE + 50))
    assert taken == tr.Session.QUEUE

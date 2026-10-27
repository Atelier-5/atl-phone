# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""translate — Übersetzen's engine: German and French speech to text, and text from one to the other, offline.

    t = Translator("/models")
    u = t.listen("fr"); u.feed(pcm); ...; heard = u.text()     # 16 kHz mono PCM16, while the talk button is held
    t.translate(heard, "fr", "de")                              # sentence by sentence

Speech: Vosk's small models (one recognizer per utterance). Vosk gives words without punctuation, and the translator
then drops whole sentences; so the words are cut into sentences at pauses longer than GAP, each with a capital and a
full stop. Translation: Opus-MT converted to CTranslate2 int8, with its sentencepiece vocabularies.
The models are loaded on first use (the speech model about 5 s, a translator under 1 s) and kept; nothing heard or
said is kept here: an utterance's sound is dropped when its text is made. At most MAX_SECONDS of sound and
MAX_CHARS of text a request. scripts/get_models.sh fetches the models; no ROS, and vosk and ctranslate2 are only
imported when a model loads, so the tests run with fake engines.
"""
import json
import queue
import re
import threading
import time
from pathlib import Path

LANGS = ("de", "fr")
RATE = 16000                      # Hz, mono PCM16
MAX_SECONDS = 30
MAX_BYTES = MAX_SECONDS * RATE * 2
MAX_CHARS = 500
GAP = 0.3                         # s of silence between words that ends a sentence
ASR = {"de": "vosk-model-small-de-0.15", "fr": "vosk-model-small-fr-0.22"}
MT = {("de", "fr"): "opus-mt-de-fr-ct2", ("fr", "de"): "opus-mt-fr-de-ct2"}


def other(lang: str) -> str:
    return "fr" if lang == "de" else "de"


def sentences(words: list, gap: float = GAP) -> list:
    """Vosk's words ({word, start, end}) as sentences: cut at pauses, a capital and a full stop each."""
    out, cur, last = [], [], None
    for w in words:
        if cur and last is not None and w.get("start", 0) - last > gap:
            out.append(cur)
            cur = []
        cur.append(str(w.get("word", "")))
        last = w.get("end", w.get("start", 0))
    if cur:
        out.append(cur)
    return [s[0].upper() + s[1:] + "." for s in (" ".join(x for x in c if x) for c in out) if s]


def split_text(text: str) -> list:
    """Written text as sentences for the translator (a letter's lines, a typed message); at most MAX_CHARS in all."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:MAX_CHARS]
    return [s for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]


class VoskEngine:
    """One Vosk model; recognizer() makes a fresh one for each utterance."""

    def __init__(self, path: Path):
        import vosk
        vosk.SetLogLevel(-1)
        self.model = vosk.Model(str(path))

    def recognizer(self):
        import vosk
        r = vosk.KaldiRecognizer(self.model, RATE)
        r.SetWords(True)
        return _VoskUtt(r)


class _VoskUtt:
    def __init__(self, r):
        self.r, self.words = r, []

    def accept(self, pcm: bytes):
        if self.r.AcceptWaveform(pcm):  # Vosk ends a stretch of its own at a long pause: keep its words
            self.words += json.loads(self.r.Result()).get("result", [])

    def final(self) -> list:
        return self.words + json.loads(self.r.FinalResult()).get("result", [])


class OpusEngine:
    """One Opus-MT direction in CTranslate2, with its two sentencepiece vocabularies."""

    def __init__(self, path: Path, threads: int = 2):
        import ctranslate2
        import sentencepiece
        self.tr = ctranslate2.Translator(str(path), device="cpu", compute_type="int8", intra_threads=threads)
        self.src = sentencepiece.SentencePieceProcessor(str(path / "source.spm"))
        self.dst = sentencepiece.SentencePieceProcessor(str(path / "target.spm"))

    def translate(self, lines: list) -> list:
        out = self.tr.translate_batch([self.src.encode(s, out_type=str) + ["</s>"] for s in lines], beam_size=2)
        return [self.dst.decode(o.hypotheses[0]) for o in out]


class Utterance:
    """What one hold of the talk button heard: fed while held, its text made once, its sound never kept."""

    def __init__(self, rec, lang: str):
        self.rec, self.lang, self.size, self.done = rec, lang, 0, False

    def feed(self, pcm: bytes) -> bool:
        """False once MAX_SECONDS are heard (the rest is dropped) or the text was made."""
        if self.done or self.size + len(pcm) > MAX_BYTES:
            return False
        self.size += len(pcm)
        self.rec.accept(bytes(pcm))
        return True

    @property
    def seconds(self) -> float:
        return self.size / (RATE * 2)

    def text(self) -> str:
        if self.done:
            return ""
        self.done = True
        words, self.rec = self.rec.final(), None
        return " ".join(sentences(words))


class Translator:
    def __init__(self, folder, threads: int = 2, asr=None, mt=None):
        """asr(path) and mt(path, threads) make the engines (tests pass fakes)."""
        self.dir = Path(folder) if folder else None
        self.threads = threads
        self.make_asr = asr or VoskEngine
        self.make_mt = mt or OpusEngine
        self.engines, self.lock = {}, threading.Lock()

    def models(self) -> dict:
        """Which models are on disk: {"de": True, "fr": True, "de-fr": True, "fr-de": False}."""
        have = {}
        for lang, name in ASR.items():
            have[lang] = bool(self.dir) and (self.dir / name).is_dir()
        for (a, b), name in MT.items():
            have[f"{a}-{b}"] = bool(self.dir) and (self.dir / name).is_dir()
        return have

    @property
    def ready(self) -> bool:
        return all(self.models().values())

    def _engine(self, key, name: str, make):
        with self.lock:  # one load at a time; a second caller waits for it
            if key not in self.engines:
                path = self.dir / name if self.dir else None
                if not path or not path.is_dir():
                    raise LookupError(f"no model {name}")
                self.engines[key] = make(path)
            return self.engines[key]

    def listen(self, lang: str) -> Utterance:
        if lang not in LANGS:
            raise ValueError(f"not a language here: {lang!r}")
        return Utterance(self._engine(lang, ASR[lang], self.make_asr).recognizer(), lang)

    def hear(self, pcm: bytes, lang: str) -> str:
        u = self.listen(lang)
        for i in range(0, min(len(pcm), MAX_BYTES), 8000):
            u.feed(pcm[i:i + 8000])
        return u.text()

    def translate(self, text: str, src: str, dst: str) -> str:
        if (src, dst) not in MT:
            raise ValueError(f"no translation {src!r} to {dst!r}")
        lines = split_text(text)
        if not lines:
            return ""
        return " ".join(s.strip() for s in self._engine((src, dst), MT[(src, dst)], lambda p: self.make_mt(p, self.threads)).translate(lines))


class Session:
    """The phone's talking, on a worker thread: the sound of one hold comes in chunks, what was heard and its translation
    go back to the phone only (send), and how it went, as counts, to done (ROS). The WebSocket reader never waits on
    a model: a chunk is queued (at most QUEUE of them; more are dropped) and the worker hears and translates."""
    QUEUE = 240   # chunks: a minute of 250 ms ones

    def __init__(self, translator: Translator, send, done=None, log=None):
        self.t, self.send, self.done, self.log = translator, send, done or (lambda r: None), log or (lambda s: None)
        self.q = queue.Queue(self.QUEUE)
        self.cur = None           # the utterance being heard, or "failed" until the next hold
        self.worker = threading.Thread(target=self._run, name="translate", daemon=True)
        self.worker.start()

    def _put(self, job) -> bool:
        try:
            self.q.put_nowait(job)
            return True
        except queue.Full:  # the phone sends faster than it can be heard; this chunk is dropped
            return False

    def audio(self, m: dict) -> bool:
        """A parsed {"t": "audio"} message: a chunk of a hold, or its end."""
        return self._put(("end", m["lang"]) if m.get("end") else ("pcm", m["lang"], m["seq"], m["pcm"]))

    def text(self, text: str, src: str, dst: str, n: int = 0) -> bool:
        """Written text to translate (a piece of a letter read on the phone): the translation goes back the same way,
        with "source": "text" and the request's number n."""
        return self._put(("text", text, src, dst, n))

    def warm(self) -> bool:
        """Load the models now, so the first hold is quick (the speech models take a few seconds)."""
        return self._put(("warm",))

    def cancel(self) -> bool:
        """Drop what is being heard (the phone went, or talking is no longer allowed)."""
        return self._put(("cancel",))

    def stop(self):
        self._put(None)

    def _run(self):
        while True:
            job = self.q.get()
            if job is None:
                self.q.task_done()
                return
            try:
                if job[0] == "pcm":
                    _, lang, seq, pcm = job
                    if self.cur is None or seq == 0 or getattr(self.cur, "lang", lang) != lang:
                        try:
                            self.cur = self.t.listen(lang)
                        except LookupError:
                            self.cur = "failed"
                            self.send({"t": "heard", "lang": lang, "text": "", "error": "models"})
                    if self.cur != "failed":
                        self.cur.feed(pcm)
                elif job[0] == "end":
                    u, self.cur = self.cur, None
                    if u is None or u == "failed":
                        continue
                    t0 = time.monotonic()
                    heard = u.text()
                    self._result(heard, u.lang, other(u.lang), t0, u.seconds)
                elif job[0] == "text":
                    _, text, src, dst, n = job
                    self._result(" ".join(split_text(text)), src, dst, time.monotonic(), None, n=n)
                elif job[0] == "warm":
                    for lang in LANGS:
                        self.t.listen(lang)
                    for a, b in MT:
                        self.t.translate("Hallo.", a, b)
                elif job[0] == "cancel":
                    self.cur = None
            except Exception as e:  # never the words: only what went wrong
                self.cur = None
                self.log(f"translate: {type(e).__name__}")
            finally:
                self.q.task_done()

    def _result(self, heard: str, src: str, dst: str, t0: float, seconds, n=None):
        spoken = n is None   # else written text, request n
        kind = {} if spoken else {"source": "text"}   # for ROS; the phone also gets n back
        tag = {} if spoken else dict(kind, n=n)
        if spoken:
            self.send({"t": "heard", "lang": src, "text": heard, **({} if heard else {"error": "nothing"})})
        if not heard:
            if not spoken:
                self.send({"t": "translated", "lang": dst, "text": "", "error": "nothing", **tag})
            self.done({"ok": False, "from": src, "to": dst, "words": 0, "ms": 0,
                       **({"seconds": round(seconds or 0, 1)} if spoken else kind)})
            return
        try:
            out = self.t.translate(heard, src, dst)
        except LookupError:
            self.send({"t": "translated", "lang": dst, "text": "", "error": "models", **tag})
            self.done({"ok": False, "from": src, "to": dst, "words": len(heard.split()), "ms": 0, **kind})
            return
        ms = int((time.monotonic() - t0) * 1000)
        self.send({"t": "translated", "lang": dst, "text": out, "ms": ms, **tag})
        r = {"ok": bool(out), "from": src, "to": dst, "words": len(heard.split()), "ms": ms, **kind}
        if seconds is not None:
            r["seconds"] = round(seconds, 1)
        self.done(r)

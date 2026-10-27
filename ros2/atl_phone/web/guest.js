// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// The guest page's own small helpers (talk.html): its language, words, voice and link to the bridge's guest port, so
// talk.js (Übersetzen's two halves, the same as on the robot's phone) runs here too. The link's code (?k=) comes from
// the QR code on the robot's phone; it changes each time Übersetzen is allowed again. Plain ES2017, no libraries.
'use strict';

var TALK_GUEST = true;
var Q = {};
location.search.slice(1).split('&').forEach(function (kv) { if (kv) { var p = kv.split('='); Q[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ''); } });
var lang = (navigator.language || 'fr').slice(0, 2);
if (['en', 'fr', 'de'].indexOf(Q.lang) >= 0) lang = Q.lang;
if (['en', 'fr', 'de'].indexOf(lang) < 0) lang = 'fr';
document.documentElement.lang = lang;
function ot(l, k) { return (TEXTS.omi[l] || TEXTS.omi.en)[k]; }
function mt(k) { return TEXTS.mode[lang][k] || TEXTS.mode.en[k] || k; }

var toastEl = document.getElementById('toast'), statusEl = document.getElementById('status'), toastOff = 0;
function tell(text, l, ms) {
  clearTimeout(toastOff); toastEl.textContent = text; toastEl.style.display = text ? 'block' : 'none';
  toastOff = setTimeout(function () { toastEl.style.display = 'none'; }, ms || 5000);
}
var LANG_TAG = { en: 'en-GB', fr: 'fr-FR', de: 'de-DE' };
function hush() { if ('speechSynthesis' in window) speechSynthesis.cancel(); }  // talk.js: quiet while a half is held
function speak(text, l) {  // the voice of the language (the country's first, as the face chooses it)
  if (!('speechSynthesis' in window) || !text) return;
  speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text), tag = LANG_TAG[l] || 'fr-FR', vs = speechSynthesis.getVoices();
  var norm = function (v) { return v.lang.replace('_', '-'); };
  u.lang = tag;
  u.voice = vs.filter(function (v) { return norm(v) === tag; })[0] || vs.filter(function (v) { return norm(v).slice(0, 2) === tag.slice(0, 2); })[0] || null;
  speechSynthesis.speak(u);
}

var ws = null, wait = 1000;
function send(o) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); }
function status(k) { statusEl.textContent = k ? ot(lang, k) : ''; statusEl.style.display = k ? 'block' : 'none'; }
function connect() {
  if (!Q.k) { status('guestOld'); return; }
  status('guestWait');
  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/talk?k=' + encodeURIComponent(Q.k));
  var opened = false;
  ws.onopen = function () { opened = true; wait = 1000; status(''); };
  ws.onmessage = function (e) { var m; try { m = JSON.parse(e.data); } catch (x) { return; } talkMsg(m); if (m.t === 'translate') status(m.allowed ? '' : 'guestOff'); };
  ws.onclose = function (e) {
    if (typeof talkStop === 'function') talkStop();
    talk.allowed = false;
    if (!opened || e.code === 4002) { status('guestOld'); return; }   // a refused code, or a new one was made: scan again
    if (e.code === 4000) { status('guestOld'); return; }               // another guest phone took over
    status('guestWait'); setTimeout(connect, wait); wait = Math.min(wait * 2, 10000);
  };
}
document.getElementById('title').textContent = ot(lang, 'guestTitle');
document.getElementById('cert').textContent = location.protocol === 'https:' ? ot(lang, 'guestCert') : '';
if ('speechSynthesis' in window) speechSynthesis.getVoices();
window.addEventListener('load', connect);

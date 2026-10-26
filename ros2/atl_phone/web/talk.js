// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// Übersetzen, on the phone (contract atl-phone/0.7): the panel's translate mode is two big halves, Deutsch and Français.
// Hold one and speak: only while it is held, and only when the bridge allows it, the microphone is open (the badge
// HÖRT ZU says so) and its sound goes to the bridge, 16 kHz PCM16 in 250 ms chunks. The robot's computer hears and
// translates it offline and keeps nothing; the words come back to this phone alone ("heard", "translated"), are shown
// in the two halves and said in the other language. The screen report says only the state, never the words.
// A guest phone on the home Wi-Fi can join (talk.html, the bridge's guest port): in this mode the robot's phone shows
// its link as a QR code where the eyes are, until a guest is there; then both phones see what either says, and the
// other phone, the one of the person who listens, says the translation aloud (alone, the robot's phone says it).
// Loaded after face.js and omi.js (speak, send, setPanel, tell, ot), or on the guest page after guest.js (TALK_GUEST).
'use strict';

var TALK_RATE = 16000, TALK_CHUNK = 4096, TALK_MAX_MS = 30000;   // 4096 samples at 16 kHz: about 250 ms
var TALK_NAME = { de: '🇩🇪 Deutsch', fr: '🇫🇷 Français' };   // each half says its language in that language
var TALK_GUEST = !!window.TALK_GUEST;   // this is the guest page (talk.html)
var talk = { allowed: false, ready: false, lang: '', seq: 0, stream: null, ctx: null, node: null, src: null, off: 0,
             holding: false, state: '', stateLang: '', last: { de: ['', ''], fr: ['', ''] }, guest: '', guestOn: false, qrFor: '' };
var talkEl = document.getElementById('talk'), listenEl = document.getElementById('listening'), guestEl = document.getElementById('guest');

function talkBuild() {  // the two halves: the language's name, how to use it, and what was said and its translation
  talkEl.textContent = '';
  ['de', 'fr'].forEach(function (l) {
    var h = document.createElement('div'); h.className = 'half'; h.dataset.l = l;
    h.innerHTML = '<b></b><small></small><p class="heard"></p><p class="said"></p>';
    h.querySelector('b').textContent = TALK_NAME[l];
    h.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); talkStart(l); });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (k) { h.addEventListener(k, function () { talkStop(); }); });
    h.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    talkEl.appendChild(h);
  });
  talkShow();
}
function talkShow() {
  [].forEach.call(talkEl.children, function (h) {
    var l = h.dataset.l, r = talk.last[l];
    h.classList.toggle('on', talk.holding && talk.lang === l);
    h.querySelector('small').textContent = talk.state === 'wait' && talk.stateLang !== l ? '…' : ot(l, 'talkHold');
    h.querySelector('.heard').textContent = r[0];
    h.querySelector('.said').textContent = r[1];
  });
  listenEl.textContent = '● ' + mt('listening');
  listenEl.style.display = talk.holding && talk.stream ? 'block' : 'none';
}
function talkSet(state, l) { talk.state = state; talk.stateLang = l || ''; talkShow(); }

function talkPanel(mode) {  // face.js showPanel(): the halves show in the translate mode only; leaving it stops listening
  talkEl.style.display = mode === 'translate' ? 'flex' : 'none';
  if (mode !== 'translate' && talk.holding) talkStop();
  talkQr(mode === 'translate');
}
function talkQr(on) {  // the robot's phone: the guest page's link as a QR code over the eyes, until a guest is there
  if (!guestEl) return;
  var qr = on && talk.allowed && talk.guest && !talk.guestOn && typeof qrcode === 'function';
  guestEl.style.display = on && talk.allowed && (qr || talk.guestOn) ? 'flex' : 'none';
  guestEl.classList.toggle('on', !!talk.guestOn);
  guestEl.querySelector('span').textContent = talk.guestOn ? '📱 ' + mt('guest_on') : mt('guest_scan');
  var c = guestEl.querySelector('canvas');
  c.style.display = qr ? 'block' : 'none';
  if (!qr || talk.qrFor === talk.guest + '|' + innerWidth + 'x' + innerHeight) return;
  talk.qrFor = talk.guest + '|' + innerWidth + 'x' + innerHeight;
  var q = qrcode(0, 'M'); q.addData(talk.guest); q.make();
  var n = q.getModuleCount() + 8, px = Math.min(innerWidth - 40, Math.round(innerHeight * SPLIT) - 70), s = Math.max(2, Math.floor(px / n));
  c.width = c.height = n * s;
  var g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, n * s, n * s); g.fillStyle = '#000';
  for (var y = 0; y < n - 8; y++) for (var x = 0; x < n - 8; x++) if (q.isDark(y, x)) g.fillRect((x + 4) * s, (y + 4) * s, s, s);
}
function talkStart(l) {
  if (talk.holding) return;
  if (!talk.allowed) { tell(ot(lang, 'talkNo'), lang, 5000); return; }
  if (!talk.ready) { tell(ot(lang, 'talkModels'), lang, 5000); return; }
  speechSynthesis.cancel();
  talk.holding = true; talk.lang = l; talk.seq = 0;
  talk.last[l] = ['', '']; talk.last[l === 'de' ? 'fr' : 'de'] = ['', ''];
  talkSet('listening', l);
  if (navigator.vibrate) navigator.vibrate(30);
  navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } }).then(function (s) {
    if (!talk.holding || talk.lang !== l) { s.getTracks().forEach(function (k) { k.stop(); }); return; }  // let go meanwhile
    var Ctx = window.AudioContext || window.webkitAudioContext, ctx;
    try { ctx = new Ctx({ sampleRate: TALK_RATE }); } catch (e) { ctx = new Ctx(); }  // the browser resamples to 16 kHz
    talk.stream = s; talk.ctx = ctx;
    talk.src = ctx.createMediaStreamSource(s);
    talk.node = ctx.createScriptProcessor(TALK_CHUNK, 1, 1);
    var ratio = ctx.sampleRate / TALK_RATE;
    talk.node.onaudioprocess = function (e) {
      if (!talk.holding) return;
      var x = e.inputBuffer.getChannelData(0), n = Math.floor(x.length / ratio), pcm = new Int16Array(n);
      for (var i = 0; i < n; i++) { var v = x[Math.floor(i * ratio)]; pcm[i] = Math.max(-32768, Math.min(32767, Math.round(v * 32767))); }
      var b = new Uint8Array(pcm.buffer), str = '';
      for (var j = 0; j < b.length; j += 8192) str += String.fromCharCode.apply(null, b.subarray(j, j + 8192));
      send({ t: 'audio', lang: l, seq: talk.seq++, pcm: btoa(str) });
    };
    talk.src.connect(talk.node); talk.node.connect(ctx.destination);   // (a script node runs only when connected)
    ctx.resume().catch(function () {});
    talkShow();
    talk.off = setTimeout(talkStop, TALK_MAX_MS);
  }, function () { talk.holding = false; talkSet(''); tell(ot(lang, 'talkMic'), lang, 5000); });
}
function talkStop() {
  if (!talk.holding) return;
  var l = talk.lang, sent = talk.seq > 0;
  talk.holding = false; clearTimeout(talk.off);
  if (talk.node) { talk.node.onaudioprocess = null; talk.node.disconnect(); }
  if (talk.src) talk.src.disconnect();
  if (talk.stream) talk.stream.getTracks().forEach(function (k) { k.stop(); });   // the microphone closes at once
  if (talk.ctx) talk.ctx.close().catch(function () {});
  talk.stream = talk.ctx = talk.node = talk.src = null;
  if (sent) { send({ t: 'audio', lang: l, end: true }); talkSet('wait', l); } else talkSet('');
}
function talkMsg(m) {  // face.js handle(): translate (allowed?), heard, translated
  if (m.t === 'translate') {
    talk.allowed = !!m.allowed; talk.ready = !!m.ready;
    talk.guest = typeof m.guest === 'string' ? m.guest : ''; talk.guestOn = !!m.guest_on;
    if (!talk.allowed && talk.holding) talkStop();
    if (typeof buildMenu === 'function') buildMenu();   // its tile comes or goes
    if (!TALK_GUEST) talkQr(typeof panel === 'object' && panel.mode === 'translate');
    talkShow();
    return;
  }
  var l = m.lang === 'fr' ? 'fr' : 'de', text = String(m.text || '').replace(/ ([?!:;»])/g, '\u00a0$1');  // French: « ? » stays with its word
  if (m.t === 'heard') {
    if (!text) {
      if (!talk.holding) talkSet('nothing', l);
      tell(ot(lang, m.error === 'models' ? 'talkModels' : 'talkNothing'), lang, 4000); return;
    }
    talk.last[l] = [text, '']; talkShow();
  } else if (m.t === 'translated' && text) {
    var from = l === 'de' ? 'fr' : 'de';
    talk.last[from][1] = ''; talk.last[l] = ['', text];
    talkSet('result', l);
    var mine = (m.who || 'robot') === (TALK_GUEST ? 'guest' : 'robot');   // said on this phone's half
    if (TALK_GUEST ? !mine : !mine || !talk.guestOn) speak(text, l);   // in the other language's voice, for the one who listens
  }
}
talkBuild();

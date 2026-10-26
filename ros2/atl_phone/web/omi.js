// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// Omi Assist's helpers, on the phone (contract atl-phone/0.6): the time, the magnifier, reading aloud, "what is this?",
// the eyes following, and showing the picture to the PC. Loaded after face.js and see.js, whose camera, speech, panel and
// vision it uses. Reading (vendor/tesseract) and "what is this?" (MediaPipe's objects) run here: what they read or see
// is said and written on this screen, and ROS only hears how it went (lines, characters, a label, how long). Showing is
// the one exception to "pictures stay on the phone": only when the bridge allows it, only while the person shows, with
// the red badge on, at most a minute; the frames go to the bridge, which hands them to the setup page and keeps none.
'use strict';

var TESS = 'vendor/tesseract', OCR_LANG = { en: 'eng', fr: 'fra', de: 'deu' };
var SHOW_FPS = 2, SHOW_PX = 320, SHOW_MAX_MS = 60000, STILL_SETTLE_MS = 700;
var OMI_TEXT = TEXTS.omi;  // the words (texts.js, shared with the Webots twin)
// the presentation (the setup page's "Introduce"): what each step says, in the order of the tiles
var TOUR_TEXT = TEXTS.tour;
// its steps: the tile it points at, the mode it then shows for a moment, the time said, the sample card
var TOUR = [{ k: 'hello', face: 'happy' }, { k: 'menu', menu: true }, { k: 'time', tile: 'time', time: true },
            { k: 'front', tile: 'front', mode: 'camera' }, { k: 'back', tile: 'back', mode: 'camera_back' },
            { k: 'magnify', tile: 'magnify', mode: 'magnify' }, { k: 'read', tile: 'read' },
            { k: 'sensors', tile: 'sensors', mode: 'sensors' }, { k: 'follow', tile: 'follow' },
            { k: 'show', mode: 'camera', allowed: true }, { k: 'remind', card: true },
            { k: 'face', tile: 'face' }, { k: 'bye', face: 'love' }];
// what "what is this?" says, for each of the model's labels (contract OBJECTS): [English, French, German], with the article
var WHAT = TEXTS.what;
var omi = { busy: '', tess: {}, toastOff: 0, reading: 0, showAllowed: false, showing: false, showTimer: 0, showOff: 0,
            zoom: 1, cssZoom: false, held: false, torch: false, full: false, still: document.createElement('video'),
            canvas: document.createElement('canvas'), tour: 0, touring: false };
omi.still.muted = true; omi.still.setAttribute('playsinline', '');
function ot(l, k) { return (OMI_TEXT[l] || OMI_TEXT.en)[k]; }
function li(l) { return { en: 0, fr: 1, de: 2 }[l] || 0; }
var toastEl = document.getElementById('toast'), showEl = document.getElementById('showing'), magEl = document.getElementById('mag');

function toast(text, ms, key, arg) {  // said and also written, big, for a moment; key: what the screen report says of it
  clearTimeout(omi.toastOff);
  toastEl.textContent = text; toastEl.style.display = text ? 'block' : 'none';
  omi.toastKey = text ? (key === undefined ? textKey(text) : key) : ''; omi.toastArg = arg || '';
  if (text) omi.toastOff = setTimeout(function () { toastEl.style.display = 'none'; }, ms || 6000);
}
function tell(text, l, ms, done, key, arg) { toast(text, ms, key, arg); speak(text, l || lang, false, done); }
function textKey(text) {  // a fixed text's key in texts.js, or '' (a text that is not one of them is never reported)
  var k, l;
  for (l in OMI_TEXT) for (k in OMI_TEXT[l]) if (OMI_TEXT[l][k] === text) return k;
  for (l in TOUR_TEXT) for (k in TOUR_TEXT[l]) if (TOUR_TEXT[l][k] === text) return 'tour.' + k;
  return '';
}

// ---- what the tiles do (face.js pick()), and what ROS asks (read, what, show) -----------------------------------
function omiTile(id, was) {
  if (id === 'time') sayTime(lang);
  else if (id === 'read') readAloud(lang);
  else if (id === 'what') whatIsIt(lang);
  else if (id === 'follow') followToggle();
  else if (id === 'show') { if (omi.showing) stopShow(true); else startShow(); }
  else if (id === 'magnify' && was === 'magnify') { omi.full = !omi.full; panelEl.classList.toggle('full', omi.full); }  // again: the whole screen
}
function omiHome() {  // the face tile: everything this file has on stops
  tourStop(); stopReading();
  if (omi.showing) stopShow(true);
  omi.full = false; panelEl.classList.remove('full');
}
function omiBack() {  // the face tile: "here I am again", with a short love face before the usual one
  var was = expression === 'love' ? 'neutral' : expression;
  setExpression('love'); tell(ot(lang, 'back'), lang, 2500);
  clearTimeout(omi.backOff); omi.backOff = setTimeout(function () { if (expression === 'love') setExpression(was); }, 1800);
}
function omiAsk(m) {
  var l = OMI_TEXT[m.lang] ? m.lang : lang;
  if (m.t === 'tour') tour(l);
  else if (m.t === 'read') readAloud(l);
  else if (m.t === 'what') whatIsIt(l);
  else if (m.t === 'show') {
    omi.showAllowed = !!m.allowed;
    if (omi.showing && (!m.allowed || !m.on)) stopShow(false);
    camBar(split() ? panel.mode : '');   // its Zeigen button comes or goes
  }
}

// ---- the presentation: Omi Assist says what it can, pointing at each tile and showing it; a tap ends it ------------------
function tourSay(text, l, done, key) {  // said and written; on to the next when said, or after a while if the voice is stuck
  var once = function () { if (once) { once = null; done(); } };
  tell(text, l, 30000, once, key);
  setTimeout(function () { if (once) once(); }, 2500 + text.length * 110);
}
function tourMenu(tile) {  // the tiles open, and stay, the one spoken of in yellow
  if (panel.mode !== 'mouth') setPanel({ mode: 'mouth' }, true);
  showMenu(); clearTimeout(menuOff); toastEl.classList.add('above');
  [].forEach.call(menuEl.children, function (b) { b.classList.toggle('tour', !!tile && b.dataset.mode === tile); });
}
function tourStop() {
  if (!omi.touring) return;
  omi.touring = false; omi.tour++;
  document.removeEventListener('pointerdown', tourStop, true);
  speechSynthesis.cancel(); speaking = false; toast('');
  [].forEach.call(menuEl.children, function (b) { b.classList.remove('tour'); });
  toastEl.classList.remove('above');
  if (cardId === 'tour') noteCard({ id: 'tour', text: '' });
  hideMenu();
}
function tour(l) {
  tourStop(); omiHome();
  var run = ++omi.tour, t = TOUR_TEXT[l] || TOUR_TEXT.en;
  omi.touring = true;
  setTimeout(function () { if (run === omi.tour) document.addEventListener('pointerdown', tourStop, true); }, 300);
  (function step(i) {
    if (run !== omi.tour) return;
    var s = TOUR[i], wait = function (ms) { setTimeout(function () { step(i + 1); }, ms); };
    if (!s) { tourStop(); setTimeout(function () { if (expression === 'love') setExpression('neutral'); }, 1500); return; }  // the end: as a tap
    if (s.allowed && !omi.showAllowed) return step(i + 1);   // Zeigen only where the assistant allowed it
    if (s.face) setExpression(s.face);
    if (s.menu || s.tile) tourMenu(s.tile); else { hideMenu(); toastEl.classList.remove('above'); }
    if (s.card) noteCard({ id: 'tour', text: t.card, buttons: [{ id: 'done', label: noteWord('done', l) }, { id: 'later', label: noteWord('later', l) }] });
    tourSay(t[s.k], l, function () {
      if (run !== omi.tour) return;
      if (s.card) { noteCard({ id: 'tour', text: '' }); return wait(500); }
      if (s.time) return tourSay(timePhrase(new Date(), l), l, function () { wait(600); }, 'time');
      if (!s.mode) return wait(600);
      hideMenu(); toastEl.classList.remove('above'); setPanel({ mode: s.mode }, true);   // what that tile shows, for a moment
      setTimeout(function () { if (run === omi.tour) { setPanel({ mode: 'mouth' }, true); wait(400); } }, 3500);
    });
  })(0);
}
function noteWord(k, l) { return { done: { en: 'Done', fr: 'Fait', de: 'Erledigt' }, later: { en: 'Later', fr: 'Plus tard', de: 'Später' } }[k][l]; }

// ---- the time and the date, from the phone's own clock -----------------------------------------------------------
function timeWords(d, l) {
  var h = d.getHours(), mi = d.getMinutes(), t = OMI_TEXT[l] || OMI_TEXT.en, h12 = h % 12 || 12, n12 = (h + 1) % 12 || 12;
  var plural = function (s, n) { return s.replace('heure(s)', n === 1 ? 'heure' : 'heures'); };
  if (mi === 0) return plural(t.oclock.replace('{h}', l === 'en' ? h12 : h), h);
  if (mi % 15 === 0) {
    var q = t.quarter[mi / 15].replace('{h}', h12).replace('{n}', n12);
    return plural(q, mi === 45 ? n12 : h12);
  }
  return d.toLocaleTimeString(LANG_TAG[l] || 'en-GB', { hour: 'numeric', minute: '2-digit' });
}
function timePhrase(d, l) {
  var day = d.toLocaleDateString(LANG_TAG[l] || 'en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
  return ot(l, 'now').replace('{t}', timeWords(d, l)) + ' ' + ot(l, 'today').replace('{d}', day);
}
function sayTime(l) { tell(timePhrase(new Date(), l), l, 8000, null, 'time'); }

// ---- the eyes follow the nearest thing (see.js), or look around ------------------------------------------------------
function followToggle() {
  var on = !vision.follow;
  if (on && !finders().length) seeAt({ camera: 'front', find: ['faces'], follow: true });  // nothing looks yet: faces, the lightest finder
  else { vision.follow = on; seeing.follow = { cur: null, cand: null, candAt: 0 }; seeReport({}); }
  if (!on && finders().length && vision.find.join() === 'faces') seeAt({ camera: 'front', find: [] });  // what the tile started
  buildMenu();
  tell(ot(lang, on ? 'followOn' : 'followOff'), lang, 4000);
}

// ---- a still from the back camera, for reading and "what is this?" ---------------------------------------------------
function grabStill(width) {
  want.still = true;
  function done() { want.still = false; omi.still.srcObject = null; closeCamIfIdle(); }
  return openCam().then(function (s) {
    var v = omi.still;
    if (v.srcObject !== s) { v.srcObject = s; v.play().catch(function () {}); }
    return new Promise(function (ok, no) {  // a moment for the light and the focus to settle
      var t0 = performance.now();
      (function wait() {
        if (v.readyState >= 2 && v.videoWidth && performance.now() - t0 > STILL_SETTLE_MS) return ok(v);
        if (performance.now() - t0 > 6000) return no({ name: 'NoPicture' });
        setTimeout(wait, 100);
      })();
    });
  }).then(function (v) {
    var c = omi.canvas, k = Math.min(1, width / v.videoWidth);
    c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k);
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
    done(); return c;
  }, function (e) { done(); throw e; });
}

// ---- reading aloud: Tesseract on the phone, said sentence by sentence; a tap stops it ---------------------------------
function tesseract(l) {
  if (!omi.tess[l]) {
    var base = new URL(TESS + '/', location.href).href;
    omi.tess[l] = (window.Tesseract ? Promise.resolve() : script(TESS + '/tesseract.min.js')).then(function () {
      return Tesseract.createWorker(OCR_LANG[l] || 'eng', 1, { workerPath: base + 'worker.min.js', corePath: base, langPath: base + 'lang',
                                                              workerBlobURL: false, gzip: true, cacheMethod: 'none' });
    });
    omi.tess[l].catch(function () { delete omi.tess[l]; });
  }
  return omi.tess[l];
}
function sentences(text) {
  return (text.replace(/-\n/g, '').replace(/\s*\n\s*/g, ' ').replace(/\s+/g, ' ').trim()
    .match(/[^.!?…:;]+[.!?…:;]*/g) || []).map(function (s) { return s.trim(); }).filter(function (s) { return /[A-Za-zÀ-ÿ0-9]/.test(s); });
}
function stopReading() {
  omi.reading++; document.removeEventListener('pointerdown', stopReading, true);
  speechSynthesis.cancel(); speaking = false; toast('');
}
function readAloud(l) {
  if (omi.busy) return;
  omi.busy = 'read';
  var t0 = performance.now(), run = ++omi.reading;
  tell(ot(l, 'reading'), l, 20000);
  Promise.all([grabStill(1600), tesseract(l)]).then(function (r) {
    return r[1].recognize(r[0]);
  }).then(function (res) {
    var d = res.data || {}, lines = (d.lines || []).filter(function (x) { return x.confidence >= 40 && /[A-Za-zÀ-ÿ0-9]{2}/.test(x.text); });
    var text = lines.map(function (x) { return x.text; }).join('\n'), ss = sentences(text), ms = Math.round(performance.now() - t0);
    omi.busy = '';
    send({ t: 'read', ok: true, lines: lines.length, chars: text.replace(/\s/g, '').length, ms: ms });
    if (run !== omi.reading) return;
    if (!ss.length) return tell(ot(l, 'notext'), l, 8000);
    document.addEventListener('pointerdown', stopReading, true);
    (function next(i) {
      if (run !== omi.reading) return;
      if (i >= ss.length) { document.removeEventListener('pointerdown', stopReading, true); toast(''); return; }
      tell(ss[i], l, 60000, function () { next(i + 1); }, 'reading');  // the screen report: "reading", never the text
    })(0);
  }).catch(function (e) {
    omi.busy = '';
    send({ t: 'read', ok: false, lines: 0, chars: 0, ms: Math.round(performance.now() - t0), error: camError(e) });
    tell(ot(l, e && e.name === 'NoLibrary' ? 'notext' : 'noCam'), l, 6000);
  });
}

// ---- what is this? one look of the object finder at a still from the back camera --------------------------------------
function whatPhrase(label, score, l) {
  if (!label) return ot(l, 'nothing');
  if (label === 'person') return ot(l, 'person');
  var x = (WHAT[label] || [label, label, label])[li(l)];
  return ot(l, score < 0.6 ? 'think' : 'is').replace('{x}', x);
}
function nearest(dets) {  // the biggest box, a person only when nothing else is there (it is often the one who holds it)
  var best = null, area = function (d) { return d.boundingBox.width * d.boundingBox.height; };
  dets.forEach(function (d) {
    var c = d.categories[0];
    if (!c || !WHAT[c.categoryName]) return;
    var person = c.categoryName === 'person', bp = best && best.categories[0].categoryName === 'person';
    if (!best || (bp && !person) || (bp === person && area(d) > area(best))) best = d;
  });
  return best;
}
function whatIsIt(l) {
  if (omi.busy) return;
  omi.busy = 'what';
  var t0 = performance.now();
  tell(ot(l, 'wait'), l, 15000);
  Promise.all([grabStill(640), task('objects')]).then(function (r) {
    var best = nearest(r[1].detectForVideo(r[0], performance.now()).detections), c = best && best.categories[0];
    var label = c ? c.categoryName : null, score = c ? Math.round(c.score * 100) / 100 : 0;
    omi.busy = '';
    send({ t: 'what', ok: true, label: label, score: score, ms: Math.round(performance.now() - t0) });
    tell(whatPhrase(label, score, l), l, 8000, null, !label ? 'nothing' : label === 'person' ? 'person' : score < 0.6 ? 'think' : 'is',
         label && label !== 'person' ? label : '');
  }).catch(function (e) {
    omi.busy = '';
    send({ t: 'what', ok: false, label: null, score: 0, ms: Math.round(performance.now() - t0) });
    tell(ot(l, 'noCam'), l, 6000);
  });
}

// ---- the camera views' buttons: the magnifier's zoom, torch and hold; "what is this?" on the back camera; Zeigen on
// every camera view, when the assistant allowed it. The magnifier: the back camera in the panel; zoom (the camera's
// own, else a scale), the torch, hold
var CAM_BUTTONS = [['minus', '−', ['magnify']], ['plus', '+', ['magnify']], ['torch', '💡', ['magnify']], ['hold', '✋', ['magnify']],
                   ['what', '❓', ['camera_back']], ['show', '📡', ['camera', 'camera_back', 'magnify']]];
CAM_BUTTONS.forEach(function (b) {
  var el = document.createElement('button');
  el.textContent = b[1]; el.dataset.id = b[0]; el.dataset.modes = b[2].join(' ');
  el.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); camButton(b[0]); if (navigator.vibrate) navigator.vibrate(20); });
  magEl.appendChild(el);
});
function camButton(id) {
  if (id === 'what') whatIsIt(lang);
  else if (id === 'show') { if (omi.showing) stopShow(true); else startShow(); }
  else magnify(id);
}
function magTrack() { return cam && camFacing === 'environment' ? cam.getVideoTracks()[0] : null; }
function magnify(what) {
  var k = magTrack(), c = k && k.getCapabilities ? k.getCapabilities() : {};
  if (what === 'plus' || what === 'minus') {
    var up = what === 'plus';
    if (c.zoom && c.zoom.max > c.zoom.min) {
      omi.cssZoom = false;
      omi.zoom = Math.max(c.zoom.min, Math.min(c.zoom.max, omi.zoom * (up ? 1.5 : 1 / 1.5)));
      k.applyConstraints({ advanced: [{ zoom: omi.zoom }] }).catch(function () {});
    } else { omi.cssZoom = true; omi.zoom = Math.max(1, Math.min(6, omi.zoom * (up ? 1.5 : 1 / 1.5))); }
  } else if (what === 'torch' && k) {
    omi.torch = !omi.torch && !!c.torch;
    k.applyConstraints({ advanced: [{ torch: omi.torch }] }).catch(function () { omi.torch = false; });
  } else if (what === 'hold') {
    omi.held = !omi.held;
    if (omi.held) pcam.pause(); else pcam.play().catch(function () {});
  }
  camBar(split() ? panel.mode : '');
}
function camBar(mode) {  // face.js showPanel(): the buttons of this camera view, or none
  var any = false;
  [].forEach.call(magEl.children, function (b) {
    var on = b.dataset.modes.split(' ').indexOf(mode) >= 0 && (b.dataset.id !== 'show' || omi.showAllowed);
    b.style.display = on ? '' : 'none'; any = any || on;
    if (b.dataset.id === 'show' || b.dataset.id === 'what') {   // these two say their word too
      b.textContent = (b.dataset.id === 'show' ? '📡 ' : '❓ ') + mt(b.dataset.id); b.classList.add('word');
    }
  });
  magEl.style.display = any ? 'flex' : 'none';
  [].forEach.call(magEl.children, function (b) {
    b.classList.toggle('on', (b.dataset.id === 'torch' && omi.torch) || (b.dataset.id === 'hold' && omi.held)
                             || (b.dataset.id === 'show' && omi.showing));
  });
  if (mode !== 'magnify') {
    if (omi.held) { omi.held = false; pcam.play().catch(function () {}); }
    if (omi.torch) { omi.torch = false; var k = magTrack(); if (k) k.applyConstraints({ advanced: [{ torch: false }] }).catch(function () {}); }
    omi.zoom = 1; omi.cssZoom = false;
    if (omi.full) { omi.full = false; panelEl.classList.remove('full'); }
    return;
  }
  pcam.style.transform = omi.cssZoom && omi.zoom > 1 ? 'scale(' + omi.zoom.toFixed(2) + ')' : 'none';
}

// ---- showing the picture to the PC: only when allowed, only while on, with the red badge ------------------------------
function showBadge() {
  showEl.textContent = '● ' + mt('showing');
  showEl.style.display = omi.showing ? 'block' : 'none';
  buildMenu(); camBar(split() ? panel.mode : '');
}
function startShow() {
  if (!omi.showAllowed) { tell(ot(lang, 'showNo'), lang, 6000); return; }
  if (['camera', 'camera_back', 'magnify'].indexOf(panel.mode) < 0) setPanel({ mode: 'camera' }, true);  // she sees what it shows
  omi.showing = true; showBadge(); send({ t: 'show', on: true });
  tell(ot(lang, 'showOn'), lang, 4000);
  var c = document.createElement('canvas');
  omi.showTimer = setInterval(function () {
    if (pcam.readyState < 2 || !pcam.videoWidth || !pcam.srcObject) return;
    c.width = SHOW_PX; c.height = Math.round(SHOW_PX * pcam.videoHeight / pcam.videoWidth);
    c.getContext('2d').drawImage(pcam, 0, 0, c.width, c.height);
    send({ t: 'frame', jpeg: c.toDataURL('image/jpeg', 0.6).split(',')[1] });
  }, 1000 / SHOW_FPS);
  omi.showOff = setTimeout(function () { stopShow(true); }, SHOW_MAX_MS);
}
function stopShow(tellBridge) {
  if (!omi.showing) return;
  clearInterval(omi.showTimer); clearTimeout(omi.showOff);
  omi.showing = false; showBadge();
  if (tellBridge) send({ t: 'show', on: false });
  tell(ot(lang, 'showOff'), lang, 3000);
}
showEl.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); stopShow(true); });  // a tap on the badge stops

// ---- the screen report (contract 0.6): what this screen shows, as keys and ids, for the bridge's mirrors (the Webots
// twin draws the same). Sent when it changes, and every 5 s; never a picture, never a sentence read aloud
function screenState() {
  var shown = function (el) { return el.style.display && el.style.display !== 'none'; };
  var hi = menuEl.querySelector('button.tour'), tiles = [].map.call(menuEl.children, function (b) { return b.dataset.mode; });
  return { t: 'screen', lang: lang, mode: panel.mode, expression: expression, style: panel.style || 'chips', menu: shown(menuEl),
           tiles: tiles, hi: hi ? hi.dataset.mode : '', toast: shown(toastEl) ? omi.toastKey || '' : '',
           arg: shown(toastEl) ? omi.toastArg || '' : '', note: shown(cardEl) ? cardId : '', badge: omi.showing, allowed: omi.showAllowed, speaking: speaking,
           sensors: panel.mode === 'sensors' ? sensorNumbers() : {} };
}
function sensorNumbers() {  // what the sensors panel shows, for the twin: numbers only, never the location
  var r1 = function (x) { return Math.round(x * 10) / 10; };
  return { battery: battery ? battery.level : null, charging: !!(battery && battery.charging),
           heading: lastHeading >= 0 ? Math.round(lastHeading) : null, acc: acc ? acc.map(r1) : null };
}
(function () {
  var last = '', at = 0;
  setInterval(function () {
    var s = JSON.stringify(screenState()), now = Date.now();
    if (s !== last || now - at > 5000) { last = s; at = now; send(JSON.parse(s)); }
  }, 250);
})();

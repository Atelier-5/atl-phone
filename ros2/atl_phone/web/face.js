// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// The robot's face (contract atl-phone/0.5). Plain ES2017, no libraries: old phones run it too. Only vision (see.js:
// the camera finding faces, markers, colours, objects, hands) and the helpers (omi.js: reading, "what is this?") load
// some, and only when asked.
// The phone is a peripheral: it draws what the bridge asks and reports what it senses; it decides nothing.
'use strict';

var Q = {};
location.search.slice(1).split('&').forEach(function (kv) { if (kv) { var p = kv.split('='); Q[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ''); } });
var OFFLINE = Q.offline === '1', STILL = Q.still === '1';
var LAYOUT = ['portrait', 'auto'].indexOf(Q.layout) >= 0 ? Q.layout : 'landscape';  // portrait: eyes on top, the panel below
// the page's language: ?lang=, else the one a program's panel asks for (Omi Assist: German), else the phone's own
var PHONE_LANG = (navigator.language || 'en').slice(0, 2);
if (['en', 'fr', 'de'].indexOf(PHONE_LANG) < 0) PHONE_LANG = 'en';
var SAVED_LANG = '';  // the last one a panel asked for: so the start screen, before the bridge is heard, speaks it too
try { SAVED_LANG = localStorage.getItem('atl-phone-lang') || ''; } catch (e) {}
var lang = Q.lang || (['en', 'fr', 'de'].indexOf(SAVED_LANG) >= 0 ? SAVED_LANG : PHONE_LANG);
document.documentElement.lang = lang;  // the tiles' words break where this language hyphenates
function setLang(l) {  // a panel's "lang": en, fr, de, or auto (the phone's own again); ?lang= wins
  var n = Q.lang || (l === 'auto' ? PHONE_LANG : l);
  try { if (l === 'auto') localStorage.removeItem('atl-phone-lang'); else localStorage.setItem('atl-phone-lang', l); } catch (e) {}
  if (['en', 'fr', 'de'].indexOf(n) < 0 || n === lang) return;
  lang = n; document.documentElement.lang = lang;
  var h = document.getElementById('hint');
  if (h) h.textContent = TEXT[lang].hint;
}

var TEXT = {
  en: { hint: 'Tap to wake the robot’s face', insecure: 'Not a secure page: motion may be blocked. Use USB (localhost) or HTTPS.' },
  fr: { hint: 'Touchez pour réveiller le visage du robot', insecure: 'Page non sécurisée : le mouvement peut être bloqué. Passez par USB (localhost) ou HTTPS.' },
  de: { hint: 'Tippe, um das Gesicht des Roboters zu wecken', insecure: 'Keine sichere Seite: Bewegung ist vielleicht gesperrt. USB (localhost) oder HTTPS nutzen.' }
};

// ---- the eyes ----------------------------------------------------------------------------------
// One eye: w, h (of the base size), r (corner radius, of the smaller side), top (upper lid, 0..1 of h),
// tilt (upper lid, degrees, + = inner corner down), bottom (lower crescent 0..1), dx, dy (of the base size), heart.
var EYE = { w: 0.8, h: 1, r: 0.28, top: 0, tilt: 0, bottom: 0, dx: 0, dy: 0, heart: 0 };
var EXPRESSIONS = {
  neutral: {},
  happy: { bottom: 0.6, h: 0.9, r: 0.5 },
  sad: { top: 0.4, tilt: -22, dy: 0.12, h: 0.85 },
  angry: { top: 0.4, tilt: 24, h: 0.85 },
  surprised: { w: 0.95, h: 1.2, r: 0.5 },
  sleepy: { top: 0.62, dy: 0.1 },
  curious: [{ w: 0.85, h: 1.1 }, { top: 0.38, h: 0.8, tilt: -8 }],
  wink: [{}, { bottom: 0.72, h: 0.8, r: 0.5 }],
  scared: { w: 0.6, h: 0.75, r: 0.5 },
  love: { heart: 1, w: 0.9, h: 0.9 }
};
function eyes(name) {
  var e = EXPRESSIONS[name] || {};
  var l = Array.isArray(e) ? e[0] : e, r = Array.isArray(e) ? e[1] : e;
  return [Object.assign({}, EYE, l), Object.assign({}, EYE, r)];
}

var canvas = document.getElementById('face'), ctx = canvas.getContext('2d');
var W = 0, H = 0, base = 0, eyeH = 0, apart = 0;  // eyeH: the height the eyes have (all of it, or the top half in portrait)
var expression = EXPRESSIONS[Q.expression] ? Q.expression : 'neutral';
var target = eyes(expression), cur = eyes(expression), GLANCE = eyes('surprised');
var color = [63, 216, 255];
var gaze = { x: 0, y: 0 }, gazeAt = 0, faceAim = { x: 0, y: 0 }, faceAt = -1e9, look = { x: 0, y: 0 }, nextLook = 0, eyeX = 0, eyeY = 0;
var blinkAt = -1e9, nextBlink = 0, speaking = false, ripples = [];
if (Q.gaze) { var g = Q.gaze.split(','); gaze.x = +g[0] || 0; gaze.y = +g[1] || 0; gazeAt = Infinity; }

function resize() {
  var dpr = Math.min(window.devicePixelRatio || 1, 1.5);  // old GPUs: a softer picture, a steady frame rate
  W = canvas.width = Math.round(innerWidth * dpr);
  H = canvas.height = Math.round(innerHeight * dpr);
  canvas.style.height = innerHeight + 'px';  // what shows, not 100vh: the panel and the menu are placed on the same line
  eyeH = split() ? Math.round(H * SPLIT) : H;
  var up = split();  // upright, the screen is narrow: bigger eyes, a little further apart
  base = Math.min(W * (up ? 0.32 : 0.26), eyeH * 0.55); apart = W * (up ? 0.22 : 0.2);
  showPanel();
}
window.addEventListener('resize', resize);

function setExpression(name) {
  if (!EXPRESSIONS[name]) return;
  expression = name; target = eyes(name);
}

function roundRect(x, y, w, h, r) {
  r = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath(); ctx.fill();
}
function heart(x, y, s) {
  ctx.beginPath();
  ctx.moveTo(x, y + s * 0.38);
  ctx.bezierCurveTo(x - s * 0.62, y - s * 0.02, x - s * 0.36, y - s * 0.56, x, y - s * 0.2);
  ctx.bezierCurveTo(x + s * 0.36, y - s * 0.56, x + s * 0.62, y - s * 0.02, x, y + s * 0.38);
  ctx.fill();
}

// side: +1 for the left eye (its inner corner is to the right), -1 for the right eye
function drawEye(p, cx, cy, side, blink, now) {
  var w = p.w * base, h = p.h * base * blink;
  var x = cx + p.dx * base, y = cy + p.dy * base;
  var rgb = p.heart > 0.5 ? [255, 90, 150] : color;
  ctx.fillStyle = 'rgb(' + rgb.join(',') + ')';
  ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = base * 0.08;
  if (p.heart > 0.5) { heart(x, y, base * 1.1 * (1 + 0.06 * Math.sin(now / 160))); ctx.shadowBlur = 0; return; }
  var x0 = x - w / 2, y0 = y - h / 2;
  roundRect(x0, y0, w, h, p.r * Math.min(w, h));
  ctx.shadowBlur = 0; ctx.fillStyle = '#000';
  var m = base * 0.15;  // the lids reach past the glow, or it shows at their ends
  if (p.top > 0.01) {
    var yl = y0 + p.top * h, s = side * Math.tan(p.tilt * Math.PI / 180) * (w / 2 + m);
    ctx.beginPath();
    ctx.moveTo(x0 - m, y0 - h); ctx.lineTo(x0 + w + m, y0 - h);
    ctx.lineTo(x0 + w + m, yl + s); ctx.lineTo(x0 - m, yl - s);
    ctx.closePath(); ctx.fill();
  }
  if (p.bottom > 0.01) {
    ctx.beginPath();
    ctx.ellipse(x, y0 + h + h * 0.55 - p.bottom * h * 0.8, w / 2 + m, h * 0.6, 0, 0, 2 * Math.PI);
    ctx.fill();
  }
}

var glanceUntil = 0;
function glance() { glanceUntil = performance.now() + 400; }  // a face came: wide eyes at once, before ROS answers
function step(now) {
  var k = STILL ? 1 : 0.22, goal = now < glanceUntil ? GLANCE : target;
  for (var i = 0; i < 2; i++) for (var key in EYE) cur[i][key] += (goal[i][key] - cur[i][key]) * k;
  // where the eyes look: as asked, or, left alone for a while, around the room
  if (!STILL && now - gazeAt > 4000 && now > nextLook) {
    look = Math.random() < 0.4 ? { x: 0, y: 0 } : { x: (Math.random() - 0.5) * 0.8, y: (Math.random() - 0.5) * 0.5 };
    nextLook = now + 1500 + Math.random() * 2500;
  }
  var aim = now - gazeAt <= 4000 || STILL ? gaze : now - faceAt < 1000 ? faceAim : look;  // asked, else at a face, else around
  eyeX += (aim.x - eyeX) * (STILL ? 1 : 0.15);
  eyeY += (aim.y - eyeY) * (STILL ? 1 : 0.15);
  if (!STILL && now > nextBlink) { blinkAt = now; nextBlink = now + 2000 + Math.random() * 4000; }
}

function draw(now) {
  step(now);
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  var t = (now - blinkAt) / 180, blink = t < 1 ? 0.08 + 0.92 * Math.abs(1 - 2 * t) : 1;
  var ox = eyeX * base * 0.35, oy = -eyeY * base * 0.25;
  if (speaking) oy += Math.sin(now / 50) * base * 0.02;
  if (expression === 'scared' && !STILL) { ox += (Math.random() - 0.5) * base * 0.02; oy += (Math.random() - 0.5) * base * 0.02; }
  drawEye(cur[0], W / 2 - apart + ox, eyeH / 2 + oy, 1, blink, now);
  drawEye(cur[1], W / 2 + apart + ox, eyeH / 2 + oy, -1, expression === 'wink' ? 1 : blink, now);
  if (split() && panel.mode === 'mouth') drawMouth(now);
  ripples = ripples.filter(function (r) { return now - r.t < 500; });
  ripples.forEach(function (r) {  // (a busy phone's frame can be older than the tap: never more than full)
    var a = Math.min(1, 1 - (now - r.t) / 500);
    ctx.strokeStyle = 'rgba(255,255,255,' + (a * 0.6) + ')'; ctx.lineWidth = base * 0.02;
    ctx.beginPath(); ctx.arc(r.x, r.y, base * (0.1 + 0.4 * (1 - a)), 0, 2 * Math.PI); ctx.stroke();
  });
}
function frame(now) {  // the next frame first: one that throws must not leave the screen black for good
  requestAnimationFrame(frame);
  try { draw(now); } catch (e) { if (!frame.said) { frame.said = true; console.error('face: a frame failed', e); } }
}

// ---- the panel: in portrait, the lower part of the screen is the robot's own input device -------------
// mouth (the default): follows the expression, and turns into a sound wave while the robot speaks; pad: buttons a
// program defines (a press goes to ROS as "pad"); off: the eyes alone; camera, camera_back: what that camera sees, on
// this screen only; sensors: what the phone senses. A tap on the eyes opens the menu, a swipe left or right steps
// through it; a program sets which modes it offers ("menu"), and learns what the person picked ("panel" back).
var SPLIT = 0.54;  // of the height, for the eyes
var MODES = ['mouth', 'pad', 'off', 'camera', 'camera_back', 'sensors', 'magnify'];
// the menu's style: chips (a strip, for the class) or tiles (big, each says its name, for someone who sees less well);
// an entry is a mode, a tile (TILES: omi.js does it), or a program's own {id, label, icon}: every pick goes to ROS (menu)
var TILES = ['time', 'magnify', 'read', 'what', 'front', 'back', 'show', 'follow'];
var ICON = TEXTS.icon;
var SPEAKS = ['time', 'read', 'what', 'follow', 'show', 'face'];  // these tiles speak for themselves: not their name first
var MODE_TEXT = TEXTS.mode;  // the words: texts.js, shared with the Webots twin
function mt(k) { return MODE_TEXT[lang][k] || MODE_TEXT.en[k] || k; }
var DEFAULT_PANEL = { mode: 'mouth', buttons: [{ id: 'a', label: 'A', rgb: [64, 217, 255] }, { id: 'b', label: 'B', rgb: [51, 255, 102] },
                                               { id: 'c', label: 'C', rgb: [255, 204, 51] }, { id: 'd', label: 'D', rgb: [255, 102, 178] }] };
var panel = { mode: MODES.indexOf(Q.panel) >= 0 ? Q.panel : DEFAULT_PANEL.mode, buttons: DEFAULT_PANEL.buttons,
              menu: MODES.slice(0, 6), style: Q.style === 'tiles' ? 'tiles' : 'chips' };
var panelEl = document.getElementById('panel'), padEl = document.getElementById('pad'), pcam = document.getElementById('pcam');
var sensorsEl = document.getElementById('sensors'), menuEl = document.getElementById('menu'), menuOff = 0, lastPad = '';
function upright() { return LAYOUT !== 'landscape' && innerHeight > innerWidth; }
function split() { return upright() && panel.mode !== 'off'; }
function panelFacing() {
  return !upright() ? '' : panel.mode === 'camera' ? 'user' : panel.mode === 'camera_back' || panel.mode === 'magnify' ? 'environment' : '';
}
function entryId(x) { return typeof x === 'string' ? x : x.id; }
function entryLabel(x) {
  if (typeof x === 'string') return mt(x);
  var l = x.label || x.id;
  return typeof l === 'string' ? l : l[lang] || l.en || l.de || l.fr || x.id;
}
function setPanel(m, mine) {  // mine: the person picked it here, so the bridge is told
  if (Array.isArray(m.menu)) panel.menu = m.menu.filter(function (x) {
    return typeof x === 'string' ? MODES.indexOf(x) >= 0 || TILES.indexOf(x) >= 0 : !!(x && x.id);
  });
  if (!panel.menu.length) panel.menu = MODES.slice(0, 6);
  if (m.style === 'tiles' || m.style === 'chips') panel.style = m.style;
  if (m.lang) setLang(m.lang);
  if (Array.isArray(m.buttons)) panel.buttons = m.buttons.slice(0, 8);
  if (MODES.indexOf(m.mode) >= 0 && m.mode !== panel.mode) {
    panel.mode = m.mode;
    if (mine) send({ t: 'panel', mode: m.mode });
  }
  resize(); buildMenu();
}
function stepMode(d) {  // a swipe on the eyes: the next or previous mode of the menu
  var modes = panel.menu.filter(function (x) { return MODES.indexOf(x) >= 0; }), i = modes.indexOf(panel.mode), n = modes.length;
  if (!n) return;
  setPanel({ mode: modes[((i < 0 ? 0 : i) + d + n) % n] }, true);
  showMenu();
}
function pick(x, el) {  // a chip or a tile: the bridge hears of it; a tile says its name first (unless it speaks itself)
  var id = entryId(x), tiles = panel.style === 'tiles', was = panel.mode;
  if (typeof tourStop === 'function') tourStop();  // omi.js: a tap ends the presentation
  send({ t: 'menu', id: id });
  if (tiles) {
    if (navigator.vibrate) navigator.vibrate(30);
    if (el) { el.classList.add('flash'); setTimeout(function () { el.classList.remove('flash'); }, 300); }
    if (SPEAKS.indexOf(id) < 0) speak(entryLabel(x), lang);
  }
  if (id === 'face') {  // the last tile: back to the face, whatever was on (reading, the magnifier, showing)
    if (typeof omiHome === 'function') omiHome();
    setPanel({ mode: 'mouth' }, true); hideMenu();
    if (typeof omiBack === 'function') omiBack(); else if (tiles) speak(entryLabel(x), lang);
    return;
  }
  if (MODES.indexOf(id) >= 0) setPanel({ mode: id }, true);
  else if (id === 'front' || id === 'back') setPanel({ mode: id === 'front' ? 'camera' : 'camera_back' }, true);
  if (typeof omiTile === 'function' && TILES.indexOf(id) >= 0) omiTile(id, was);  // omi.js: time, read, what, show, follow, magnify
  if (tiles && id !== 'follow' && id !== 'show') setTimeout(hideMenu, 400); else showMenu();
}
function buildMenu() {
  var tiles = panel.style === 'tiles', list = tiles ? panel.menu.concat(['face']) : panel.menu;
  var key = list.map(function (x) { return entryId(x) + ':' + entryLabel(x); }).join(',') + '|' + lang + '|' + panel.style;
  if (menuEl.dataset.key !== key) {
    menuEl.dataset.key = key; menuEl.textContent = '';
    menuEl.className = tiles ? 'tiles' : '';
    list.forEach(function (x) {
      var b = document.createElement('button'), id = entryId(x);
      if (tiles) {
        var i = document.createElement('i'), s = document.createElement('span');
        i.textContent = (typeof x === 'object' && x.icon) || ICON[id] || '•'; s.textContent = entryLabel(x);
        b.appendChild(i); b.appendChild(s);
      } else b.textContent = entryLabel(x);
      b.dataset.mode = id;
      b.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); pick(x, b); });
      b.addEventListener('contextmenu', function (e) { e.preventDefault(); });
      menuEl.appendChild(b);
    });
  }
  var mode = { camera: 'front', camera_back: 'back' }[panel.mode];
  [].forEach.call(menuEl.children, function (b) {
    var on = b.dataset.mode === panel.mode || b.dataset.mode === mode || (b.dataset.mode === 'follow' && typeof vision === 'object' && vision.follow);
    b.classList.toggle('on', !!on);
  });
}
function splitY() { return Math.round(innerHeight * SPLIT); }  // css px: where the eyes end and the panel begins
function hideMenu() { clearTimeout(menuOff); menuEl.style.display = 'none'; }
function showMenu() {
  var tiles = panel.style === 'tiles';
  if (!upright() && !tiles) return;
  buildMenu(); clearTimeout(menuOff);
  if (tiles) {  // the lower three quarters (in landscape the whole screen): the eyes still show above
    menuEl.style.display = 'grid'; menuEl.style.bottom = '0';
    menuEl.style.top = upright() ? Math.round(innerHeight * 0.25) + 'px' : '0';
    menuEl.style.gridTemplateColumns = 'repeat(' + (upright() ? 3 : Math.ceil(menuEl.children.length / 2)) + ', 1fr)';
  } else {
    menuEl.style.display = 'flex'; menuEl.style.top = ''; menuEl.style.bottom = (innerHeight - splitY() + 8) + 'px';
    menuEl.style.gridTemplateColumns = '';
  }
  menuOff = setTimeout(hideMenu, tiles ? 10000 : 6000);
}
function showPanel() {
  var on = split(), mode = on ? panel.mode : '';
  panelEl.style.display = mode && mode !== 'mouth' ? 'flex' : 'none';
  panelEl.style.top = splitY() + 'px';
  if (menuEl.style.display === 'flex') menuEl.style.bottom = (innerHeight - splitY() + 8) + 'px';
  padEl.style.display = mode === 'pad' ? 'grid' : 'none';
  sensorsEl.style.display = mode === 'sensors' ? 'grid' : 'none';
  var picture = mode === 'camera' || mode === 'camera_back' || mode === 'magnify';
  pcam.style.display = picture ? 'block' : 'none';
  pcam.style.transform = mode === 'camera' ? 'scaleX(-1)' : 'none';  // the front camera as a mirror
  if (typeof camBar === 'function') camBar(mode);  // omi.js: the camera view's buttons (zoom, torch, hold; what is this?; Zeigen)
  geoWatch(mode === 'sensors');
  var cols = panel.buttons.length <= 4 ? 2 : panel.buttons.length <= 6 ? 3 : 4;
  padEl.style.gridTemplateColumns = 'repeat(' + cols + ', 1fr)';
  var key = panel.buttons.map(function (b) { return b.id + '|' + b.label + '|' + b.rgb; }).join(',');
  if (padEl.dataset.key !== key) {
    padEl.dataset.key = key; padEl.textContent = '';
    panel.buttons.forEach(function (b) {
      var el = document.createElement('button');
      el.textContent = b.label || b.id; el.dataset.id = b.id;
      var c = (b.rgb || [64, 217, 255]).join(',');
      el.style.borderColor = 'rgb(' + c + ')'; el.style.color = 'rgb(' + c + ')'; el.style.background = 'rgba(' + c + ',0.12)';
      el.addEventListener('pointerdown', function (e) {
        e.preventDefault(); el.classList.add('down');
        if (navigator.vibrate) navigator.vibrate(15);
        lastPad = b.label || b.id;
        send({ t: 'pad', id: b.id });
      });
      el.addEventListener('pointerup', function () { el.classList.remove('down'); });
      el.addEventListener('pointerleave', function () { el.classList.remove('down'); });
      el.addEventListener('contextmenu', function (e) { e.preventDefault(); });
      padEl.appendChild(el);
    });
  }
  var f = panelFacing();
  if (f !== want.panel) {
    want.panel = f;
    if (f) openCam().then(attachPanelCam, function () {}); else closeCamIfIdle();
  }
  attachPanelCam();
}
function attachPanelCam() {  // the picture of the camera the panel wants, when that one is open (the torch, the test and vision win)
  var f = panelFacing(), mine = !!f && !!cam && camFacing === f;
  if (mine && pcam.srcObject !== cam) { pcam.srcObject = cam; pcam.play().catch(function () {}); }
  if (!mine && pcam.srcObject) pcam.srcObject = null;
  pcam.title = f && !mine ? mt('busy') : '';
}
// a note: a big card over the face (a reminder), with up to three buttons; the pressed one goes to ROS ("answer").
// A tap on its text says it again.
var cardEl = document.getElementById('card'), cardId = '';
function noteCard(m) {
  if (!m.text) { if (!m.id || m.id === cardId) { cardEl.style.display = 'none'; cardId = ''; } return; }
  cardId = m.id || 'note'; cardEl.textContent = ''; hideMenu();
  var p = document.createElement('p'), row = document.createElement('div');
  p.textContent = m.text;
  p.addEventListener('pointerdown', function (e) { e.preventDefault(); speak(m.text, lang); });
  (m.buttons || []).forEach(function (b) {
    var el = document.createElement('button');
    el.textContent = entryLabel(b);
    el.addEventListener('pointerdown', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (navigator.vibrate) navigator.vibrate(30);
      send({ t: 'answer', note: cardId, id: b.id });
      speak(entryLabel(b), lang);
      cardEl.style.display = 'none'; cardId = '';
    });
    row.appendChild(el);
  });
  if (!row.children.length) cardEl.addEventListener('pointerdown', function close() {  // no button: a tap puts it away
    cardEl.removeEventListener('pointerdown', close); cardEl.style.display = 'none'; cardId = '';
  });
  cardEl.appendChild(p); cardEl.appendChild(row); cardEl.style.display = 'flex';
  if (m.say) speak(m.text, lang);
}
// the sensor panel: what this phone senses, drawn here. Its numbers go in the screen report (for the twin), but the
// location never leaves this screen: it is asked only while the panel shows, and given to no one
var acc = null, sentN = 0, sentRate = 0, geo = { watch: null, at: null, err: '' };
function geoWatch(on) {
  if (!navigator.geolocation) return;
  if (on && geo.watch === null) {
    geo.watch = navigator.geolocation.watchPosition(function (p) { geo.at = p.coords; geo.err = ''; },
      function (e) { geo.err = e.code === 1 ? 'blocked' : ''; }, { enableHighAccuracy: false, maximumAge: 60000, timeout: 30000 });
  } else if (!on && geo.watch !== null) { navigator.geolocation.clearWatch(geo.watch); geo.watch = null; geo.at = null; }
}
setInterval(function () { sentRate = sentN; sentN = 0; }, 1000);
function tile(k, v, extra) { return '<div class="tile"><b>' + mt(k) + '</b><span>' + v + '</span>' + (extra || '') + '</div>'; }
function updateSensors() {
  if (sensorsEl.style.display !== 'grid') return;
  var bubble = '';
  if (acc) {
    var bx = Math.max(-1, Math.min(1, -acc[0] / 9.81)), by = Math.max(-1, Math.min(1, acc[1] / 9.81));
    bubble = '<i class="bubble"><i style="left:' + (50 + bx * 40) + '%;top:' + (50 + by * 40) + '%"></i></i>';
  }
  var v = typeof visionState === 'function' ? visionState() : '';
  sensorsEl.innerHTML =
    tile('battery', battery ? Math.round(battery.level * 100) + '%' + (battery.charging ? ' ⚡' : '') : mt('none')) +
    tile('tilt', acc ? acc.map(function (a) { return a.toFixed(1); }).join(' ') : mt('none'), bubble) +
    tile('compass', lastHeading >= 0 ? Math.round(lastHeading) + '°' : mt('none'),
         lastHeading >= 0 ? '<i class="needle" style="transform:rotate(' + lastHeading + 'deg)"></i>' : '') +
    tile('link', (ws && ws.readyState === 1 ? '● ' : '○ ') + sentRate + '/s') +
    tile('location', geo.at ? geo.at.latitude.toFixed(4) + '°' : geo.err ? mt('blocked') : mt('none'),
         geo.at ? '<small>' + geo.at.longitude.toFixed(4) + '° ±' + Math.round(geo.at.accuracy) + ' m</small>' : '') +
    tile('vision', v || mt('none')) +
    tile('pressed', lastPad || mt('none'));
}
setInterval(updateSensors, 250);
// the mouth: a curve whose bend follows the expression; while the robot speaks, a sound wave. The browser does not hand
// out the voice's sound, so the wave follows the words (each word a burst) instead of the samples.
var MOUTHS = { neutral: [0.15, 0], happy: [0.6, 0.15], sad: [-0.45, 0], angry: [-0.2, 0], surprised: [0, 0.55], sleepy: [0.05, 0],
               curious: [0.1, 0.2], wink: [0.4, 0], scared: [-0.15, 0.25], love: [0.7, 0.2] };
var mouthNow = [0.15, 0], wave = { env: 0, amp: [], word: 0 };
for (var wi = 0; wi < 48; wi++) wave.amp.push(0);
function word() { wave.env = 1; wave.word++; }
function drawMouth(now) {
  var cx = W / 2, cy = eyeH + (H - eyeH) * 0.45, w = W * 0.42, u = (H - eyeH) * 0.18;
  ctx.fillStyle = ctx.strokeStyle = 'rgb(' + color.join(',') + ')';
  ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = base * 0.08;
  ctx.lineWidth = Math.max(4, u * 0.28); ctx.lineCap = ctx.lineJoin = 'round';
  wave.env = speaking ? Math.max(0.3, wave.env * 0.93) : wave.env * 0.85;
  wave.amp.shift(); wave.amp.push(wave.env * (STILL ? 0.8 : 0.35 + 0.65 * Math.random()));
  if (wave.amp.some(function (a) { return a > 0.02; })) {  // speaking: the wave scrolls from right to left
    var n = wave.amp.length, ww = W * 0.8;
    ctx.lineWidth = Math.max(3, u * 0.14);
    ctx.beginPath();
    for (var i = 0; i < n; i++) {
      var x = cx - ww / 2 + ww * i / (n - 1), fade = Math.sin(Math.PI * i / (n - 1));
      var y = cy + Math.sin(i * 1.7 + now / 45) * wave.amp[i] * u * 2.2 * fade;
      if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    }
    ctx.stroke(); ctx.shadowBlur = 0;
    mouthNow[1] = 0;
    return;
  }
  var shape = MOUTHS[expression] || MOUTHS.neutral, k = STILL ? 1 : 0.2;
  mouthNow[0] += (shape[0] - mouthNow[0]) * k; mouthNow[1] += (shape[1] - mouthNow[1]) * k;
  var bend = mouthNow[0] * u, gap = Math.max(0, mouthNow[1]) * u;
  ctx.beginPath();
  ctx.moveTo(cx - w / 2, cy - bend / 2);
  ctx.quadraticCurveTo(cx, cy + bend * 1.5, cx + w / 2, cy - bend / 2);
  if (gap > 1) { ctx.quadraticCurveTo(cx, cy + bend * 1.5 + gap * 2, cx - w / 2, cy - bend / 2); ctx.fill(); }
  ctx.stroke();
  ctx.shadowBlur = 0;
}

// ---- the link to the bridge ----------------------------------------------------------------------
var ws = null, retry = 1000;
function send(o) { if (ws && ws.readyState === 1) { ws.send(JSON.stringify(o)); sentN++; } }
function caps() {
  return { motion: 'DeviceMotionEvent' in window, compass: 'ondeviceorientationabsolute' in window,
           tts: 'speechSynthesis' in window, vibrate: 'vibrate' in navigator, battery: 'getBattery' in navigator,
           wakelock: 'wakeLock' in navigator, camera: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
           barcode: 'BarcodeDetector' in window };
}
function phoneId() {  // a random id kept in this browser: it ties this phone's check report to its face, and says nothing about the phone
  try {
    var id = localStorage.getItem('atl-phone-id');
    if (!/^[0-9a-f]{16}$/.test(id || '')) {
      id = Array.prototype.map.call(crypto.getRandomValues(new Uint8Array(8)), function (b) { return (b + 256).toString(16).slice(1); }).join('');
      localStorage.setItem('atl-phone-id', id);
    }
    return id;
  } catch (e) { return ''; }  // storage blocked: the setup page falls back to the model
}
function hello() {  // Chrome hides the model in the user agent ("K"); client hints still tell it, on a secure page
  var h = { t: 'hello', id: phoneId(), ua: navigator.userAgent, secure: !!window.isSecureContext, caps: caps(), screen: [screen.width, screen.height] };
  var uad = navigator.userAgentData;
  (uad && uad.getHighEntropyValues ? uad.getHighEntropyValues(['model']).catch(function () { return {}; }) : Promise.resolve({}))
    .then(function (v) { h.model = v.model || ''; send(h); sendBattery(); });
}
function connect() {
  var url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws' + (Q.key ? '?key=' + encodeURIComponent(Q.key) : '');
  ws = new WebSocket(url);
  ws.onopen = function () {
    retry = 1000; document.getElementById('link').className = 'dot on';
    hello();
  };
  ws.onclose = function (e) {
    document.getElementById('link').className = 'dot';
    if (e.code === 4000) return;  // another phone took over: this one stays quiet
    setTimeout(connect, retry); retry = Math.min(retry * 2, 5000);
  };
  ws.onmessage = function (e) { var m; try { m = JSON.parse(e.data); } catch (x) { return; } handle(m); };
}
function handle(m) {
  if (m.t === 'face') setExpression(m.expression);
  else if (m.t === 'gaze') { gaze = { x: +m.x || 0, y: +m.y || 0 }; gazeAt = performance.now(); }
  else if (m.t === 'color' && m.rgb && m.rgb.length === 3) color = m.rgb.map(function (v) { return Math.max(0, Math.min(255, v | 0)); });
  else if (m.t === 'say') speak(String(m.text || ''), m.lang || lang);
  else if (m.t === 'torch') torch(!!m.on);
  else if (m.t === 'camera') camera(!!m.on);
  else if (m.t === 'look') lookAt(!!m.on, !!m.familiar);
  else if (m.t === 'forget') forget();
  else if (m.t === 'vibrate' && navigator.vibrate) navigator.vibrate(Math.max(0, Math.min(2000, m.ms | 0)));
  else if (m.t === 'panel') setPanel(m);
  else if (m.t === 'see') seeAt(m);
  else if (m.t === 'note') noteCard(m);
  else if (['read', 'what', 'show', 'tour'].indexOf(m.t) >= 0 && typeof omiAsk === 'function') omiAsk(m);  // omi.js
  else if (m.t === 'web' && /^[0-9a-f]{16}$/.test(m.id)) newPages(m.id);
  else if (m.t === 'open' && ['face.html', 'check.html'].indexOf(m.page) >= 0) {
    var q = Object.assign({}, Q);
    if (['landscape', 'portrait', 'auto'].indexOf(m.layout) >= 0) q.layout = m.layout;
    location.href = m.page + query(q);
  }
}
function query(q) { return '?' + Object.keys(q).map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(q[k]); }).join('&'); }
var pages = null;  // the fingerprint of the bridge's pages, as first got: another one means it restarted with new pages
function newPages(id) {
  if (pages === null || pages === id) { pages = id; return; }
  // this page's code is older than the bridge's: load the new one, started at once (what needs a tap waits for the next touch)
  location.replace(location.pathname + query(Object.assign({}, Q, { autostart: '1' })));
}

// ---- voice -----------------------------------------------------------------------------------------
// Some phones (the ANE-LX1) say their voices' languages as fr_FR and load them late: an utterance with a language and no
// voice then never starts. So the voice is always chosen (the country's first), after the voices are there, and a voice
// that has not started in 3 s is asked again once.
var LANG_TAG = { en: 'en-GB', fr: 'fr-FR', de: 'de-DE' }, voicesWait = [];
function voiceFor(l) {
  var tag = LANG_TAG[l] || 'en-GB', vs = speechSynthesis.getVoices(), norm = function (v) { return v.lang.replace('_', '-'); };
  return vs.filter(function (v) { return norm(v) === tag; })[0] || vs.filter(function (v) { return norm(v).slice(0, 2) === tag.slice(0, 2); })[0];
}
if ('speechSynthesis' in window) speechSynthesis.addEventListener('voiceschanged', function () {
  var w = voicesWait; voicesWait = []; w.forEach(function (f) { f(); });
});
function warmVoice() {  // the first words after a load took over 6 s to start on the ANE-LX1: wake the voice now, silently
  if (!speechSynthesis.getVoices().length) { voicesWait.push(warmVoice); return; }
  var u = new SpeechSynthesisUtterance(' ');
  u.volume = 0; u.lang = LANG_TAG[lang] || 'en-GB';
  var v = voiceFor(lang);
  if (v) u.voice = v;
  speechSynthesis.speak(u);
}
function speak(text, l, again, done) {  // done: called when it was said to its end (reading goes on with the next sentence)
  if (!('speechSynthesis' in window) || !text) return;
  if (!speechSynthesis.getVoices().length && !again) {  // not loaded yet: in a moment, or without a voice after 2 s
    var go = function () { if (go) { go = null; speak(text, l, true, done); } };
    voicesWait.push(go); setTimeout(go, 2000); return;
  }
  speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text), started = false;
  u.lang = LANG_TAG[l] || 'en-GB';
  var v = voiceFor(l);
  if (v) u.voice = v;
  u.onstart = function () { started = true; speaking = true; word(); };
  u.onboundary = word;  // each word: a burst of the mouth's wave
  u.onerror = function () { speaking = false; };
  u.onend = function () { speaking = false; if (done) done(); };
  speechSynthesis.speak(u);
  setTimeout(function () { if (!started && again !== 'retried') { speechSynthesis.cancel(); speak(text, l, 'retried', done); } }, 3000);
}

// ---- the camera: the torch and the setup page's camera test use the back camera; vision (see.js: look, see) the camera
// it was asked for; the panel's picture the one picked. A phone opens one at a time: the torch and the test win, then
// vision, then the panel's picture, which shows only when its camera is the one open. The face shows that one is on.
// Pictures stay on the phone: what leaves it is whether it works, its size, the codes it read and where faces are.
var cam = null, camFacing = '', camOpening = null, want = { torch: false, view: false, look: false, panel: '', still: false }, camOk = false;
var view = document.getElementById('view'), viewOff = 0, scanTimer = 0, lastCode = '';
function camReport(o) { o.t = 'camera'; o.on = !!cam && camFacing === 'environment'; o.ok = 'ok' in o ? o.ok : camOk; camOk = o.ok; send(o); }
function camError(e) { return (e && e.name) || String(e); }
function facing() {  // with tiles, what the person picked (a camera, the magnifier) wins over vision, which waits meanwhile
  if (want.torch || want.view || want.still) return 'environment';
  return panel.style === 'tiles' && want.panel ? want.panel : visionFacing() || want.panel;
}
function eyeBadge() {
  var b = document.getElementById('eye');
  b.style.display = cam ? 'block' : 'none';
  b.textContent = visionFacing() && camFacing === visionFacing() ? '● look' : '● cam';
}
function stopCam() {
  if (cam) cam.getTracks().forEach(function (k) { k.stop(); });
  cam = null; camFacing = ''; eyeBadge();
}
function openCam() {
  var f = facing();
  if (cam && camFacing === f) return Promise.resolve(cam);
  if (camOpening) return camOpening.then(openCam);
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return Promise.reject({ name: window.isSecureContext ? 'NoCamera' : 'NotSecure' });
  }
  stopCam();
  camOpening = navigator.mediaDevices.getUserMedia({ video: { facingMode: f, width: { ideal: f === 'user' ? 640 : 1280 } }, audio: false })
    .then(function (s) {
      camOpening = null;
      if (facing() !== f) { s.getTracks().forEach(function (k) { k.stop(); }); return openCam(); }  // asked for the other one meanwhile
      cam = s; camFacing = f; eyeBadge(); showPanel(); return s;
    }, function (e) { camOpening = null; throw e; });
  return camOpening;
}
function closeCamIfIdle() {  // nobody needs this camera any more: close it (look reopens the front one by itself, the panel here)
  if (cam && camFacing !== facing()) stopCam();
  if (!cam && want.panel && facing() === want.panel) openCam().then(attachPanelCam, function () {});
}
function torch(on) {
  want.torch = on;
  if (!on) {
    if (cam && camFacing === 'environment') cam.getVideoTracks()[0].applyConstraints({ advanced: [{ torch: false }] }).catch(function () {});
    closeCamIfIdle(); return;
  }
  openCam().then(function (s) {
    var k = s.getVideoTracks()[0], c = k.getCapabilities ? k.getCapabilities() : {};
    if (!c.torch) { want.torch = false; closeCamIfIdle(); camReport({ ok: true, torch: false }); return; }
    return k.applyConstraints({ advanced: [{ torch: true }] }).then(function () { camReport({ ok: true, torch: true }); });
  }).catch(function (e) { want.torch = false; closeCamIfIdle(); camReport({ ok: false, error: camError(e), torch: false }); });
}
function camera(on) {  // the setup page's test: the picture on the phone's screen for a minute, codes read on the phone
  want.view = on; clearTimeout(viewOff); clearInterval(scanTimer);
  if (!on) { view.style.display = 'none'; view.srcObject = null; closeCamIfIdle(); camReport({}); return; }
  openCam().then(function (s) {
    if (!want.view) return closeCamIfIdle();
    view.srcObject = s; view.style.display = 'block'; view.play().catch(function () {});
    var st = s.getVideoTracks()[0].getSettings ? s.getVideoTracks()[0].getSettings() : {};
    camReport({ ok: true, size: [st.width || 0, st.height || 0] });
    viewOff = setTimeout(function () { camera(false); }, 60000);
    var det = null; lastCode = '';
    try { det = 'BarcodeDetector' in window ? new BarcodeDetector() : null; } catch (e) {}
    if (det) scanTimer = setInterval(function () {
      if (view.readyState < 2) return;
      det.detect(view).then(function (cs) {
        if (cs.length && cs[0].rawValue !== lastCode) { lastCode = cs[0].rawValue; camReport({ ok: true, code: lastCode }); }
      }).catch(function () {});
    }, 400);
  }).catch(function (e) { want.view = false; closeCamIfIdle(); camReport({ ok: false, error: camError(e) }); });
}

// ---- senses ------------------------------------------------------------------------------------------
var lastImu = 0, lastHeading = -1, lastHeadingAt = 0;
window.addEventListener('devicemotion', function (e) {
  var now = performance.now(); if (now - lastImu < 33) return; lastImu = now;
  var a = e.accelerationIncludingGravity, r = e.rotationRate, d = Math.PI / 180;
  if (!a || a.x == null) return;
  acc = [a.x, a.y, a.z];
  send({ t: 'imu', acc: acc, gyro: r && r.alpha != null ? [r.beta * d, r.gamma * d, r.alpha * d] : [0, 0, 0] });
});
window.addEventListener('deviceorientationabsolute', function (e) {
  if (e.alpha == null) return;
  var now = performance.now(), h = (360 - e.alpha) % 360;
  if (now - lastHeadingAt < 200 || Math.abs(h - lastHeading) < 1) return;
  lastHeading = h; lastHeadingAt = now; send({ t: 'heading', deg: h });
});
var battery = null;
function sendBattery() { if (battery) send({ t: 'battery', level: battery.level, charging: battery.charging }); }
if (navigator.getBattery) navigator.getBattery().then(function (b) {
  battery = b; b.onlevelchange = b.onchargingchange = sendBattery; sendBattery();
});

// touch: tap, long press ("pet") or swipe, in the left, centre or right third
var down = null;
canvas.addEventListener('pointerdown', function (e) { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
canvas.addEventListener('pointercancel', function () { down = null; });
canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });  // a long press is the robot's, not the browser's
canvas.addEventListener('pointerup', function (e) {
  if (!down) return;
  var dx = e.clientX - down.x, dy = e.clientY - down.y, dt = performance.now() - down.t;
  var zone = ['left', 'centre', 'right'][Math.min(2, Math.floor(down.x / innerWidth * 3))];
  var m = { t: 'touch', zone: zone };
  if (Math.sqrt(dx * dx + dy * dy) > 60) { m.kind = 'swipe'; m.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'); }
  else m.kind = dt > 600 ? 'long' : 'tap';
  if (upright() && m.kind === 'tap') showMenu();                                       // upright: a tap opens the menu,
  if (upright() && m.kind === 'swipe' && (m.dir === 'left' || m.dir === 'right')) stepMode(m.dir === 'left' ? 1 : -1);  // a swipe steps through it
  var dpr = W / innerWidth; ripples.push({ x: down.x * dpr, y: down.y * dpr, t: performance.now() });
  send(m); down = null;
});

// ---- start: full screen, turned as the layout wants, screen on, motion permission: they all need a tap ----------------
var lock = null;
function keepAwake() { if (navigator.wakeLock && document.visibilityState === 'visible') navigator.wakeLock.request('screen').then(function (l) { lock = l; }).catch(function () {}); }
document.addEventListener('visibilitychange', keepAwake);
function start() {
  document.getElementById('start').style.display = 'none';
  tapped();
  keepAwake();
  // started without a tap (autostart, or reloaded for a new bridge): full screen and the voice come with her first touch
  if (navigator.userActivation && !navigator.userActivation.isActive) document.addEventListener('pointerdown', tapped, { once: true });
  connect();
}
function tapped() {  // what the browser allows only during a tap
  var el = document.documentElement, fs = el.requestFullscreen || el.webkitRequestFullscreen;
  var p = fs && !(document.fullscreenElement || document.webkitFullscreenElement) ? fs.call(el) : null;
  var turn = { landscape: 'landscape', portrait: 'portrait' }[LAYOUT];  // auto: as the phone is held
  if (p && p.then) p.then(function () { if (turn && screen.orientation && screen.orientation.lock) return screen.orientation.lock(turn); }).catch(function () {});
  if (window.DeviceMotionEvent && DeviceMotionEvent.requestPermission) DeviceMotionEvent.requestPermission().catch(function () {});
  if ('speechSynthesis' in window) warmVoice();
}

resize();
if (OFFLINE) {
  document.getElementById('start').style.display = 'none';
  document.getElementById('link').style.display = 'none';
} else {
  document.getElementById('hint').textContent = TEXT[lang].hint;
  if (!window.isSecureContext) document.getElementById('note').textContent = TEXT[lang].insecure;
  document.getElementById('go').onclick = start;
  if (Q.autostart === '1') start();  // a phone in kiosk mode, or a test: what needs a tap may then be refused
}
requestAnimationFrame(frame);  // still pictures too: a frame drawn before layout would stay black
if ('serviceWorker' in navigator && window.isSecureContext && !OFFLINE) navigator.serviceWorker.register('sw.js').catch(function () {});  // installable

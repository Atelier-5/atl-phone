// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// The robot's face (contract atl-phone/0.1). Plain ES2017, no libraries: old phones run it too.
// The phone is a peripheral: it draws what the bridge asks and reports what it senses; it decides nothing.
'use strict';

var Q = {};
location.search.slice(1).split('&').forEach(function (kv) { if (kv) { var p = kv.split('='); Q[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ''); } });
var OFFLINE = Q.offline === '1', STILL = Q.still === '1';
var lang = Q.lang || (navigator.language || 'en').slice(0, 2);
if (['en', 'fr', 'de'].indexOf(lang) < 0) lang = 'en';

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
var W = 0, H = 0, base = 0;
var expression = EXPRESSIONS[Q.expression] ? Q.expression : 'neutral';
var target = eyes(expression), cur = eyes(expression);
var color = [63, 216, 255];
var gaze = { x: 0, y: 0 }, gazeAt = 0, look = { x: 0, y: 0 }, nextLook = 0, eyeX = 0, eyeY = 0;
var blinkAt = -1e9, nextBlink = 0, speaking = false, ripples = [];
if (Q.gaze) { var g = Q.gaze.split(','); gaze.x = +g[0] || 0; gaze.y = +g[1] || 0; gazeAt = Infinity; }

function resize() {
  var dpr = Math.min(window.devicePixelRatio || 1, 1.5);  // old GPUs: a softer picture, a steady frame rate
  W = canvas.width = Math.round(innerWidth * dpr);
  H = canvas.height = Math.round(innerHeight * dpr);
  base = Math.min(W * 0.26, H * 0.55);
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

function step(now) {
  var k = STILL ? 1 : 0.22;
  for (var i = 0; i < 2; i++) for (var key in EYE) cur[i][key] += (target[i][key] - cur[i][key]) * k;
  // where the eyes look: as asked, or, left alone for a while, around the room
  if (!STILL && now - gazeAt > 4000 && now > nextLook) {
    look = Math.random() < 0.4 ? { x: 0, y: 0 } : { x: (Math.random() - 0.5) * 0.8, y: (Math.random() - 0.5) * 0.5 };
    nextLook = now + 1500 + Math.random() * 2500;
  }
  var aim = now - gazeAt <= 4000 || STILL ? gaze : look;
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
  drawEye(cur[0], W / 2 - W * 0.2 + ox, H / 2 + oy, 1, blink, now);
  drawEye(cur[1], W / 2 + W * 0.2 + ox, H / 2 + oy, -1, expression === 'wink' ? 1 : blink, now);
  ripples = ripples.filter(function (r) { return now - r.t < 500; });
  ripples.forEach(function (r) {
    var a = 1 - (now - r.t) / 500;
    ctx.strokeStyle = 'rgba(255,255,255,' + (a * 0.6) + ')'; ctx.lineWidth = base * 0.02;
    ctx.beginPath(); ctx.arc(r.x, r.y, base * (0.1 + 0.4 * (1 - a)), 0, 2 * Math.PI); ctx.stroke();
  });
}
function frame(now) { draw(now); requestAnimationFrame(frame); }

// ---- the link to the bridge ----------------------------------------------------------------------
var ws = null, retry = 1000;
function send(o) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); }
function caps() {
  return { motion: 'DeviceMotionEvent' in window, compass: 'ondeviceorientationabsolute' in window,
           tts: 'speechSynthesis' in window, vibrate: 'vibrate' in navigator, battery: 'getBattery' in navigator,
           wakelock: 'wakeLock' in navigator, camera: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
           barcode: 'BarcodeDetector' in window };
}
function hello() {  // Chrome hides the model in the user agent ("K"); client hints still tell it, on a secure page
  var h = { t: 'hello', ua: navigator.userAgent, secure: !!window.isSecureContext, caps: caps(), screen: [screen.width, screen.height] };
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
  else if (m.t === 'vibrate' && navigator.vibrate) navigator.vibrate(Math.max(0, Math.min(2000, m.ms | 0)));
  else if (m.t === 'open' && ['face.html', 'check.html'].indexOf(m.page) >= 0) location.href = m.page + location.search;
}

// ---- voice -----------------------------------------------------------------------------------------
function speak(text, l) {
  if (!('speechSynthesis' in window) || !text) return;
  speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text);
  u.lang = { en: 'en-GB', fr: 'fr-FR', de: 'de-DE' }[l] || 'en-GB';
  var v = speechSynthesis.getVoices().filter(function (v) { return v.lang.slice(0, 2) === l; })[0];
  if (v) u.voice = v;
  u.onstart = function () { speaking = true; };
  u.onend = u.onerror = function () { speaking = false; };
  speechSynthesis.speak(u);
}

// ---- the camera: the torch and the setup page's camera test share one stream; the face shows when it is on.
// The picture is shown on the phone only: what leaves it is whether it works, its size and the codes it read.
var cam = null, camOpening = null, want = { torch: false, view: false }, camOk = false;
var view = document.getElementById('view'), viewOff = 0, scanTimer = 0, lastCode = '';
function camReport(o) { o.t = 'camera'; o.on = !!cam; o.ok = 'ok' in o ? o.ok : camOk; camOk = o.ok; send(o); }
function camError(e) { return (e && e.name) || String(e); }
function openCam() {
  if (cam) return Promise.resolve(cam);
  if (camOpening) return camOpening;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return Promise.reject({ name: window.isSecureContext ? 'NoCamera' : 'NotSecure' });
  }
  camOpening = navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 } }, audio: false })
    .then(function (s) { camOpening = null; cam = s; document.getElementById('eye').style.display = 'block'; return s; },
          function (e) { camOpening = null; throw e; });
  return camOpening;
}
function closeCamIfIdle() {
  if (want.torch || want.view || !cam) return;
  cam.getTracks().forEach(function (k) { k.stop(); });
  cam = null; document.getElementById('eye').style.display = 'none';
}
function torch(on) {
  want.torch = on;
  if (!on) {
    if (cam) cam.getVideoTracks()[0].applyConstraints({ advanced: [{ torch: false }] }).catch(function () {});
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
  send({ t: 'imu', acc: [a.x, a.y, a.z], gyro: r && r.alpha != null ? [r.beta * d, r.gamma * d, r.alpha * d] : [0, 0, 0] });
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
  var dpr = W / innerWidth; ripples.push({ x: down.x * dpr, y: down.y * dpr, t: performance.now() });
  send(m); down = null;
});

// ---- start: full screen, landscape, screen on, motion permission: they all need a tap ----------------
var lock = null;
function keepAwake() { if (navigator.wakeLock && document.visibilityState === 'visible') navigator.wakeLock.request('screen').then(function (l) { lock = l; }).catch(function () {}); }
document.addEventListener('visibilitychange', keepAwake);
function start() {
  document.getElementById('start').style.display = 'none';
  var el = document.documentElement, fs = el.requestFullscreen || el.webkitRequestFullscreen;
  var p = fs ? fs.call(el) : null;
  if (p && p.then) p.then(function () { if (screen.orientation && screen.orientation.lock) return screen.orientation.lock('landscape'); }).catch(function () {});
  keepAwake();
  if (window.DeviceMotionEvent && DeviceMotionEvent.requestPermission) DeviceMotionEvent.requestPermission().catch(function () {});
  if ('speechSynthesis' in window) speechSynthesis.getVoices();
  connect();
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

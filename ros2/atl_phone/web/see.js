// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// Vision on the phone (contract atl-phone/0.5): the camera finds faces (look), ArUco markers, colour blobs, objects and
// hands, here on the phone; only numbers leave it, never a picture. Loaded after face.js, whose camera (openCam,
// facing), send() and eyes it uses. The libraries (vendor/mediapipe, vendor/aruco, vendor/face-api) load when first asked.
// With "familiar" it also keeps, in this page's memory only, a signature of each face (128 numbers) to give the same
// face the same number. The signatures are never sent nor stored, and are forgotten on reload, when look or familiar
// ends, on "forget", and ten minutes after a face was last seen.
// With "follow" the eyes look at the nearest thing found (a face, a hand, a marker, an object when objects are quick
// here), and hold it: another one takes over only when it is clearly nearer for a moment.
'use strict';

var MP = 'vendor/mediapipe', FACE_API = 'vendor/face-api', SAME = 0.5, KEEP = 600000, EVERY = 100;  // ms: at most 10 searches a second
var FOV = 65;        // degrees across the picture, when a program does not say (a marker at a known distance tells it)
var KNOWN_M = { person: 1.7, cup: 0.1, bottle: 0.25, 'cell phone': 0.15, book: 0.24, chair: 0.9, 'teddy bear': 0.3 };  // heights, for a distance
var GESTURE = { None: 'none', Closed_Fist: 'fist', Open_Palm: 'open_palm', Pointing_Up: 'pointing_up', Thumb_Down: 'thumbs_down',
                Thumb_Up: 'thumbs_up', Victory: 'victory', ILoveYou: 'love' };
var vision = { find: [], camera: 'front', blob: { hue: 0, tol: 20 }, marker_cm: 5, fov_deg: null, follow: false };  // as "see" asked
var SIZE_M = { faces: 0.2, hands: 0.19, objects: 0.25 };  // a thing's height when nothing better is known: for its distance
var NEARER = 0.75, SWITCH_MS = 500, HOLD_MS = 1000, QUICK_MS = 400;  // follow: 25 % nearer for 0.5 s; held 1 s once lost
var seeing = { familiar: false, timer: 0, video: document.createElement('video'), canvas: document.createElement('canvas'),
               known: [], prev: [], sigAt: 0, codeAt: 0, code: '', codeSent: 0, det: null, ok: null, lastAt: 0, period: 0,
               ms: {}, backend: {}, mp: null, tasks: {}, faceApi: null, recog: null, aruco: null, hadFace: false, reportAt: 0,
               near: [], follow: { cur: null, cand: null, candAt: 0 } };
seeing.video.muted = true; seeing.video.setAttribute('playsinline', '');

function finders() {  // what to find now: what see asked, and faces while look is on (look is the front camera's only:
  var f = vision.find.slice();  // faces from the back one would be on the other side, so look waits while see has it)
  if (want.look && f.indexOf('faces') < 0 && !lookWaits()) f.push('faces');
  return f;
}
function lookWaits() { return want.look && vision.find.length > 0 && vision.camera === 'back'; }
function visionFacing() {  // the camera vision wants: see's, or the front one for look alone
  var f = finders();
  if (!f.length) return '';
  return vision.find.length && vision.camera === 'back' ? 'environment' : 'user';
}
function visionState() {  // for the sensor panel
  var f = finders();
  return f.length ? f.map(function (k) { return k + (seeing.ms[k] != null ? ' ' + seeing.ms[k] + 'ms' : ''); }).join(', ') : '';
}

// ---- the libraries, each loaded once -------------------------------------------------------------------------
function script(src) {
  return new Promise(function (ok, no) {
    var sc = document.createElement('script'); sc.src = src;
    sc.onload = ok; sc.onerror = function () { no({ name: 'NoLibrary' }); }; document.head.appendChild(sc);
  });
}
function mediapipe() {
  if (!seeing.mp) seeing.mp = import('./' + MP + '/vision_bundle.mjs').then(function (m) {
    return m.FilesetResolver.forVisionTasks(MP + '/wasm').then(function (files) { return { m: m, files: files }; });
  });
  return seeing.mp;
}
function task(kind) {  // a MediaPipe task: on the GPU when the phone lets it, else on the CPU
  if (!seeing.tasks[kind]) seeing.tasks[kind] = mediapipe().then(function (mp) {
    var make = { faces: mp.m.FaceDetector, objects: mp.m.ObjectDetector, hands: mp.m.GestureRecognizer }[kind];
    var model = { faces: 'blaze_face_short_range.tflite', objects: 'efficientdet_lite0.tflite', hands: 'gesture_recognizer.task' }[kind];
    function options(delegate) {
      var o = { baseOptions: { modelAssetPath: MP + '/models/' + model, delegate: delegate }, runningMode: 'VIDEO' };
      if (kind === 'faces') o.minDetectionConfidence = 0.5;
      if (kind === 'objects') { o.scoreThreshold = 0.4; o.maxResults = 8; }
      if (kind === 'hands') o.numHands = 2;
      return o;
    }
    return make.createFromOptions(mp.files, options('GPU')).then(function (t) { seeing.backend[kind] = 'gpu'; return t; }, function () {
      return make.createFromOptions(mp.files, options('CPU')).then(function (t) { seeing.backend[kind] = 'cpu'; return t; });
    });
  });
  return seeing.tasks[kind];
}
function faceApi(familiar) {  // face-api: the signatures for "familiar", and the faces when MediaPipe cannot run here
  if (!seeing.faceApi) seeing.faceApi = script(FACE_API + '/face-api.js')
    .then(function () { return faceapi.nets.tinyFaceDetector.loadFromUri(FACE_API + '/models'); });
  if (familiar && !seeing.recog) seeing.recog = seeing.faceApi.then(function () {
    return Promise.all([faceapi.nets.faceLandmark68TinyNet.loadFromUri(FACE_API + '/models'),
                        faceapi.nets.faceRecognitionNet.loadFromUri(FACE_API + '/models')]);
  });
  return familiar ? seeing.recog : seeing.faceApi;
}
function aruco() {
  if (!seeing.aruco) seeing.aruco = ['cv.js', 'svd.js', 'posit1.js', 'aruco.js', 'aruco_4x4_1000.js'].reduce(function (p, f) {
    return p.then(function () { return script('vendor/aruco/' + f); });
  }, Promise.resolve()).then(function () { return new AR.Detector({ dictionaryName: 'ARUCO_4X4_1000' }); });
  return seeing.aruco;
}

// ---- asked from the bridge -------------------------------------------------------------------------------------
function forget() { seeing.known = []; seeing.prev = []; }
function lookReport(o) {
  o.t = 'look'; o.on = want.look; o.familiar = want.look && seeing.familiar;
  if (!('ok' in o)) o.ok = seeing.ok === true;
  send(o);
}
function seeReport(o) {
  o.t = 'see'; o.on = finders().length > 0; o.camera = visionFacing() === 'environment' ? 'back' : 'front'; o.find = finders();
  o.follow = !!vision.follow;
  var tg = vision.follow && followTarget();
  if (tg) o.target = tg;
  o.ms = seeing.ms; o.backend = Object.keys(seeing.backend).map(function (k) { return k + ':' + seeing.backend[k]; }).join(',').slice(0, 60);
  if (!('ok' in o)) o.ok = seeing.ok === true;
  send(o); seeing.reportAt = Date.now();
}
function lookAt(on, familiar) {
  var was = want.look;
  if (!on || !familiar) forget();
  want.look = on; seeing.familiar = on && familiar;
  if (on && !was) seeing.ok = null;
  if (!on && was) send({ t: 'faces', faces: [] });
  lookReport(lookWaits() ? { ok: false, error: 'busy: see has the back camera' } : {});
  restart();
}
function seeAt(m) {
  var before = finders().indexOf('faces') >= 0;
  vision.find = Array.isArray(m.find) ? m.find : [];
  vision.camera = m.camera === 'back' ? 'back' : 'front';
  if (m.blob) vision.blob = { hue: +m.blob.hue || 0, tol: +m.blob.tol || 20 };
  vision.marker_cm = +m.marker_cm || 5; vision.fov_deg = m.fov_deg ? +m.fov_deg : null;
  vision.follow = !!m.follow; seeing.follow = { cur: null, cand: null, candAt: 0 };
  if (before && finders().indexOf('faces') < 0) { forget(); send({ t: 'faces', faces: [] }); }
  seeing.ok = null; seeing.ms = {};
  seeReport({});
  if (lookWaits()) lookReport({ ok: false, error: 'busy: see has the back camera' });
  restart();
}
function restart() {
  clearTimeout(seeing.timer);
  if (!finders().length) { seeing.video.srcObject = null; closeCamIfIdle(); eyeBadge(); return; }
  try { seeing.det = seeing.det || ('BarcodeDetector' in window ? new BarcodeDetector({ formats: ['qr_code'] }) : null); } catch (e) {}
  eyeBadge();  // a camera already open (the panel's) is vision's now: ● look
  seeTick();
}

// ---- one search: every finder asked, on the same picture -------------------------------------------------------
function distance(a, b) { var s = 0; for (var i = 0; i < a.length; i++) { var d = a[i] - b[i]; s += d * d; } return Math.sqrt(s); }
function slotOf(desc, now) {  // the number of this face this session: a face seen before, else a new number
  var best = null, bd = SAME;
  seeing.known.forEach(function (k) { var d = distance(k.d, desc); if (d < bd) { bd = d; best = k; } });
  if (best) {  // follow slow changes (light, angle): a running mean
    var n = Math.min(best.n, 9);
    for (var i = 0; i < desc.length; i++) best.d[i] = (best.d[i] * n + desc[i]) / (n + 1);
    best.n++; best.at = now; return best.slot;
  }
  var used = seeing.known.map(function (k) { return k.slot; }), slot = 1;
  while (used.indexOf(slot) >= 0) slot++;
  if (slot > 8) {  // full: the face not seen for the longest gives its number
    var old = seeing.known.reduce(function (a, b) { return a.at < b.at ? a : b; });
    seeing.known.splice(seeing.known.indexOf(old), 1); slot = old.slot;
  }
  seeing.known.push({ slot: slot, d: Float32Array.from(desc), n: 1, at: now });
  return slot;
}
function timed(kind, f) {  // runs one finder and keeps how long it took (ms)
  var t0 = performance.now();
  return Promise.resolve().then(f).then(function (r) { seeing.ms[kind] = Math.round(performance.now() - t0); return r; });
}
function where(cx, cy, front) { return { x: front ? 1 - 2 * cx : 2 * cx - 1, y: 1 - 2 * cy }; }  // the front camera as the face sees it
function focal(w) { return (w / 2) / Math.tan((vision.fov_deg || FOV) * Math.PI / 360); }  // in pixels, for a picture w wide

function findFaces(v, now, front) {
  var sign = seeing.familiar && now - seeing.sigAt >= 1000;  // signatures cost more: once a second
  var w = v.videoWidth, h = v.videoHeight;
  function box(b) {
    var f = where((b.x + b.width / 2) / w, (b.y + b.height / 2) / h, front);
    f.size = Math.min(1, b.height / h); f.familiar = null; return f;
  }
  var found;
  if (sign) {
    found = faceApi(true).then(function () {
      return faceapi.detectAllFaces(v, new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 }))
        .withFaceLandmarks(true).withFaceDescriptors();
    }).then(function (rs) {
      seeing.sigAt = now;
      return rs.map(function (r) { var f = box(r.detection.box); f.familiar = slotOf(r.descriptor, now); return f; });
    });
  } else {
    found = task('faces').then(function (t) {
      return t.detectForVideo(v, performance.now()).detections.map(function (d) {
        var b = d.boundingBox; return box({ x: b.originX, y: b.originY, width: b.width, height: b.height });
      });
    }, function () {  // no MediaPipe on this phone: face-api's own finder
      seeing.backend.faces = 'face-api';
      return faceApi(false).then(function () {
        return faceapi.detectAllFaces(v, new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 }));
      }).then(function (rs) { return rs.map(function (r) { return box(r.box); }); });
    });
  }
  return timed('faces', function () { return found; }).then(function (faces) {
    faces = faces.slice(0, 8);
    if (seeing.familiar && !sign) faces.forEach(function (f) {  // between signatures: the number of the face nearest a moment ago
      var near = null, nd = 0.25;
      seeing.prev.forEach(function (p) { var d = Math.hypot(p.x - f.x, p.y - f.y); if (d < nd && p.familiar) { nd = d; near = p; } });
      if (near) f.familiar = near.familiar;
    });
    faces.sort(function (a, b) { return b.size - a.size; });
    seeing.prev = faces;
    if (faces.length) {
      if (!vision.follow) { faceAim = { x: faces[0].x, y: faces[0].y }; faceAt = performance.now(); }
      if (!seeing.hadFace) glance();
    }
    faces.forEach(function (f) { near('faces', f.x, f.y, focal(w) * SIZE_M.faces / Math.max(1, f.size * h)); });
    seeing.hadFace = faces.length > 0;
    send({ t: 'faces', faces: faces, period: seeing.period });
  });
}
function frame2d(v, width) {  // the picture, small, as pixels
  var c = seeing.canvas, h = Math.round(width * v.videoHeight / v.videoWidth);
  if (c.width !== width || c.height !== h) { c.width = width; c.height = h; }
  var g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(v, 0, 0, width, h);
  return g.getImageData(0, 0, width, h);
}
function findMarkers(v, front, cam) {
  return timed('markers', function () {
    return aruco().then(function (det) {
      var img = frame2d(v, 320), w = img.width, h = img.height;
      var posit = new POS.Posit(vision.marker_cm * 10, focal(w));
      var ms = det.detect(img).slice(0, 8).map(function (mk) {
        var cs = mk.corners, cx = 0, cy = 0, top = 1e9, bottom = -1e9;
        cs.forEach(function (p) { cx += p.x / 4; cy += p.y / 4; top = Math.min(top, p.y); bottom = Math.max(bottom, p.y); });
        var o = where(cx / w, cy / h, front);
        o.id = mk.id; o.size = Math.min(1, (bottom - top) / h);
        try {
          var pose = posit.pose(cs.map(function (p) { return { x: p.x - w / 2, y: h / 2 - p.y }; }));
          var t = pose.bestTranslation, r = pose.bestRotation;
          o.distance_m = Math.round(Math.sqrt(t[0] * t[0] + t[1] * t[1] + t[2] * t[2])) / 1000;
          var yaw = Math.atan2(r[0][2], r[2][2]) * 180 / Math.PI;
          if (yaw > 90) yaw -= 180; else if (yaw < -90) yaw += 180;
          o.yaw_deg = Math.round(front ? -yaw : yaw);
        } catch (e) { o.distance_m = null; o.yaw_deg = null; }
        near('markers', o.x, o.y, o.distance_m || focal(w) * vision.marker_cm / 100 / Math.max(1, o.size * h));
        return o;
      });
      send({ t: 'markers', camera: cam, markers: ms });
    });
  });
}
function findBlobs(v, front, cam) {  // the asked hue, saturated and bright enough, in connected areas on a 160-pixel picture
  return timed('blobs', function () {
    var img = frame2d(v, 160), w = img.width, h = img.height, d = img.data, n = w * h;
    var mask = new Uint8Array(n), hue = vision.blob.hue, tol = vision.blob.tol;
    for (var i = 0; i < n; i++) {
      var r = d[i * 4], g = d[i * 4 + 1], b = d[i * 4 + 2], mx = Math.max(r, g, b), mn = Math.min(r, g, b), c = mx - mn;
      if (mx < 60 || c < mx * 0.35) continue;
      var hh = mx === r ? ((g - b) / c + 6) % 6 : mx === g ? (b - r) / c + 2 : (r - g) / c + 4;
      var dh = Math.abs(hh * 60 - hue); if (dh > 180) dh = 360 - dh;
      if (dh <= tol) mask[i] = 1;
    }
    var blobs = [], stack = [];
    for (var s = 0; s < n; s++) {
      if (mask[s] !== 1) continue;
      var area = 0, sx = 0, sy = 0, y0 = h, y1 = 0;
      mask[s] = 2; stack.push(s);
      while (stack.length) {
        var q = stack.pop(), x = q % w, y = (q - x) / w;
        area++; sx += x; sy += y; if (y < y0) y0 = y; if (y > y1) y1 = y;
        if (x > 0 && mask[q - 1] === 1) { mask[q - 1] = 2; stack.push(q - 1); }
        if (x < w - 1 && mask[q + 1] === 1) { mask[q + 1] = 2; stack.push(q + 1); }
        if (y > 0 && mask[q - w] === 1) { mask[q - w] = 2; stack.push(q - w); }
        if (y < h - 1 && mask[q + w] === 1) { mask[q + w] = 2; stack.push(q + w); }
      }
      if (area >= 12) { var o = where(sx / area / w, sy / area / h, front); o.size = (y1 - y0 + 1) / h; o.area = area; blobs.push(o); }
    }
    blobs.sort(function (a, b) { return b.area - a.area; });
    send({ t: 'blobs', camera: cam, blobs: blobs.slice(0, 8).map(function (o) { return { x: o.x, y: o.y, size: o.size }; }) });
  });
}
function findObjects(v, front, cam) {
  return timed('objects', function () {
    return task('objects').then(function (t) {
      var w = v.videoWidth, h = v.videoHeight, f = focal(w);
      var os = t.detectForVideo(v, performance.now()).detections.slice(0, 8).map(function (d) {
        var b = d.boundingBox, c = d.categories[0], o = where((b.originX + b.width / 2) / w, (b.originY + b.height / 2) / h, front);
        o.label = c.categoryName; o.score = Math.round(c.score * 100) / 100; o.w = b.width / w; o.h = b.height / h;
        o.distance_m = KNOWN_M[o.label] && b.height > 4 ? Math.round(f * KNOWN_M[o.label] / b.height * 100) / 100 : null;
        return o;
      }).filter(function (o) { return o.label && o.label !== '???'; });
      if (seeing.ms.objects == null || seeing.ms.objects < QUICK_MS) os.forEach(function (o) {  // slow here: not followed
        near('objects', o.x, o.y, o.distance_m || f * SIZE_M.objects / Math.max(1, o.h * h));
      });
      send({ t: 'objects', camera: cam, objects: os });
    });
  });
}
function findHands(v, front, cam) {
  return timed('hands', function () {
    return task('hands').then(function (t) {
      var r = t.recognizeForVideo(v, performance.now());
      var hs = (r.landmarks || []).slice(0, 8).map(function (lm, i) {
        var cx = 0, cy = 0, y0 = 1, y1 = 0;
        lm.forEach(function (p) { cx += p.x / lm.length; cy += p.y / lm.length; y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); });
        var o = where(cx, cy, front), g = (r.gestures[i] || [])[0];
        near('hands', o.x, o.y, focal(v.videoWidth) * SIZE_M.hands / Math.max(1, (y1 - y0) * v.videoHeight));
        o.gesture = GESTURE[g && g.categoryName] || 'none';
        return o;
      });
      send({ t: 'hands', camera: cam, hands: hs });
    });
  });
}
// ---- the follower ------------------------------------------------------------------------------------------------
function near(kind, x, y, d) { if (vision.follow && isFinite(d) && d > 0) seeing.near.push({ kind: kind, x: x, y: y, d: d }); }
function followPick(cands, now) {  // the thing the eyes hold: the nearest, kept until another is NEARER for SWITCH_MS
  var F = seeing.follow, cur = F.cur, best = null, same = null;
  cands.forEach(function (c) {
    if (!best || c.d < best.d) best = c;
    if (cur && c.kind === cur.kind && Math.hypot(c.x - cur.x, c.y - cur.y) < 0.35 && (!same || c.d < same.d)) same = c;
  });
  if (same) { cur.x = same.x; cur.y = same.y; cur.d = same.d; cur.at = now; }
  if (!cur || now - cur.at > HOLD_MS) {  // nothing held, or it is gone: the nearest now
    F.cur = best ? { kind: best.kind, x: best.x, y: best.y, d: best.d, at: now } : null; F.cand = null;
  } else if (best && best !== same && best.d < cur.d * NEARER) {
    if (F.cand && F.cand.kind === best.kind && Math.hypot(F.cand.x - best.x, F.cand.y - best.y) < 0.35) {
      F.cand.x = best.x; F.cand.y = best.y;
      if (now - F.candAt >= SWITCH_MS) { F.cur = { kind: best.kind, x: best.x, y: best.y, d: best.d, at: now }; F.cand = null; }
    } else { F.cand = { kind: best.kind, x: best.x, y: best.y }; F.candAt = now; }
  } else F.cand = null;
  return F.cur;
}
function followTarget() { var c = seeing.follow.cur; return c ? { kind: c.kind, x: c.x, y: c.y } : null; }
function seeTick() {
  var f = finders();
  if (!f.length) return;
  var started = performance.now();
  function next() {
    clearTimeout(seeing.timer);
    seeing.timer = setTimeout(seeTick, Math.max(0, EVERY - (performance.now() - started)));
  }
  function fail(e) {
    seeing.ok = false;
    if (want.look) lookReport({ ok: false, error: camError(e) });
    seeReport({ ok: false, error: camError(e) });
    seeing.timer = setTimeout(seeTick, 5000);
  }
  var want_ = visionFacing();
  if (facing() !== want_) return next();  // the torch or the camera test has the camera: vision waits
  if (camFacing !== want_) return void openCam().then(next, fail);
  var v = seeing.video, now = Date.now(), front = want_ === 'user', side = front ? 'front' : 'back';
  if (v.srcObject !== cam) { v.srcObject = cam; v.play().catch(function () {}); }
  if (v.readyState < 2 || !v.videoWidth) return next();
  seeing.known = seeing.known.filter(function (k) { return now - k.at < KEEP; });
  seeing.period = seeing.lastAt ? Math.round(started - seeing.lastAt) : 0;
  seeing.lastAt = started;
  var jobs = [];  // one after the other: a phone has one GPU
  seeing.near = [];
  if (f.indexOf('faces') >= 0) jobs.push(function () { return findFaces(v, now, front); });
  if (f.indexOf('markers') >= 0) jobs.push(function () { return findMarkers(v, front, side); });
  if (f.indexOf('blobs') >= 0) jobs.push(function () { return findBlobs(v, front, side); });
  if (f.indexOf('objects') >= 0) jobs.push(function () { return findObjects(v, front, side); });
  if (f.indexOf('hands') >= 0) jobs.push(function () { return findHands(v, front, side); });
  jobs.reduce(function (p, j) { return p.then(j); }, Promise.resolve()).then(function () {
    if (finders().join() !== f.join()) return next();  // asked something else meanwhile
    if (vision.follow) {
      var was = followTarget(), t = followPick(seeing.near, performance.now());
      if (t && performance.now() - t.at < HOLD_MS) { faceAim = { x: t.x, y: t.y }; faceAt = performance.now(); }
      var now_ = followTarget();
      if (!was !== !now_ || (was && now_ && was.kind !== now_.kind)) seeReport({});  // what the eyes follow changed
    }
    if (seeing.ok !== true) { seeing.ok = true; if (want.look) lookReport({ ok: true }); seeReport({ ok: true }); }
    else if (Date.now() - seeing.reportAt > 2000) seeReport({ ok: true });  // the timings, now and then
    if (seeing.det && now - seeing.codeAt > 500) {  // a card held up to the camera
      seeing.codeAt = now;
      seeing.det.detect(v).then(function (cs) {
        var c = cs.length ? cs[0].rawValue : '';
        if (c && (c !== seeing.code || Date.now() - seeing.codeSent > 3000)) { send({ t: 'code', text: c }); seeing.codeSent = Date.now(); }
        seeing.code = c;
      }).catch(function () {});
    }
    next();
  }, fail);
}

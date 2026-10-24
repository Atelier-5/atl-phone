// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// Phone setup, on the PC: it watches the bridge (/api/state) and asks it for tests (/api/act).
'use strict';

var T = {
  en: {
    title: 'Phone setup', s1: 'The bridge', s2: 'Connect the phone', s3: 'Phone check', s4: 'Test it', s5: 'Summary',
    s1_lead: 'The bridge connects the phone to ROS 2. If you can read this, it runs.',
    s2_lead: 'By USB at the desk, or by Wi-Fi on the table.',
    s3_lead: 'What can this phone do? The check tests each part once. You can skip it.',
    s4_lead: 'Each test goes through ROS 2, as a robot program would. Outputs: say what you saw. Senses: they tick by themselves.',
    usb1: 'On the phone: Settings › About phone › tap “Build number” seven times.',
    usb2: 'Settings › Developer options › turn on “USB debugging”.',
    usb3: 'Plug the phone into this PC and allow it on the phone.',
    usb4: 'On this PC, in the atl-phone folder:', usb5: 'The face opens on the phone: tap ▶.',
    usb_why: 'USB makes the page the phone’s “localhost”: a secure page, so camera, microphone and motion work without certificates. The cable charges the phone too.',
    wifi_warn: 'Without HTTPS the face works, but camera, microphone and motion are blocked on Wi-Fi. Use USB, or start the bridge with a certificate: ./start.sh --cert DIR',
    wifi1: 'Put the phone on the same Wi-Fi as this PC.', wifi2: 'Scan the code with the phone’s camera, or type the address:',
    open_check: 'Open the check on the phone', chk2: 'On the phone: “Test everything”, allow camera, microphone and motion.',
    chk3: 'Then “Send report to the PC”, and “Robot face →” to come back.',
    outputs: 'The robot → the phone', inputs: 'The phone → the robot',
    copy: 'Copy', copied: 'Copied.', copy_summary: 'Copy summary', back: '← Back', next: 'Next →',
    bridge_ok: 'The bridge runs.', bridge_no: 'No bridge: start it with ./start.sh', robot: 'Robot', contract: 'Contract',
    usb_url: 'USB address', wifi_url: 'Wi-Fi address',
    waiting: 'Waiting for the phone…', connected: 'Phone connected:', no_phone: 'No phone: connect one first (step 2).',
    no_report: 'No report yet.', report_from: 'Report from', core_ok: 'everything version 1 needs works', core_missing: 'missing:',
    face: 'Face', face_q: 'Did the face change?', gaze: 'Gaze', gaze_hint: 'Drag in the box: the eyes follow.', gaze_q: 'Did the eyes follow?',
    color: 'Eye colour', color_q: 'Did the colour change?', say: 'Voice', say_text: 'Hello, I am your robot.', say_btn: 'Say', say_q: 'Did you hear it?',
    vibrate: 'Vibration', vibrate_btn: 'Buzz', vibrate_q: 'Did you feel it?', torch: 'Torch', on: 'On', off: 'Off',
    torch_q: 'Did the light come on? (the face shows ● cam)', yes: 'yes', no: 'no',
    touch: 'Touch', touch_hint: 'On the phone: tap left, centre and right; press long; swipe.',
    motion: 'Motion', motion_hint: 'Tilt the phone.', compass: 'Compass', compass_hint: 'Turn the phone, lying flat.',
    battery: 'Battery', charging: 'charging', none_yet: 'nothing yet', not_here: 'this phone has none',
    summary_lead: 'What works on this phone. Copy it into your notes or the robot’s build.', untested: 'not tested', skipped: 'skipped',
    down: 'down:',
    camera: 'Camera', show: 'Show on the phone', hide: 'Hide', camera_q: 'Did the phone show what its camera sees?',
    camera_hint: 'The phone shows its back camera’s picture on its own screen, for a minute. Nothing leaves the phone.',
    code: 'Reading codes', code_hint: 'With the picture on: hold the phone’s back camera to this code.', code_read: 'read:',
    no_reader: 'this phone’s browser cannot read codes; the card scanner (step 3) brings its own reader',
    blocked: 'blocked: the phone’s page is not secure. Connect by USB, or start with --cert',
    insecure: 'This phone uses a page that is not secure (http over Wi-Fi): its camera, motion, compass and battery are blocked. Connect it by USB, or start the bridge with a certificate (./start.sh --cert DIR).',
    no_torch: 'the phone says it has no torch', cam_error: 'the camera did not open:', size: 'picture'
  },
  fr: {
    title: 'Installer le téléphone', s1: 'Le pont', s2: 'Connecter le téléphone', s3: 'Test du téléphone', s4: 'L’essayer', s5: 'Bilan',
    s1_lead: 'Le pont relie le téléphone à ROS 2. Si vous lisez ceci, il tourne.',
    s2_lead: 'Par USB au bureau, ou par Wi-Fi sur la table.',
    s3_lead: 'Que sait faire ce téléphone ? Le test essaie chaque partie une fois. Vous pouvez le passer.',
    s4_lead: 'Chaque essai passe par ROS 2, comme un programme du robot. Sorties : dites ce que vous avez vu. Sens : ils se cochent tout seuls.',
    usb1: 'Sur le téléphone : Paramètres › À propos du téléphone › touchez sept fois « Numéro de build ».',
    usb2: 'Paramètres › Options pour les développeurs › activez « Débogage USB ».',
    usb3: 'Branchez le téléphone sur ce PC et autorisez-le sur le téléphone.',
    usb4: 'Sur ce PC, dans le dossier atl-phone :', usb5: 'Le visage s’ouvre sur le téléphone : touchez ▶.',
    usb_why: 'Par USB, la page est le « localhost » du téléphone : une page sécurisée, donc caméra, micro et mouvement marchent sans certificat. Le câble charge aussi le téléphone.',
    wifi_warn: 'Sans HTTPS, le visage marche, mais caméra, micro et mouvement sont bloqués en Wi-Fi. Passez par USB, ou lancez le pont avec un certificat : ./start.sh --cert DOSSIER',
    wifi1: 'Mettez le téléphone sur le même Wi-Fi que ce PC.', wifi2: 'Scannez le code avec la caméra du téléphone, ou tapez l’adresse :',
    open_check: 'Ouvrir le test sur le téléphone', chk2: 'Sur le téléphone : « Tout tester », autorisez caméra, micro et mouvement.',
    chk3: 'Puis « Envoyer le rapport au PC », et « Visage du robot → » pour revenir.',
    outputs: 'Le robot → le téléphone', inputs: 'Le téléphone → le robot',
    copy: 'Copier', copied: 'Copié.', copy_summary: 'Copier le bilan', back: '← Retour', next: 'Suivant →',
    bridge_ok: 'Le pont tourne.', bridge_no: 'Pas de pont : lancez-le avec ./start.sh', robot: 'Robot', contract: 'Contrat',
    usb_url: 'Adresse USB', wifi_url: 'Adresse Wi-Fi',
    waiting: 'En attente du téléphone…', connected: 'Téléphone connecté :', no_phone: 'Pas de téléphone : connectez-en un d’abord (étape 2).',
    no_report: 'Pas encore de rapport.', report_from: 'Rapport de', core_ok: 'tout ce qu’il faut pour la version 1 marche', core_missing: 'manque :',
    face: 'Visage', face_q: 'Le visage a-t-il changé ?', gaze: 'Regard', gaze_hint: 'Glissez dans le cadre : les yeux suivent.', gaze_q: 'Les yeux ont-ils suivi ?',
    color: 'Couleur des yeux', color_q: 'La couleur a-t-elle changé ?', say: 'Voix', say_text: 'Bonjour, je suis ton robot.', say_btn: 'Dire', say_q: 'L’avez-vous entendu ?',
    vibrate: 'Vibration', vibrate_btn: 'Vibrer', vibrate_q: 'L’avez-vous senti ?', torch: 'Lampe', on: 'Allumer', off: 'Éteindre',
    torch_q: 'La lampe s’est-elle allumée ? (le visage montre ● cam)', yes: 'oui', no: 'non',
    touch: 'Toucher', touch_hint: 'Sur le téléphone : touchez à gauche, au centre et à droite ; appuyez longtemps ; glissez.',
    motion: 'Mouvement', motion_hint: 'Inclinez le téléphone.', compass: 'Boussole', compass_hint: 'Tournez le téléphone, posé à plat.',
    battery: 'Batterie', charging: 'en charge', none_yet: 'rien encore', not_here: 'ce téléphone n’en a pas',
    summary_lead: 'Ce qui marche sur ce téléphone. Copiez-le dans vos notes ou dans le montage du robot.', untested: 'pas testé', skipped: 'passé',
    down: 'en bas :',
    camera: 'Caméra', show: 'Montrer sur le téléphone', hide: 'Cacher', camera_q: 'Le téléphone a-t-il montré ce que voit sa caméra ?',
    camera_hint: 'Le téléphone montre l’image de sa caméra arrière sur son propre écran, pendant une minute. Rien ne quitte le téléphone.',
    code: 'Lire des codes', code_hint: 'Image allumée : tenez la caméra arrière du téléphone devant ce code.', code_read: 'lu :',
    no_reader: 'le navigateur de ce téléphone ne lit pas les codes ; le lecteur de cartes (étape 3) apporte le sien',
    blocked: 'bloqué : la page du téléphone n’est pas sécurisée. Connectez par USB, ou lancez avec --cert',
    insecure: 'Ce téléphone utilise une page non sécurisée (http en Wi-Fi) : sa caméra, son mouvement, sa boussole et sa batterie sont bloqués. Connectez-le par USB, ou lancez le pont avec un certificat (./start.sh --cert DOSSIER).',
    no_torch: 'le téléphone dit ne pas avoir de lampe', cam_error: 'la caméra ne s’est pas ouverte :', size: 'image'
  },
  de: {
    title: 'Handy einrichten', s1: 'Die Brücke', s2: 'Handy verbinden', s3: 'Handy-Check', s4: 'Ausprobieren', s5: 'Zusammenfassung',
    s1_lead: 'Die Brücke verbindet das Handy mit ROS 2. Wenn du das liest, läuft sie.',
    s2_lead: 'Per USB am Tisch, oder per WLAN auf dem Spielfeld.',
    s3_lead: 'Was kann dieses Handy? Der Check testet jedes Teil einmal. Du kannst ihn überspringen.',
    s4_lead: 'Jeder Test geht über ROS 2, wie ein Roboterprogramm. Ausgaben: sag, was du gesehen hast. Sinne: sie haken sich selbst ab.',
    usb1: 'Auf dem Handy: Einstellungen › Über das Telefon › siebenmal auf „Build-Nummer“ tippen.',
    usb2: 'Einstellungen › Entwickleroptionen › „USB-Debugging“ einschalten.',
    usb3: 'Handy an diesen PC anschließen und auf dem Handy erlauben.',
    usb4: 'Auf diesem PC, im Ordner atl-phone:', usb5: 'Das Gesicht öffnet sich auf dem Handy: auf ▶ tippen.',
    usb_why: 'Per USB ist die Seite der „localhost“ des Handys: eine sichere Seite, also gehen Kamera, Mikrofon und Bewegung ohne Zertifikat. Das Kabel lädt das Handy auch.',
    wifi_warn: 'Ohne HTTPS geht das Gesicht, aber Kamera, Mikrofon und Bewegung sind im WLAN gesperrt. USB nutzen, oder die Brücke mit Zertifikat starten: ./start.sh --cert ORDNER',
    wifi1: 'Das Handy ins selbe WLAN wie diesen PC bringen.', wifi2: 'Den Code mit der Handykamera scannen, oder die Adresse eintippen:',
    open_check: 'Check auf dem Handy öffnen', chk2: 'Auf dem Handy: „Alles testen“, Kamera, Mikrofon und Bewegung erlauben.',
    chk3: 'Dann „Bericht an den PC senden“, und „Robotergesicht →“ für zurück.',
    outputs: 'Der Roboter → das Handy', inputs: 'Das Handy → der Roboter',
    copy: 'Kopieren', copied: 'Kopiert.', copy_summary: 'Zusammenfassung kopieren', back: '← Zurück', next: 'Weiter →',
    bridge_ok: 'Die Brücke läuft.', bridge_no: 'Keine Brücke: mit ./start.sh starten', robot: 'Roboter', contract: 'Vertrag',
    usb_url: 'USB-Adresse', wifi_url: 'WLAN-Adresse',
    waiting: 'Warte auf das Handy…', connected: 'Handy verbunden:', no_phone: 'Kein Handy: erst eins verbinden (Schritt 2).',
    no_report: 'Noch kein Bericht.', report_from: 'Bericht von', core_ok: 'alles für Version 1 funktioniert', core_missing: 'fehlt:',
    face: 'Gesicht', face_q: 'Hat sich das Gesicht geändert?', gaze: 'Blick', gaze_hint: 'Im Feld ziehen: die Augen folgen.', gaze_q: 'Sind die Augen gefolgt?',
    color: 'Augenfarbe', color_q: 'Hat sich die Farbe geändert?', say: 'Stimme', say_text: 'Hallo, ich bin dein Roboter.', say_btn: 'Sagen', say_q: 'Hast du es gehört?',
    vibrate: 'Vibration', vibrate_btn: 'Brummen', vibrate_q: 'Hast du es gespürt?', torch: 'Lampe', on: 'An', off: 'Aus',
    torch_q: 'Ging das Licht an? (das Gesicht zeigt ● cam)', yes: 'ja', no: 'nein',
    touch: 'Berührung', touch_hint: 'Auf dem Handy: links, Mitte und rechts tippen; lange drücken; wischen.',
    motion: 'Bewegung', motion_hint: 'Das Handy kippen.', compass: 'Kompass', compass_hint: 'Das Handy flach liegend drehen.',
    battery: 'Akku', charging: 'lädt', none_yet: 'noch nichts', not_here: 'dieses Handy hat keinen',
    summary_lead: 'Was auf diesem Handy funktioniert. In deine Notizen oder den Roboterbau kopieren.', untested: 'nicht getestet', skipped: 'übersprungen',
    down: 'unten:',
    camera: 'Kamera', show: 'Auf dem Handy zeigen', hide: 'Verbergen', camera_q: 'Hat das Handy gezeigt, was seine Kamera sieht?',
    camera_hint: 'Das Handy zeigt das Bild seiner Rückkamera auf dem eigenen Bildschirm, eine Minute lang. Nichts verlässt das Handy.',
    code: 'Codes lesen', code_hint: 'Bei laufendem Bild: die Rückkamera des Handys vor diesen Code halten.', code_read: 'gelesen:',
    no_reader: 'der Browser dieses Handys liest keine Codes; der Kartenleser (Schritt 3) bringt einen eigenen mit',
    blocked: 'gesperrt: die Seite des Handys ist nicht sicher. Per USB verbinden, oder mit --cert starten',
    insecure: 'Dieses Handy nutzt eine nicht sichere Seite (http im WLAN): Kamera, Bewegung, Kompass und Akku sind gesperrt. Per USB verbinden, oder die Brücke mit Zertifikat starten (./start.sh --cert ORDNER).',
    no_torch: 'das Handy sagt, es hat keine Lampe', cam_error: 'die Kamera ging nicht auf:', size: 'Bild'
  }
};
var lang = 'en';
try { lang = localStorage.getItem('atl-lang') || (navigator.language || 'en').slice(0, 2); } catch (e) {}
if (!T[lang]) lang = 'en';
function t(k) { return T[lang][k] || T.en[k] || k; }
function $(id) { return document.getElementById(id); }
function el(tag, attrs, kids) {
  var e = document.createElement(tag);
  for (var k in attrs || {}) { if (k === 'text') e.textContent = attrs[k]; else if (k.slice(0, 2) === 'on') e[k] = attrs[k]; else e.setAttribute(k, attrs[k]); }
  (kids || []).forEach(function (c) { if (c) e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
  return e;
}

var STEPS = ['bridge', 'connect', 'check', 'test', 'summary'];
var step = 0, S = null, bridgeUp = null;
var answers = {};          // outputs: true / false, as the person says
var touched = {};          // touches seen: tap-left, tap-centre, tap-right, long, swipe
var imuRate = 0, lastImu = { n: 0, at: 0 }, tilt = {};
var passed = {};           // senses that worked once stay ticked, even if the phone reconnects
var CODE = 'atl-phone camera test';

// ---- talking to the bridge ---------------------------------------------------------------------------
function act(body) {
  return fetch('/api/act', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(function (r) { if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || r.status); }); })
    .catch(function (e) { $('meta').textContent = '⚠ ' + e.message; });
}
function poll() {
  fetch('/api/state').then(function (r) { return r.json(); }).then(function (s) {
    S = s; bridgeUp = true; update();
  }).catch(function () { bridgeUp = false; update(); }).then(function () { setTimeout(poll, 250); });
}

// ---- the steps ---------------------------------------------------------------------------------------
function marks() {
  var m = { bridge: bridgeUp === null ? '' : bridgeUp ? 'yes' : 'no' };
  m.connect = S && S.connected ? 'yes' : 'wait';
  var r = report();
  m.check = r ? (coreMissing(r).length ? 'no' : 'yes') : '';
  var res = results(), vals = Object.keys(res).map(function (k) { return res[k]; });
  m.test = vals.indexOf(false) >= 0 ? 'no' : vals.every(function (v) { return v === true || v === 'na'; }) ? 'yes' : 'wait';
  m.summary = '';
  return m;
}
function renderStepper() {
  var m = marks(), ol = $('stepper'); ol.innerHTML = '';
  STEPS.forEach(function (s, i) {
    var sym = m[s] === 'yes' ? '✓' : m[s] === 'no' ? '✗' : String(i + 1);
    ol.appendChild(el('li', { class: i === step ? 'on' : '', onclick: function () { go(i); } },
      [el('span', { class: 'mark ' + (m[s] || ''), text: sym }), el('span', { text: t('s' + (i + 1)) })]));
  });
}
function go(i) {
  step = Math.max(0, Math.min(STEPS.length - 1, i));
  STEPS.forEach(function (s, j) { $('s-' + s).className = j === step ? 'on' : ''; });
  $('back').disabled = step === 0; $('next').style.visibility = step === STEPS.length - 1 ? 'hidden' : 'visible';
  if (STEPS[step] === 'summary') renderSummary();
  renderStepper();
}

function update() {
  renderStepper();
  // 1: the bridge
  $('bridge-status').textContent = bridgeUp ? '✓ ' + t('bridge_ok') : bridgeUp === false ? '✗ ' + t('bridge_no') : '…';
  if (S) {
    $('meta').textContent = S.robot + ' · ' + S.contract;
    var info = $('bridge-info'); info.innerHTML = '';
    [[t('robot'), S.robot], [t('contract'), S.contract], [t('usb_url'), S.urls.usb], [t('wifi_url'), S.urls.wifi]].forEach(function (r) {
      info.appendChild(el('tr', {}, [el('th', { text: r[0] }), el('td', {}, [el('code', { text: r[1] })])]));
    });
    // 2: connect
    $('wifi-url').textContent = S.urls.wifi; $('wifi-warn').style.display = S.secure_wifi ? 'none' : 'block';
    drawQr(S.urls.wifi);
    var ps = $('phone-status'), caps = $('phone-caps');
    if (S.connected) {
      var ph = S.phone || {};
      ps.textContent = '✓ ' + t('connected') + ' ' + (ph.model || '…') + (ph.screen ? ' · ' + ph.screen.join('×') : '') + ' · ' + (ph.peer || '');
      caps.innerHTML = '';
      Object.keys(ph.caps || {}).forEach(function (k) { caps.appendChild(el('span', { class: 'chip ' + (ph.caps[k] ? 'yes' : 'no'), text: k })); });
    } else { ps.textContent = '⏳ ' + t('waiting'); caps.innerHTML = ''; }
    $('phone-insecure').style.display = insecure() ? 'block' : 'none';
    $('open-check').disabled = !S.connected;
    // 3: the check
    renderReport();
    // 4: live senses
    updateInputs();
    if (STEPS[step] === 'summary') renderSummary();
  }
}

function report() {
  if (!S || !S.reports.length) return null;
  var model = S.phone && S.phone.model, rs = S.reports.filter(function (r) { return !model || r.model === model; });
  return rs.length ? rs[rs.length - 1] : S.reports[S.reports.length - 1];
}
function coreMissing(r) { return Object.keys(r.checks).filter(function (k) { return r.checks[k].need === 'core' && r.checks[k].ok === false; }); }
var reportShown = null;
function renderReport() {
  var r = report(), st = $('report-status');
  if (!r) { st.textContent = t('no_report'); $('report').innerHTML = ''; return; }
  var miss = coreMissing(r);
  st.textContent = (miss.length ? '✗ ' : '✓ ') + t('report_from') + ' ' + r.model + ': ' + (miss.length ? t('core_missing') + ' ' + miss.join(', ') : t('core_ok'));
  if (reportShown === r.at) return; reportShown = r.at;
  var tb = $('report'); tb.innerHTML = '';
  Object.keys(r.checks).forEach(function (k) {
    var c = r.checks[k];
    tb.appendChild(el('tr', {}, [el('td', {}, [el('span', { class: 'mark ' + (c.ok === true ? 'yes' : c.ok === false ? 'no' : ''), text: c.ok === true ? '✓' : c.ok === false ? '✗' : '?' })]),
      el('td', { text: k }), el('td', { class: 'hint', text: (c.need || '') + (c.note ? ' · ' + c.note : '') })]));
  });
}

// ---- 4: the tests ------------------------------------------------------------------------------------
function ask(key, q) {
  var y = el('button', { text: t('yes') }), n = el('button', { text: t('no') });
  function paint() { y.className = answers[key] === true ? 'yes' : ''; n.className = answers[key] === false ? 'no' : ''; }
  y.onclick = function () { answers[key] = true; paint(); renderStepper(); };
  n.onclick = function () { answers[key] = false; paint(); renderStepper(); };
  paint();
  return el('div', { class: 'ask' }, [el('span', { text: t(q) }), y, n]);
}
function card(title, body, foot) {
  return el('div', { class: 'test' }, [el('div', { class: 'head' }, [el('b', { text: t(title) })])].concat(body).concat(foot ? [foot] : []));
}
function buildOutputs() {
  var o = $('outputs'); o.innerHTML = '';
  var exprs = (S && S.expressions) || ['neutral', 'happy', 'sad', 'angry', 'surprised', 'sleepy', 'curious', 'wink', 'scared', 'love'];
  o.appendChild(card('face', [el('div', { class: 'row' }, exprs.map(function (e) {
    return el('button', { class: 'b ghost small', text: e, onclick: function () { act({ topic: 'expression', value: e }); } });
  }))], ask('face', 'face_q')));
  var dot = el('i'), pad = el('div', { class: 'pad' }, [dot]), last = 0;
  function aim(e) {
    var r = pad.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    x = Math.max(0, Math.min(1, x)); y = Math.max(0, Math.min(1, y));
    dot.style.left = x * 100 + '%'; dot.style.top = y * 100 + '%';
    var now = Date.now(); if (now - last < 100) return; last = now;
    act({ topic: 'gaze', value: { x: x * 2 - 1, y: 1 - y * 2 } });
  }
  pad.onpointerdown = function (e) { pad.setPointerCapture(e.pointerId); aim(e); };
  pad.onpointermove = function (e) { if (e.buttons) aim(e); };
  o.appendChild(card('gaze', [el('div', { class: 'row' }, [pad, el('span', { class: 'hint', text: t('gaze_hint') })])], ask('gaze', 'gaze_q')));
  var pick = el('input', { type: 'color', value: '#3fd8ff' });
  pick.oninput = function () {
    var h = pick.value; act({ topic: 'color', value: [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16) / 255; }) });
  };
  o.appendChild(card('color', [el('div', { class: 'row' }, [pick])], ask('color', 'color_q')));
  var text = el('input', { type: 'text', value: t('say_text') }), sel = el('select', {}, ['en', 'fr', 'de'].map(function (l) {
    var op = el('option', { value: l, text: l.toUpperCase() }); if (l === lang) op.selected = true; return op;
  }));
  o.appendChild(card('say', [el('div', { class: 'row' }, [text, sel, el('button', { class: 'b', text: t('say_btn'), onclick: function () {
    act({ topic: 'say', value: { text: text.value, lang: sel.value } });
  } })])], ask('say', 'say_q')));
  o.appendChild(card('vibrate', [el('button', { class: 'b', text: t('vibrate_btn'), onclick: function () { act({ topic: 'vibrate', value: 400 }); } })], ask('vibrate', 'vibrate_q')));
  o.appendChild(card('torch', [el('div', { class: 'row' }, [
    el('button', { class: 'b', text: t('on'), onclick: function () { act({ topic: 'torch', value: true }); } }),
    el('button', { class: 'b ghost', text: t('off'), onclick: function () { act({ topic: 'torch', value: false }); } })]), live.torch = el('div', { class: 'hint' })],
    ask('torch', 'torch_q')));
  var qr = el('canvas', { class: 'qr' });
  drawQr(CODE, qr, 4);
  live.camera = el('div', { class: 'live' }); live.code = el('div', { class: 'live' }); live.codeMark = el('span', { class: 'mark' });
  o.appendChild(card('camera', [el('div', { class: 'hint', text: t('camera_hint') }), el('div', { class: 'row' }, [
    el('button', { class: 'b', text: t('show'), onclick: function () { act({ camera: true }); } }),
    el('button', { class: 'b ghost', text: t('hide'), onclick: function () { act({ camera: false }); } })]), live.camera,
    el('h3', { text: t('code') }), el('div', { class: 'qr' }, [qr, el('div', {}, [el('div', { class: 'hint', text: t('code_hint') }),
      el('div', { class: 'row' }, [live.codeMark, live.code])])])], ask('camera', 'camera_q')));
}
var live = {};
function buildInputs() {
  var o = $('inputs'); o.innerHTML = '';
  live.touch = el('div', { class: 'chips' }, GESTURES.map(function (k) { return el('span', { class: 'chip', 'data-k': k, text: k }); }));
  live.touchLast = el('div', { class: 'live' });
  o.appendChild(card('touch', [el('div', { class: 'hint', text: t('touch_hint') }), live.touch, live.touchLast]));
  live.motion = el('div', { class: 'live' }); live.motionMark = el('span', { class: 'mark' });
  o.appendChild(card('motion', [el('div', { class: 'row' }, [live.motionMark, el('span', { class: 'hint', text: t('motion_hint') })]), live.motion]));
  live.needle = el('i'); live.compass = el('div', { class: 'live' }); live.compassMark = el('span', { class: 'mark' });
  o.appendChild(card('compass', [el('div', { class: 'row' }, [el('div', { class: 'dial' }, [live.needle]), el('div', {}, [
    el('div', { class: 'row' }, [live.compassMark, el('span', { class: 'hint', text: t('compass_hint') })]), live.compass])])]));
  live.batteryBar = el('i'); live.battery = el('span', { class: 'live' }); live.batteryMark = el('span', { class: 'mark' });
  o.appendChild(card('battery', [el('div', { class: 'row' }, [live.batteryMark, el('span', { class: 'bar' }, [live.batteryBar]), live.battery])]));
}
function setMark(m, v) {
  m.className = 'mark ' + (v === true ? 'yes' : v === false ? 'no' : v === 'na' ? '' : 'wait');
  m.textContent = v === true ? '✓' : v === false ? '✗' : v === 'na' ? '–' : v === 'blocked' ? '!' : '…';
}
function fmt(v) { return (v >= 0 ? ' ' : '') + v.toFixed(1); }
function updateInputs() {
  if (!live.touch) return;
  var seen = S.seen || {}, now = S.now;
  (seen.touch || []).forEach(function (k) { touched[k.kind === 'tap' ? 'tap-' + k.zone : k.kind] = true; });
  [].forEach.call(live.touch.children, function (c) { c.className = 'chip' + (touched[c.getAttribute('data-k')] ? ' yes' : ''); });
  var lt = (seen.touch || []).slice(-1)[0];
  live.touchLast.textContent = lt ? lt.kind + ' · ' + lt.zone + (lt.dir ? ' · ' + lt.dir : '') : t('none_yet');
  var imu = seen.imu;
  if (imu) {
    if (imu.n < lastImu.n) lastImu = { n: 0, at: now };
    if (now - lastImu.at >= 1) { imuRate = (imu.n - lastImu.n) / (now - lastImu.at); lastImu = { n: imu.n, at: now }; }
    var a = imu.acc, ax = ['x', 'y', 'z'], big = 0;
    for (var i = 1; i < 3; i++) if (Math.abs(a[i]) > Math.abs(a[big])) big = i;
    tilt[(a[big] > 0 ? '+' : '-') + ax[big]] = true;
    live.motion.textContent = 'acc' + a.map(fmt).join('') + ' m/s²  gyro' + imu.gyro.map(fmt).join('') + ' rad/s  ' +
      Math.round(imuRate) + ' Hz  ' + t('down') + ' ' + (a[big] > 0 ? '-' : '+') + ax[big];
  } else live.motion.textContent = t('none_yet');
  var caps = (S.phone && S.phone.caps) || {};
  setMark(live.motionMark, inputResult('motion'));
  if (seen.heading) { live.needle.style.transform = 'rotate(' + seen.heading.deg + 'deg)'; live.compass.textContent = Math.round(seen.heading.deg) + '°'; }
  else live.compass.textContent = caps.compass === false ? t('not_here') : t('none_yet');
  setMark(live.compassMark, inputResult('compass'));
  if (seen.battery) {
    live.batteryBar.style.width = Math.round(seen.battery.level * 100) + '%';
    live.battery.textContent = Math.round(seen.battery.level * 100) + '%' + (seen.battery.charging ? ' · ' + t('charging') : '');
  } else live.battery.textContent = caps.battery === false ? t('not_here') : t('none_yet');
  setMark(live.batteryMark, inputResult('battery'));
  var c = seen.camera;
  live.camera.textContent = insecure() ? t('blocked') : !c ? '' : c.ok === false ? t('cam_error') + ' ' + (c.error || '?') :
    c.size && c.size[0] ? '● ' + t('size') + ' ' + c.size.join('×') + (c.on ? '' : ' (' + t('off').toLowerCase() + ')') : '';
  live.torch.textContent = c && c.torch === false && c.ok !== false ? t('no_torch') : '';
  live.code.textContent = c && c.codes ? t('code_read') + ' ' + c.codes[c.codes.length - 1] :
    insecure() ? '' : noteOf('code', inputResult('code')) || t('none_yet');  // blocked: said once, above
  setMark(live.codeMark, inputResult('code'));
}
function insecure() { return !!(S && S.connected && S.phone && S.phone.secure === false); }
function noteOf(k, v) {  // why a result is not a plain yes or no
  if (v === 'blocked') return t('blocked');
  if (v === 'na') return k === 'code' ? t('no_reader') : k === 'torch' ? t('no_torch') : t('not_here');
  if (v === null) return partial(k) || t('untested');
  var c = S && S.seen && S.seen.camera;
  if (k === 'camera' && v === false && c && c.error) return t('cam_error') + ' ' + c.error;
  return '';
}
var NEED_SECURE = { camera: 1, torch: 1, code: 1, motion: 1, compass: 1, battery: 1 };
function inputResult(k) {
  var v = passed[k] || inputNow(k);
  if (v === true) passed[k] = true;
  return v !== true && insecure() && NEED_SECURE[k] ? 'blocked' : v;
}
function inputNow(k) {
  var seen = (S && S.seen) || {}, caps = (S && S.phone && S.phone.caps) || {};
  if (k === 'code') return seen.camera && seen.camera.codes ? true : caps.barcode === false ? 'na' : null;
  if (k === 'touch') return GESTURES.every(function (x) { return touched[x]; }) || null;
  if (k === 'motion') return seen.imu ? (Object.keys(tilt).length >= 2 || null) : (caps.motion === false ? false : null);
  if (k === 'compass') return seen.heading ? true : caps.compass === false ? 'na' : null;
  if (k === 'battery') return seen.battery ? true : caps.battery === false ? 'na' : null;
}
var GESTURES = ['tap-left', 'tap-centre', 'tap-right', 'long', 'swipe'];
function partial(k) {  // a test begun but not finished: what is still missing
  if (k !== 'touch') return '';
  var miss = GESTURES.filter(function (x) { return !touched[x]; });
  return miss.length < GESTURES.length ? t('core_missing') + ' ' + miss.join(', ') : '';
}
function results() {
  var r = {};
  var cam = (S && S.seen && S.seen.camera) || {};
  ['face', 'gaze', 'color', 'say', 'vibrate', 'torch', 'camera'].forEach(function (k) {
    r[k] = k in answers ? answers[k] : null;
    if (r[k] === null && NEED_SECURE[k] && insecure()) r[k] = 'blocked';
  });
  if (r.torch === null && cam.torch === false && cam.ok !== false) r.torch = 'na';
  if (r.camera === null && cam.ok === false) r.camera = false;
  ['touch', 'motion', 'compass', 'battery', 'code'].forEach(function (k) { r[k] = inputResult(k); });
  return r;
}

// ---- 5: summary --------------------------------------------------------------------------------------
function summaryText() {
  var r = results(), ph = (S && S.phone) || {}, rep = report();
  var lines = ['Phone: ' + (ph.model || '?') + ' (' + (S ? S.robot : '?') + ', ' + (S ? S.contract : '') + ')', 'Date: ' + new Date().toISOString().slice(0, 10)];
  if (rep) lines.push('Check: ' + (coreMissing(rep).length ? 'missing ' + coreMissing(rep).join(', ') : 'core complete'));
  if (insecure()) lines.push('Page: not secure (http over Wi-Fi): camera, motion, compass, battery blocked');
  Object.keys(r).forEach(function (k) {
    var v = r[k], more = v === 'na' ? ' (none)' : v === 'blocked' ? ' (blocked: page not secure)' :
      v === null ? ' (' + (partial(k) ? 'missing ' + GESTURES.filter(function (x) { return !touched[x]; }).join(', ') : 'not tested') + ')' : '';
    lines.push((v === true ? '[x] ' : v === false ? '[ ] ' : '[-] ') + k + more);
  });
  return lines.join('\n');
}
function renderSummary() {
  var r = results(), ph = (S && S.phone) || {}, tb = $('summary'); tb.innerHTML = '';
  $('summary-lead').textContent = t('summary_lead') + (ph.model ? ' · ' + ph.model : '');
  var rep = report();
  tb.appendChild(el('tr', {}, [el('td', {}, [el('span', { class: 'mark ' + (rep ? (coreMissing(rep).length ? 'no' : 'yes') : ''), text: rep ? (coreMissing(rep).length ? '✗' : '✓') : '–' })]),
    el('td', { text: t('s3') }), el('td', { class: 'hint', text: rep ? (coreMissing(rep).length ? t('core_missing') + ' ' + coreMissing(rep).join(', ') : t('core_ok')) : t('skipped') })]));
  Object.keys(r).forEach(function (k) {
    var m = el('span'); setMark(m, r[k]);
    tb.appendChild(el('tr', {}, [el('td', {}, [m]), el('td', { text: t(k) }), el('td', { class: 'hint', text: noteOf(k, r[k]) })]));
  });
}

// ---- the page ----------------------------------------------------------------------------------------
var qrFor = null;
function drawQr(text, c, s) {
  if (!c) { if (qrFor === text) return; qrFor = text; c = $('qr'); s = 5; }
  if (typeof qrcode !== 'function') return;
  var q = qrcode(0, 'M'); q.addData(text); q.make();
  var n = q.getModuleCount(); c.width = c.height = n * s;
  var g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, n * s, n * s); g.fillStyle = '#000';
  for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) if (q.isDark(y, x)) g.fillRect(x * s, y * s, s, s);
}
function copy(text, done) {
  (navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(text) : Promise.reject())
    .then(done, function () { var a = el('textarea'); a.value = text; document.body.appendChild(a); a.select(); document.execCommand('copy'); a.remove(); done(); });
}
function translate() {
  document.documentElement.lang = lang;
  [].forEach.call(document.querySelectorAll('[data-t]'), function (e) { e.textContent = t(e.getAttribute('data-t')); });
  [].forEach.call(document.querySelectorAll('.lang button'), function (b) { b.className = b.getAttribute('data-l') === lang ? 'on' : ''; });
  document.title = t('title');
  buildOutputs(); buildInputs(); go(step);
  if (S) update();
}
[].forEach.call(document.querySelectorAll('.lang button'), function (b) {
  b.onclick = function () { lang = b.getAttribute('data-l'); try { localStorage.setItem('atl-lang', lang); } catch (e) {} translate(); };
});
[].forEach.call(document.querySelectorAll('.tabs button'), function (b) {
  b.onclick = function () {
    [].forEach.call(document.querySelectorAll('.tabs button'), function (x) { x.className = x === b ? 'on' : ''; });
    $('tab-usb').style.display = b.getAttribute('data-tab') === 'usb' ? 'block' : 'none';
    $('tab-wifi').style.display = b.getAttribute('data-tab') === 'wifi' ? 'block' : 'none';
  };
});
[].forEach.call(document.querySelectorAll('[data-copy]'), function (b) { b.onclick = function () { copy(b.getAttribute('data-copy'), function () { b.textContent = t('copied'); }); }; });
$('copy-wifi').onclick = function () { copy($('wifi-url').textContent, function () { $('copy-wifi').textContent = t('copied'); }); };
$('copy-summary').onclick = function () { copy(summaryText(), function () { $('copied').textContent = t('copied'); }); };
$('open-check').onclick = function () { act({ open: 'check.html' }); };
$('back').onclick = function () { go(step - 1); };
$('next').onclick = function () { go(step + 1); };
translate();
poll();

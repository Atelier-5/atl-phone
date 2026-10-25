// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// Omi Assist's helpers, on the phone (contract atl-phone/0.5): the time, the magnifier, reading aloud, "what is this?",
// the eyes following, and showing the picture to the PC. Loaded after face.js and see.js, whose camera, speech, panel and
// vision it uses. Reading (vendor/tesseract) and "what is this?" (MediaPipe's objects) run here: what they read or see
// is said and written on this screen, and ROS only hears how it went (lines, characters, a label, how long). Showing is
// the one exception to "pictures stay on the phone": only when the bridge allows it, only while the person shows, with
// the red badge on, at most a minute; the frames go to the bridge, which hands them to the setup page and keeps none.
'use strict';

var TESS = 'vendor/tesseract', OCR_LANG = { en: 'eng', fr: 'fra', de: 'deu' };
var SHOW_FPS = 2, SHOW_PX = 320, SHOW_MAX_MS = 60000, STILL_SETTLE_MS = 700;
var OMI_TEXT = {
  en: { wait: 'One moment…', reading: 'One moment, I am reading.', notext: 'I find no text. Hold it closer to the back camera, in good light.',
        is: 'This is {x}.', think: 'I think this is {x}.', nothing: 'I see nothing I know. Hold it in front of the back camera.',
        person: 'I see a person.', followOn: 'My eyes follow what is nearest.', followOff: 'I look around again.',
        showOn: 'I am showing the picture to the computer.', showOff: 'I stopped showing.', showNo: 'Showing is not allowed. Ask your assistant.',
        noCam: 'The camera does not open.', back: 'Here I am again!', now: 'It is {t}.', today: 'Today is {d}.',
        quarter: ['', 'a quarter past {h}', 'half past {h}', 'a quarter to {n}'], oclock: '{h} o’clock' },
  fr: { wait: 'Un instant…', reading: 'Un instant, je lis.', notext: 'Je ne trouve pas de texte. Approche-le de la caméra arrière, avec de la lumière.',
        is: 'C’est {x}.', think: 'Je crois que c’est {x}.', nothing: 'Je ne reconnais rien. Tiens-le devant la caméra arrière.',
        person: 'Je vois une personne.', followOn: 'Mes yeux suivent ce qui est le plus près.', followOff: 'Je regarde de nouveau autour de moi.',
        showOn: 'Je montre l’image à l’ordinateur.', showOff: 'J’ai arrêté de montrer.', showNo: 'Montrer n’est pas permis. Demande à la personne qui t’assiste.',
        noCam: 'La caméra ne s’ouvre pas.', back: 'Me revoilà !', now: 'Il est {t}.', today: 'Nous sommes {d}.',
        quarter: ['', '{h} heure(s) et quart', '{h} heure(s) et demie', '{n} heure(s) moins le quart'], oclock: '{h} heure(s)' },
  de: { wait: 'Moment…', reading: 'Moment, ich lese.', notext: 'Ich finde keinen Text. Halte ihn näher an die hintere Kamera, bei gutem Licht.',
        is: 'Das ist {x}.', think: 'Ich glaube, das ist {x}.', nothing: 'Ich erkenne nichts. Halte es vor die hintere Kamera.',
        person: 'Ich sehe einen Menschen.', followOn: 'Meine Augen folgen dem, was am nächsten ist.', followOff: 'Ich schaue mich wieder um.',
        showOn: 'Ich zeige das Bild dem Computer.', showOff: 'Ich zeige nicht mehr.', showNo: 'Zeigen ist nicht erlaubt. Frag deine Assistenz.',
        noCam: 'Die Kamera geht nicht auf.', back: 'Hier bin ich wieder!', now: 'Es ist {t}.', today: 'Heute ist {d}.',
        quarter: ['', 'Viertel nach {h}', 'halb {n}', 'Viertel vor {n}'], oclock: '{h} Uhr' }
};
// the presentation (the setup page's "Introduce"): what each step says, in the order of the tiles
var TOUR_TEXT = {
  en: { hello: 'Hello Omi! I am Omi Assist, your personal helper. I live in this phone. Let me show you what I can do.',
        menu: 'When I can help you, just tap my eyes. Then these big tiles come. Each one tells you its name.',
        time: 'Time: I tell you what time it is, and what day it is today.',
        front: 'Front camera: you see yourself, as in a mirror.',
        back: 'Back camera: you see what is behind the phone. One tap is enough to switch.',
        magnify: 'The magnifier makes small print big. Plus and minus zoom, the lamp helps in the dark, and the hand holds the picture still.',
        read: 'Read aloud: hold a letter in front of the back camera, and I read it to you. One tap, and I stop.',
        what: 'What is this? Hold something up, and I tell you what it is, a cup for example.',
        follow: 'Follow: my eyes always look at what is nearest to me. At you, for example.',
        show: 'Show: you can show something to your assistant at the computer. Only while you press it, and then you see a red dot at the top.',
        remind: 'And your assistant can give me reminders. Then a card like this one comes. Tap Done, or Later, and I remind you again in ten minutes.',
        card: 'For example: take the tablets',
        face: 'And with Face you always come back to me.',
        bye: 'That is all. I am glad to help you!' },
  fr: { hello: 'Bonjour Omi ! Je suis Omi Assist, ton assistant personnel. J’habite dans ce téléphone. Je te montre ce que je sais faire.',
        menu: 'Si je peux t’aider, touche simplement mes yeux. Ces grandes tuiles arrivent alors. Chacune te dit son nom.',
        time: 'L’heure : je te dis quelle heure il est, et quel jour nous sommes.',
        front: 'Caméra avant : tu te vois toi-même, comme dans un miroir.',
        back: 'Caméra arrière : tu vois ce qui est derrière le téléphone. Un toucher suffit pour changer.',
        magnify: 'La loupe rend les petites lettres grandes. Plus et moins agrandissent, la lampe aide dans le noir, et la main fige l’image.',
        read: 'Lire : tiens une lettre devant la caméra arrière, et je te la lis. Un toucher, et je m’arrête.',
        what: 'Qu’est-ce que c’est ? Montre-moi quelque chose, et je te dis ce que c’est, une tasse par exemple.',
        follow: 'Suivre : mes yeux regardent toujours ce qui est le plus près de moi. Toi, par exemple.',
        show: 'Montrer : tu peux montrer quelque chose à la personne qui t’assiste, à l’ordinateur. Seulement pendant que tu appuies, et tu vois alors un point rouge en haut.',
        remind: 'Et la personne qui t’assiste peut me donner des rappels. Une carte comme celle-ci arrive alors. Touche Fait, ou Plus tard, et je te le rappelle dans dix minutes.',
        card: 'Par exemple : prendre les comprimés',
        face: 'Et avec Visage, tu reviens toujours vers moi.',
        bye: 'C’est tout. Je suis content de t’aider !' },
  de: { hello: 'Hallo Omi! Ich bin Omi Assist, dein persönlicher Helfer. Ich wohne in diesem Handy. Ich zeige dir kurz, was ich kann.',
        menu: 'Wenn ich dir helfen kann, tippe einfach auf meine Augen. Dann kommen diese großen Kacheln. Jede sagt dir ihren Namen.',
        time: 'Uhrzeit: ich sage dir, wie spät es ist, und welcher Tag heute ist.',
        front: 'Vordere Kamera: du siehst dich selbst, wie in einem Spiegel.',
        back: 'Hintere Kamera: du siehst, was hinter dem Handy ist. Ein Tipp genügt zum Wechseln.',
        magnify: 'Die Lupe macht kleine Schrift groß. Plus und Minus vergrößern, die Lampe hilft im Dunkeln, und die Hand hält das Bild fest.',
        read: 'Vorlesen: halte mir einen Brief vor die hintere Kamera, und ich lese ihn dir vor. Ein Tipp, und ich höre auf.',
        what: 'Was ist das? Halte mir etwas hin, und ich sage dir, was es ist, zum Beispiel eine Tasse.',
        follow: 'Folgen: meine Augen schauen immer auf das, was mir am nächsten ist. Auf dich zum Beispiel.',
        show: 'Zeigen: so kannst du deiner Assistenz am Computer etwas zeigen. Nur solange du es drückst, und dann siehst du oben einen roten Punkt.',
        remind: 'Und deine Assistenz kann mir Erinnerungen geben. Dann kommt so eine Karte. Tippe auf Erledigt, oder auf Später, dann erinnere ich dich in zehn Minuten noch einmal.',
        card: 'Zum Beispiel: Tabletten nehmen',
        face: 'Und mit Gesicht kommst du immer zurück zu mir.',
        bye: 'Das war es. Ich freue mich, dir zu helfen!' }
};
// its steps: the tile it points at, the mode it then shows for a moment, the time said, the sample card
var TOUR = [{ k: 'hello', face: 'happy' }, { k: 'menu', menu: true }, { k: 'time', tile: 'time', time: true },
            { k: 'front', tile: 'front', mode: 'camera' }, { k: 'back', tile: 'back', mode: 'camera_back' },
            { k: 'magnify', tile: 'magnify', mode: 'magnify' }, { k: 'read', tile: 'read' }, { k: 'what', tile: 'what' },
            { k: 'follow', tile: 'follow' }, { k: 'show', tile: 'show' }, { k: 'remind', card: true },
            { k: 'face', tile: 'face' }, { k: 'bye', face: 'love' }];
// what "what is this?" says, for each of the model's labels (contract OBJECTS): [English, French, German], with the article
var WHAT = {
  person: ['a person', 'une personne', 'ein Mensch'], bicycle: ['a bicycle', 'un vélo', 'ein Fahrrad'], car: ['a car', 'une voiture', 'ein Auto'],
  motorcycle: ['a motorbike', 'une moto', 'ein Motorrad'], airplane: ['an aeroplane', 'un avion', 'ein Flugzeug'], bus: ['a bus', 'un bus', 'ein Bus'],
  train: ['a train', 'un train', 'ein Zug'], truck: ['a lorry', 'un camion', 'ein Lastwagen'], boat: ['a boat', 'un bateau', 'ein Boot'],
  'traffic light': ['a traffic light', 'un feu de circulation', 'eine Ampel'], 'fire hydrant': ['a fire hydrant', 'une bouche d’incendie', 'ein Hydrant'],
  'stop sign': ['a stop sign', 'un panneau stop', 'ein Stoppschild'], 'parking meter': ['a parking meter', 'un parcmètre', 'eine Parkuhr'],
  bench: ['a bench', 'un banc', 'eine Bank'], bird: ['a bird', 'un oiseau', 'ein Vogel'], cat: ['a cat', 'un chat', 'eine Katze'],
  dog: ['a dog', 'un chien', 'ein Hund'], horse: ['a horse', 'un cheval', 'ein Pferd'], sheep: ['a sheep', 'un mouton', 'ein Schaf'],
  cow: ['a cow', 'une vache', 'eine Kuh'], elephant: ['an elephant', 'un éléphant', 'ein Elefant'], bear: ['a bear', 'un ours', 'ein Bär'],
  zebra: ['a zebra', 'un zèbre', 'ein Zebra'], giraffe: ['a giraffe', 'une girafe', 'eine Giraffe'], backpack: ['a backpack', 'un sac à dos', 'ein Rucksack'],
  umbrella: ['an umbrella', 'un parapluie', 'ein Regenschirm'], handbag: ['a handbag', 'un sac à main', 'eine Handtasche'],
  tie: ['a tie', 'une cravate', 'eine Krawatte'], suitcase: ['a suitcase', 'une valise', 'ein Koffer'], frisbee: ['a frisbee', 'un frisbee', 'eine Frisbeescheibe'],
  skis: ['skis', 'des skis', 'Skier'], snowboard: ['a snowboard', 'un snowboard', 'ein Snowboard'], 'sports ball': ['a ball', 'un ballon', 'ein Ball'],
  kite: ['a kite', 'un cerf-volant', 'ein Drachen'], 'baseball bat': ['a baseball bat', 'une batte de baseball', 'ein Baseballschläger'],
  'baseball glove': ['a baseball glove', 'un gant de baseball', 'ein Baseballhandschuh'], skateboard: ['a skateboard', 'un skateboard', 'ein Skateboard'],
  surfboard: ['a surfboard', 'une planche de surf', 'ein Surfbrett'], 'tennis racket': ['a tennis racket', 'une raquette de tennis', 'ein Tennisschläger'],
  bottle: ['a bottle', 'une bouteille', 'eine Flasche'], 'wine glass': ['a wine glass', 'un verre à vin', 'ein Weinglas'], cup: ['a cup', 'une tasse', 'eine Tasse'],
  fork: ['a fork', 'une fourchette', 'eine Gabel'], knife: ['a knife', 'un couteau', 'ein Messer'], spoon: ['a spoon', 'une cuillère', 'ein Löffel'],
  bowl: ['a bowl', 'un bol', 'eine Schüssel'], banana: ['a banana', 'une banane', 'eine Banane'], apple: ['an apple', 'une pomme', 'ein Apfel'],
  sandwich: ['a sandwich', 'un sandwich', 'ein Sandwich'], orange: ['an orange', 'une orange', 'eine Orange'], broccoli: ['broccoli', 'du brocoli', 'Brokkoli'],
  carrot: ['a carrot', 'une carotte', 'eine Karotte'], 'hot dog': ['a hot dog', 'un hot-dog', 'ein Hotdog'], pizza: ['a pizza', 'une pizza', 'eine Pizza'],
  donut: ['a doughnut', 'un beignet', 'ein Donut'], cake: ['a cake', 'un gâteau', 'ein Kuchen'], chair: ['a chair', 'une chaise', 'ein Stuhl'],
  couch: ['a sofa', 'un canapé', 'ein Sofa'], 'potted plant': ['a pot plant', 'une plante en pot', 'eine Topfpflanze'], bed: ['a bed', 'un lit', 'ein Bett'],
  'dining table': ['a table', 'une table', 'ein Tisch'], toilet: ['a toilet', 'des toilettes', 'eine Toilette'], tv: ['a television', 'une télévision', 'ein Fernseher'],
  laptop: ['a laptop', 'un ordinateur portable', 'ein Laptop'], mouse: ['a computer mouse', 'une souris', 'eine Computermaus'],
  remote: ['a remote control', 'une télécommande', 'eine Fernbedienung'], keyboard: ['a keyboard', 'un clavier', 'eine Tastatur'],
  'cell phone': ['a mobile phone', 'un téléphone portable', 'ein Handy'], microwave: ['a microwave', 'un micro-ondes', 'eine Mikrowelle'],
  oven: ['an oven', 'un four', 'ein Backofen'], toaster: ['a toaster', 'un grille-pain', 'ein Toaster'], sink: ['a sink', 'un évier', 'ein Waschbecken'],
  refrigerator: ['a fridge', 'un réfrigérateur', 'ein Kühlschrank'], book: ['a book', 'un livre', 'ein Buch'], clock: ['a clock', 'une horloge', 'eine Uhr'],
  vase: ['a vase', 'un vase', 'eine Vase'], scissors: ['scissors', 'des ciseaux', 'eine Schere'], 'teddy bear': ['a teddy bear', 'un ours en peluche', 'ein Teddybär'],
  'hair drier': ['a hair dryer', 'un sèche-cheveux', 'ein Föhn'], toothbrush: ['a toothbrush', 'une brosse à dents', 'eine Zahnbürste']
};
var omi = { busy: '', tess: {}, toastOff: 0, reading: 0, showAllowed: false, showing: false, showTimer: 0, showOff: 0,
            zoom: 1, cssZoom: false, held: false, torch: false, full: false, still: document.createElement('video'),
            canvas: document.createElement('canvas'), tour: 0, touring: false };
omi.still.muted = true; omi.still.setAttribute('playsinline', '');
function ot(l, k) { return (OMI_TEXT[l] || OMI_TEXT.en)[k]; }
function li(l) { return { en: 0, fr: 1, de: 2 }[l] || 0; }
var toastEl = document.getElementById('toast'), showEl = document.getElementById('showing'), magEl = document.getElementById('mag');

function toast(text, ms) {  // said and also written, big, for a moment
  clearTimeout(omi.toastOff);
  toastEl.textContent = text; toastEl.style.display = text ? 'block' : 'none';
  if (text) omi.toastOff = setTimeout(function () { toastEl.style.display = 'none'; }, ms || 6000);
}
function tell(text, l, ms, done) { toast(text, ms); speak(text, l || lang, false, done); }

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
  }
}

// ---- the presentation: Omi Assist says what it can, pointing at each tile and showing it; a tap ends it ------------------
function tourSay(text, l, done) {  // said and written; on to the next when said, or after a while if the voice is stuck
  var once = function () { if (once) { once = null; done(); } };
  tell(text, l, 30000, once);
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
    if (s.face) setExpression(s.face);
    if (s.menu || s.tile) tourMenu(s.tile); else { hideMenu(); toastEl.classList.remove('above'); }
    if (s.card) noteCard({ id: 'tour', text: t.card, buttons: [{ id: 'done', label: noteWord('done', l) }, { id: 'later', label: noteWord('later', l) }] });
    tourSay(t[s.k], l, function () {
      if (run !== omi.tour) return;
      if (s.card) { noteCard({ id: 'tour', text: '' }); return wait(500); }
      if (s.time) return tourSay(timePhrase(new Date(), l), l, function () { wait(600); });
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
function sayTime(l) { tell(timePhrase(new Date(), l), l, 8000); }

// ---- the eyes follow the nearest thing (see.js), or look around ------------------------------------------------------
function followToggle() {
  var on = !vision.follow;
  if (on && !finders().length) seeAt({ camera: 'front', find: ['faces', 'hands'], follow: true });  // nothing looks yet: the quick finders
  else { vision.follow = on; seeing.follow = { cur: null, cand: null, candAt: 0 }; seeReport({}); }
  if (!on && finders().length && vision.find.join() === 'faces,hands') seeAt({ camera: 'front', find: [] });  // what the tile started
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
      tell(ss[i], l, 60000, function () { next(i + 1); });
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
    tell(whatPhrase(label, score, l), l, 8000);
  }).catch(function (e) {
    omi.busy = '';
    send({ t: 'what', ok: false, label: null, score: 0, ms: Math.round(performance.now() - t0) });
    tell(ot(l, 'noCam'), l, 6000);
  });
}

// ---- the magnifier: the back camera in the panel; zoom (the camera's own, else a scale), the torch, hold ---------------
var MAG = [['minus', '−'], ['plus', '+'], ['torch', '💡'], ['hold', '✋']];
MAG.forEach(function (b) {
  var el = document.createElement('button');
  el.textContent = b[1]; el.dataset.id = b[0];
  el.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); magnify(b[0]); if (navigator.vibrate) navigator.vibrate(20); });
  magEl.appendChild(el);
});
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
  magnifyShow(true);
}
function magnifyShow(on) {
  magEl.style.display = on ? 'flex' : 'none';
  if (!on) {
    if (omi.held) { omi.held = false; pcam.play().catch(function () {}); }
    if (omi.torch) { omi.torch = false; var k = magTrack(); if (k) k.applyConstraints({ advanced: [{ torch: false }] }).catch(function () {}); }
    omi.zoom = 1; omi.cssZoom = false;
    if (omi.full) { omi.full = false; panelEl.classList.remove('full'); }
    return;
  }
  pcam.style.transform = omi.cssZoom && omi.zoom > 1 ? 'scale(' + omi.zoom.toFixed(2) + ')' : 'none';
  [].forEach.call(magEl.children, function (b) {
    b.classList.toggle('on', (b.dataset.id === 'torch' && omi.torch) || (b.dataset.id === 'hold' && omi.held));
  });
}

// ---- showing the picture to the PC: only when allowed, only while on, with the red badge ------------------------------
function showBadge() {
  showEl.textContent = '● ' + mt('showing');
  showEl.style.display = omi.showing ? 'block' : 'none';
  buildMenu();
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

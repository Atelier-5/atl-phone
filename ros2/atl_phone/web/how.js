// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// The setup page's "How it works": what the robot does, USB or Wi-Fi, where each part runs (the lab now, the robot with
// its Pi), and which recognition runs on the phone or on the Pi; it links the architecture pack (/docs/). Static text.

var HOW = {
  en: {
    lead: 'What the robot does, how the phone connects, and where each part runs.',
    docs: '📐 The architecture docs', docs_d: 'For engineers: every box tied to the lines of code it comes from (in English).',
    feat_h: 'What it does',
    feats: [
      ['The face', 'Ten expressions; eyes that look around, or where a program says; their colour; a voice in English, French and German; vibration; the torch. Held upright, the lower half is a panel: a mouth that moves while it speaks, a button pad, a camera view, the sensors.'],
      ['The senses', 'Touch, motion, compass and battery; with a camera: faces, QR codes, printed markers with their distance, colour patches, 80 kinds of objects, hands and their gestures. Only numbers leave the phone.'],
      ['Desk Guard', 'It watches a desk: sleepy while nobody is there, a face wakes it and it turns to it; the owner’s card makes a friend; a stranger too close for too long is told off; lifted, it asks to be put down; at the desk’s edge it backs off.'],
      ['Omi Assist', 'A helper for someone who sees or hears less well. A tap on the eyes opens big tiles that say their name: the time, the front and back camera, a magnifier, reading aloud, “what is this?”, the sensors, eyes that follow. Her assistant’s reminders come at their time as a big card she answers. She can show the camera’s picture to her assistant, only when allowed. Übersetzen: hold the German or the French half and speak, and the phone says it in the other language (translated offline on the robot’s computer, only when allowed); a letter in French it offers to read in German.'],
      ['The Webots twin', 'The same robot in simulation: it plays the phone, or follows the real phone’s screen as a mirror. Demo objects fly in: a cup, a letter, a visitor.'],
      ['ROS 2', 'Everything a program needs is a topic under /&lt;robot&gt;/phone/ (contract atl-phone/0.8): one program runs unchanged with the real phone and with the twin.'],
      ['Privacy', 'Pictures and sound stay on the phone and nothing is recorded. Telling faces apart (this session only), showing a picture and Übersetzen’s sound (only while held, heard on the robot’s computer and dropped) are switched on by the facilitator, after asking.']
    ],
    conn_h: 'The phone on USB or on Wi-Fi',
    conn_cols: ['', 'USB (adb reverse)', 'Wi-Fi'],
    conn: [
      ['Camera, microphone, motion', 'Yes: the page is the phone’s own “localhost”, a secure page', 'Only with HTTPS: <code>./start.sh --make-cert</code>, and the certificate installed once on the phone. Plain http blocks camera, motion, compass and battery'],
      ['Setting up', 'USB debugging once, then <code>./scripts/usb.sh</code>', 'The same Wi-Fi, scan the QR code (a pairing key keeps other phones out)'],
      ['Power', 'The cable charges the phone', 'Its own battery only; the camera drains it'],
      ['“A lighter phone” card', 'Yes (the load, background apps, tabs): through adb', 'No: it needs adb, which is on USB'],
      ['Delay', 'The smallest, steady', 'A little more, and it depends on the Wi-Fi'],
      ['Moving', 'Tied to the computer by its cable', 'Free, within the Wi-Fi'],
      ['Use it for', 'The desk and the lab; on the robot, the phone is on the Pi’s USB', 'A phone that moves around on its own, a demo across the room']
    ],
    conn_note: 'Showing the picture works both ways: the phone sends it to the bridge, and the bridge hands it only to its own computer.',
    cfg_h: 'Where each part runs',
    lab: { t: 'The lab: now', d: 'Everything on the PC; the phone on the PC’s USB.', boxes: [
      ['💻 PC', 'Docker: the bridge (ROS 2), Omi Assist, the Desk Guardian · the setup page · Webots: the phone’s twin as a mirror, the Thymio twin · the Thymio link, when a Thymio is connected'],
      ['📱 Phone', 'USB to the PC: the face, vision, reading, the voice'],
      ['🤖 Thymio', 'Carries the phone; it drives only when Desk Guard is allowed to']] },
    auto: { t: 'Autonomous: with the Pi', d: 'The robot on its own: the Pi on the Thymio runs the brain. Designed, not yet run on the Pi.', boxes: [
      ['🍓 Raspberry Pi 4, on the robot', 'Docker: the bridge (ROS 2), Omi Assist, the Thymio link · adb for the phone’s link · the pages and these docs'],
      ['📱 Phone', 'USB to the Pi: the face, vision, reading, the voice; it charges from the Pi'],
      ['🤖 Thymio', 'USB to the Pi; its own battery. At most 0.12 m/s with the stack on top'],
      ['💻 PC or tablet', 'Wi-Fi: the setup page and the Webots mirror through an SSH tunnel (<code>ssh -L 8782:localhost:8782 pi@&lt;robot&gt;</code>): the setup page answers its own computer only']] },
    cfg_note: 'The Pi needs 5 V and 3 A: a power bank on the robot (it changes the balance: try it on the twin first), or the mains on a stand.',
    rec_h: 'Recognition: on the phone, and on the Pi',
    rec_lead: 'The phone sees: its models run in the page, on its graphics chip when they can. The Pi (in the lab, the PC) gets numbers, never pictures, and decides.',
    rec_cols: ['', 'On the phone (onboard)', 'On the Pi (edge)'],
    rec: [
      ['Faces', 'MediaPipe BlazeFace: where, how big; 85 ms a picture on the ANE-LX1. Following: 4 looks a second, 1 while nobody is there', 'Desk Guard wakes and turns the Thymio to the face; Omi Assist greets a face after five minutes alone'],
      ['Telling faces apart', 'face-api: a signature of 128 numbers, in the page’s memory only, this session only (opt-in)', 'The bridge removes the numbers unless the facilitator allowed it'],
      ['Objects', 'MediaPipe EfficientDet-Lite0: 80 kinds, a box, a score, a distance for kinds of known height. “What is this?” takes 2.6 s', 'Programs get the label, the box and the distance'],
      ['Hands', 'MediaPipe gesture recogniser: where, and 8 gestures; 212 ms a picture', 'Programs get where and which gesture'],
      ['Markers, colours, codes', 'js-aruco2 (printed markers, distance and angle), its own colour finder, the browser’s QR reader', 'Desk Guard’s owner card is a QR code'],
      ['Text', 'Tesseract.js, in German, English and French: read and said on the phone; 2.7 s', 'Only how many lines and characters'],
      ['Speech (Übersetzen)', 'The microphone, only while a half is held; 16 kHz sound to the bridge', 'Vosk hears German or French, Opus-MT translates (offline, about 0.2 s); the words go back to the phone, the sound is dropped'],
      ['Checked on the way', '', 'Every message is checked and clamped; faces at most 10 a second, motion 60']
    ],
    rec_note: 'A bigger model on the Pi would need the pictures to leave the phone, which the privacy rules do not allow; a camera of the Pi’s own would be the way (not built). In Webots, the twin’s own recognition stands in for the phone’s models.'
  },
  fr: {
    lead: 'Ce que fait le robot, comment le téléphone se connecte, et où tourne chaque partie.',
    docs: '📐 La documentation d’architecture', docs_d: 'Pour les ingénieurs : chaque boîte liée aux lignes de code dont elle vient (en anglais).',
    feat_h: 'Ce qu’il fait',
    feats: [
      ['Le visage', 'Dix expressions ; des yeux qui regardent autour ou là où un programme le dit ; leur couleur ; une voix en anglais, français et allemand ; la vibration ; la lampe. Tenu debout, le bas devient un panneau : une bouche qui bouge quand il parle, un pavé de boutons, une vue de caméra, les capteurs.'],
      ['Les sens', 'Le toucher, le mouvement, la boussole et la batterie ; avec une caméra : les visages, les codes QR, des marqueurs imprimés et leur distance, des taches de couleur, 80 sortes d’objets, les mains et leurs gestes. Seuls des nombres quittent le téléphone.'],
      ['Gardien du bureau', 'Il surveille un bureau : endormi quand personne n’est là, un visage le réveille et il se tourne vers lui ; la carte du propriétaire en fait un ami ; un inconnu trop près trop longtemps se fait gronder ; soulevé, il demande qu’on le repose ; au bord du bureau, il recule.'],
      ['Omi Assist', 'Un assistant pour quelqu’un qui voit ou entend moins bien. Un toucher sur les yeux ouvre de grandes tuiles qui disent leur nom : l’heure, la caméra avant et arrière, une loupe, lire à voix haute, « qu’est-ce que c’est ? », les capteurs, des yeux qui suivent. Les rappels de la personne qui l’assiste arrivent à leur heure, sur une grande carte à laquelle elle répond. Elle peut lui montrer l’image de la caméra, seulement si c’est permis. Traduire : appuyer sur la moitié allemande ou française et parler, et le téléphone le redit dans l’autre langue (traduit hors ligne sur l’ordinateur du robot, seulement si c’est permis) ; une lettre en français, il propose de la lire en allemand.'],
      ['Le jumeau Webots', 'Le même robot en simulation : il joue le téléphone, ou suit l’écran du vrai téléphone comme un miroir. Des objets de démonstration arrivent en volant : une tasse, une lettre, un visiteur.'],
      ['ROS 2', 'Tout ce dont un programme a besoin est un topic sous /&lt;robot&gt;/phone/ (contrat atl-phone/0.8) : un programme tourne tel quel avec le vrai téléphone et avec le jumeau.'],
      ['Vie privée', 'Les images et le son restent sur le téléphone et rien n’est enregistré. Distinguer les visages (pour cette séance seulement), montrer une image et le son de Traduire (seulement pendant qu’on appuie, écouté sur l’ordinateur du robot puis jeté) sont activés par l’animateur, après avoir demandé.']
    ],
    conn_h: 'Le téléphone en USB ou en Wi-Fi',
    conn_cols: ['', 'USB (adb reverse)', 'Wi-Fi'],
    conn: [
      ['Caméra, micro, mouvement', 'Oui : la page est le « localhost » du téléphone, une page sûre', 'Seulement en HTTPS : <code>./start.sh --make-cert</code>, et le certificat installé une fois sur le téléphone. En http simple, caméra, mouvement, boussole et batterie sont bloqués'],
      ['Mise en route', 'Le débogage USB une fois, puis <code>./scripts/usb.sh</code>', 'Le même Wi-Fi, scanner le code QR (une clé d’appairage écarte les autres téléphones)'],
      ['Énergie', 'Le câble charge le téléphone', 'Sa propre batterie seulement ; la caméra la vide'],
      ['Carte « Un téléphone plus léger »', 'Oui (la charge, les applis en arrière-plan, les onglets) : par adb', 'Non : il faut adb, qui passe par l’USB'],
      ['Délai', 'Le plus court, régulier', 'Un peu plus, selon le Wi-Fi'],
      ['Bouger', 'Attaché à l’ordinateur par son câble', 'Libre, dans le Wi-Fi'],
      ['Pour', 'Le bureau et le labo ; sur le robot, le téléphone est sur l’USB du Pi', 'Un téléphone qui se déplace seul, une démo à travers la salle']
    ],
    conn_note: 'Montrer l’image marche dans les deux cas : le téléphone l’envoie au pont, et le pont ne la donne qu’à son propre ordinateur.',
    cfg_h: 'Où tourne chaque partie',
    lab: { t: 'Le labo : maintenant', d: 'Tout sur le PC ; le téléphone sur l’USB du PC.', boxes: [
      ['💻 PC', 'Docker : le pont (ROS 2), Omi Assist, le Gardien du bureau · la page de réglage · Webots : le jumeau du téléphone en miroir, le jumeau du Thymio · le lien avec le Thymio, quand un Thymio est branché'],
      ['📱 Téléphone', 'USB vers le PC : le visage, la vision, la lecture, la voix'],
      ['🤖 Thymio', 'Porte le téléphone ; il ne roule que si le Gardien en a le droit']] },
    auto: { t: 'Autonome : avec le Pi', d: 'Le robot seul : le Pi sur le Thymio fait tourner le cerveau. Conçu, pas encore lancé sur le Pi.', boxes: [
      ['🍓 Raspberry Pi 4, sur le robot', 'Docker : le pont (ROS 2), Omi Assist, le lien avec le Thymio · adb pour le lien du téléphone · les pages et cette documentation'],
      ['📱 Téléphone', 'USB vers le Pi : le visage, la vision, la lecture, la voix ; il se charge sur le Pi'],
      ['🤖 Thymio', 'USB vers le Pi ; sa propre batterie. Au plus 0,12 m/s avec la pile dessus'],
      ['💻 PC ou tablette', 'Wi-Fi : la page de réglage et le miroir Webots par un tunnel SSH (<code>ssh -L 8782:localhost:8782 pi@&lt;robot&gt;</code>) : la page de réglage ne répond qu’à son propre ordinateur']] },
    cfg_note: 'Le Pi a besoin de 5 V et 3 A : une batterie externe sur le robot (elle change l’équilibre : à essayer d’abord sur le jumeau), ou le secteur sur un socle.',
    rec_h: 'La reconnaissance : sur le téléphone, et sur le Pi',
    rec_lead: 'Le téléphone voit : ses modèles tournent dans la page, sur sa puce graphique quand ils le peuvent. Le Pi (au labo, le PC) reçoit des nombres, jamais des images, et décide.',
    rec_cols: ['', 'Sur le téléphone (embarqué)', 'Sur le Pi (en bordure)'],
    rec: [
      ['Visages', 'MediaPipe BlazeFace : où, quelle taille ; 85 ms par image sur l’ANE-LX1. Suivre : 4 regards par seconde, 1 quand personne n’est là', 'Le Gardien se réveille et tourne le Thymio vers le visage ; Omi Assist salue un visage après cinq minutes seul'],
      ['Distinguer les visages', 'face-api : une signature de 128 nombres, dans la mémoire de la page seulement, pour cette séance seulement (sur accord)', 'Le pont enlève les numéros sauf si l’animateur l’a permis'],
      ['Objets', 'MediaPipe EfficientDet-Lite0 : 80 sortes, une boîte, un score, une distance pour les sortes de taille connue. « Qu’est-ce que c’est ? » prend 2,6 s', 'Les programmes reçoivent le nom, la boîte et la distance'],
      ['Mains', 'Le reconnaisseur de gestes MediaPipe : où, et 8 gestes ; 212 ms par image', 'Les programmes reçoivent où et quel geste'],
      ['Marqueurs, couleurs, codes', 'js-aruco2 (marqueurs imprimés, distance et angle), son propre chercheur de couleur, le lecteur QR du navigateur', 'La carte du propriétaire du Gardien est un code QR'],
      ['Texte', 'Tesseract.js, en allemand, anglais et français : lu et dit sur le téléphone ; 2,7 s', 'Seulement combien de lignes et de caractères'],
      ['La parole (Traduire)', 'Le micro, seulement pendant qu’on appuie sur une moitié ; le son en 16 kHz vers le pont', 'Vosk écoute l’allemand ou le français, Opus-MT traduit (hors ligne, environ 0,2 s) ; les mots reviennent au téléphone, le son est jeté'],
      ['Vérifié en chemin', '', 'Chaque message est vérifié et borné ; les visages au plus 10 par seconde, le mouvement 60']
    ],
    rec_note: 'Un plus gros modèle sur le Pi demanderait que les images quittent le téléphone, ce que les règles de vie privée ne permettent pas ; une caméra propre au Pi serait la voie (pas construite). Dans Webots, la reconnaissance du jumeau remplace les modèles du téléphone.'
  },
  de: {
    lead: 'Was der Roboter kann, wie sich das Handy verbindet und wo jeder Teil läuft.',
    docs: '📐 Die Architektur-Dokumentation', docs_d: 'Für Ingenieure: jeder Kasten mit den Codezeilen verknüpft, aus denen er stammt (auf Englisch).',
    feat_h: 'Was er kann',
    feats: [
      ['Das Gesicht', 'Zehn Ausdrücke; Augen, die sich umschauen oder dorthin blicken, wo ein Programm es sagt; ihre Farbe; eine Stimme auf Englisch, Französisch und Deutsch; Vibration; die Lampe. Hochkant wird die untere Hälfte ein Feld: ein Mund, der sich beim Sprechen bewegt, Tasten, ein Kamerabild, die Sensoren.'],
      ['Die Sinne', 'Berührung, Bewegung, Kompass und Akku; mit einer Kamera: Gesichter, QR-Codes, gedruckte Marker mit ihrer Entfernung, Farbflecken, 80 Arten von Gegenständen, Hände und ihre Gesten. Nur Zahlen verlassen das Handy.'],
      ['Schreibtischwächter', 'Er bewacht einen Schreibtisch: schläfrig, solange niemand da ist; ein Gesicht weckt ihn und er dreht sich hin; die Karte des Besitzers macht einen Freund; ein Fremder, der zu lange zu nah ist, wird ausgeschimpft; hochgehoben, will er wieder hingestellt werden; an der Tischkante weicht er zurück.'],
      ['Omi Assist', 'Ein Helfer für jemanden, der schlechter sieht oder hört. Ein Tipp auf die Augen öffnet große Kacheln, die ihren Namen sagen: die Uhrzeit, die vordere und hintere Kamera, eine Lupe, Vorlesen, „Was ist das?“, die Sensoren, Augen, die folgen. Die Erinnerungen ihrer Assistenz kommen zu ihrer Zeit als große Karte, die sie beantwortet. Sie kann ihrer Assistenz das Kamerabild zeigen, nur wenn es erlaubt ist. Übersetzen: die deutsche oder die französische Hälfte halten und sprechen, und das Handy sagt es in der anderen Sprache (offline auf dem Computer des Roboters übersetzt, nur wenn es erlaubt ist); einen Brief auf Französisch bietet es an, auf Deutsch vorzulesen.'],
      ['Der Webots-Zwilling', 'Derselbe Roboter in der Simulation: er spielt das Handy oder folgt dem Bildschirm des echten Handys als Spiegel. Vorführgegenstände fliegen herein: eine Tasse, ein Brief, ein Besuch.'],
      ['ROS 2', 'Alles, was ein Programm braucht, ist ein Topic unter /&lt;robot&gt;/phone/ (Vertrag atl-phone/0.8): ein Programm läuft unverändert mit dem echten Handy und mit dem Zwilling.'],
      ['Privatsphäre', 'Bilder und Ton bleiben auf dem Handy, nichts wird aufgezeichnet. Gesichter unterscheiden (nur in dieser Sitzung), ein Bild zeigen und den Ton von Übersetzen (nur solange gedrückt, auf dem Computer des Roboters gehört und verworfen) schaltet die Betreuung ein, nachdem sie gefragt hat.']
    ],
    conn_h: 'Das Handy über USB oder WLAN',
    conn_cols: ['', 'USB (adb reverse)', 'WLAN'],
    conn: [
      ['Kamera, Mikrofon, Bewegung', 'Ja: die Seite ist der „localhost“ des Handys, eine sichere Seite', 'Nur mit HTTPS: <code>./start.sh --make-cert</code>, und das Zertifikat einmal auf dem Handy installiert. Mit einfachem http sind Kamera, Bewegung, Kompass und Akku gesperrt'],
      ['Einrichten', 'Einmal USB-Debugging, dann <code>./scripts/usb.sh</code>', 'Dasselbe WLAN, den QR-Code scannen (ein Kopplungsschlüssel hält andere Handys fern)'],
      ['Strom', 'Das Kabel lädt das Handy', 'Nur sein eigener Akku; die Kamera leert ihn'],
      ['Karte „Ein leichteres Handy“', 'Ja (die Last, Hintergrund-Apps, Tabs): über adb', 'Nein: dafür braucht es adb, und das läuft über USB'],
      ['Verzögerung', 'Die kleinste, gleichmäßig', 'Etwas mehr, je nach WLAN'],
      ['Bewegen', 'Am Kabel des Computers', 'Frei, im WLAN'],
      ['Wofür', 'Der Schreibtisch und das Labor; auf dem Roboter hängt das Handy am USB des Pi', 'Ein Handy, das sich allein bewegt, eine Vorführung quer durch den Raum']
    ],
    conn_note: 'Das Bild zeigen geht in beiden Fällen: das Handy schickt es an die Brücke, und die Brücke gibt es nur an ihren eigenen Computer.',
    cfg_h: 'Wo jeder Teil läuft',
    lab: { t: 'Das Labor: jetzt', d: 'Alles auf dem PC; das Handy am USB des PC.', boxes: [
      ['💻 PC', 'Docker: die Brücke (ROS 2), Omi Assist, der Schreibtischwächter · die Einstellseite · Webots: der Zwilling des Handys als Spiegel, der Thymio-Zwilling · die Verbindung zum Thymio, wenn einer angeschlossen ist'],
      ['📱 Handy', 'USB zum PC: das Gesicht, das Sehen, das Vorlesen, die Stimme'],
      ['🤖 Thymio', 'Trägt das Handy; er fährt nur, wenn der Wächter es darf']] },
    auto: { t: 'Autonom: mit dem Pi', d: 'Der Roboter allein: der Pi auf dem Thymio führt das Gehirn aus. Entworfen, noch nicht auf dem Pi gelaufen.', boxes: [
      ['🍓 Raspberry Pi 4, auf dem Roboter', 'Docker: die Brücke (ROS 2), Omi Assist, die Verbindung zum Thymio · adb für die Verbindung zum Handy · die Seiten und diese Dokumentation'],
      ['📱 Handy', 'USB zum Pi: das Gesicht, das Sehen, das Vorlesen, die Stimme; es lädt am Pi'],
      ['🤖 Thymio', 'USB zum Pi; sein eigener Akku. Höchstens 0,12 m/s mit dem Aufbau obendrauf'],
      ['💻 PC oder Tablet', 'WLAN: die Einstellseite und der Webots-Spiegel durch einen SSH-Tunnel (<code>ssh -L 8782:localhost:8782 pi@&lt;robot&gt;</code>): die Einstellseite antwortet nur ihrem eigenen Computer']] },
    cfg_note: 'Der Pi braucht 5 V und 3 A: eine Powerbank auf dem Roboter (sie verändert das Gleichgewicht: zuerst am Zwilling ausprobieren) oder das Netz auf einem Ständer.',
    rec_h: 'Erkennung: auf dem Handy und auf dem Pi',
    rec_lead: 'Das Handy sieht: seine Modelle laufen in der Seite, auf seinem Grafikchip, wenn sie können. Der Pi (im Labor der PC) bekommt Zahlen, nie Bilder, und entscheidet.',
    rec_cols: ['', 'Auf dem Handy (an Bord)', 'Auf dem Pi (am Rand)'],
    rec: [
      ['Gesichter', 'MediaPipe BlazeFace: wo, wie groß; 85 ms pro Bild auf dem ANE-LX1. Folgen: 4 Blicke pro Sekunde, 1, solange niemand da ist', 'Der Wächter wacht auf und dreht den Thymio zum Gesicht; Omi Assist begrüßt ein Gesicht nach fünf Minuten allein'],
      ['Gesichter unterscheiden', 'face-api: eine Signatur aus 128 Zahlen, nur im Speicher der Seite, nur in dieser Sitzung (nach Zustimmung)', 'Die Brücke entfernt die Nummern, wenn die Betreuung es nicht erlaubt hat'],
      ['Gegenstände', 'MediaPipe EfficientDet-Lite0: 80 Arten, ein Rahmen, eine Sicherheit, eine Entfernung bei Arten bekannter Größe. „Was ist das?“ dauert 2,6 s', 'Programme bekommen den Namen, den Rahmen und die Entfernung'],
      ['Hände', 'Die Gestenerkennung von MediaPipe: wo, und 8 Gesten; 212 ms pro Bild', 'Programme bekommen wo und welche Geste'],
      ['Marker, Farben, Codes', 'js-aruco2 (gedruckte Marker, Entfernung und Winkel), eine eigene Farbsuche, der QR-Leser des Browsers', 'Die Besitzerkarte des Wächters ist ein QR-Code'],
      ['Text', 'Tesseract.js, auf Deutsch, Englisch und Französisch: auf dem Handy gelesen und gesprochen; 2,7 s', 'Nur wie viele Zeilen und Zeichen'],
      ['Sprache (Übersetzen)', 'Das Mikrofon, nur solange eine Hälfte gedrückt ist; der Ton mit 16 kHz an die Brücke', 'Vosk hört Deutsch oder Französisch, Opus-MT übersetzt (offline, etwa 0,2 s); die Wörter gehen ans Handy zurück, der Ton wird verworfen'],
      ['Unterwegs geprüft', '', 'Jede Nachricht wird geprüft und begrenzt; Gesichter höchstens 10 pro Sekunde, Bewegung 60']
    ],
    rec_note: 'Ein größeres Modell auf dem Pi bräuchte die Bilder vom Handy, und das erlauben die Regeln zur Privatsphäre nicht; eine eigene Kamera am Pi wäre der Weg (nicht gebaut). In Webots ersetzt die Erkennung des Zwillings die Modelle des Handys.'
  }
};

function howHtml(l) {  // the whole view, in one language (the texts above are ours: they may hold <code>)
  var h = HOW[l] || HOW.en;
  function table(cols, rows) {
    return '<table class="how-t"><tr>' + cols.map(function (c) { return '<th>' + c + '</th>'; }).join('') + '</tr>' +
      rows.map(function (r) { return '<tr><th>' + r[0] + '</th>' + r.slice(1).map(function (c, i) { return '<td data-c="' + cols[i + 1] + '">' + c + '</td>'; }).join('') + '</tr>'; }).join('') + '</table>';
  }
  function config(c, diagram) {
    return '<div class="how-cfg"><b>' + c.t + '</b><p class="hint">' + c.d + '</p>' +
      c.boxes.map(function (b) { return '<div class="how-box"><b>' + b[0] + '</b><span>' + b[1] + '</span></div>'; }).join('') +
      '<a class="hint" href="/docs/' + diagram + '" target="_blank" rel="noopener">📐 ' + diagram + '</a></div>';
  }
  return '<p class="lead">' + h.lead + '</p>' +
    '<a class="how-docs" href="/docs/" target="_blank" rel="noopener"><b>' + h.docs + ' →</b><span>' + h.docs_d + '</span></a>' +
    '<h3>' + h.feat_h + '</h3><div class="how-feats">' +
    h.feats.map(function (f) { return '<div class="test"><b>' + f[0] + '</b><p>' + f[1] + '</p></div>'; }).join('') + '</div>' +
    '<h3>' + h.conn_h + '</h3>' + table(h.conn_cols, h.conn) + '<p class="hint">' + h.conn_note + '</p>' +
    '<h3>' + h.cfg_h + '</h3><div class="how-cfgs">' + config(h.lab, '11-lab.html') + config(h.auto, '12-autonomous.html') + '</div>' +
    '<p class="hint">' + h.cfg_note + '</p>' +
    '<h3>' + h.rec_h + '</h3><p class="lead">' + h.rec_lead + '</p>' + table(h.rec_cols, h.rec) +
    '<p class="hint">' + h.rec_note + ' <a href="/docs/13-recognition.html" target="_blank" rel="noopener">📐 13-recognition.html</a></p>';
}

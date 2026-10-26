// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Atelier-5
// Phone setup, on the PC: it watches the bridge (/api/state) and asks it for tests (/api/act). At the top, what to do:
// Connect and Test (the six steps), Desk Guard (the Desk Guardian), Omi Assist (the helper, its reminders, showing).
'use strict';

var T = {
  en: {
    title: 'Phone setup', s1: 'The bridge', s2: 'Connect the phone', s3: 'Phone check', s4: 'Test it', s5: 'Scenarios', s6: 'Summary',
    s1_lead: 'The bridge connects the phone to ROS 2. If you can read this, it runs.',
    s2_lead: 'By USB at the desk, or by Wi-Fi on the table.',
    s3_lead: 'What can this phone do? The check tests each part once. You can skip it.',
    s4_lead: 'Each test goes through ROS 2, as a robot program would. Outputs: say what you saw. Senses: they tick by themselves.',
    s5_lead: 'Examples that use it all at once. They run in ROS 2 beside the bridge and talk to the phone only through its topics.',
    usb1: 'On the phone: Settings › About phone › tap “Build number” seven times.',
    usb2: 'Settings › Developer options › turn on “USB debugging”.',
    usb3: 'Plug the phone into this PC and allow it on the phone.',
    usb4: 'On this PC, in the atl-phone folder:', usb5: 'The face opens on the phone: tap ▶.',
    usb_why: 'USB makes the page the phone’s “localhost”: a secure page, so camera, microphone and motion work without certificates. The cable charges the phone too.',
    wifi_warn: 'Without HTTPS the face works, but camera, microphone and motion are blocked on Wi-Fi. Use USB, or start the bridge with its own certificate: ./start.sh --make-cert',
    ca_h: 'Once per phone: let it trust this PC', ca_then: 'Then, every time: the face',
    ca1: 'Put the phone on the same Wi-Fi and scan this code. Chrome warns once that the connection is not private: Advanced › Proceed. The file atl-phone-ca.crt downloads.',
    ca2: 'Settings › Security › Encryption & credentials › Install a certificate › CA certificate, and pick atl-phone-ca.crt. Menus differ per phone: search Settings for “certificate”. On older phones, opening the file installs it.',
    ca3: 'Close Chrome completely and open it again.',
    ca_note: 'The phone then trusts pages signed by this PC. When it leaves the class, remove it: Settings › … › Trusted credentials › User.',
    wifi1: 'Put the phone on the same Wi-Fi as this PC.', wifi2: 'Scan the code with the phone’s camera, or type the address:',
    open_check: 'Open the check on the phone', chk2: 'On the phone: “Test everything”, allow camera, microphone and motion.',
    chk3: 'Then “Send report to the PC”, and “Robot face →” to come back.',
    outputs: 'The robot → the phone', inputs: 'The phone → the robot',
    copy: 'Copy', copied: 'Copied.', copy_summary: 'Copy summary', save_summary: 'Save on the PC', saved_summary: 'Saved on the PC:', no_registry: 'not kept: the bridge has no registry (start it with ./start.sh)', back: '← Back', next: 'Next →',
    bridge_ok: 'The bridge runs.', bridge_no: 'No bridge: start it with ./start.sh', robot: 'Robot', contract: 'Contract',
    usb_url: 'USB address', wifi_url: 'Wi-Fi address',
    waiting: 'Waiting for the phone…', connected: 'Phone connected:', no_phone: 'No phone: connect one first (step 2).',
    no_report: 'No report yet.', report_from: 'Report from', core_ok: 'everything version 1 needs works', core_missing: 'missing:',
    face: 'Face', face_q: 'Did the face change?', gaze: 'Gaze', gaze_hint: 'Drag in the box: the eyes follow.', gaze_q: 'Did the eyes follow?',
    color: 'Eye colour', color_q: 'Did the colour change?', say: 'Voice', say_text: 'Hello, I am your robot.', say_btn: 'Say', say_q: 'Did you hear it?',
    vibrate: 'Vibration', vibrate_btn: 'Buzz', vibrate_q: 'Did you feel it?', torch: 'Torch', on: 'On', off: 'Off',
    torch_q: 'Did the light come on? (the face shows ● cam)', yes: 'yes', no: 'no',
    touch: 'Touch', touch_hint: 'On the phone: tap left, centre and right; press long; swipe.',
    motion: 'Motion', motion_hint: 'Tilt or turn the phone.', compass: 'Compass', compass_hint: 'Turn the phone, lying flat.',
    battery: 'Battery', charging: 'charging', none_yet: 'nothing yet', not_here: 'this phone has none',
    summary_lead: 'What works on this phone. Copy it into your notes or the robot’s build.', untested: 'not tested', skipped: 'skipped',
    down: 'down:', test_no_phone: 'No phone connected: the tests cannot reach it. Open the face on the phone (step 2).',
    camera: 'Camera', show: 'Show on the phone', hide: 'Hide', camera_q: 'Did the phone show what its camera sees?',
    camera_hint: 'The phone shows its back camera’s picture on its own screen, for a minute. Nothing leaves the phone.',
    code: 'Reading codes', code_hint: 'With the picture on: hold the phone’s back camera to this code.', code_read: 'read:',
    no_reader: 'this phone’s browser cannot read codes; the card scanner (step 3) brings its own reader',
    blocked: 'blocked: the phone’s page is not secure. Connect by USB, or start with --cert',
    insecure: 'This phone uses a page that is not secure (http over Wi-Fi): its camera, motion, compass and battery are blocked. Connect it by USB, or start the bridge with a certificate (./start.sh --cert DIR).',
    no_torch: 'the phone says it has no torch', cam_error: 'the camera did not open:', size: 'picture',
    look: 'Look (front camera)', look_hint: 'The front camera finds faces, on the phone; only where they are comes here. Stand in front of the phone.',
    familiar_allow: 'Allow telling faces apart (this session only)', forget: 'Forget the faces', faces_n: 'faces:',
    familiar_note: 'The phone then keeps a signature of each face in its memory, to give the same face the same number. Nothing is stored or sent, and it is forgotten on reload. Ask the people at the table, and the parents, first.',
    look_error: 'look did not start:', look_wait: 'the back camera is in use: look waits',
    guardian: 'Desk Guardian', guardian_hint: 'Like Cozmo: it watches the desk with the front camera, turns to whoever comes, greets its owner (the card in step 4) and is scared when picked up. With a Thymio (atl-bot-thymio, or its twin in Webots) it turns its body and keeps away from the edge.',
    start: 'Start', stop: 'Stop', drive: 'It may drive the Thymio', g_off: 'stopped', g_none: 'the guardian does not answer: restart the bridge (./start.sh)',
    st_guarding: 'watching', st_alert: 'alert', st_friend: 'friend', st_intruder: 'intruder', st_scared: 'scared', st_edge: 'at the edge', st_petted: 'petted',
    thymio_yes: 'the Thymio answers', thymio_no: 'no Thymio: the phone alone', friends: 'friends:',
    g_tip: 'For friends who stay friends, allow telling faces apart first (step 4, Look).',
    panel: 'Portrait panel', panel_hint: 'Held upright, the face has its eyes on top and a panel below: a mouth that turns into a sound wave when it speaks, buttons a program defines (each press goes to ROS), a camera’s picture (on the phone only), or the sensors. A tap on the eyes opens the menu; a swipe steps through it.',
    layout: 'Layout:', landscape: 'Landscape', portrait: 'Portrait', auto: 'Auto (as held)', layout_note: 'The face reloads: tap ▶ on the phone again.',
    panel_mode: 'Panel:', mode_pad: 'Buttons', mode_camera: 'Front camera', mode_camera_back: 'Back camera', mode_sensors: 'Sensors', mode_mouth: 'Mouth', mode_off: 'Eyes only', thymio_pad: 'Thymio buttons', abcd_pad: 'A B C D', pad: 'Panel buttons', pad_seen: 'pressed:',
    topics: 'Programs:',
    vision: 'Vision (camera)', vision_hint: 'The phone’s camera finds things, on the phone; only numbers come here: markers (their number, distance and angle), a colour, objects (80 kinds), hands and gestures.',
    cam_front: 'Front', cam_back: 'Back', f_faces: 'faces', f_markers: 'markers', f_blobs: 'colour', f_objects: 'objects', f_hands: 'hands',
    marker_cm: 'Marker size, cm:', print_markers: 'Print the markers', vision_ms: 'time per picture:',
    owner: 'The Desk Guardian’s owner card: hold it up to the front camera, with your face in view (start the guardian in step 5).', code_seen: 'read:'
  },
  fr: {
    title: 'Installer le téléphone', s1: 'Le pont', s2: 'Connecter le téléphone', s3: 'Test du téléphone', s4: 'L’essayer', s5: 'Scénarios', s6: 'Bilan',
    s1_lead: 'Le pont relie le téléphone à ROS 2. Si vous lisez ceci, il tourne.',
    s2_lead: 'Par USB au bureau, ou par Wi-Fi sur la table.',
    s3_lead: 'Que sait faire ce téléphone ? Le test essaie chaque partie une fois. Vous pouvez le passer.',
    s4_lead: 'Chaque essai passe par ROS 2, comme un programme du robot. Sorties : dites ce que vous avez vu. Sens : ils se cochent tout seuls.',
    s5_lead: 'Des exemples qui utilisent tout à la fois. Ils tournent dans ROS 2 à côté du pont et ne parlent au téléphone que par ses topics.',
    usb1: 'Sur le téléphone : Paramètres › À propos du téléphone › touchez sept fois « Numéro de build ».',
    usb2: 'Paramètres › Options pour les développeurs › activez « Débogage USB ».',
    usb3: 'Branchez le téléphone sur ce PC et autorisez-le sur le téléphone.',
    usb4: 'Sur ce PC, dans le dossier atl-phone :', usb5: 'Le visage s’ouvre sur le téléphone : touchez ▶.',
    usb_why: 'Par USB, la page est le « localhost » du téléphone : une page sécurisée, donc caméra, micro et mouvement marchent sans certificat. Le câble charge aussi le téléphone.',
    wifi_warn: 'Sans HTTPS, le visage marche, mais caméra, micro et mouvement sont bloqués en Wi-Fi. Passez par USB, ou lancez le pont avec son propre certificat : ./start.sh --make-cert',
    ca_h: 'Une fois par téléphone : qu’il fasse confiance à ce PC', ca_then: 'Ensuite, à chaque fois : le visage',
    ca1: 'Mettez le téléphone sur le même Wi-Fi et scannez ce code. Chrome prévient une fois que la connexion n’est pas privée : Paramètres avancés › Continuer. Le fichier atl-phone-ca.crt se télécharge.',
    ca2: 'Paramètres › Sécurité › Chiffrement et identifiants › Installer un certificat › Certificat CA, et choisissez atl-phone-ca.crt. Les menus varient selon le téléphone : cherchez « certificat » dans les Paramètres. Sur les vieux téléphones, ouvrir le fichier l’installe.',
    ca3: 'Fermez complètement Chrome et rouvrez-le.',
    ca_note: 'Le téléphone fait alors confiance aux pages signées par ce PC. Quand il quitte la classe, retirez-le : Paramètres › … › Identifiants de confiance › Utilisateur.',
    wifi1: 'Mettez le téléphone sur le même Wi-Fi que ce PC.', wifi2: 'Scannez le code avec la caméra du téléphone, ou tapez l’adresse :',
    open_check: 'Ouvrir le test sur le téléphone', chk2: 'Sur le téléphone : « Tout tester », autorisez caméra, micro et mouvement.',
    chk3: 'Puis « Envoyer le rapport au PC », et « Visage du robot → » pour revenir.',
    outputs: 'Le robot → le téléphone', inputs: 'Le téléphone → le robot',
    copy: 'Copier', copied: 'Copié.', copy_summary: 'Copier le bilan', save_summary: 'Enregistrer sur le PC', saved_summary: 'Enregistré sur le PC :', no_registry: 'non gardé : le pont n’a pas de registre (lancez-le avec ./start.sh)', back: '← Retour', next: 'Suivant →',
    bridge_ok: 'Le pont tourne.', bridge_no: 'Pas de pont : lancez-le avec ./start.sh', robot: 'Robot', contract: 'Contrat',
    usb_url: 'Adresse USB', wifi_url: 'Adresse Wi-Fi',
    waiting: 'En attente du téléphone…', connected: 'Téléphone connecté :', no_phone: 'Pas de téléphone : connectez-en un d’abord (étape 2).',
    no_report: 'Pas encore de rapport.', report_from: 'Rapport de', core_ok: 'tout ce qu’il faut pour la version 1 marche', core_missing: 'manque :',
    face: 'Visage', face_q: 'Le visage a-t-il changé ?', gaze: 'Regard', gaze_hint: 'Glissez dans le cadre : les yeux suivent.', gaze_q: 'Les yeux ont-ils suivi ?',
    color: 'Couleur des yeux', color_q: 'La couleur a-t-elle changé ?', say: 'Voix', say_text: 'Bonjour, je suis ton robot.', say_btn: 'Dire', say_q: 'L’avez-vous entendu ?',
    vibrate: 'Vibration', vibrate_btn: 'Vibrer', vibrate_q: 'L’avez-vous senti ?', torch: 'Lampe', on: 'Allumer', off: 'Éteindre',
    torch_q: 'La lampe s’est-elle allumée ? (le visage montre ● cam)', yes: 'oui', no: 'non',
    touch: 'Toucher', touch_hint: 'Sur le téléphone : touchez à gauche, au centre et à droite ; appuyez longtemps ; glissez.',
    motion: 'Mouvement', motion_hint: 'Inclinez ou tournez le téléphone.', compass: 'Boussole', compass_hint: 'Tournez le téléphone, posé à plat.',
    battery: 'Batterie', charging: 'en charge', none_yet: 'rien encore', not_here: 'ce téléphone n’en a pas',
    summary_lead: 'Ce qui marche sur ce téléphone. Copiez-le dans vos notes ou dans le montage du robot.', untested: 'pas testé', skipped: 'passé',
    down: 'en bas :', test_no_phone: 'Aucun téléphone connecté : les essais ne l’atteignent pas. Ouvrez le visage sur le téléphone (étape 2).',
    camera: 'Caméra', show: 'Montrer sur le téléphone', hide: 'Cacher', camera_q: 'Le téléphone a-t-il montré ce que voit sa caméra ?',
    camera_hint: 'Le téléphone montre l’image de sa caméra arrière sur son propre écran, pendant une minute. Rien ne quitte le téléphone.',
    code: 'Lire des codes', code_hint: 'Image allumée : tenez la caméra arrière du téléphone devant ce code.', code_read: 'lu :',
    no_reader: 'le navigateur de ce téléphone ne lit pas les codes ; le lecteur de cartes (étape 3) apporte le sien',
    blocked: 'bloqué : la page du téléphone n’est pas sécurisée. Connectez par USB, ou lancez avec --cert',
    insecure: 'Ce téléphone utilise une page non sécurisée (http en Wi-Fi) : sa caméra, son mouvement, sa boussole et sa batterie sont bloqués. Connectez-le par USB, ou lancez le pont avec un certificat (./start.sh --cert DOSSIER).',
    no_torch: 'le téléphone dit ne pas avoir de lampe', cam_error: 'la caméra ne s’est pas ouverte :', size: 'image',
    look: 'Regard (caméra avant)', look_hint: 'La caméra avant trouve les visages, sur le téléphone ; seul l’endroit où ils sont arrive ici. Placez-vous devant le téléphone.',
    familiar_allow: 'Permettre de distinguer les visages (cette séance seulement)', forget: 'Oublier les visages', faces_n: 'visages :',
    familiar_note: 'Le téléphone garde alors une signature de chaque visage dans sa mémoire, pour donner le même numéro au même visage. Rien n’est enregistré ni envoyé, et tout est oublié au rechargement. Demandez d’abord aux personnes à la table, et aux parents.',
    look_error: 'le regard n’a pas démarré :', look_wait: 'la caméra arrière est utilisée : le regard attend',
    guardian: 'Gardien du bureau', guardian_hint: 'Comme Cozmo : il surveille le bureau avec la caméra avant, se tourne vers qui arrive, salue son propriétaire (la carte de l’étape 4) et a peur quand on le soulève. Avec un Thymio (atl-bot-thymio, ou son jumeau dans Webots), il tourne son corps et s’éloigne du bord.',
    start: 'Démarrer', stop: 'Arrêter', drive: 'Il peut conduire le Thymio', g_off: 'arrêté', g_none: 'le gardien ne répond pas : relancez le pont (./start.sh)',
    st_guarding: 'surveille', st_alert: 'en alerte', st_friend: 'ami', st_intruder: 'intrus', st_scared: 'effrayé', st_edge: 'au bord', st_petted: 'caressé',
    thymio_yes: 'le Thymio répond', thymio_no: 'pas de Thymio : le téléphone seul', friends: 'amis :',
    g_tip: 'Pour que les amis restent des amis, permettez d’abord de distinguer les visages (étape 4, Regard).',
    panel: 'Panneau en portrait', panel_hint: 'Tenu debout, le visage a ses yeux en haut et un panneau en bas : une bouche qui devient une onde sonore quand il parle, des boutons définis par un programme (chaque appui va à ROS), l’image d’une caméra (sur le téléphone seulement), ou les capteurs. Toucher les yeux ouvre le menu ; glisser le parcourt.',
    layout: 'Disposition :', landscape: 'Paysage', portrait: 'Portrait', auto: 'Auto (selon le téléphone)', layout_note: 'Le visage se recharge : touchez ▶ de nouveau sur le téléphone.',
    panel_mode: 'Panneau :', mode_pad: 'Boutons', mode_camera: 'Caméra avant', mode_camera_back: 'Caméra arrière', mode_sensors: 'Capteurs', mode_mouth: 'Bouche', mode_off: 'Yeux seuls', thymio_pad: 'Boutons du Thymio', abcd_pad: 'A B C D', pad: 'Boutons du panneau', pad_seen: 'appuyé :',
    topics: 'Programmes :',
    vision: 'Vision (caméra)', vision_hint: 'La caméra du téléphone trouve des choses, sur le téléphone ; seuls des nombres arrivent ici : des marqueurs (leur numéro, distance et angle), une couleur, des objets (80 sortes), des mains et des gestes.',
    cam_front: 'Avant', cam_back: 'Arrière', f_faces: 'visages', f_markers: 'marqueurs', f_blobs: 'couleur', f_objects: 'objets', f_hands: 'mains',
    marker_cm: 'Taille des marqueurs, cm :', print_markers: 'Imprimer les marqueurs', vision_ms: 'temps par image :',
    owner: 'La carte du propriétaire pour le Gardien du bureau : montrez-la à la caméra avant, avec votre visage (démarrez le gardien à l’étape 5).', code_seen: 'lu :'
  },
  de: {
    title: 'Handy einrichten', s1: 'Die Brücke', s2: 'Handy verbinden', s3: 'Handy-Check', s4: 'Ausprobieren', s5: 'Szenarien', s6: 'Zusammenfassung',
    s1_lead: 'Die Brücke verbindet das Handy mit ROS 2. Wenn du das liest, läuft sie.',
    s2_lead: 'Per USB am Tisch, oder per WLAN auf dem Spielfeld.',
    s3_lead: 'Was kann dieses Handy? Der Check testet jedes Teil einmal. Du kannst ihn überspringen.',
    s4_lead: 'Jeder Test geht über ROS 2, wie ein Roboterprogramm. Ausgaben: sag, was du gesehen hast. Sinne: sie haken sich selbst ab.',
    s5_lead: 'Beispiele, die alles auf einmal nutzen. Sie laufen in ROS 2 neben der Brücke und sprechen mit dem Handy nur über seine Topics.',
    usb1: 'Auf dem Handy: Einstellungen › Über das Telefon › siebenmal auf „Build-Nummer“ tippen.',
    usb2: 'Einstellungen › Entwickleroptionen › „USB-Debugging“ einschalten.',
    usb3: 'Handy an diesen PC anschließen und auf dem Handy erlauben.',
    usb4: 'Auf diesem PC, im Ordner atl-phone:', usb5: 'Das Gesicht öffnet sich auf dem Handy: auf ▶ tippen.',
    usb_why: 'Per USB ist die Seite der „localhost“ des Handys: eine sichere Seite, also gehen Kamera, Mikrofon und Bewegung ohne Zertifikat. Das Kabel lädt das Handy auch.',
    wifi_warn: 'Ohne HTTPS geht das Gesicht, aber Kamera, Mikrofon und Bewegung sind im WLAN gesperrt. USB nutzen, oder die Brücke mit eigenem Zertifikat starten: ./start.sh --make-cert',
    ca_h: 'Einmal pro Handy: diesem PC vertrauen', ca_then: 'Danach, jedes Mal: das Gesicht',
    ca1: 'Das Handy ins selbe WLAN bringen und diesen Code scannen. Chrome warnt einmal, die Verbindung sei nicht privat: Erweitert › Weiter. Die Datei atl-phone-ca.crt wird geladen.',
    ca2: 'Einstellungen › Sicherheit › Verschlüsselung & Anmeldedaten › Zertifikat installieren › CA-Zertifikat, dann atl-phone-ca.crt wählen. Die Menüs sind je Handy anders: in den Einstellungen nach „Zertifikat“ suchen. Auf alten Handys installiert es sich beim Öffnen der Datei.',
    ca3: 'Chrome ganz schließen und neu öffnen.',
    ca_note: 'Das Handy vertraut dann Seiten, die dieser PC signiert. Verlässt es die Klasse, wieder entfernen: Einstellungen › … › Vertrauenswürdige Anmeldedaten › Nutzer.',
    wifi1: 'Das Handy ins selbe WLAN wie diesen PC bringen.', wifi2: 'Den Code mit der Handykamera scannen, oder die Adresse eintippen:',
    open_check: 'Check auf dem Handy öffnen', chk2: 'Auf dem Handy: „Alles testen“, Kamera, Mikrofon und Bewegung erlauben.',
    chk3: 'Dann „Bericht an den PC senden“, und „Robotergesicht →“ für zurück.',
    outputs: 'Der Roboter → das Handy', inputs: 'Das Handy → der Roboter',
    copy: 'Kopieren', copied: 'Kopiert.', copy_summary: 'Zusammenfassung kopieren', save_summary: 'Auf dem PC speichern', saved_summary: 'Auf dem PC gespeichert:', no_registry: 'nicht gespeichert: die Brücke hat kein Verzeichnis (mit ./start.sh starten)', back: '← Zurück', next: 'Weiter →',
    bridge_ok: 'Die Brücke läuft.', bridge_no: 'Keine Brücke: mit ./start.sh starten', robot: 'Roboter', contract: 'Vertrag',
    usb_url: 'USB-Adresse', wifi_url: 'WLAN-Adresse',
    waiting: 'Warte auf das Handy…', connected: 'Handy verbunden:', no_phone: 'Kein Handy: erst eins verbinden (Schritt 2).',
    no_report: 'Noch kein Bericht.', report_from: 'Bericht von', core_ok: 'alles für Version 1 funktioniert', core_missing: 'fehlt:',
    face: 'Gesicht', face_q: 'Hat sich das Gesicht geändert?', gaze: 'Blick', gaze_hint: 'Im Feld ziehen: die Augen folgen.', gaze_q: 'Sind die Augen gefolgt?',
    color: 'Augenfarbe', color_q: 'Hat sich die Farbe geändert?', say: 'Stimme', say_text: 'Hallo, ich bin dein Roboter.', say_btn: 'Sagen', say_q: 'Hast du es gehört?',
    vibrate: 'Vibration', vibrate_btn: 'Brummen', vibrate_q: 'Hast du es gespürt?', torch: 'Lampe', on: 'An', off: 'Aus',
    torch_q: 'Ging das Licht an? (das Gesicht zeigt ● cam)', yes: 'ja', no: 'nein',
    touch: 'Berührung', touch_hint: 'Auf dem Handy: links, Mitte und rechts tippen; lange drücken; wischen.',
    motion: 'Bewegung', motion_hint: 'Das Handy kippen oder drehen.', compass: 'Kompass', compass_hint: 'Das Handy flach liegend drehen.',
    battery: 'Akku', charging: 'lädt', none_yet: 'noch nichts', not_here: 'dieses Handy hat keinen',
    summary_lead: 'Was auf diesem Handy funktioniert. In deine Notizen oder den Roboterbau kopieren.', untested: 'nicht getestet', skipped: 'übersprungen',
    down: 'unten:', test_no_phone: 'Kein Handy verbunden: die Tests erreichen es nicht. Das Gesicht auf dem Handy öffnen (Schritt 2).',
    camera: 'Kamera', show: 'Auf dem Handy zeigen', hide: 'Verbergen', camera_q: 'Hat das Handy gezeigt, was seine Kamera sieht?',
    camera_hint: 'Das Handy zeigt das Bild seiner Rückkamera auf dem eigenen Bildschirm, eine Minute lang. Nichts verlässt das Handy.',
    code: 'Codes lesen', code_hint: 'Bei laufendem Bild: die Rückkamera des Handys vor diesen Code halten.', code_read: 'gelesen:',
    no_reader: 'der Browser dieses Handys liest keine Codes; der Kartenleser (Schritt 3) bringt einen eigenen mit',
    blocked: 'gesperrt: die Seite des Handys ist nicht sicher. Per USB verbinden, oder mit --cert starten',
    insecure: 'Dieses Handy nutzt eine nicht sichere Seite (http im WLAN): Kamera, Bewegung, Kompass und Akku sind gesperrt. Per USB verbinden, oder die Brücke mit Zertifikat starten (./start.sh --cert ORDNER).',
    no_torch: 'das Handy sagt, es hat keine Lampe', cam_error: 'die Kamera ging nicht auf:', size: 'Bild',
    look: 'Schauen (Frontkamera)', look_hint: 'Die Frontkamera findet Gesichter, auf dem Handy; nur wo sie sind, kommt hier an. Stell dich vor das Handy.',
    familiar_allow: 'Gesichter unterscheiden erlauben (nur in dieser Sitzung)', forget: 'Gesichter vergessen', faces_n: 'Gesichter:',
    familiar_note: 'Das Handy behält dann eine Signatur jedes Gesichts im Speicher, damit dasselbe Gesicht dieselbe Nummer bekommt. Nichts wird gespeichert oder gesendet, und beim Neuladen ist alles vergessen. Frag zuerst die Leute am Tisch, und die Eltern.',
    look_error: 'Schauen startete nicht:', look_wait: 'die Rückkamera ist belegt: Schauen wartet',
    guardian: 'Schreibtischwächter', guardian_hint: 'Wie Cozmo: er bewacht den Schreibtisch mit der Frontkamera, dreht sich zu jedem, der kommt, begrüßt seinen Besitzer (die Karte aus Schritt 4) und erschrickt, wenn man ihn hochhebt. Mit einem Thymio (atl-bot-thymio, oder seinem Zwilling in Webots) dreht er den Körper und hält sich von der Kante fern.',
    start: 'Starten', stop: 'Stoppen', drive: 'Er darf den Thymio fahren', g_off: 'gestoppt', g_none: 'der Wächter antwortet nicht: die Brücke neu starten (./start.sh)',
    st_guarding: 'wacht', st_alert: 'aufmerksam', st_friend: 'Freund', st_intruder: 'Eindringling', st_scared: 'erschrocken', st_edge: 'an der Kante', st_petted: 'gestreichelt',
    thymio_yes: 'der Thymio antwortet', thymio_no: 'kein Thymio: nur das Handy', friends: 'Freunde:',
    g_tip: 'Damit Freunde Freunde bleiben, zuerst das Unterscheiden von Gesichtern erlauben (Schritt 4, Schauen).',
    panel: 'Hochformat-Feld', panel_hint: 'Aufrecht gehalten zeigt das Gesicht oben die Augen und unten ein Feld: einen Mund, der beim Sprechen zur Schallwelle wird, Tasten, die ein Programm festlegt (jeder Druck geht an ROS), das Bild einer Kamera (nur auf dem Handy), oder die Sensoren. Ein Tippen auf die Augen öffnet das Menü; Wischen blättert.',
    layout: 'Ausrichtung:', landscape: 'Quer', portrait: 'Hoch', auto: 'Auto (wie gehalten)', layout_note: 'Das Gesicht lädt neu: auf dem Handy wieder ▶ tippen.',
    panel_mode: 'Feld:', mode_pad: 'Tasten', mode_camera: 'Frontkamera', mode_camera_back: 'Rückkamera', mode_sensors: 'Sensoren', mode_mouth: 'Mund', mode_off: 'Nur Augen', thymio_pad: 'Thymio-Tasten', abcd_pad: 'A B C D', pad: 'Feld-Tasten', pad_seen: 'gedrückt:',
    topics: 'Programme:',
    vision: 'Sehen (Kamera)', vision_hint: 'Die Kamera des Handys findet Dinge, auf dem Handy; nur Zahlen kommen hier an: Marker (ihre Nummer, Entfernung und Winkel), eine Farbe, Gegenstände (80 Arten), Hände und Gesten.',
    cam_front: 'Vorne', cam_back: 'Hinten', f_faces: 'Gesichter', f_markers: 'Marker', f_blobs: 'Farbe', f_objects: 'Gegenstände', f_hands: 'Hände',
    marker_cm: 'Markergröße, cm:', print_markers: 'Marker drucken', vision_ms: 'Zeit pro Bild:',
    owner: 'Die Besitzerkarte des Schreibtischwächters: vor die Frontkamera halten, mit deinem Gesicht im Bild (den Wächter in Schritt 5 starten).', code_seen: 'gelesen:'
  }
};
// the three choices at the top, and Omi Assist
Object.assign(T.en, {
  ph_look: 'Look at the phone', ph_wait: 'asking the phone (about ten seconds)…', ph_free: 'free memory', ph_of: 'of',
  ph_load: 'load', ph_load_d: '(tasks waiting: far above its cores, it slows down)', ph_tabs: 'Chrome tabs', ph_batt: 'battery',
  ph_thermal: 'thermal status', ph_thermal_d: '(0 none … 3 severe: the phone slows itself down)', ph_busy: 'the busiest apps (CPU %)',
  ph_mem: 'the apps that hold most memory', ph_kill: 'Stop background apps', ph_kill_q: 'Stop the apps in the background? They start again when opened; no data is lost.',
  ph_stay: 'Screen stays on (on USB)', ph_sleep: 'Screen may sleep', ph_stay_on: 'the screen stays on while on USB', ph_stay_off: 'the screen may sleep again',
  ph_list: 'Chrome tabs…', ph_list_d: 'The phone’s own tabs, other than the face: tick the ones to close.', ph_close: 'Close the ticked tabs',
  ph_close_q: 'Close {n} tabs on the phone?', ph_closed: 'closed:', ph_none: 'no other tab',
  v_setup: 'Connect and Test', v_setup_d: 'Connect a phone, check it, test each part', v_guard: 'Desk Guard', v_guard_d: 'It watches the desk, greets its owner',
  v_omi: 'Omi Assist', v_omi_d: 'A helper on a stand: big spoken tiles, reminders',
  omi_lead: 'The phone on a stand as a helper. A tap on its eyes opens big tiles that say their name: the time, the front and back camera, the magnifier, reading aloud, the sensors, eyes that follow. The back camera asks “what is this?”; each camera view can show its picture. Her assistant’s reminders come at their time, as a big card she answers.',
  no_phone_here: 'No phone connected: open the face on the phone (Connect and Test, step 2).', omi: 'Omi Assist',
  omi_none: 'Omi Assist does not answer: start the bridge with ./start.sh --omi', omi_on: 'running', omi_off: 'stopped', omi_face: 'Face upright on the phone', omi_tour: 'Introduce Omi Assist',
  omi_tour_d: 'The phone says what it can, tile by tile, in its language (about two minutes). A tap on the phone ends it.',
  twin: 'Webots twin', twin_d: 'Fly something in front of the twin, for a demo: the cup for “What is this?”, the letter for “Read aloud” (on its stand behind the robot, or held), a visitor for the greeting.',
  prop_cup: 'Cup', prop_letter: 'Letter', prop_hand: 'Held letter', prop_visitor: 'Visitor', prop_away: 'Away',
  omi_stops: 'Starting one stops the other (Desk Guard, Omi Assist): they share the face.',
  reminders: 'Reminders', rem_add: '+ Add a reminder', rem_save: 'Save the reminders', rem_test: 'Test: one in a minute', rem_test_text: 'Drink a glass of water',
  rem_text: 'What to remind', rem_saved: 'saved', rem_next: 'next:', rem_none: 'no reminder yet', every_day: 'every day', answers: 'answered:',
  ans_done: 'done', ans_later: 'later', picks: 'tiles picked:', days: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
  show_card: 'Showing the picture', show_allow: 'Allow her to show the camera’s picture to this PC (only while she presses “Show”)',
  show_note: 'Only while she shows: a red badge on the phone, at most a minute, a tap stops it. The picture comes to this page only: it is not kept, nor sent on to ROS. Agree on it with her first (docs/consent-show.md).',
  show_live: 'showing now', show_wait: 'not showing', show_stop: 'Stop showing', show_off: 'not allowed',
  lighter: 'A lighter phone', install_hint: 'On the phone, in Chrome: ⋮ › Install app (or Add to Home screen). The face then opens as its own window, without the tabs and the address bar.',
  tidy_hint: 'Or in a terminal on this PC, the same:', more_views: 'Desk Guard and Omi Assist: at the top of this page.'
});
Object.assign(T.fr, {
  ph_look: 'Regarder le téléphone', ph_wait: 'je demande au téléphone (environ dix secondes)…', ph_free: 'mémoire libre', ph_of: 'sur',
  ph_load: 'charge', ph_load_d: '(tâches en attente : bien au-dessus de ses cœurs, il ralentit)', ph_tabs: 'onglets Chrome', ph_batt: 'batterie',
  ph_thermal: 'état thermique', ph_thermal_d: '(0 rien … 3 sévère : le téléphone se ralentit)', ph_busy: 'les applis les plus actives (CPU %)',
  ph_mem: 'les applis qui tiennent le plus de mémoire', ph_kill: 'Arrêter les applis en arrière-plan', ph_kill_q: 'Arrêter les applis en arrière-plan ? Elles repartent quand on les ouvre ; rien n’est perdu.',
  ph_stay: 'Écran allumé (sur USB)', ph_sleep: 'Écran peut s’éteindre', ph_stay_on: 'l’écran reste allumé sur USB', ph_stay_off: 'l’écran peut de nouveau s’éteindre',
  ph_list: 'Onglets Chrome…', ph_list_d: 'Les onglets du téléphone, autres que le visage : cochez ceux à fermer.', ph_close: 'Fermer les onglets cochés',
  ph_close_q: 'Fermer {n} onglets sur le téléphone ?', ph_closed: 'fermés :', ph_none: 'aucun autre onglet',
  v_setup: 'Connecter et tester', v_setup_d: 'Connecter un téléphone, le vérifier, tester chaque partie', v_guard: 'Gardien du bureau', v_guard_d: 'Il surveille le bureau, salue son propriétaire',
  v_omi: 'Omi Assist', v_omi_d: 'Un assistant sur un support : de grandes tuiles qui parlent, des rappels',
  omi_lead: 'Le téléphone sur un support, comme assistant. Un toucher sur ses yeux ouvre de grandes tuiles qui disent leur nom : l’heure, la caméra avant et arrière, la loupe, lire à voix haute, les capteurs, des yeux qui suivent. La caméra arrière demande « qu’est-ce que c’est ? » ; chaque vue de caméra peut montrer son image. Les rappels de la personne qui l’assiste arrivent à leur heure, sur une grande carte à laquelle elle répond.',
  no_phone_here: 'Aucun téléphone connecté : ouvrez le visage sur le téléphone (Connecter et tester, étape 2).', omi: 'Omi Assist',
  omi_none: 'Omi Assist ne répond pas : lancez le pont avec ./start.sh --omi', omi_on: 'en marche', omi_off: 'arrêté', omi_face: 'Visage debout sur le téléphone', omi_tour: 'Présenter Omi Assist',
  omi_tour_d: 'Le téléphone dit ce qu’il sait faire, tuile par tuile, dans sa langue (environ deux minutes). Un toucher sur le téléphone l’arrête.',
  twin: 'Jumeau Webots', twin_d: 'Faites venir un objet devant le jumeau, pour une démo : la tasse pour « Qu’est-ce que c’est ? », la lettre pour « Lire » (sur son support derrière le robot, ou tenue), un visiteur pour le bonjour.',
  prop_cup: 'Tasse', prop_letter: 'Lettre', prop_hand: 'Lettre tenue', prop_visitor: 'Visiteur', prop_away: 'Enlever',
  omi_stops: 'En lancer un arrête l’autre (Gardien du bureau, Omi Assist) : ils partagent le visage.',
  reminders: 'Rappels', rem_add: '+ Ajouter un rappel', rem_save: 'Enregistrer les rappels', rem_test: 'Essai : un dans une minute', rem_test_text: 'Boire un verre d’eau',
  rem_text: 'De quoi se souvenir', rem_saved: 'enregistré', rem_next: 'prochain :', rem_none: 'pas encore de rappel', every_day: 'tous les jours', answers: 'réponses :',
  ans_done: 'fait', ans_later: 'plus tard', picks: 'tuiles choisies :', days: ['lu', 'ma', 'me', 'je', 've', 'sa', 'di'],
  show_card: 'Montrer l’image', show_allow: 'Lui permettre de montrer l’image de la caméra à ce PC (seulement quand elle appuie sur « Montrer »)',
  show_note: 'Seulement pendant qu’elle montre : un badge rouge sur le téléphone, une minute au plus, un toucher l’arrête. L’image vient sur cette page seulement : elle n’est ni gardée, ni envoyée à ROS. Mettez-vous d’accord avec elle d’abord (docs/consent-show.md).',
  show_live: 'elle montre', show_wait: 'rien de montré', show_stop: 'Arrêter de montrer', show_off: 'non permis',
  lighter: 'Un téléphone plus léger', install_hint: 'Sur le téléphone, dans Chrome : ⋮ › Installer l’application (ou Ajouter à l’écran d’accueil). Le visage s’ouvre alors dans sa propre fenêtre, sans les onglets ni la barre d’adresse.',
  tidy_hint: 'Ou dans un terminal sur ce PC, la même chose :', more_views: 'Gardien du bureau et Omi Assist : en haut de cette page.'
});
Object.assign(T.de, {
  ph_look: 'Das Handy ansehen', ph_wait: 'ich frage das Handy (etwa zehn Sekunden)…', ph_free: 'freier Speicher', ph_of: 'von',
  ph_load: 'Last', ph_load_d: '(wartende Aufgaben: weit über seinen Kernen wird es langsam)', ph_tabs: 'Chrome-Tabs', ph_batt: 'Akku',
  ph_thermal: 'Wärmestatus', ph_thermal_d: '(0 nichts … 3 stark: das Handy bremst sich selbst)', ph_busy: 'die aktivsten Apps (CPU %)',
  ph_mem: 'die Apps mit dem meisten Speicher', ph_kill: 'Hintergrund-Apps beenden', ph_kill_q: 'Die Apps im Hintergrund beenden? Sie starten wieder, wenn man sie öffnet; nichts geht verloren.',
  ph_stay: 'Bildschirm bleibt an (an USB)', ph_sleep: 'Bildschirm darf aus', ph_stay_on: 'der Bildschirm bleibt an USB an', ph_stay_off: 'der Bildschirm darf wieder ausgehen',
  ph_list: 'Chrome-Tabs…', ph_list_d: 'Die Tabs des Handys außer dem Gesicht: die zu schließenden ankreuzen.', ph_close: 'Angekreuzte Tabs schließen',
  ph_close_q: '{n} Tabs auf dem Handy schließen?', ph_closed: 'geschlossen:', ph_none: 'kein anderer Tab',
  v_setup: 'Verbinden und testen', v_setup_d: 'Ein Handy verbinden, prüfen, jeden Teil testen', v_guard: 'Schreibtischwächter', v_guard_d: 'Er bewacht den Schreibtisch, begrüßt seinen Besitzer',
  v_omi: 'Omi Assist', v_omi_d: 'Ein Helfer auf einem Ständer: große sprechende Kacheln, Erinnerungen',
  omi_lead: 'Das Handy auf einem Ständer als Helfer. Ein Tipp auf die Augen öffnet große Kacheln, die ihren Namen sagen: die Uhrzeit, die vordere und hintere Kamera, die Lupe, Vorlesen, die Sensoren, Augen, die folgen. Die hintere Kamera fragt „Was ist das?“; jede Kameraansicht kann ihr Bild zeigen. Die Erinnerungen der Assistenz kommen zu ihrer Zeit, als große Karte, die sie beantwortet.',
  no_phone_here: 'Kein Handy verbunden: das Gesicht auf dem Handy öffnen (Verbinden und testen, Schritt 2).', omi: 'Omi Assist',
  omi_none: 'Omi Assist antwortet nicht: die Brücke mit ./start.sh --omi starten', omi_on: 'läuft', omi_off: 'gestoppt', omi_face: 'Gesicht aufrecht auf dem Handy', omi_tour: 'Omi Assist vorstellen',
  omi_tour_d: 'Das Handy sagt, was es kann, Kachel für Kachel, in seiner Sprache (etwa zwei Minuten). Ein Tipp auf das Handy beendet es.',
  twin: 'Webots-Zwilling', twin_d: 'Etwas vor den Zwilling fliegen lassen, für eine Vorführung: die Tasse für „Was ist das?“, den Brief für „Vorlesen“ (auf seinem Ständer hinter dem Roboter, oder in der Hand), einen Besuch für die Begrüßung.',
  prop_cup: 'Tasse', prop_letter: 'Brief', prop_hand: 'Brief in der Hand', prop_visitor: 'Besuch', prop_away: 'Weg damit',
  omi_stops: 'Das eine starten stoppt das andere (Schreibtischwächter, Omi Assist): sie teilen sich das Gesicht.',
  reminders: 'Erinnerungen', rem_add: '+ Erinnerung hinzufügen', rem_save: 'Erinnerungen speichern', rem_test: 'Test: eine in einer Minute', rem_test_text: 'Ein Glas Wasser trinken',
  rem_text: 'Woran erinnern', rem_saved: 'gespeichert', rem_next: 'nächste:', rem_none: 'noch keine Erinnerung', every_day: 'jeden Tag', answers: 'beantwortet:',
  ans_done: 'erledigt', ans_later: 'später', picks: 'gewählte Kacheln:', days: ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'],
  show_card: 'Das Bild zeigen', show_allow: 'Ihr erlauben, das Kamerabild diesem PC zu zeigen (nur solange sie „Zeigen“ drückt)',
  show_note: 'Nur solange sie zeigt: ein rotes Abzeichen auf dem Handy, höchstens eine Minute, ein Tipp beendet es. Das Bild kommt nur auf diese Seite: es wird weder gespeichert noch an ROS weitergegeben. Vorher mit ihr absprechen (docs/consent-show.md).',
  show_live: 'sie zeigt gerade', show_wait: 'nichts gezeigt', show_stop: 'Zeigen beenden', show_off: 'nicht erlaubt',
  lighter: 'Ein leichteres Handy', install_hint: 'Auf dem Handy, in Chrome: ⋮ › App installieren (oder Zum Startbildschirm hinzufügen). Das Gesicht öffnet sich dann in einem eigenen Fenster, ohne Tabs und Adressleiste.',
  tidy_hint: 'Oder in einem Terminal auf diesem PC, dasselbe:', more_views: 'Schreibtischwächter und Omi Assist: oben auf dieser Seite.'
});
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

var STEPS = ['bridge', 'connect', 'check', 'test', 'play', 'summary'];
var VIEWS = ['setup', 'guard', 'omi'], view = 'setup';  // what to do, picked at the top (and kept in the address: #omi)
try { view = VIEWS.indexOf(location.hash.slice(1)) >= 0 ? location.hash.slice(1) : localStorage.getItem('atl-view') || 'setup'; } catch (e) {}
if (VIEWS.indexOf(view) < 0) view = 'setup';
var step = 0, S = null, bridgeUp = null, lastModel = '', lastId = '';
var answers = {};          // outputs: true / false, as the person says
var touched = {};          // touches seen: tap-left, tap-centre, tap-right, long, swipe
var imuRate = 0, lastImu = { n: 0, at: 0 }, tilt = {}, turned = false;  // tilted to another side, or turned
var passed = {};           // senses that worked once stay ticked, even if the phone reconnects
var CODE = 'atl-phone camera test', OWNER = 'atl-guardian:owner';  // OWNER: guardian.py OWNER_CARD
var THYMIO_PAD = [{ id: 'forward', label: '▲', color: [1, 0.3, 0.3] }, { id: 'left', label: '◀', color: [1, 0.3, 0.3] },  // contract.py THYMIO_PAD
                  { id: 'centre', label: '●', color: [1, 0.3, 0.3] }, { id: 'right', label: '▶', color: [1, 0.3, 0.3] },
                  { id: 'backward', label: '▼', color: [1, 0.3, 0.3] }];
var ABCD = [{ id: 'a', label: 'A', color: [0.25, 0.85, 1] }, { id: 'b', label: 'B', color: [0.2, 1, 0.4] },  // contract.py DEFAULT_PANEL
            { id: 'c', label: 'C', color: [1, 0.8, 0.2] }, { id: 'd', label: 'D', color: [1, 0.4, 0.7] }];

// ---- talking to the bridge ---------------------------------------------------------------------------
function act(body) {
  return fetch('/api/act', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(function (r) { if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || r.status); }); })
    .catch(function (e) { $('meta').textContent = '⚠ ' + e.message; });
}
function poll() {
  fetch('/api/state').then(function (r) { return r.json(); }).then(function (s) {
    S = s; bridgeUp = true;
    if (s.phone && s.phone.model) { lastModel = s.phone.model; lastId = s.phone.id || ''; }  // still known once it is gone
    update();
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
  m.play = guardianOn() ? 'yes' : '';
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
var visionTest = false;  // the Vision card turned the camera on: it goes off when the step is left, so look gets it back
function go(i) {
  var was = step;
  step = Math.max(0, Math.min(STEPS.length - 1, i));
  if (STEPS[was] === 'test' && STEPS[step] !== 'test' && visionTest) { visionTest = false; act({ topic: 'see', value: { camera: 'front', find: [] } }); }
  STEPS.forEach(function (s, j) { $('s-' + s).className = view === 'setup' && j === step ? 'on' : ''; });
  $('back').disabled = step === 0; $('next').style.visibility = step === STEPS.length - 1 ? 'hidden' : 'visible';
  if (STEPS[step] === 'summary') { renderSummary(); if (STEPS[was] !== 'summary') keepSummary(); }
  renderStepper();
}

function showView(v) {
  var was = view;
  view = v;
  try { localStorage.setItem('atl-view', v); history.replaceState(null, '', v === 'setup' ? location.pathname : '#' + v); } catch (e) {}
  [].forEach.call($('views').children, function (b) { b.className = b.getAttribute('data-v') === v ? 'on' : ''; });
  document.querySelector('.wrap').className = 'wrap' + (v === 'setup' ? '' : ' solo');
  $('v-guard').className = v === 'guard' ? 'on' : ''; $('v-omi').className = v === 'omi' ? 'on' : '';
  if (was === 'setup' && v !== 'setup' && visionTest) { visionTest = false; act({ topic: 'see', value: { camera: 'front', find: [] } }); }
  go(step);
}
function phoneLine(id) {
  var e = $(id), ph = (S && S.phone) || {};
  e.textContent = S && S.connected ? '✓ ' + t('connected') + ' ' + (ph.model || '…') : '⚠ ' + t('no_phone_here');
  e.className = 'status' + (S && S.connected ? '' : ' off');
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
    $('ca-steps').style.display = S.urls.ca ? 'block' : 'none';
    if (S.urls.ca && qrCaFor !== S.urls.ca) { qrCaFor = S.urls.ca; drawQr(S.urls.ca, $('qr-ca'), 4); }
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
    $('test-status').textContent = S.connected ? '✓ ' + t('connected') + ' ' + ((S.phone || {}).model || '…') : '⚠ ' + t('test_no_phone');
    $('test-status').className = 'status' + (S.connected ? '' : ' off');
    // 5: scenarios, and the Desk Guard and Omi Assist views
    updatePlay(); updateOmi(); phoneLine('guard-phone'); phoneLine('omi-phone');
    if (STEPS[step] === 'summary') renderSummary();
  }
}

function report() {  // this phone's latest check report: by its id, else (storage blocked) by model; no phone yet: the latest
  if (!S || !S.reports.length) return null;
  var id = (S.phone && S.phone.id) || lastId, model = (S.phone && S.phone.model) || lastModel;
  if (!id && !model) return S.reports[S.reports.length - 1];
  var rs = S.reports.filter(function (r) { return id ? r.id === id : r.model === model; });
  return rs.length ? rs[rs.length - 1] : null;
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
  live.lookBox = el('div', { class: 'pad faces' }); live.look = el('div', { class: 'live' }); live.lookMark = el('span', { class: 'mark' });
  live.allow = el('input', { type: 'checkbox', onchange: function () { act({ allow_familiar: live.allow.checked }); } });
  var owner = el('canvas', { class: 'qr' }); drawQr(OWNER, owner, 3); live.lookCode = el('div', { class: 'live' });
  o.appendChild(card('look', [el('div', { class: 'hint', text: t('look_hint') }), el('div', { class: 'row' }, [
    el('button', { class: 'b', text: t('on'), onclick: function () { act({ topic: 'look', value: true }); } }),
    el('button', { class: 'b ghost', text: t('off'), onclick: function () { act({ topic: 'look', value: false }); } })]),
    el('div', { class: 'row' }, [live.lookBox, el('div', {}, [el('div', { class: 'row' }, [live.lookMark, live.look])])]),
    el('label', { class: 'row' }, [live.allow, el('span', { text: t('familiar_allow') })]),
    el('div', { class: 'hint', text: t('familiar_note') }),
    el('div', { class: 'row' }, [
      el('button', { class: 'b ghost small', text: 'familiar ' + t('on').toLowerCase(), onclick: function () { act({ topic: 'familiar', value: true }); } }),
      el('button', { class: 'b ghost small', text: t('forget'), onclick: function () { act({ topic: 'forget' }); } })]),
    el('div', { class: 'qr' }, [owner, el('div', {}, [el('div', { class: 'hint', text: t('owner') }), live.lookCode])])]));
  // vision: what to find, on which camera; the boxes show where
  var side = 'front', kinds = { faces: false, markers: true, blobs: false, objects: false, hands: false };
  var hue = el('input', { type: 'color', value: '#e61e1e' }), size = el('input', { type: 'text', value: '5', size: '3', style: 'flex:0 0 3em' });
  function seeValue(on) {
    var h = hue.value, rgb = [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16) / 255; });
    var mx = Math.max.apply(null, rgb), mn = Math.min.apply(null, rgb), c = mx - mn, hh = 0;
    if (c) hh = mx === rgb[0] ? ((rgb[1] - rgb[2]) / c + 6) % 6 : mx === rgb[1] ? (rgb[2] - rgb[0]) / c + 2 : (rgb[0] - rgb[1]) / c + 4;
    return { camera: side, find: on ? Object.keys(kinds).filter(function (k) { return kinds[k]; }) : [],
             blob: { hue: Math.round(hh * 60), tol: 18 }, marker_cm: parseFloat(size.value) || 5 };
  }
  var sheet = el('a', { href: 'markers.html?cm=5&lang=' + lang, target: '_blank', text: t('print_markers') });
  size.oninput = function () { sheet.href = 'markers.html?cm=' + encodeURIComponent(size.value) + '&lang=' + lang; };
  var sides = el('div', { class: 'tabs' }, ['front', 'back'].map(function (k) {
    return el('button', { 'data-side': k, class: k === side ? 'on' : '', text: t('cam_' + k), onclick: function () {
      side = k; [].forEach.call(sides.children, function (b) { b.className = b.getAttribute('data-side') === side ? 'on' : ''; });
    } });
  }));
  var boxes = el('div', { class: 'row' }, Object.keys(kinds).map(function (k) {
    var cb = el('input', { type: 'checkbox' }); cb.checked = kinds[k]; cb.onchange = function () { kinds[k] = cb.checked; };
    return el('label', { class: 'row', style: 'margin:0' }, [cb, el('span', { text: t('f_' + k) })]);
  }));
  live.visionBox = el('div', { class: 'pad faces', style: 'width:240px;height:150px' }); live.vision = el('div', { class: 'live' });
  live.visionMark = el('span', { class: 'mark' });
  o.appendChild(card('vision', [el('div', { class: 'hint', text: t('vision_hint') }), sides, boxes,
    el('div', { class: 'row' }, [el('span', { class: 'hint', text: t('f_blobs') }), hue, el('span', { class: 'hint', text: t('marker_cm') }), size,
      sheet]),
    el('div', { class: 'row' }, [
      el('button', { class: 'b', text: t('on'), onclick: function () { visionTest = true; act({ topic: 'see', value: seeValue(true) }); } }),
      el('button', { class: 'b ghost', text: t('off'), onclick: function () { visionTest = false; act({ topic: 'see', value: seeValue(false) }); } })]),
    el('div', { class: 'row' }, [live.visionBox, el('div', {}, [el('div', { class: 'row' }, [live.visionMark, live.vision])])])]));
}
// ---- 5: scenarios ------------------------------------------------------------------------------------
function guardianOn() { var g = S && S.guardian; return !!(g && g.state && g.state !== 'off' && S.now - g.at < 3); }
function buildPlay() {
  var o = $('play'); o.innerHTML = '';
  live.drive = el('input', { type: 'checkbox', checked: 'checked' });
  live.drive.onchange = function () { if (guardianOn()) act({ guardian: true, drive: live.drive.checked }); };
  live.guard = el('div', { class: 'live' }); live.guardMark = el('span', { class: 'mark' }); live.guardMore = el('div', { class: 'live' });
  $('guard-cards').innerHTML = '';
  $('guard-cards').appendChild(card('guardian', [el('div', { class: 'hint', text: t('guardian_hint') }), el('div', { class: 'row' }, [
    el('button', { class: 'b', text: '▶ ' + t('start'), onclick: function () { act({ omi: false }); act({ guardian: true, drive: live.drive.checked }); } }),
    el('button', { class: 'b ghost', text: '■ ' + t('stop'), onclick: function () { act({ guardian: false }); } })]),
    el('label', { class: 'row' }, [live.drive, el('span', { text: t('drive') })]),
    el('div', { class: 'row', style: 'margin-top:8px' }, [live.guardMark, live.guard]), live.guardMore,
    el('div', { class: 'hint', text: t('g_tip') }), el('div', { class: 'hint', text: t('omi_stops') })]));
  o.appendChild(card('v_guard', [el('div', { class: 'hint', text: t('more_views') }), el('div', { class: 'row' }, [
    el('button', { class: 'b ghost', text: t('v_guard') + ' →', onclick: function () { showView('guard'); } }),
    el('button', { class: 'b ghost', text: t('v_omi') + ' →', onclick: function () { showView('omi'); } })])]));
  buildOmi();
  function layoutBtn(k) { return el('button', { class: 'b ghost small', text: t(k), onclick: function () { act({ open: 'face.html', layout: k }); } }); }
  function modeBtn(k) { return el('button', { class: 'b ghost small', 'data-mode': k, text: t('mode_' + k), onclick: function () { act({ topic: 'panel', value: { mode: k } }); } }); }
  live.modes = el('div', { class: 'row' }, [el('span', { class: 'hint', text: t('panel_mode') })].concat(['mouth', 'pad', 'off', 'camera', 'camera_back', 'sensors'].map(modeBtn)));
  var pads = el('div', { class: 'row' }, [
    el('button', { class: 'b ghost small', text: t('abcd_pad'), onclick: function () { act({ topic: 'panel', value: { mode: 'pad', buttons: ABCD } }); } }),
    el('button', { class: 'b ghost small', text: t('thymio_pad'), onclick: function () { act({ topic: 'panel', value: { mode: 'pad', buttons: THYMIO_PAD } }); } })]);
  live.pad = el('div', { class: 'row' }); live.padMark = el('span', { class: 'mark' }); live.topics = el('div', { class: 'hint' });
  o.appendChild(card('panel', [el('div', { class: 'hint', text: t('panel_hint') }),
    el('div', { class: 'row' }, [el('span', { class: 'hint', text: t('layout') }), layoutBtn('landscape'), layoutBtn('portrait'), layoutBtn('auto')]),
    el('div', { class: 'hint', text: t('layout_note') }), live.modes, pads,
    el('div', { class: 'row', style: 'margin-top:8px' }, [live.padMark, live.pad]), live.topics]));
}
function updatePlay() {
  if (!live.guard) return;
  var g = S.guardian || {}, on = guardianOn(), heard = g.at && S.now - g.at < 3;
  setMark(live.guardMark, on ? true : heard ? 'na' : null);
  live.guard.textContent = on ? t('st_' + g.state) + ' · ' + t('faces_n') + ' ' + (g.faces || 0) : heard ? t('g_off') : t('g_none');
  live.guardMore.textContent = on ? (g.thymio ? t('thymio_yes') : t('thymio_no')) + (g.friends && g.friends.length ? ' · ' + t('friends') + ' ' + g.friends.join(', ') : '') : '';
  if (heard && document.activeElement !== live.drive) live.drive.checked = g.drive !== false;
  var mode = (S.panel && S.panel.mode) || 'mouth';
  [].forEach.call(live.modes.querySelectorAll('button'), function (b) { b.style.borderColor = b.getAttribute('data-mode') === mode ? 'var(--accent)' : ''; });
  var pads = (S.seen && S.seen.pad) || [];
  live.pad.textContent = pads.length ? t('pad_seen') + ' ' + pads.slice(-5).map(function (x) { return x.id; }).join(' ') : t('none_yet');
  setMark(live.padMark, inputResult('pad'));
  live.topics.textContent = t('topics') + ' /' + S.robot + '/phone/panel → ' + t('pad').toLowerCase() + ' → /' + S.robot + '/phone/pad';
}
// ---- Omi Assist ---------------------------------------------------------------------------------------
var DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];  // omi.py DAYS
var rems = [], remsDirty = false, remsFrom = '', showAt = 0;
function omiOn() { var g = S && S.omi; return !!(g && g.state === 'on' && S.now - g.at < 3); }
function hhmm(d) { return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
function renderRems() {
  var box = live.rems; box.innerHTML = '';
  if (!rems.length) box.appendChild(el('div', { class: 'hint', text: t('rem_none') }));
  rems.forEach(function (r, i) {
    var at = el('input', { type: 'time', value: r.at }), text = el('input', { type: 'text', value: r.text, placeholder: t('rem_text'), maxlength: '150' });
    at.oninput = function () { r.at = at.value; remsDirty = true; };
    text.oninput = function () { r.text = text.value; remsDirty = true; };
    var days = el('div', { class: 'days', title: t('every_day') }, DAYS.map(function (d, j) {
      var b = el('button', { class: r.days.indexOf(d) >= 0 ? 'on' : '', text: t('days')[j] });
      b.onclick = function () {
        var k = r.days.indexOf(d); if (k >= 0) r.days.splice(k, 1); else r.days.push(d);
        b.className = r.days.indexOf(d) >= 0 ? 'on' : ''; remsDirty = true;
      };
      return b;
    }));
    box.appendChild(el('div', { class: 'rem' }, [at, text, days,
      el('button', { class: 'b ghost small', text: '✕', onclick: function () { rems.splice(i, 1); remsDirty = true; renderRems(); } })]));
  });
}
function saveRems() {
  var list = rems.filter(function (r) { return r.text.trim() && /^\d\d:\d\d$/.test(r.at); })
    .map(function (r) { return { id: r.id, text: r.text.trim(), at: r.at, days: r.days.slice() }; });
  act({ reminders: list }).then(function () { remsDirty = false; remsFrom = ''; live.remSaved.textContent = '✓ ' + t('rem_saved'); });
}
function buildOmi() {
  var o = $('omi-cards'); o.innerHTML = '';
  live.omiMark = el('span', { class: 'mark' }); live.omi = el('div', { class: 'live' }); live.omiMore = el('div', { class: 'live' });
  o.appendChild(card('omi', [el('div', { class: 'row' }, [
    el('button', { class: 'b', text: '▶ ' + t('start'), onclick: function () { act({ guardian: false }); act({ omi: true }); } }),
    el('button', { class: 'b ghost', text: '■ ' + t('stop'), onclick: function () { act({ omi: false }); } }),
    el('button', { class: 'b ghost', text: t('omi_face'), onclick: function () { act({ open: 'face.html', layout: 'auto' }); } })]),
    el('div', { class: 'row', style: 'margin-top:8px' }, [live.omiMark, live.omi]), live.omiMore,
    el('div', { class: 'row', style: 'margin-top:8px' }, [
      el('button', { class: 'b', text: '🎤 ' + t('omi_tour'), onclick: function () { act({ omi_tour: true }); } })]),
    el('div', { class: 'hint', text: t('omi_tour_d') }),
    el('div', { class: 'hint', text: t('omi_stops') })]));
  live.twin = card('twin', [el('div', { class: 'row' }, [['cup', '🥤'], ['letter', '✉️'], ['hand', '✋'], ['visitor', '🙂'], ['away', '✕']].map(function (p) {
    return el('button', { class: 'b ghost small', text: p[1] + ' ' + t('prop_' + p[0]), onclick: function () { act({ prop: p[0] }); } });
  })), el('div', { class: 'hint', text: t('twin_d') })]);
  live.twin.style.display = 'none';   // only while a twin listens (the bridge's mirrors)
  o.appendChild(live.twin);
  live.rems = el('div'); live.remSaved = el('span', { class: 'live' }); live.remNext = el('div', { class: 'live' }); live.answers = el('div', { class: 'live' });
  o.appendChild(card('reminders', [live.rems, el('div', { class: 'row' }, [
    el('button', { class: 'b ghost small', text: t('rem_add'), onclick: function () {
      rems.push({ id: '', text: '', at: hhmm(new Date(Date.now() + 3600000)), days: [] }); remsDirty = true; renderRems(); } }),
    el('button', { class: 'b ghost small', text: t('rem_test'), onclick: function () {
      rems.push({ id: '', text: t('rem_test_text'), at: hhmm(new Date(Date.now() + 60000)), days: [] }); renderRems(); saveRems(); } }),
    el('button', { class: 'b small', text: t('rem_save'), onclick: saveRems }), live.remSaved]), live.remNext, live.answers]));
  renderRems();
  live.allowShow = el('input', { type: 'checkbox', onchange: function () { act({ allow_show: live.allowShow.checked }); } });
  live.showImg = el('img', { class: 'show', alt: '' }); live.showState = el('div', { class: 'live' });
  live.showStop = el('button', { class: 'b ghost small', text: t('show_stop'), onclick: function () { act({ show: false }); } });
  o.appendChild(card('show_card', [el('label', { class: 'row' }, [live.allowShow, el('span', { text: t('show_allow') })]),
    el('div', { class: 'hint', text: t('show_note') }), el('div', { class: 'row', style: 'margin-top:8px' }, [live.showState, live.showStop]), live.showImg]));
  live.ph = el('div', { class: 'live' }); live.phTabs = el('div');
  o.appendChild(card('lighter', [el('div', { class: 'hint', text: t('install_hint') }), el('div', { class: 'row' }, [
    el('button', { class: 'b ghost small', text: '🔍 ' + t('ph_look'), onclick: function () { phone('look'); } }),
    el('button', { class: 'b ghost small', text: t('ph_kill'), onclick: function () { if (confirm(t('ph_kill_q'))) phone('kill'); } }),
    el('button', { class: 'b ghost small', text: t('ph_stay'), onclick: function () { phone('stay_on'); } }),
    el('button', { class: 'b ghost small', text: t('ph_sleep'), onclick: function () { phone('stay_off'); } }),
    el('button', { class: 'b ghost small', text: t('ph_list'), onclick: listTabs })]), live.ph, live.phTabs,
    el('div', { class: 'hint', text: t('tidy_hint') }), el('pre', {}, [el('span', { text: './scripts/phone_tidy.sh [--kill] [--stay-on] [--close-tabs]' })])]));
}
// ---- a lighter phone: what weighs on it, and lighter when asked (the bridge's phone_health, over this PC's adb) -----
function actGet(body) {  // as act(), with the bridge's answer
  return fetch('/api/act', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || r.status); return j; }); });
}
function phone(what) {
  live.ph.textContent = t('ph_wait');
  actGet({ phone: what }).then(function (h) {
    if (h.stay_on !== undefined) { live.ph.textContent = t(h.stay_on ? 'ph_stay_on' : 'ph_stay_off'); return; }
    var n = function (x) { return x === null || x === undefined ? '?' : x; };
    var list = function (title, rows) { return el('div', {}, [el('b', { text: title })].concat(rows.map(function (r) { return el('div', { text: '  ' + r }); }))); };
    live.ph.innerHTML = '';
    [h.model + ' · Android ' + h.android,
     t('ph_free') + ' ' + h.free_mb + ' ' + t('ph_of') + ' ' + h.total_mb + ' MB · ' + t('ph_tabs') + ' ' + n(h.tabs),
     t('ph_load') + ' ' + (h.load ? h.load.join(', ') : '?') + ' ' + t('ph_load_d'),
     t('ph_batt') + ' ' + n(h.battery_c) + ' °C · ' + t('ph_thermal') + ' ' + n(h.thermal) + ' ' + t('ph_thermal_d')
    ].forEach(function (line) { live.ph.appendChild(el('div', { text: line })); });
    live.ph.appendChild(list(t('ph_busy'), h.busy.map(function (b) { return b.cpu + ' · ' + b.res + ' · ' + b.name; })));
    live.ph.appendChild(list(t('ph_mem'), h.memory.map(function (m) { return m.mb + ' MB · ' + m.name; })));
  }).catch(function (e) { live.ph.textContent = '⚠ ' + e.message; });
}
function listTabs() {
  live.phTabs.textContent = t('ph_wait');
  actGet({ phone: 'tabs' }).then(function (r) {
    live.phTabs.innerHTML = '';
    if (!r.tabs.length) { live.phTabs.appendChild(el('div', { class: 'hint', text: t('ph_none') })); return; }
    var boxes = r.tabs.map(function (tab) { return el('input', { type: 'checkbox', 'data-id': tab.id }); });   // none ticked
    live.phTabs.appendChild(el('div', { class: 'hint', text: t('ph_list_d') }));
    r.tabs.forEach(function (tab, i) { live.phTabs.appendChild(el('label', { class: 'row' }, [boxes[i], el('span', { text: tab.title })])); });
    live.phTabs.appendChild(el('button', { class: 'b small', text: t('ph_close'), onclick: function () {
      var ids = boxes.filter(function (b) { return b.checked; }).map(function (b) { return b.getAttribute('data-id'); });
      if (!ids.length || !confirm(t('ph_close_q').replace('{n}', ids.length))) return;
      actGet({ phone: 'close', ids: ids }).then(function (c) { live.phTabs.textContent = t('ph_closed') + ' ' + c.closed; });
    } }));
  }).catch(function (e) { live.phTabs.textContent = '⚠ ' + e.message; });
}
function updateOmi() {
  if (!live.omi) return;
  var g = S.omi || {}, on = omiOn(), heard = g.at && S.now - g.at < 3, sh = S.show || {};
  setMark(live.omiMark, on ? true : heard ? 'na' : null);
  live.omi.textContent = heard ? t(on ? 'omi_on' : 'omi_off') + (g.lang ? ' · ' + g.lang : '') : t('omi_none');
  if (live.twin) live.twin.style.display = S.mirrors ? '' : 'none';
  live.omiMore.textContent = heard && g.picks && g.picks.length ? t('picks') + ' ' + g.picks.map(function (p) { return p.id; }).join(' ') : '';
  var from = JSON.stringify(g.reminders || []);
  if (heard && !remsDirty && from !== remsFrom) {
    remsFrom = from;
    rems = (g.reminders || []).map(function (r) { return { id: r.id, text: r.text, at: r.at, days: (r.days || []).slice() }; });
    if (!live.rems.contains(document.activeElement)) renderRems();
  }
  live.remNext.textContent = g.next ? t('rem_next') + ' ' + g.next.at.replace('T', ' ') + ' · ' + g.next.text : '';
  live.answers.textContent = (g.answers || []).length ? t('answers') + ' ' + g.answers.slice(-3).map(function (a) {
    return a.when.slice(11, 16) + ' ' + a.text + ': ' + t(a.answer === 'later' ? 'ans_later' : 'ans_done');
  }).join(' · ') : '';
  if (document.activeElement !== live.allowShow) live.allowShow.checked = !!sh.allowed;
  live.showState.innerHTML = '';
  live.showState.appendChild(sh.on ? el('span', { class: 'badge', text: '● ' + t('show_live') }) : document.createTextNode(sh.allowed ? t('show_wait') : t('show_off')));
  live.showStop.style.display = sh.on ? '' : 'none';
  if (sh.on && sh.fresh) {
    if (Date.now() - showAt > 450) { showAt = Date.now(); live.showImg.src = '/api/show.jpg?' + showAt; }
    live.showImg.style.display = 'block';
  } else if (live.showImg.style.display !== 'none') { live.showImg.style.display = 'none'; live.showImg.removeAttribute('src'); }
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
    if (Math.max.apply(null, imu.gyro.map(Math.abs)) > 1) turned = true;  // rad/s: a clear turn, not sensor noise
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
  live.allow.checked = !!S.familiar_allowed;
  var lk = seen.look || {}, fs = seen.faces && now - seen.faces.at < 2 ? seen.faces.faces : [];
  live.lookBox.innerHTML = '';
  fs.forEach(function (f) {
    var d = Math.max(12, f.size * 100);
    live.lookBox.appendChild(el('span', { style: 'left:' + (f.x + 1) * 50 + '%;top:' + (1 - f.y) * 50 + '%;width:' + d + 'px;height:' + d + 'px;margin:' + (-d / 2) + 'px',
      text: f.familiar ? String(f.familiar) : '' }));
  });
  live.look.textContent = insecure() ? t('blocked') : lk.ok === false ? t('look_error') + ' ' + (lk.error || '?') :
    lk.on && c && c.on ? t('look_wait') : S.look || fs.length ? t('faces_n') + ' ' + fs.length + (S.familiar ? ' · familiar' : '') : '';
  setMark(live.lookMark, inputResult('look'));
  live.lookCode.textContent = seen.codes ? t('code_seen') + ' ' + seen.codes[seen.codes.length - 1] : '';
  // vision: each thing found in the last two seconds, where it is
  var sr = seen.see || {}, vb = live.visionBox; vb.innerHTML = '';
  function mark(x, y, d, text, colour) {
    vb.appendChild(el('span', { style: 'left:' + (x + 1) * 50 + '%;top:' + (1 - y) * 50 + '%;width:' + d + 'px;height:' + d + 'px;margin:' + (-d / 2) +
      'px;' + (colour ? 'border-color:' + colour + ';color:' + colour : ''), text: text }));
  }
  function fresh(k) { var v = seen[k]; return v && now - v.at < 2 ? v[k] : []; }
  fresh('markers').forEach(function (m) { mark(m.x, m.y, Math.max(16, m.size * 150), '#' + m.id + (m.distance_m != null ? ' ' + Math.round(m.distance_m * 100) + 'cm' : '')); });
  fresh('blobs').forEach(function (b) { mark(b.x, b.y, Math.max(10, b.size * 150), '', '#e61e1e'); });
  fresh('objects').forEach(function (b) { mark(b.x, b.y, Math.max(16, b.h * 150), b.label + (b.distance_m != null ? ' ' + b.distance_m + 'm' : '')); });
  fresh('hands').forEach(function (b) { mark(b.x, b.y, 22, b.gesture); });
  live.vision.textContent = insecure() ? t('blocked') : sr.ok === false ? t('look_error') + ' ' + (sr.error || '?') : sr.on ?
    t('vision_ms') + ' ' + Object.keys(sr.ms || {}).map(function (k) { return t('f_' + k) + ' ' + sr.ms[k] + ' ms'; }).join(', ') +
    (sr.backend ? ' · ' + sr.backend : '') : '';
  setMark(live.visionMark, inputResult('vision'));
}
function insecure() { return !!(S && S.connected && S.phone && S.phone.secure === false); }
function noteOf(k, v) {  // why a result is not a plain yes or no
  if (v === 'blocked') return t('blocked');
  if (v === 'na') return k === 'code' ? t('no_reader') : k === 'torch' ? t('no_torch') : t('not_here');
  if (v === null) return partial(k) || t('untested');
  var c = S && S.seen && S.seen.camera;
  if (k === 'camera' && v === false && c && c.error) return t('cam_error') + ' ' + c.error;
  var lk = S && S.seen && S.seen.look;
  if (k === 'look' && v === false && lk && lk.error) return t('look_error') + ' ' + lk.error;
  return '';
}
var NEED_SECURE = { camera: 1, torch: 1, code: 1, motion: 1, compass: 1, battery: 1, look: 1, vision: 1 };
function inputResult(k) {
  var v = passed[k] || inputNow(k);
  if (v === true) passed[k] = true;
  return v !== true && insecure() && NEED_SECURE[k] ? 'blocked' : v;
}
function inputNow(k) {
  var seen = (S && S.seen) || {}, caps = (S && S.phone && S.phone.caps) || {};
  if (k === 'code') return seen.camera && seen.camera.codes ? true : caps.barcode === false ? 'na' : null;
  if (k === 'touch') return GESTURES.every(function (x) { return touched[x]; }) || null;
  if (k === 'motion') return seen.imu ? (Object.keys(tilt).length >= 2 || turned || null) : (caps.motion === false ? false : null);
  if (k === 'compass') return seen.heading ? true : caps.compass === false ? 'na' : null;
  if (k === 'battery') return seen.battery ? true : caps.battery === false ? 'na' : null;
  if (k === 'look') return seen.faces && seen.faces.n > 0 ? true : seen.look && seen.look.ok === false ? false : null;
  if (k === 'pad') return seen.pad && seen.pad.length ? true : null;
  if (k === 'vision') return seen.see && seen.see.ok && Object.keys(seen.see.ms || {}).length ? true : seen.see && seen.see.ok === false ? false : null;
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
  ['touch', 'motion', 'compass', 'battery', 'code', 'look', 'vision', 'pad'].forEach(function (k) { r[k] = inputResult(k); });
  return r;
}

// ---- 5: summary --------------------------------------------------------------------------------------
function summaryText() {
  var r = results(), ph = (S && S.phone) || {}, rep = report();
  var lines = ['Phone: ' + (ph.model || lastModel || '?') + ' (' + (S ? S.robot : '?') + ', ' + (S ? S.contract : '') + ')', 'Date: ' + new Date().toISOString().slice(0, 10)];
  if (rep) lines.push('Check: ' + (coreMissing(rep).length ? 'missing ' + coreMissing(rep).join(', ') : 'core complete'));
  if (insecure()) lines.push('Page: not secure (http over Wi-Fi): camera, motion, compass, battery blocked');
  Object.keys(r).forEach(function (k) {
    var v = r[k], more = v === 'na' ? ' (none)' : v === 'blocked' ? ' (blocked: page not secure)' :
      v === null ? ' (' + (partial(k) ? 'missing ' + GESTURES.filter(function (x) { return !touched[x]; }).join(', ') : 'not tested') + ')' : '';
    lines.push((v === true ? '[x] ' : v === false ? '[ ] ' : '[-] ') + k + more);
  });
  return lines.join('\n');
}
function keepSummary() {  // into the PC's registry of phones tested (reports/<model>/), each time the summary is shown
  var ph = (S && S.phone) || {}, model = ph.model || lastModel;
  if (!model) return;
  fetch('/api/summary', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: model, id: ph.id || lastId, text: summaryText(), results: results(), robot: S && S.robot, contract: S && S.contract }) })
    .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || r.status); return j; }); })
    .then(function (j) { $('saved').textContent = j.saved ? t('saved_summary') + ' ' + j.saved : t('no_registry'); },
          function (e) { $('saved').textContent = '⚠ ' + e.message; });
}
function renderSummary() {
  var r = results(), ph = (S && S.phone) || {}, tb = $('summary'); tb.innerHTML = '';
  $('summary-lead').textContent = t('summary_lead') + ((ph.model || lastModel) ? ' · ' + (ph.model || lastModel) : '');
  var rep = report();
  tb.appendChild(el('tr', {}, [el('td', {}, [el('span', { class: 'mark ' + (rep ? (coreMissing(rep).length ? 'no' : 'yes') : ''), text: rep ? (coreMissing(rep).length ? '✗' : '✓') : '–' })]),
    el('td', { text: t('s3') }), el('td', { class: 'hint', text: rep ? (coreMissing(rep).length ? t('core_missing') + ' ' + coreMissing(rep).join(', ') : t('core_ok')) : t('skipped') })]));
  Object.keys(r).forEach(function (k) {
    var m = el('span'); setMark(m, r[k]);
    tb.appendChild(el('tr', {}, [el('td', {}, [m]), el('td', { text: t(k) }), el('td', { class: 'hint', text: noteOf(k, r[k]) })]));
  });
}

// ---- the page ----------------------------------------------------------------------------------------
var qrFor = null, qrCaFor = null;
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
  buildOutputs(); buildInputs(); buildPlay(); showView(view);
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
$('save-summary').onclick = keepSummary;
$('copy-summary').onclick = function () { copy(summaryText(), function () { $('copied').textContent = t('copied'); }); };
$('open-check').onclick = function () { act({ open: 'check.html' }); };
[].forEach.call($('views').children, function (b) { b.onclick = function () { showView(b.getAttribute('data-v')); }; });
$('back').onclick = function () { go(step - 1); };
$('next').onclick = function () { go(step + 1); };
translate();
poll();

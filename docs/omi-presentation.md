<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Atelier-5 -->
<!-- Omi Assist's presentation: what the phone says, step by step, and what happens on the phone and on the PC meanwhile. -->

# Omi Assist introduces itself

Start it on the setup page, at **Omi Assist › 🎤 Introduce Omi Assist**. Omi Assist must be running (`./start.sh --omi`,
or ▶ Start). The phone then speaks for about two minutes, in Omi's language (German with `--omi`), whatever language
the phone itself is set to. Each tile turns yellow while it is spoken of. A tap anywhere on the phone ends it.

## The robot as a whole

Omi Assist is not only the phone: it is the phone, clamped on top of a Raspberry Pi 4 in a brick box, on a Thymio II.
The Pi runs the bridge and Omi Assist (and the Thymio link); the phone and the Thymio are plugged into its USB. A PC,
or a laptop beside the table, opens only the setup page over Wi-Fi: the presentation is started from there. Below,
"the bridge" is on the Pi; on a desk without the robot it is on the PC, and everything else is the same. The robot
drives slowly (at most 0.12 m/s with the phone on top: `webots/omi_robot.ttl` has the robot's constraints).

In Webots, the twin of the whole robot stands alone on a table (`webots/worlds/table_omi.wbt`), and its screen can
follow the real phone's as a mirror: the tiles, the yellow one, the cards. It gets only which text is shown (a key),
never the words read aloud and no picture.

## What happens where

**Started from the PC.** The setup page (on the PC, over Wi-Fi) sends one message: "introduce yourself, in German" (`{"t": "tour", "lang": "de"}`).
The bridge (on the Pi) forwards it to the phone over the USB cable. That is all the PC does for the presentation.

**On the phone.** Everything else happens on the phone, in the face page (`web/omi.js`):

- the words;
- the voice, from the phone's own text-to-speech (on Android usually Google's speech engine);
- the yellow tile;
- the short camera views;
- the sample card.

**Nothing leaves the phone.** No picture leaves it and no word goes to the internet. The bridge only hears which tiles she
taps (`menu`), how she answers cards (`note/answer`) and which of the fixed texts the screen shows (`screen`: keys
such as `tour.time`, for the twin's mirror).

On the phone's network: if the phone's speech engine is set to use network voices, the phone's own system may fetch
them. Android: Settings › Text-to-speech output › the engine's settings.

| # | The phone says (German) | On the phone | On the Pi (or the PC) |
|---|---|---|---|
| 1 | Hallo Omi! Ich bin Omi Assist, dein persönlicher Helfer. Ich wohne in diesem Handy. Ich zeige dir kurz, was ich kann. | happy eyes; the words written big | the setup page sent the start |
| 2 | Wenn ich dir helfen kann, tippe einfach auf meine Augen. Dann kommen diese großen Kacheln. Jede sagt dir ihren Namen. | the nine tiles open | — |
| 3 | Uhrzeit: ich sage dir, wie spät es ist, und welcher Tag heute ist. *(then the real time: "Es ist Viertel nach drei. Heute ist Sonntag, 25. Oktober.")* | Uhrzeit in yellow; the time from the phone's own clock | — |
| 4 | Vordere Kamera: du siehst dich selbst, wie in einem Spiegel. | the front camera for 3.5 s, on this screen only | — (no picture) |
| 5 | Hintere Kamera: du siehst, was hinter dem Handy ist. Halte mir etwas hin und tippe auf das Fragezeichen: dann sage ich dir, was es ist, zum Beispiel eine Tasse. | the back camera for 3.5 s, with its ❓ Was ist das? button | — |
| 6 | Die Lupe macht kleine Schrift groß. Plus und Minus vergrößern, die Lampe hilft im Dunkeln, und die Hand hält das Bild fest. | the magnifier for 3.5 s, with its buttons | — |
| 7 | Vorlesen: halte mir einen Brief vor die hintere Kamera, und ich lese ihn dir vor. Ein Tipp, und ich höre auf. | Vorlesen in yellow (it does not read now) | — |
| 8 | Sensoren: hier siehst du, wie voll mein Akku ist, wohin ich schaue, wie ich stehe, und wo wir sind. | Sensoren in yellow, then the sensors for 3.5 s (the battery, the tilt, the compass, the location) | — (the location stays on the phone) |
| 9 | Folgen: meine Augen schauen immer auf das, was mir am nächsten ist. Auf dich zum Beispiel. | Folgen in yellow; the eyes keep following | — |
| 10 | Und in den Kamerabildern kannst du mit Zeigen deiner Assistenz am Computer das Bild zeigen. Nur solange es an ist, und dann siehst du oben einen roten Punkt. | only when Zeigen is allowed: the front camera for 3.5 s, with its 📡 Zeigen button (nothing is shown) | — |
| 11 | Und deine Assistenz kann mir Erinnerungen geben. Dann kommt so eine Karte. Tippe auf Erledigt, oder auf Später, dann erinnere ich dich in zehn Minuten noch einmal. | a sample card "Zum Beispiel: Tabletten nehmen", with Erledigt and Später | a tap on it only reaches `note/answer` as "tour", which Omi Assist ignores |
| 12 | Und mit Gesicht kommst du immer zurück zu mir. | Gesicht in yellow (the last tile, always there) | — |
| 13 | Das war es. Ich freue mich, dir zu helfen! | happy eyes; the face alone again | — |

The same steps exist in English and French (`tour` in `web/texts.js`). With `--omi --lang fr` the presentation is
in French.

## Each helper outside the presentation: on the phone, or on the PC?

| Helper | On the phone | On the Pi (the bridge, Omi Assist) | Leaves the phone |
|---|---|---|---|
| The tiles (a tap on the eyes) | drawn, spoken, acted on | hears which one: `menu` `{"id"}` | the tile's name |
| Language | the words and the voice | Omi Assist sends `"lang": "de"` with its panel; when stopped, `"auto"` (the phone's own again) | — |
| Uhrzeit | the phone's clock, its voice | — | — |
| Vordere / Hintere Kamera | the picture, on this screen only | — | — |
| Lupe | zoom, lamp, hold | — | — |
| Sensoren | the battery, the tilt, the compass, the location (asked only while shown), the link | the screen report's numbers for the twin: battery, compass, tilt | numbers, never the location |
| Vorlesen | the picture and the reading (Tesseract), the voice | `read/result`: lines, characters, time taken | numbers only, never the text |
| Was ist das? (the ❓ button in the back camera) | the picture and the object finder (MediaPipe), the voice | `what/result`: the label (e.g. `cup`) and the time | one word |
| Folgen | the face finder and the eyes (4 looks a second, 1 while nobody is there) | the see report: where the target is (x, y, kind) | positions only |
| Erinnerungen | the card and its buttons | Omi Assist keeps them (`omi/reminders.json`), says when one is due, logs her answer (`omi/answers.jsonl`) | her answer (Erledigt / Später) |
| Zeigen (opt-in: the 📡 button in each camera view) | the red badge; small pictures, only while she shows | the bridge keeps the last for 3 s and hands it to the setup page (`/api/show.jpg`) and the Webots twin, on its own computer only; no topic, no disk | the picture: the one exception (docs/consent-show.md) |
| Hallo, when she comes back | — | Omi Assist sees that a face is there (`faces`: a position, no picture) and says hello after 5 minutes away | — |

The models and libraries the phone uses (MediaPipe, Tesseract and its German, French and English) come from the
bridge (on the Pi, or this PC), over the cable, not from the internet.

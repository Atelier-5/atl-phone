<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Atelier-5 -->
<!-- Omi Assist's presentation: what the phone says, step by step, and what happens on the phone and on the PC meanwhile. -->

# Omi Assist introduces itself

Start it on the setup page, at **Omi Assist › 🎤 Introduce Omi Assist**. Omi Assist must be running (`./start.sh --omi`,
or ▶ Start). The phone then speaks for about two minutes, in Omi's language (German with `--omi`), whatever language
the phone itself is set to. Each tile turns yellow while it is spoken of. A tap anywhere on the phone ends it.

## What happens where

**Started from the PC.** The setup page sends one message: "introduce yourself, in German" (`{"t": "tour", "lang": "de"}`).
The bridge forwards it to the phone over the USB cable. That is all the PC does for the presentation.

**On the phone.** Everything else happens on the phone, in the face page (`web/omi.js`):

- the words;
- the voice, from the phone's own text-to-speech (on Android usually Google's speech engine);
- the yellow tile;
- the short camera views;
- the sample card.

**Nothing leaves the phone.** No picture leaves it and no word goes to the internet. The PC only hears which tiles she
taps (`menu`) and how she answers cards (`note/answer`).

On the phone's network: if the phone's speech engine is set to use network voices, the phone's own system may fetch
them. Android: Settings › Text-to-speech output › the engine's settings.

| # | The phone says (German) | On the phone | On the PC |
|---|---|---|---|
| 1 | Hallo Omi! Ich bin Omi Assist, dein persönlicher Helfer. Ich wohne in diesem Handy. Ich zeige dir kurz, was ich kann. | happy eyes; the words written big | the setup page sent the start |
| 2 | Wenn ich dir helfen kann, tippe einfach auf meine Augen. Dann kommen diese großen Kacheln. Jede sagt dir ihren Namen. | the nine tiles open | — |
| 3 | Uhrzeit: ich sage dir, wie spät es ist, und welcher Tag heute ist. *(then the real time: "Es ist Viertel nach drei. Heute ist Sonntag, 25. Oktober.")* | Uhrzeit in yellow; the time from the phone's own clock | — |
| 4 | Vordere Kamera: du siehst dich selbst, wie in einem Spiegel. | the front camera for 3.5 s, on this screen only | — (no picture) |
| 5 | Hintere Kamera: du siehst, was hinter dem Handy ist. Ein Tipp genügt zum Wechseln. | the back camera for 3.5 s | — |
| 6 | Die Lupe macht kleine Schrift groß. Plus und Minus vergrößern, die Lampe hilft im Dunkeln, und die Hand hält das Bild fest. | the magnifier for 3.5 s, with its buttons | — |
| 7 | Vorlesen: halte mir einen Brief vor die hintere Kamera, und ich lese ihn dir vor. Ein Tipp, und ich höre auf. | Vorlesen in yellow (it does not read now) | — |
| 8 | Was ist das? Halte mir etwas hin, und ich sage dir, was es ist, zum Beispiel eine Tasse. | Was ist das? in yellow | — |
| 9 | Folgen: meine Augen schauen immer auf das, was mir am nächsten ist. Auf dich zum Beispiel. | Folgen in yellow; the eyes keep following | — |
| 10 | Zeigen: so kannst du deiner Assistenz am Computer etwas zeigen. Nur solange du es drückst, und dann siehst du oben einen roten Punkt. | Zeigen in yellow (nothing is shown) | — |
| 11 | Und deine Assistenz kann mir Erinnerungen geben. Dann kommt so eine Karte. Tippe auf Erledigt, oder auf Später, dann erinnere ich dich in zehn Minuten noch einmal. | a sample card "Zum Beispiel: Tabletten nehmen", with Erledigt and Später | a tap on it only reaches `note/answer` as "tour", which Omi Assist ignores |
| 12 | Und mit Gesicht kommst du immer zurück zu mir. | Gesicht in yellow (the last tile, always there) | — |
| 13 | Das war es. Ich freue mich, dir zu helfen! | happy eyes; the face alone again | — |

The same steps exist in English and French (`TOUR_TEXT` in `web/omi.js`). With `--omi --lang fr` the presentation is
in French.

## Each helper outside the presentation: on the phone, or on the PC?

| Helper | On the phone | On the PC (the bridge, Omi Assist) | Leaves the phone |
|---|---|---|---|
| The tiles (a tap on the eyes) | drawn, spoken, acted on | hears which one: `menu` `{"id"}` | the tile's name |
| Language | the words and the voice | Omi Assist sends `"lang": "de"` with its panel; when stopped, `"auto"` (the phone's own again) | — |
| Uhrzeit | the phone's clock, its voice | — | — |
| Vordere / Hintere Kamera | the picture, on this screen only | — | — |
| Lupe | zoom, lamp, hold | — | — |
| Vorlesen | the picture and the reading (Tesseract), the voice | `read/result`: lines, characters, time taken | numbers only, never the text |
| Was ist das? | the picture and the object finder (MediaPipe), the voice | `what/result`: the label (e.g. `cup`) and the time | one word |
| Folgen | the finders (faces, hands) and the eyes | the see report: where the target is (x, y, kind) | positions only |
| Erinnerungen | the card and its buttons | Omi Assist keeps them (`omi/reminders.json`), says when one is due, logs her answer (`omi/answers.jsonl`) | her answer (Erledigt / Später) |
| Zeigen (opt-in) | the red badge; small pictures, only while she shows | the bridge keeps the last for 3 s and hands it to the setup page only (`/api/show.jpg`); no topic, no disk | the picture: the one exception (docs/consent-show.md) |
| Hallo, when she comes back | — | Omi Assist sees that a face is there (`faces`: a position, no picture) and says hello after 5 minutes away | — |

The models and libraries the phone uses (MediaPipe, Tesseract and its German, French and English) come from the
bridge on this PC, over the cable, not from the internet.

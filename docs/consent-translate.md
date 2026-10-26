<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Atelier-5 -->
<!-- The note to agree on with the people at the table before allowing Übersetzen (the phone's sound to the robot's computer). -->

# Talking with translation ("Übersetzen", Omi Assist): a note to agree on first

## 🇬🇧 English

Normally the phone's microphone stays closed, and nothing anyone says leaves the phone. "Übersetzen" (Translate) is an
exception, for a family that speaks German and French: one person holds a half of the tile and speaks, and the phone
says it in the other language.

- **Only when allowed:** someone at the robot's computer turns it on (the setup page, Omi Assist, "Allow talking…", or
  `./start.sh --translate`). Otherwise the tile is not there.
- **Only while held:** the microphone opens when a half (🇩🇪 Deutsch or 🇫🇷 Français) is pressed, and closes the moment
  it is let go, at the latest after 30 seconds. Nothing is heard between two holds.
- **Always visible:** while it listens, the phone has a red **● HÖRT ZU** (LISTENING) badge on top, and the half that is
  held turns red.
- **Where it goes:** the sound goes to the robot's computer only (the PC in the lab, the Raspberry Pi on the robot),
  over the phone's USB cable, or over the home Wi-Fi only when that link is encrypted (https). The computer turns it
  into words and translates them **offline** (Vosk and Opus-MT, on the computer itself), sends the words back to the
  phone, and drops the sound. Nothing goes to the internet or to any company.
- **Nothing kept:** the sound and the words are not written to disk, not logged, and not shown on the setup page or in
  the robot's twin in Webots. The robot's programs (ROS) only learn that a translation happened, how many words, and how
  long it took. The words stay on the phone's screen until the next one.
- **A second phone:** someone at the table can join with their own phone on the home Wi-Fi. In Übersetzen, the robot's
  phone shows a QR code where the eyes are; scanning it opens a page on the robot's computer (encrypted, https; the
  first time, Chrome warns about the connection because the robot made its own certificate). Both phones then show
  what either says, and the same rules hold: the microphone only while held, the badge, nothing kept. The code changes
  each time Übersetzen is allowed or the setup page makes a new one, and only one second phone can be there at a time.
- **Who decides:** the people at the table, Omi first. Agree on it before allowing it, and turn it off when someone asks.
  Machine translation makes mistakes: for anything important (health, money), check with a person.

## 🇫🇷 Français

D'habitude, le micro du téléphone reste fermé, et rien de ce qu'on dit ne quitte le téléphone. « Übersetzen »
(Traduire) est une exception, pour une famille qui parle allemand et français : une personne appuie sur une moitié de
la tuile et parle, et le téléphone le redit dans l'autre langue.

- **Seulement si c'est permis :** quelqu'un à l'ordinateur du robot l'active (la page d'installation, Omi Assist,
  « Permettre de parler… », ou `./start.sh --translate`). Sinon, la tuile n'est pas là.
- **Seulement pendant qu'on appuie :** le micro s'ouvre quand on appuie sur une moitié (🇩🇪 Deutsch ou 🇫🇷 Français) et se
  ferme dès qu'on la relâche, au plus tard après 30 secondes. Rien n'est écouté entre deux appuis.
- **Toujours visible :** pendant qu'il écoute, le téléphone affiche en haut un badge rouge **● HÖRT ZU** (J'ÉCOUTE), et
  la moitié appuyée devient rouge.
- **Où va le son :** seulement à l'ordinateur du robot (le PC au labo, le Raspberry Pi sur le robot), par le câble USB
  du téléphone, ou par le Wi-Fi de la maison seulement si ce lien est chiffré (https). L'ordinateur en fait des mots et
  les traduit **hors ligne** (Vosk et Opus-MT, sur l'ordinateur lui-même), renvoie les mots au téléphone, et jette le
  son. Rien ne va sur internet ni à une entreprise.
- **Rien n'est gardé :** ni le son ni les mots ne sont écrits sur le disque, ni dans le journal, ni montrés sur la page
  d'installation ou dans le jumeau du robot dans Webots. Les programmes du robot (ROS) apprennent seulement qu'une
  traduction a eu lieu, combien de mots, et en combien de temps. Les mots restent sur l'écran du téléphone jusqu'à la
  suivante.
- **Un deuxième téléphone :** quelqu'un à table peut se joindre avec son propre téléphone sur le Wi-Fi de la maison.
  Dans Übersetzen, le téléphone du robot affiche un code QR à la place des yeux ; le scanner ouvre une page sur
  l'ordinateur du robot (chiffrée, https ; la première fois, Chrome avertit au sujet de la connexion, car le robot a
  fait son propre certificat). Les deux téléphones montrent alors ce que chacun dit, avec les mêmes règles : le micro
  seulement pendant qu'on appuie, le badge, rien n'est gardé. Le code change chaque fois qu'Übersetzen est permis ou que
  la page d'installation en fait un nouveau, et un seul deuxième téléphone peut être là à la fois.
- **Qui décide :** les personnes à table, Omi d'abord. Mettez-vous d'accord avant de le permettre, et arrêtez quand
  quelqu'un le demande. La traduction automatique fait des erreurs : pour ce qui compte (santé, argent), vérifiez avec
  une personne.

## 🇩🇪 Deutsch

Normalerweise bleibt das Mikrofon des Handys zu, und nichts, was jemand sagt, verlässt das Handy. „Übersetzen" ist
eine Ausnahme, für eine Familie, die Deutsch und Französisch spricht: jemand hält eine Hälfte der Kachel gedrückt und
spricht, und das Handy sagt es in der anderen Sprache.

- **Nur wenn erlaubt:** jemand am Computer des Roboters schaltet es ein (die Einrichtungsseite, Omi Assist, „Sprechen
  mit Übersetzung erlauben…", oder `./start.sh --translate`). Sonst gibt es die Kachel nicht.
- **Nur solange gedrückt:** das Mikrofon geht auf, wenn eine Hälfte (🇩🇪 Deutsch oder 🇫🇷 Français) gedrückt wird, und
  geht zu, sobald man loslässt, spätestens nach 30 Sekunden. Zwischen zwei Mal Drücken hört es nichts.
- **Immer sichtbar:** solange es zuhört, steht oben auf dem Handy ein rotes **● HÖRT ZU**, und die gedrückte Hälfte
  wird rot.
- **Wohin es geht:** der Ton geht nur an den Computer des Roboters (den PC im Labor, den Raspberry Pi auf dem Roboter),
  über das USB-Kabel des Handys, oder über das WLAN zu Hause nur, wenn diese Verbindung verschlüsselt ist (https). Der
  Computer macht daraus Wörter und übersetzt sie **offline** (Vosk und Opus-MT, auf dem Computer selbst), schickt die
  Wörter an das Handy zurück und wirft den Ton weg. Nichts geht ins Internet oder an eine Firma.
- **Nichts wird behalten:** weder Ton noch Wörter werden auf die Festplatte geschrieben, protokolliert oder auf der
  Einrichtungsseite oder im Zwilling des Roboters in Webots gezeigt. Die Programme des Roboters (ROS) erfahren nur, dass
  übersetzt wurde, wie viele Wörter und wie lange es dauerte. Die Wörter bleiben bis zur nächsten Übersetzung auf dem
  Bildschirm des Handys.
- **Ein zweites Handy:** jemand am Tisch kann mit dem eigenen Handy im WLAN zu Hause dazukommen. In Übersetzen zeigt
  das Handy des Roboters einen QR-Code, wo sonst die Augen sind; wer ihn scannt, öffnet eine Seite auf dem Computer des
  Roboters (verschlüsselt, https; beim ersten Mal warnt Chrome vor der Verbindung, weil der Roboter sein Zertifikat
  selbst gemacht hat). Beide Handys zeigen dann, was jemand sagt, mit denselben Regeln: Mikrofon nur solange gedrückt,
  das Abzeichen, nichts wird behalten. Der Code ändert sich jedes Mal, wenn Übersetzen erlaubt wird oder die
  Einrichtungsseite einen neuen macht, und es kann immer nur ein zweites Handy dabei sein.
- **Wer entscheidet:** die Leute am Tisch, Omi zuerst. Sprechen Sie es vorher ab, und schalten Sie es aus, wenn jemand
  darum bittet. Maschinelle Übersetzung macht Fehler: bei Wichtigem (Gesundheit, Geld) mit einem Menschen nachprüfen.

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Atelier-5 -->
<!-- The note to agree on with the person who uses Omi Assist before allowing "show" (the camera's picture to the PC). -->

# Showing the picture to the PC ("show", Omi Assist): a note to agree on first

## 🇬🇧 English

Normally the phone's pictures never leave it: the phone finds faces, reads text and names things by itself, and only
numbers go to the PC. "Show" is the one exception. It lets the person using the phone **show** something to whoever
sits at the PC: a letter, a pill box, a photo. It is meant for her assistant, helping from the next room.

- **Only when allowed:** someone at the PC turns it on (the setup page, Omi Assist, "Allow…", or `./start.sh --show`).
  Otherwise the "Show" tile only says that showing is not allowed.
- **Only while she shows:** the picture goes to the PC only after she presses "Show", for at most one minute. A tap on
  the red badge, or on "Show" again, stops it. Someone at the PC can stop it too.
- **Always visible:** while it shows, the phone has a red **● SHOWING** badge on top, and its screen shows what the
  camera sees, so she knows what is being shown.
- **Where it goes:** a small picture (320 pixels wide, two a second) to the setup page on this PC only. The bridge keeps
  the last one in memory for three seconds; it writes nothing to disk, and nothing goes to ROS, the robot's programs,
  or the internet.
- **Who decides:** she does. Agree on it with her before allowing it, and turn it off when she says so.

## 🇫🇷 Français

D'habitude, les images du téléphone ne le quittent jamais : il trouve les visages, lit les textes et nomme les choses
tout seul, et seuls des nombres vont au PC. « Montrer » est la seule exception. La personne qui utilise le téléphone
peut **montrer** quelque chose à qui est au PC : une lettre, un pilulier, une photo. C'est pensé pour la personne qui
l'assiste, depuis la pièce d'à côté.

- **Seulement si c'est permis :** quelqu'un au PC l'active (la page d'installation, Omi Assist, « Lui permettre… », ou
  `./start.sh --show`). Sinon, la tuile « Montrer » dit seulement que ce n'est pas permis.
- **Seulement pendant qu'elle montre :** l'image va au PC seulement après qu'elle a appuyé sur « Montrer », une minute
  au plus. Un toucher sur le badge rouge, ou de nouveau sur « Montrer », l'arrête. Au PC, on peut l'arrêter aussi.
- **Toujours visible :** pendant ce temps, le téléphone affiche en haut un badge rouge **● JE MONTRE**, et son écran
  montre ce que voit la caméra : elle sait ce qui est montré.
- **Où va l'image :** une petite image (320 pixels de large, deux par seconde) vers la page d'installation de ce PC
  seulement. Le pont garde la dernière en mémoire trois secondes ; il n'écrit rien sur le disque, et rien ne va à ROS,
  aux programmes du robot, ni sur internet.
- **Qui décide :** elle. Mettez-vous d'accord avec elle avant de le permettre, et arrêtez quand elle le dit.

## 🇩🇪 Deutsch

Normalerweise verlassen die Bilder das Handy nie: es findet Gesichter, liest Text und erkennt Dinge selbst, und nur
Zahlen gehen an den PC. „Zeigen" ist die eine Ausnahme. Damit kann die Person am Handy jemandem am PC etwas **zeigen**:
einen Brief, eine Tablettendose, ein Foto. Gedacht ist es für ihre Assistenz, die aus dem Nebenzimmer hilft.

- **Nur wenn erlaubt:** jemand am PC schaltet es ein (die Einrichtungsseite, Omi Assist, „Ihr erlauben…", oder
  `./start.sh --show`). Sonst sagt die Kachel „Zeigen" nur, dass Zeigen nicht erlaubt ist.
- **Nur solange sie zeigt:** das Bild geht erst an den PC, wenn sie „Zeigen" drückt, höchstens eine Minute lang. Ein
  Tipp auf das rote Abzeichen oder noch einmal auf „Zeigen" beendet es. Am PC kann man es auch beenden.
- **Immer sichtbar:** solange es zeigt, steht oben auf dem Handy ein rotes **● ZEIGEN**, und sein Bildschirm zeigt, was
  die Kamera sieht: sie weiß, was gezeigt wird.
- **Wohin es geht:** ein kleines Bild (320 Pixel breit, zwei pro Sekunde) nur an die Einrichtungsseite auf diesem PC.
  Die Brücke behält das letzte drei Sekunden im Speicher; sie schreibt nichts auf die Festplatte, und nichts geht an
  ROS, an die Programme des Roboters oder ins Internet.
- **Wer entscheidet:** sie. Sprechen Sie es vorher mit ihr ab, und schalten Sie es aus, wenn sie es sagt.

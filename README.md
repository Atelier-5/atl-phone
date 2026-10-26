# atl-phone: an old phone as the robot's face, eyes and ears

🇬🇧 An old Android phone as a payload: it shows the face, sees faces, markers, colours, objects and hands, hears and speaks, over ROS 2. The brain stays on the PC.
🇫🇷 Un vieux téléphone Android comme charge utile : il montre le visage, voit visages, marqueurs, couleurs, objets et mains, entend et parle, via ROS 2. Le cerveau reste sur le PC.
🇩🇪 Ein altes Android-Handy als Nutzlast: es zeigt das Gesicht, sieht Gesichter, Marker, Farben, Gegenstände und Hände, hört und spricht, über ROS 2. Das Gehirn bleibt auf dem PC.

![The ten expressions](docs/faces.png)

The phone runs a web page, nothing to install; any phone whose browser is recent enough will do, whatever its
OS (stock Android, LineageOS, …). The ROS 2 node `atl_phone/bridge` serves the page and maps it to topics.

## Start here

```bash
./start.sh            # builds the image if needed, starts the bridge in Docker, opens the setup page
```

The **setup page** (`http://localhost:8782/setup.html`, on this PC only), in EN/FR/DE, starts with what to do:
**Connect and Test**, **Desk Guard** ([the Desk Guardian](#the-desk-guardian)), **Omi Assist** ([the helper on a
stand](#omi-assist)) or **How it works** (what the robot does, the phone on USB or Wi-Fi, where each part runs in the lab
and on the robot with its Pi, which recognition runs on the phone and which on the Pi, and a link to the architecture
docs, which the bridge serves at `/docs/`). Connect and Test guides through it:
the bridge → connecting the phone (USB, or Wi-Fi with a QR code) → the phone check → testing each output
(face, gaze, colour, voice, vibration, torch, camera: you say what you saw) and each sense (touch, motion, compass,
battery, reading a code, look, vision: they tick by themselves) → scenarios (try the portrait panel)
→ a summary to copy. Its tests go through ROS 2, on the contract's
topics; the camera test goes to the phone directly and its picture stays on the phone's screen. A phone on plain
http (Wi-Fi without `--cert`) shows its camera, motion, compass and battery as *blocked*: use USB, or HTTPS.

`./start.sh --robot thymio_1 --port 8782 --lang fr --key KEY` · `./start.sh --guardian [--familiar]` · `./start.sh --omi [--show] [--translate]` · `./start.sh logs` · `./start.sh stop`

**Wi-Fi with camera and motion:** `./start.sh --make-cert`. It makes this PC's own certificate authority once
(`certs/`, git-ignored; `scripts/make_cert.sh`) and the bridge's certificate for this PC's addresses, renewed when the
address changes. Each phone installs the authority once: the setup page's Wi-Fi tab has a QR code for `ca.crt` and the
steps. Then the bridge speaks only https, over USB too. The authority's key never leaves `certs/`.
Your own certificate instead: `--cert DIR` (`cert.pem`, `key.pem`, and `ca.crt` if the phones should get it).

## By hand

```bash
docker build -f docker/Dockerfile -t atl-phone:kilted .
docker run --rm --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp atl-phone:kilted   # the bridge, for thymio_1
docker run ... atl-phone:kilted ros2 launch atl_phone phone.launch.py robot:=thymio_1 \
    [port:=8782] [key:=...] [cert:=c.pem cert_key:=k.pem [ca:=ca.crt]] [lang:=fr] [familiar:=true] [guardian:=true] \
    [omi:=true] [omi_folder:=/omi] [show:=true] [reports:=/reports] \
    [translate:=true] [models:=/models] [guest_port:=8783 guest_cert:=c.pem guest_cert_key:=k.pem [guest_ca:=ca.crt]]
./scripts/usb.sh face.html                                       # USB: adb reverse, then opens the face on the phone
docker exec <container> /entrypoint.sh python3 -m atl_phone.contract_check     # the contract, with a mock phone: 65 checks, 66 with --wav (--wav: German speech for Übersetzen)
python3 scripts/browser_check.py --container <container> [--face <picture>] [--fake-adb A:C] [--speech <wav>]   # the pages in headless Chrome: 71 checks
    # (--fake-adb: a fake adb and phone Chrome on the ports the bridge got as ADB_SERVER_PORT, ATL_CDP_PORT; never the real phone)
./test.sh                                                        # protocol, WebSocket, check server, guardian, reminders: no ROS, no phone
./scripts/phone_tidy.sh [--kill] [--stay-on] [--close-tabs]      # what weighs on the phone (adb); changes only what you confirm
```

**How the phone connects.** Camera, microphone and motion need a *secure* page. Over **USB**, `adb reverse` makes the
bridge the phone's `localhost`, which counts as secure, and the cable charges the phone: the way to set up at the desk.
Over **Wi-Fi** the bridge needs HTTPS (`cert`, `cert_key`, `ca`): `./start.sh --make-cert`, with the authority installed once on each phone.
On the phone, tap ▶: full screen, landscape, the screen stays on (`face.html?layout=portrait`: upright, with the panel). A `key` pairs the bridge with its phones (`/?key=...`).
A bridge that restarts with new pages makes the phone load them: on each hello it sends their fingerprint, and a page
an older bridge served reloads itself, started without a tap (full screen and the voice come back with the next touch).
The setup page does the same. On the robot with its Pi (autonomous), the phone stays on USB, now the Pi's, and a PC
opens the setup page through an SSH tunnel (`ssh -L 8782:localhost:8782 pi@<robot>`), since it answers its own computer only.

## The contract: `atl-phone/0.7` (`atl_phone/contract.py`)

Under the robot that carries the phone, so `/thymio_1/phone/...`; the robot's own contract stays as it is.

| Topic under `/<robot>/phone/` | Type | Dir. | |
|---|---|---|---|
| `status` | String JSON | out | latched: contract, connected, model, caps, screen, look, familiar |
| `imu` | Imu | out | phone frame (x right, y up the screen, z out of it), m/s² with gravity, rad/s, no orientation; ≤ 60 Hz |
| `heading` | Float32 | out | degrees clockwise from magnetic north, when the phone has a compass |
| `touch` | String JSON | out | `{"kind": "tap"\|"long"\|"swipe", "zone": "left"\|"centre"\|"right", "dir"}` |
| `battery` | BatteryState | out | the phone's own battery, latched |
| `faces` | String JSON | out | while looking, up to 10 Hz: `{"n", "faces": [{"x", "y", "size", "familiar"}], "period"}`, largest first; x right and y up as the face sees it (-1..1), size = the face's height in the picture (0..1), familiar = `null` or the same number 1–8 for the same face this session; period = ms between two searches on this phone |
| `markers` | String JSON | out | while seeing them: `{"camera", "markers": [{"id", "x", "y", "size", "distance_m", "yaw_deg"}]}`: ArUco 4×4 markers (ids 0–999); the distance from their printed size |
| `blobs` | String JSON | out | `{"camera", "blobs": [{"x", "y", "size"}]}`: the largest patches of the asked colour |
| `objects` | String JSON | out | `{"camera", "objects": [{"label", "score", "x", "y", "w", "h", "distance_m"}]}`: COCO's 80 kinds (`cup`, `person`, `sports ball`, …); a distance only for kinds of known height |
| `hands` | String JSON | out | `{"camera", "hands": [{"x", "y", "gesture"}]}`: `none` `fist` `open_palm` `pointing_up` `thumbs_down` `thumbs_up` `victory` `love` |
| `panel/mode` | String | out | latched: the panel's mode, as a program set it or the person picked it in the menu |
| `codes` | String JSON | out | `{"text"}`: a QR code held up to the front camera while looking |
| `pad` | String JSON | out | `{"id"}`: a button of the panel's pad was pressed |
| `menu` | String JSON | out | `{"id"}`: the person picked a chip or a tile of the menu (a mode, one of the phone's tiles, or a program's own entry) |
| `note/answer` | String JSON | out | `{"note", "id"}`: the button pressed on a note card |
| `read/result` | String JSON | out | `{"ok", "lines", "chars", "ms"}`: the phone read the back camera's text aloud; the text itself stays on the phone |
| `what/result` | String JSON | out | `{"ok", "label", "score", "ms"}`: what the back camera saw nearest (a COCO label, or `null`), said aloud on the phone |
| `translate/result` | String JSON | out | `{"ok", "from", "to", "words", "seconds", "ms"}` (0.7): Übersetzen heard and translated what was said while a half was held; counts only, the words stay between the phone and the bridge |
| `face/expression` | String | in | `neutral` `happy` `sad` `angry` `surprised` `sleepy` `curious` `wink` `scared` `love` |
| `face/gaze` | Point | in | where the eyes look, x right and y up, each -1..1; left alone, they look around by themselves |
| `face/color` | ColorRGBA | in | the eyes' colour |
| `say` | String | in | text, or `{"text", "lang": "en"\|"fr"\|"de"}`; at most 200 characters |
| `torch` | Bool | in | the headlight; it needs the camera, and the face then shows **● cam** |
| `vibrate` | Int32 | in | milliseconds, at most 2000 |
| `look` | Bool | in | the front camera finds faces, on the phone; the face shows **● look** |
| `look/familiar` | Bool | in | also tell faces apart, this session only; only if the bridge allows it (`familiar:=true`, or the setup page) |
| `look/forget` | Empty | in | forget every face seen so far |
| `see` | String JSON | in | what one camera finds, on the phone: `{"camera": "front"\|"back", "find": ["faces", "markers", "blobs", "objects", "hands"], "blob": {"hue": 0–359, "tol"}, "marker_cm": 5, "fov_deg"}`; `"find": []` closes it; `"follow": true`: the eyes follow the nearest thing found; the face shows **● look** |
| `panel` | String JSON | in | in portrait, the panel under the eyes: `{"mode": "mouth"\|"pad"\|"off"\|"camera"\|"camera_back"\|"sensors"\|"magnify"\|"translate", "buttons": [{"id", "label", "color": [r, g, b]}], "style": "chips"\|"tiles", "menu": [...], "lang": "en"\|"fr"\|"de"\|"auto"}`, at most 8 buttons, labels ≤ 12 characters; `menu`: what a tap on the eyes offers, in order, at most 9: modes, the phone's own tiles (`time` `magnify` `read` `what` `front` `back` `show` `follow`) or a program's `{"id", "label": text or {"en", "fr", "de"}, "icon"}`; `lang`: the face's words and voice from now on, whatever the phone's language (`auto`: the phone's own again; the page's `?lang=` wins); a phone that comes gets the last one |
| `note` | String JSON | in | a big card over the face: `{"id", "text", "buttons": [{"id", "label"}], "say"}`, at most 3 buttons and 200 characters; `{"text": ""}` takes it away |
| `read` | String JSON | in | `{"lang"}` (or empty): read aloud what the back camera sees |
| `what` | String JSON | in | `{"lang"}` (or empty): say what the back camera sees nearest |

The phone is not trusted: what it sends is checked and clamped (`atl_phone/protocol.py`), and what it cannot do it skips.
One phone per bridge: a new one takes over and the old one is closed. A phone has one camera open at a time: the
torch and the camera test (back camera) win, and look (front camera) waits for them. With no phone connected, `see`,
`panel` and `note` are still taken and kept for the phone that comes (so a test left on can be turned off); the setup
page's other tests are refused with "no phone".

**The mirror** (`/ws/mirror`, from 0.6): a twin or a second screen can watch the phone without taking over. It
connects from this computer (or with the pairing key), says hello and then only listens: it gets a copy of what the
bridge sends the phone (face, gaze, colour, panel, say, note, tour), the phone's comings and goings, and the phone's
**`screen` reports**: what its screen shows, as ids only (`{"t": "screen", "mode", "expression", "menu", "tiles",
"hi", "toast", "arg", "note", "badge", "allowed", "sensors"}`; `sensors`: the sensors panel's numbers while it shows,
battery, compass and tilt, never the location). A toast is a key of the fixed texts (`web/texts.js`: `time`, `reading`,
`is` with an object's label, `tour.<step>`, …), never the words read aloud: the bridge refuses anything
else (`protocol.py`). No picture either, except while she shows one (Zeigen, allowed): then a mirror on the bridge's
own computer gets the frames too (`{"t": "frame", "jpeg"}`), as the setup page does; a mirror over Wi-Fi never. What a mirror sends besides hello is dropped. `/api/act {"prop": "cup"}` goes to the mirrors
only (the Webots twin's demo objects, below); `/api/state` says how many mirrors are connected.

**Portrait.** Held upright (`layout=portrait`, or `auto` as the phone is held; the setup page's Scenarios step
switches it), the eyes move to the top and the lower part becomes the robot's own input device:
- **Mouth** (the default): it follows the expression; while the robot speaks it becomes a scrolling sound wave, drawn
  from the words being spoken (the browser does not hand over the voice's sound, and the microphone stays off).
- **Buttons**: a pad (A–D until a program defines its own; each press is a `pad` message).
- **Eyes only**, **Front camera**, **Back camera**: the picture stays on the phone's screen (the face shows **● cam**).
- **Sensors**: six tiles drawn on the phone: battery, a tilt bubble, the compass, the link, vision, the last press.

A tap on the eyes shows the menu across the top of the panel for 6 s (its chips wrap on a narrow phone); a swipe
left or right steps to the next mode. With `"style": "tiles"` the menu is big tiles instead (see [Omi Assist](#omi-assist)).
Taps and swipes still go to ROS as `touch`. The phone tells the bridge what was picked (`panel/mode`). A program
changes the menu for its robot: `ros2 run atl_phone thymio_pad` (`atl_phone/thymio_pad.py`, a sample of some forty
lines) gives the pad the Thymio's five buttons ▲ ◀ ● ▶ ▼ and a menu without the cameras, and drives `cmd_vel` with them.
Landscape stays as it was: the eyes alone.

## Vision

One camera at a time finds what a program asks for on `see`, on the phone; only numbers leave it. The page runs
[MediaPipe Tasks Vision](https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector) (faces with BlazeFace,
objects with EfficientDet-Lite0, hands with the gesture recogniser; on the phone's GPU when it can) and
[js-aruco2](https://github.com/damianofalcioni/js-aruco2) for markers; colour blobs are its own code. Everything is in
`web/vendor/` (licences in its README) and served by the bridge: no internet needed, the models load when first asked.
- **Markers** carry an id and give a distance and an angle: print `markers.html?cm=5` (ids 0–9; the setup page links it)
  at 100 %, and tell `see` the black square's size (`marker_cm`). A camera's field of view differs between phones:
  `fov_deg` corrects the distances (65° when not said).
- **Colour**: `blob.hue` (0 red, 120 green, 240 blue) and a tolerance; the setup page has a colour picker.
- **Objects**: a label, a box, a score; a distance for a few kinds of known height (a person, a cup, a bottle…).
- **Hands**: where, and the gesture.

The setup page's **Vision** card picks the camera and the finders and shows what they find, live, with each finder's
time per picture; `check.html` times them on each phone, so its report says what the phone can afford. The Desk
Guardian's faces come from BlazeFace too, up to 10 searches a second, and a face that appears makes the eyes start at
once, before ROS answers; `faces` says how long a search takes, so the guardian keeps a face that long.

**Follow.** With `"follow": true` on `see`, the eyes look at the nearest thing found: a face, a hand, a marker, or an
object when objects are quick on this phone (under 400 ms). Nearness is the distance when it is known, else the
thing's size in the picture. The eyes hold what they follow: another one takes over only when it is 25 % nearer for
half a second, and a lost one is held a second. A `face/gaze` from a program still wins. When following is all the
camera does (faces, hands), the phone rests: a search every 0.25 s while the eyes hold something, every second while
nothing is in view; other finders keep the full pace (at most 10 a second). The `see` report says what
the eyes follow (`"target": {"kind", "x", "y"}`).

**Further, not built yet:** line following with the back camera turned down; depth from one picture (too heavy for an
A50); NFC tags read by Chrome (cards without a camera); geolocation; the ambient light sensor (behind a browser flag);
spoken keywords recognised on the phone (offline); BLE sensors over Web Bluetooth. Other apps on the phone: a web page
cannot drive them; over USB the PC can (adb), when the person allows it, or a small companion app later.

## The phone's Webots twin

The phone is a payload like any other: `webots/protos/AtlPhone.proto` (sizes from `webots/phones.json`: the ANE-LX1,
the A50, and a generic phone), standing in `AtlPhoneClamp.proto` on Omi Assist's stack, or on the placeholder block
`AtlPhoneHolder.proto` in a Thymio's body slot (the busy table below). Its controller (`webots/controllers/atl_phone_twin`) speaks the face page's protocol to the bridge, so the bridge
cannot tell it from a real phone and a program runs unchanged on both:
- its screen (a Display) shows the eyes, the panel's mouth, wave, pad or sensors; `say` speaks through Webots;
- `imu` and `heading` come from its motion on the robot; `torch` is a light;
- `see` and `look` use Webots' Recognition: a Solid whose `model` is `face` is a face, `aruco:<id>` a marker, a COCO
  label an object, and a `recognitionColors` within the asked hue a blob. Hands are not simulated.

`webots/payload.ttl` is its card for atl-ide's library (copy it into `mydocs/library/`): the phone, its holders, and
the phone as its own controller. `webots/omi_robot.ttl` is the whole Omi Assist robot (below).

```bash
docker build -f docker/Dockerfile.twin -t atl-phone-twin:kilted .            # on top of atl-phone:kilted
python3 scripts/phone_twin_world.py ~/atl/atl-ide/mydocs/twin --things        # webots/worlds/table_phone.wbt
/snap/bin/webots --port=1240 webots/worlds/table_phone.wbt
# then, together (three extern robots wait for each other): atl-bot-thymio's launch and the twin
docker run -d --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp -e WEBOTS_CONTROLLER_URL=tcp://127.0.0.1:1240/PH5v0001 \
    atl-phone-twin:kilted /entrypoint.sh python3 /ws/webots/controllers/atl_phone_twin/atl_phone_twin.py --bridge ws://127.0.0.1:8782/ws
python3 scripts/phone_twin_check.py --port 8782                               # 11 checks
```

The check reads only the bridge and the Thymio's gateway: the twin rides leaning back (gravity in its frame), faces
east, finds the marker within 2 cm of the world's geometry, the cup and the face on the left, the red ball on the
right, nothing with the back camera; and the Desk Guardian, unchanged, turns the Thymio to the face it sees through the
twin's camera.

### Omi Assist's robot: Thymio + Pi 4 + phone

🇬🇧 Omi Assist is one robot: a Thymio II, a Raspberry Pi 4 in its brick box on top, a brick riser and a phone clamp
in it, and the phone. The Pi runs the bridge, Omi Assist and the Thymio link; the phone and the Thymio are on its USB;
a PC opens only the setup page, over Wi-Fi. 🇫🇷 Omi Assist est un seul robot : un Thymio II, un Raspberry Pi 4 dans sa
boîte en briques dessus, une rehausse en briques avec un support de téléphone, et le téléphone. Le Pi fait tourner le
pont, Omi Assist et le lien avec le Thymio ; le téléphone et le Thymio sont sur son USB ; un PC n'ouvre que la page de
réglage, par le Wi-Fi. 🇩🇪 Omi Assist ist ein Roboter: ein Thymio II, ein Raspberry Pi 4 in seiner Box aus Steinen
darauf, ein Aufsatz aus Steinen mit einer Handyhalterung und das Handy. Der Pi führt die Brücke, Omi Assist und die
Verbindung zum Thymio aus; Handy und Thymio hängen an seinem USB; ein PC öffnet nur die Einstellseite, über WLAN.

- **The model** (`webots/protos/AtlOmiStack.proto`, in the Thymio2's body slot): the Pi's box (ATL's `atlrpi4`, 12×8
  studs, 8 plates, 80 g), a 4×6 riser of 6 plates, and `AtlPhoneClamp.proto`, a generic spring side clamp until the
  real one is measured (55–90 mm, 15° back, its arms below the phone's buttons, 60 g). Every part has its mass and is
  part of the Thymio's body, so the twin tips as the robot would: the phone's 145 g ride as a ballast at its centre.
- **The ontology** (`webots/omi_robot.ttl`, in atl-ide's vocabulary; `./test.sh` runs atl-ide's SHACL shapes on it):
  the mounting tree with the PROTO's numbers, the two USB cables, what runs on the Pi, the phone and the PC, and the
  constraints: about 0.55 kg with its centre of gravity about 9 cm up; **at most 0.12 m/s** (measured on the twin: it
  rocks from 0.14 m/s and falls over backwards at the Thymio's full 0.2 m/s; the guardian drives at 0.06 m/s at most);
  5 V 3 A for the Pi (a power bank on the robot changes the balance: try it on the twin first); the back camera's view
  free; phones 55–90 mm wide; the screen 12–25 cm above the table for someone sitting; privacy. Its new terms
  (`omi:Constraint`, `omi:runsOn`, …) are proposed for atl-ide's T-Box and live in this file until then.
- **An empty table** (`--scene omi`): the robot alone. Its demo objects wait under the table and **fly in** when
  called (the setup page's twin card, shown while a twin is connected: 🥤 cup · ✉️ letter · ✋ held · 🙂 visitor · away;
  or keys 1–4 and 0 in Webots): a cup behind the robot for "Was ist das?", a German letter on an easel behind it or held
  in a hand for "Vorlesen", a visitor in front for the greeting. As the phone, the twin reads the letter's text from
  `webots/letter.json` (`scripts/make_letter.py` draws it) and names the nearest object it recognises, marked
  `"backend": "webots"`.
- **Two modes:** `--bridge ws://…/ws` the twin is the phone (simulation only), and listens on the mirror for the
  props; `--mirror ws://…/ws/mirror` the real phone is in charge, and the twin's screen follows its `screen` reports
  (the tiles with the highlighted one in yellow, the toast at the top, the note card, the ZEIGEN badge, the sensors'
  numbers, the camera views' buttons, "…" while the phone is away). In the camera views it shows the real phone's
  picture only while she shows it (Zeigen), else a camera symbol; as the phone, its own Webots camera. `--snap FILE`
  saves its screen as a PNG every second. The twin sends nothing then; the words come from the same `web/texts.js`
  as the phone's. When the bridge restarts, the twin shows the phone away and joins the mirror again by itself.

```bash
python3 scripts/phone_twin_world.py ~/atl/atl-ide/mydocs/twin --scene omi     # webots/worlds/table_omi.wbt (+ .json)
/snap/bin/webots --port=1240 webots/worlds/table_omi.wbt
# atl-bot-thymio's launch with table:=webots/worlds/table_omi.json, and the twin as the phone (test bridge):
docker run -d --net=host --user "$(id -u):$(id -g)" -e HOME=/tmp -e WEBOTS_CONTROLLER_URL=tcp://127.0.0.1:1240/PH5v0001 \
    atl-phone-twin:kilted /entrypoint.sh python3 /ws/webots/controllers/atl_phone_twin/atl_phone_twin.py --bridge ws://127.0.0.1:8792/ws --model ANE-LX1
python3 scripts/omi_twin_check.py --port 8792                                 # 10 checks
# or beside the real phone: ... atl_phone_twin.py --mirror ws://127.0.0.1:8782/ws/mirror --model ANE-LX1
```

The check: the twin is the ANE-LX1 in its clamp, leaning back 15° (gravity in its frame); the table is empty for
both cameras; the cup is named; the letter is read on its easel and in a hand (its six lines); the visitor's face is
seen; "away" empties the table; and the robot stays on its wheels starting, stopping and turning as the guardian does.
It prints the full-speed tip as INFO.

## The Desk Guardian

🇬🇧 A robot that keeps watch over a desk, like Cozmo: sleepy while nobody is there, it looks around; a face wakes it
and it turns to it; the owner shows their card and becomes a friend; a stranger who comes too close for too long is
told off; lifted, it asks to be put down; at the desk's edge it backs off. 🇫🇷 Un robot qui garde un bureau, comme
Cozmo : endormi quand personne n'est là, il regarde autour de lui ; un visage le réveille et il se tourne vers lui ; le
propriétaire montre sa carte et devient un ami ; un inconnu qui s'approche trop longtemps se fait gronder ; soulevé,
il demande qu'on le repose ; au bord du bureau, il recule. 🇩🇪 Ein Roboter, der einen Schreibtisch bewacht, wie Cozmo:
schläfrig, solange niemand da ist, schaut er sich um; ein Gesicht weckt ihn und er dreht sich hin; der Besitzer zeigt
seine Karte und wird ein Freund; ein Fremder, der zu lange zu nah kommt, wird ausgeschimpft; hochgehoben, will er
wieder hingestellt werden; an der Tischkante weicht er zurück.

```bash
./start.sh [--familiar] [--lang fr]     # then the setup page's Desk Guard: ▶ Start (and whether it may drive the Thymio)
./start.sh --guardian                   # or started at once
```

The guardian runs beside the bridge, waiting: Start and Stop on the setup page publish `/<robot>/guardian/run` (and
`/<robot>/guardian/drive`), as any program could. Stopped, it stops the wheels and the front camera and puts the face back to neutral.

The guardian (`atl_phone/guardian.py`, plain Python; `guardian_node.py` wires it) knows only topics: the phone's
(`faces`, `codes`, `touch`, `imu` in; the face, `say`, `vibrate`, `look` out) and, when a Thymio answers on the same
ROS domain, `prox/ground` in and `cmd_vel`, `leds/top` out (atl-thymio/0.1). So one brain runs in every world:

| World | Phone | Body | Run |
|---|---|---|---|
| unit tests | invented inputs | invented | `./test.sh -k guardian` |
| the backend's test scenario | mock phone | fake Thymio (ground sensors, records `cmd_vel`) | `docker exec <container> /entrypoint.sh python3 -m atl_phone.guardian_check`: 13 steps, from guarding to petted |
| the twin | mock phone, or the real one | the Thymio twin in Webots (atl-ide's table, atl-bot-thymio's container) | `python3 scripts/guardian_twin_check.py`: the twin turns, stops, backs off |
| both twins | the phone's twin (its camera sees a face in Webots) | the Thymio twin | `python3 scripts/phone_twin_check.py`: the guardian turns to the face |
| the table | the real phone | a real Thymio (later: same topics) | `./start.sh`, then Start on the setup page |

The owner card is a QR code that says `atl-guardian:owner` (a token, no name): print it, or show it on a screen.
With `--familiar` the guardian knows the owner again by the face's number; without it, the owner stays a friend while
the face is in view and ten seconds after. `/<robot>/guardian/state` (String JSON, 5 Hz; `{"state": "off"}` once a second while stopped) says what it is doing; the setup page shows it.
The bridge and atl-bot-thymio's container must share the ROS domain; `start.sh` makes Fast DDS use UDP, because
containers do not share their memory.

## Omi Assist

🇬🇧 The phone on a fixed or movable stand as a helper for someone who sees or hears less well, or finds a phone's
menus tricky. A tap on its eyes opens big tiles that say their name: the time, the front and the back camera, a
magnifier, reading aloud, the sensors, eyes that follow. In the back camera, "what is this?"; in each camera view,
showing the picture to her assistant. The assistant's reminders come
at their time, as a big card she answers. 🇫🇷 Le téléphone sur un support, fixe ou mobile, comme assistant pour
quelqu'un qui voit ou entend moins bien, ou que les menus d'un téléphone embrouillent. Un toucher sur ses yeux ouvre de
grandes tuiles qui disent leur nom : l'heure, la caméra avant et arrière, une loupe, lire à voix haute, les capteurs,
des yeux qui suivent. Dans la caméra arrière, « qu'est-ce que c'est ? » ; dans chaque vue de caméra, montrer l'image à la
personne qui l'assiste. Ses rappels arrivent à leur heure, sur
une grande carte à laquelle elle répond. 🇩🇪 Das Handy auf einem festen oder beweglichen Ständer als Helfer für jemanden,
der schlechter sieht oder hört oder mit den Menüs eines Handys nicht zurechtkommt. Ein Tipp auf die Augen öffnet große
Kacheln, die ihren Namen sagen: die Uhrzeit, die vordere und die hintere Kamera, eine Lupe, Vorlesen, die Sensoren,
Augen, die folgen. In der hinteren Kamera „Was ist das?"; in jeder Kameraansicht der Assistenz das Bild zeigen. Die Erinnerungen der Assistenz kommen zu ihrer Zeit, als große Karte, die sie
beantwortet.

```bash
./start.sh --omi [--show]     # in German unless --lang says otherwise; then the setup page's Omi Assist (setup.html#omi)
./scripts/get_models.sh       # once, for Übersetzen: the offline speech and translation models into models/ (about 310 MB)
./start.sh --omi --translate  # Übersetzen allowed from the start (else the setup page's card allows it)
                              # and the guest page on https port 8783 for a second phone (--no-guest: not)
```

- **Tiles** (`face.js`): eight in three rows in the lower three quarters (seven, and **Gesicht** last, which goes back
  to the face from anything: reading, the magnifier, showing), an icon and one word, 18 px and more; a touch vibrates,
  says the tile's name and acts; they close after 10 s. The words and the voice are Omi's language (`lang`, German with
  `--omi`), even on a phone set to French.
- **The presentation:** the setup page's **🎤 Introduce Omi Assist** makes the phone say what it can, tile by tile, in
  about two minutes ("Hallo Omi! Ich bin Omi Assist, dein persönlicher Helfer …"); a tap ends it. Its script, and what
  happens on the phone and on the PC at each step: [docs/omi-presentation.md](docs/omi-presentation.md).
- **The helpers run on the phone** (`web/omi.js`): the time and the date from its clock; the **magnifier** (the back
  camera big in the panel, zoom with the camera's own zoom or a scale, the torch, hold; tap again for the whole screen);
  **reading** a still from the back camera with [Tesseract.js](https://github.com/naptha/tesseract.js) (German, English
  and French, in `web/vendor/tesseract/`), said sentence by sentence and written big, a tap stops it; **front** and
  **back** show that camera big on her screen, with buttons over the picture as the magnifier has: **❓ Was ist das?**
  on the back camera (one look of the object finder, said with its article: "Das ist eine Tasse.") and **📡 Zeigen**
  on every camera view when allowed; **Sensoren**: the battery, the tilt, the compass, the location (asked only while
  the panel shows, and kept on its screen: never sent), the link, the camera, the last press. With tiles, what she picks wins the camera over the eyes' following, which waits meanwhile.
- **Omi Assist** (`atl_phone/omi_assist.py`, beside the bridge, waiting like the guardian) sets the tiles and the eyes'
  following (faces only, the lightest), greets a face that comes after five minutes alone, and brings the reminders (`atl_phone/omi.py`): a text,
  a time, the days (none: every day). At their time it says them and shows a card with **Erledigt** and **Später**
  (ten minutes later). The setup page edits them; they are kept in `omi/reminders.json` and the answers in
  `omi/answers.jsonl` (git-ignored). Stopped, it puts the chips back. Starting it stops the Desk Guardian, and the
  other way round: they share the face.
- **Übersetzen** (0.7, `web/talk.js`, `atl_phone/translate.py`), for a family that speaks German and French: the tile
  opens two halves, **🇩🇪 Deutsch** and **🇫🇷 Français**. Hold one and speak; let go, and the phone shows what it heard
  small on that half, the translation big on the other, and says it in the other language's voice. The phone sends its
  sound (16 kHz, 250 ms chunks) only while a half is held, with a red **● HÖRT ZU** badge; the bridge hears it with
  [Vosk](https://alphacephei.com/vosk/) (small German and French models) and translates it with Opus-MT in
  [CTranslate2](https://github.com/OpenNMT/CTranslate2), offline, on its own computer, and drops the sound. Vosk gives
  no punctuation, so the words are cut into sentences at pauses before translating. The tile is there only when the
  facilitator allowed it (`--translate`, or the setup page's **Übersetzen** card, which also shows whether the models are
  there and how long the last one took, never its words). The models: `./scripts/get_models.sh` (the speech models
  checked against their sha256, the translation models at a pinned revision, converted in a throwaway container;
  `models/README.md` lists their licences, all Apache-2.0); `start.sh` mounts `models/` read-only. Measured on this PC
  in the container: the text is ready 0.04 s after letting go (it is heard while she speaks), the translation 0.15–0.4 s
  later; the four models take about 555 MB. See [Privacy](#privacy).
- **A second phone** (`web/talk.html`, `web/guest.js`): in the Übersetzen mode the robot's phone shows a QR code where
  the eyes are; a phone on the home Wi-Fi that scans it opens the guest page on the bridge's own https port (8783,
  tests 8793, the certificate `start.sh` makes in `certs/`: Chrome warns the first time, the page says to tap Advanced,
  then Proceed; `/ca.crt` is there to install). That port serves only the guest page and `/ws/talk?k=CODE`; the code
  (in the QR code, compared with `hmac.compare_digest`) is new each time Übersetzen is allowed, or with the setup
  page's **New guest code**, which drops the guest. One guest at a time: a new one takes over. Both phones show what
  either says; the other phone, the listener's, says the translation aloud, and the speaker's only shows it. When the guest
  is there, the QR code gives way to "📱 a second phone is with us"; when it goes, the QR code comes back. The link
  and the words go to the two phones only, never to a mirror or ROS.
- **Showing the picture** is the one exception to "pictures stay on the phone", and only when allowed: see
  [Privacy](#privacy).
- **A lighter phone.** The face installs as its own app window (`manifest.webmanifest`, `sw.js`, which keeps
  nothing): in Chrome, ⋮ › Install app, over USB or HTTPS. It then opens full screen without the tabs.
  `./scripts/phone_tidy.sh` shows what weighs on the phone (free memory, the load, the busiest apps, the Chrome tab
  count, the battery's temperature) and, each only on a typed y: `--kill` stops background apps (`am kill-all`, no
  data lost), `--stay-on` keeps the screen on while on USB, `--close-tabs` closes Chrome tabs other than the bridge's,
  one by one. The setup page's Omi Assist view has the same as a card, **A lighter phone**: look at the phone, stop
  background apps (it asks first), screen on or sleeping, and the Chrome tabs other than the face, listed unticked, to
  tick and close (it asks first; the face's own tab is never offered, nor closed). The bridge does it for this PC only
  (`/api/act {"phone": "look"|"kill"|"stay_on"|"stay_off"|"tabs"|"close"}`, `phone_health.py`), through the adb server
  already running on the computer, in adb's own protocol, so no second adb (of another version) kills the phone's
  link; the tab titles go to the setup page only, nothing else of the tabs. The check page's **Headroom** says memory,
  cores and how busy the phone is.

Measured on the ANE-LX1 over USB (2026-10-25): the nine tiles fit its 360×730 screen (105×168 px each, every word whole);
the eyes' following searches every 0.33–0.37 s (faces 85 ms, hands 212 ms, on the GPU); the time is spoken 0.33 s after
the tap (1.0 s for the first words after a reload); reading takes 2.7 s and "what is this?" 2.6 s (10.8 s and 7.6 s the
first time, while their models load). Its load average was about 40 with 45 Chrome tabs open: the app window and
`phone_tidy.sh` are for that. The Webots twin follows the phone's screen as a mirror, or plays the helpers itself
(simulated: [Omi Assist's robot](#omi-assists-robot-thymio--pi-4--phone)).

## The phone check, and the phones tested

Which phones in the drawer qualify? Open `check.html` on each phone (USB or HTTPS) and tap **Test everything**: when
the tests are done the report goes to the PC by itself, and 3 s later the phone opens the face, turned as it is held
(`face.html?layout=auto`; **Stay here** keeps the check). **Send report to the PC** sends it again.

Every phone tested is kept on the PC, in `reports/` (git-ignored; `atl_phone/registry.py`), by the bridge (`./start.sh`
mounts it) or by `python3 scripts/serve.py` (the check alone):
- `reports/phones.md`: one row per model: Android, Chrome, screen, GPU, the check's verdict, what failed in the setup;
- `reports/phones.json`: the same, with more details; its `notes` are yours to write, and they are kept;
- `reports/<model>/<day>-check.json`: the whole check report; `<day>-summary.txt`: the setup page's summary, saved
  when you reach step 6 (or with **Save on the PC**). Checked again the same day, a phone replaces that day's file.

What is kept is what a phone says about itself: no pictures, no names. The check's **Headroom** (memory, cores, how
busy the main thread is) goes into it too.

## Privacy

Camera and microphone open only when asked (the torch, the check's tests, look, see, the panel's picture, Omi's helpers) and the face shows when a camera is on
(**● cam**, **● look**). Nothing is recorded; pictures and sound do not leave the phone: what leaves it is whether a
camera works, the codes it read, and where faces, markers, colours, objects and hands are. The microphone is never
used for the mouth's wave.
**Faces.** Look finds faces on the phone (`web/vendor/face-api`, run in the page). It never says who someone is.
With **familiar**, the phone also keeps a signature of each face (128 numbers) in the page's memory, only to give the
same face the same number: never sent, never stored, forgotten on reload, when look or familiar ends, on
`look/forget`, and ten minutes after a face was last seen. A program cannot turn it on alone: the facilitator allows it
(`--familiar`, or the setup page), after asking the people at the table and the parents: [consent note](docs/consent-familiar.md).
While it is not allowed, the bridge strips the numbers, whatever a phone sends.
**Reading and "what is this?"** run on the phone: the text read and the thing seen are said and written on its
screen; ROS gets only how many lines and characters, or a label.
**Showing (Omi Assist, opt-in).** The one exception: the person may show the camera's picture to the PC, so her assistant
can help from the next room. Only when the facilitator allows it (`--show`, or the setup page), only while she presses
**Zeigen** (show), at most a minute, with a red **● ZEIGEN** badge on the face; a tap stops it. The frames (320 px, two
a second) go to the setup page (`/api/show.jpg`) and the Webots twin's mirror, both on the bridge's own computer only:
the bridge keeps the last one three seconds in memory, writes nothing, and puts nothing on a ROS topic. (With the bridge
on Omi's Raspberry Pi, a PC over Wi-Fi gets no pictures yet.) Agree on it with her first: [consent note](docs/consent-show.md).
**Übersetzen (Omi Assist, opt-in)** is the one exception for sound: only when the facilitator allows it (`--translate`,
or the setup page), only while a half is held (at most 30 s), with a red **● HÖRT ZU** badge, and only over a link that
is this computer (USB) or https: the bridge refuses it otherwise. A second phone joins only with the code in the QR
code on the robot's phone, over https, with the same rules. The sound goes to the bridge's own computer, is heard
and translated there offline and dropped; the words go back to the phone alone, never to a mirror, a ROS topic, a
file, the log or the setup page; ROS gets counts. Agree on it with the people at the table first:
[consent note](docs/consent-translate.md).
The browser's own speech recognition is not used: it sends voices to the cloud.

License: GPL-3.0-or-later. The name "Atelier-5" and its logos are reserved for modified versions (GPLv3 §7(e),
see [atl-hub/TRADEMARKS.md](https://github.com/Atelier-5/atl-hub/blob/main/TRADEMARKS.md)). What else it ships, fetches
and runs on, and their licences: [NOTICE.md](NOTICE.md).

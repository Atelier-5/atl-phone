# atl-phone: an old phone as the robot's face, eyes and ears

🇬🇧 An old Android phone as a payload: it shows the face, sees cards, hears and speaks, over ROS 2. The brain stays on the PC.
🇫🇷 Un vieux téléphone Android comme charge utile : il montre le visage, lit les cartes, entend et parle, via ROS 2. Le cerveau reste sur le PC.
🇩🇪 Ein altes Android-Handy als Nutzlast: es zeigt das Gesicht, liest Karten, hört und spricht, über ROS 2. Das Gehirn bleibt auf dem PC.

![The ten expressions](docs/faces.png)

The phone runs a web page, nothing to install; any phone whose browser is recent enough will do, whatever its
OS (stock Android, LineageOS, …). The ROS 2 node `atl_phone/bridge` serves the page and maps it to topics.

## Start here

```bash
./start.sh            # builds the image if needed, starts the bridge in Docker, opens the setup page
```

The **setup page** (`http://localhost:8782/setup.html`, on this PC only) guides through it, in EN/FR/DE:
the bridge → connecting the phone (USB, or Wi-Fi with a QR code) → the phone check → testing each output
(face, gaze, colour, voice, vibration, torch, camera: you say what you saw) and each sense (touch, motion, compass,
battery, reading a code, look: they tick by themselves) → a summary to copy. Its tests go through ROS 2, on the contract's
topics; the camera test goes to the phone directly and its picture stays on the phone's screen. A phone on plain
http (Wi-Fi without `--cert`) shows its camera, motion, compass and battery as *blocked*: use USB, or HTTPS.

`./start.sh --robot thymio_1 --port 8782 --lang fr --key KEY` · `./start.sh --guardian [--familiar]` · `./start.sh logs` · `./start.sh stop`

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
    [port:=8782] [key:=...] [cert:=c.pem cert_key:=k.pem [ca:=ca.crt]] [lang:=fr] [familiar:=true] [guardian:=true]
./scripts/usb.sh face.html                                       # USB: adb reverse, then opens the face on the phone
docker exec <container> /entrypoint.sh python3 -m atl_phone.contract_check     # the contract, with a mock phone: 24 checks
python3 scripts/browser_check.py --container <container> [--face <picture>]   # the face page in headless Chrome: 9 checks (12 with a face)
./test.sh                                                        # protocol, WebSocket, check server, guardian: no ROS, no phone
```

**How the phone connects.** Camera, microphone and motion need a *secure* page. Over **USB**, `adb reverse` makes the
bridge the phone's `localhost`, which counts as secure, and the cable charges the phone: the way to set up at the desk.
Over **Wi-Fi** the bridge needs HTTPS (`cert`, `cert_key`, `ca`): `./start.sh --make-cert`, with the authority installed once on each phone.
On the phone, tap ▶: full screen, landscape, the screen stays on. A `key` pairs the bridge with its phones (`/?key=...`).

## The contract: `atl-phone/0.2` (`atl_phone/contract.py`)

Under the robot that carries the phone, so `/thymio_1/phone/...`; the robot's own contract stays as it is.

| Topic under `/<robot>/phone/` | Type | Dir. | |
|---|---|---|---|
| `status` | String JSON | out | latched: contract, connected, model, caps, screen, look, familiar |
| `imu` | Imu | out | phone frame (x right, y up the screen, z out of it), m/s² with gravity, rad/s, no orientation; ≤ 60 Hz |
| `heading` | Float32 | out | degrees clockwise from magnetic north, when the phone has a compass |
| `touch` | String JSON | out | `{"kind": "tap"\|"long"\|"swipe", "zone": "left"\|"centre"\|"right", "dir"}` |
| `battery` | BatteryState | out | the phone's own battery, latched |
| `faces` | String JSON | out | while looking, about 4 Hz: `{"n", "faces": [{"x", "y", "size", "familiar"}]}`, largest first; x right and y up as the face sees it (-1..1), size = the face's height in the picture (0..1), familiar = `null` or the same number 1–8 for the same face this session |
| `codes` | String JSON | out | `{"text"}`: a QR code held up to the front camera while looking |
| `face/expression` | String | in | `neutral` `happy` `sad` `angry` `surprised` `sleepy` `curious` `wink` `scared` `love` |
| `face/gaze` | Point | in | where the eyes look, x right and y up, each -1..1; left alone, they look around by themselves |
| `face/color` | ColorRGBA | in | the eyes' colour |
| `say` | String | in | text, or `{"text", "lang": "en"\|"fr"\|"de"}`; at most 200 characters |
| `torch` | Bool | in | the headlight; it needs the camera, and the face then shows **● cam** |
| `vibrate` | Int32 | in | milliseconds, at most 2000 |
| `look` | Bool | in | the front camera finds faces, on the phone; the face shows **● look** |
| `look/familiar` | Bool | in | also tell faces apart, this session only; only if the bridge allows it (`familiar:=true`, or the setup page) |
| `look/forget` | Empty | in | forget every face seen so far |

The phone is not trusted: what it sends is checked and clamped (`atl_phone/protocol.py`), and what it cannot do it skips.
One phone per bridge: a new one takes over and the old one is closed. A phone has one camera open at a time: the
torch and the camera test (back camera) win, and look (front camera) waits for them.

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
./start.sh --guardian [--familiar] [--lang fr]     # the bridge and the guardian; the phone over USB (./scripts/usb.sh)
```

The guardian (`atl_phone/guardian.py`, plain Python; `guardian_node.py` wires it) knows only topics: the phone's
(`faces`, `codes`, `touch`, `imu` in; the face, `say`, `vibrate`, `look` out) and, when a Thymio answers on the same
ROS domain, `prox/ground` in and `cmd_vel`, `leds/top` out (atl-thymio/0.1). So one brain runs in three worlds:

| World | Phone | Body | Run |
|---|---|---|---|
| unit tests | invented inputs | invented | `./test.sh -k guardian` |
| the backend's test scenario | mock phone | fake Thymio (ground sensors, records `cmd_vel`) | `docker exec <container> /entrypoint.sh python3 -m atl_phone.guardian_check`: 13 steps, from guarding to petted |
| the twin | mock phone, or the real one | the Thymio twin in Webots (atl-ide's table, atl-bot-thymio's container) | `python3 scripts/guardian_twin_check.py`: the twin turns, stops, backs off |
| the table | the real phone | a real Thymio (later: same topics) | `./start.sh --guardian` |

The owner card is a QR code that says `atl-guardian:owner` (a token, no name): print it, or show it on a screen.
With `--familiar` the guardian knows the owner again by the face's number; without it, the owner stays a friend while
the face is in view and ten seconds after. `/<robot>/guardian/state` (String JSON, 5 Hz) says what it is doing.
The bridge and atl-bot-thymio's container must share the ROS domain; `start.sh` makes Fast DDS use UDP, because
containers do not share their memory.

## The phone check

Which phones in the drawer qualify? `python3 scripts/serve.py`, open `check.html` on each phone (USB or HTTPS),
tap **Test everything**, then **Send report to the PC**: one line per phone in the terminal, the report in `reports/`.

## Privacy

Camera and microphone open only when asked (the torch, the check's tests, look) and the face shows when a camera is on
(**● cam**, **● look**). Nothing is recorded; pictures and sound do not leave the phone: what leaves it is whether a
camera works, the codes it read, and where faces are.
**Faces.** Look finds faces on the phone (`web/vendor/face-api`, run in the page). It never says who someone is.
With **familiar**, the phone also keeps a signature of each face (128 numbers) in the page's memory, only to give the
same face the same number: never sent, never stored, forgotten on reload, when look or familiar ends, on
`look/forget`, and ten minutes after a face was last seen. A program cannot turn it on alone: the facilitator allows it
(`--familiar`, or the setup page), after asking the people at the table and the parents: [consent note](docs/consent-familiar.md).
While it is not allowed, the bridge strips the numbers, whatever a phone sends.
The browser's own speech recognition is not used: it sends voices to the cloud.

License: GPL-3.0-or-later.

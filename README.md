# atl-phone: an old phone as the robot's face, eyes and ears

🇬🇧 An old Android phone as a payload: it shows the face, sees cards, hears and speaks, over ROS 2. The brain stays on the PC.
🇫🇷 Un vieux téléphone Android comme charge utile : il montre le visage, lit les cartes, entend et parle, via ROS 2. Le cerveau reste sur le PC.
🇩🇪 Ein altes Android-Handy als Nutzlast: es zeigt das Gesicht, liest Karten, hört und spricht, über ROS 2. Das Gehirn bleibt auf dem PC.

The phone runs a web page, nothing to install. Step 0 is the **phone check**: which phones in the drawer qualify?

```bash
python3 scripts/serve.py                 # serves web/ on :8782, keeps the reports in reports/
./scripts/usb.sh                         # USB: adb reverse + opens the check on the phone (localhost = secure page)
python3 scripts/serve.py --cert c.pem --key k.pem    # Wi-Fi: HTTPS, or camera and microphone stay blocked
./test.sh                                # the tests: no ROS, no phone
```

On the phone: **Test everything**, allow camera, microphone and motion, then **Send report to the PC**.
The terminal prints one line per phone, e.g. `SM-G950F: 21 yes, 3 no; core complete`.

Privacy: the check page keeps nothing; camera and microphone are opened only while their test runs, and the
report holds capabilities only, no pictures, no sound.

License: GPL-3.0-or-later.

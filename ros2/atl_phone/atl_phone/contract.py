# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""contract.py — the phone payload's interface: the topics every phone (real, or later its Webots twin) offers.

The phone is a peripheral: it shows the face, senses and speaks; the robot's
brain runs elsewhere and only sees these topics. They live under the robot
that carries the phone, /<robot>/phone/..., so a robot with a phone keeps its
own contract and gains these. Bump CONTRACT when a topic changes.
"""

CONTRACT = "atl-phone/0.5"         # 0.2: the front camera (look), faces, codes; 0.3: the panel and its pad (portrait);
                                   # 0.4: vision (see: markers, blobs, objects, hands), the panel's menu and its mode;
                                   # 0.5: tiles (the spoken menu) and their picks, notes, read, what, follow (Omi Assist)
PORT = 8782                 # the bridge's page and WebSocket (atl-ide 8780, the Thymio gateway 8781)


def topics(robot: str) -> dict:
    ns = f"/{robot}/phone"
    return {
        # out: published by the phone (through the bridge)
        "status": f"{ns}/status",           # std_msgs/String JSON {"contract", "connected", "model", "caps", "screen"}, latched
        "imu": f"{ns}/imu",                 # sensor_msgs/Imu, phone frame (x right, y up the screen, z out of it), m/s2 with gravity, rad/s; no orientation
        "heading": f"{ns}/heading",         # std_msgs/Float32, degrees clockwise from magnetic north (compass), when the phone has one
        "touch": f"{ns}/touch",             # std_msgs/String JSON {"kind": "tap"|"long"|"swipe", "zone": "left"|"centre"|"right", "dir"?}
        "battery": f"{ns}/battery",         # sensor_msgs/BatteryState: the phone's own battery
        "faces": f"{ns}/faces",             # std_msgs/String JSON {"n", "faces": [{"x", "y", "size", "familiar"}]}, while looking (about 4 Hz):
                                            #   x right, y up, each -1..1 as the face sees it; size: the face's height / the picture's;
                                            #   familiar: null, or 1..MAX_FACES, the same number for the same face this session (opt-in)
        "codes": f"{ns}/codes",             # std_msgs/String JSON {"text"}: a code (QR, ...) the front camera read while looking
        "pad": f"{ns}/pad",                 # std_msgs/String JSON {"id"}: a button of the panel's pad was pressed
        "panel_mode": f"{ns}/panel/mode",   # std_msgs/String, latched: what the panel shows now (a program set it, or the person picked it)
        # vision (see): numbers only, at most MAX_ITEMS each; x right, y up, -1..1 in the picture (the front camera's mirrored,
        # as the face sees it); size: the thing's height / the picture's
        "markers": f"{ns}/markers",         # std_msgs/String JSON {"camera", "markers": [{"id", "x", "y", "size", "distance_m", "yaw_deg"}]}: ArUco 4x4
        "blobs": f"{ns}/blobs",             # std_msgs/String JSON {"camera", "blobs": [{"x", "y", "size"}]}: areas of the asked colour, largest first
        "objects": f"{ns}/objects",         # std_msgs/String JSON {"camera", "objects": [{"label", "score", "x", "y", "w", "h", "distance_m"}]}: OBJECTS
        "hands": f"{ns}/hands",             # std_msgs/String JSON {"camera", "hands": [{"x", "y", "gesture"}]}: GESTURES
        "menu": f"{ns}/menu",               # std_msgs/String JSON {"id"}: the person picked a tile or a chip of the menu (a mode or TILES)
        "note_answer": f"{ns}/note/answer", # std_msgs/String JSON {"note", "id"}: the button pressed on a note card
        "read_result": f"{ns}/read/result", # std_msgs/String JSON {"ok", "lines", "chars", "ms", "error"?}: the phone read and spoke it; the text stays on the phone
        "what_result": f"{ns}/what/result", # std_msgs/String JSON {"ok", "label", "score", "ms"}: what the back camera saw nearest (OBJECTS), and said
        # in: listened to by the phone
        "expression": f"{ns}/face/expression",  # std_msgs/String, one of EXPRESSIONS
        "gaze": f"{ns}/face/gaze",          # geometry_msgs/Point, x right, y up, each -1..1 (z unused)
        "color": f"{ns}/face/color",        # std_msgs/ColorRGBA 0..1: the eyes' colour
        "say": f"{ns}/say",                 # std_msgs/String: text, or JSON {"text", "lang": "en"|"fr"|"de"}
        "torch": f"{ns}/torch",             # std_msgs/Bool: the headlight (it opens the camera, and the face shows it)
        "vibrate": f"{ns}/vibrate",         # std_msgs/Int32: milliseconds, at most MAX_VIBRATE
        "look": f"{ns}/look",               # std_msgs/Bool: the front camera finds faces (on the phone; pictures never leave it)
        "familiar": f"{ns}/look/familiar",  # std_msgs/Bool: also tell faces apart this session; only if the bridge allows it (familiar:=true)
        "forget": f"{ns}/look/forget",      # std_msgs/Empty: forget every face seen so far
        "panel": f"{ns}/panel",             # std_msgs/String JSON {"mode": PANEL_MODES, "buttons": [{"id", "label", "color": [r, g, b] 0..1}],
                                            #   "menu": [PANEL_MODES]}: the lower half of the face in portrait; the buttons are the pad's (at
                                            #   most MAX_BUTTONS); menu: the modes a tap on the eyes offers, in order
        "see": f"{ns}/see",                 # std_msgs/String JSON {"camera": "front"|"back", "find": [FINDERS], "blob": {"hue", "tol"},
                                            #   "marker_cm", "fov_deg", "follow"}: what to find, on which camera; {"find": []} stops;
                                            #   follow: the eyes follow the nearest thing found (faces, hands, markers, quick objects)
        "note": f"{ns}/note",               # std_msgs/String JSON {"id", "text", "buttons": [{"id", "label"}], "say"}: a big card over the
                                            #   face (a reminder), at most MAX_NOTE_BUTTONS; {"text": ""} takes it away
        "read": f"{ns}/read",               # std_msgs/String JSON {"lang"}: read aloud what the back camera sees (text, on the phone)
        "what": f"{ns}/what",               # std_msgs/String JSON {"lang"}: say what the back camera sees nearest
    }


EXPRESSIONS = ("neutral", "happy", "sad", "angry", "surprised", "sleepy", "curious", "wink", "scared", "love")
LANGS = ("en", "fr", "de")
MAX_SAY = 200               # characters
MAX_VIBRATE = 2000          # ms
MAX_IMU_RATE = 60.0         # Hz: faster messages from a phone are dropped
MAX_FACES = 8               # faces per message, and faces told apart in a session
MAX_FACES_RATE = 10.0       # Hz
PANEL_MODES = ("mouth", "pad", "off", "camera", "camera_back", "sensors", "magnify")  # camera(_back), magnify: the picture, on the phone's screen only
PANEL_STYLES = ("chips", "tiles")   # the menu a tap on the eyes opens: a strip of chips, or big tiles that say their name
TILES = ("time", "magnify", "read", "what", "front", "back", "show", "follow")   # what a tile does, besides a mode
MAX_MENU = 9                # entries of the menu
MAX_NOTE_BUTTONS = 3
OMI_MENU = ["time", "front", "back", "magnify", "read", "what", "follow", "show"]   # Omi Assist's tiles
MAX_BUTTONS = 8
DEFAULT_PANEL = {"mode": "mouth", "buttons": [{"id": "a", "label": "A", "color": [0.25, 0.85, 1.0]},
                                            {"id": "b", "label": "B", "color": [0.2, 1.0, 0.4]},
                                            {"id": "c", "label": "C", "color": [1.0, 0.8, 0.2]},
                                            {"id": "d", "label": "D", "color": [1.0, 0.4, 0.7]}]}
THYMIO_PAD = [{"id": "forward", "label": "▲", "color": [1.0, 0.3, 0.3]}, {"id": "left", "label": "◀", "color": [1.0, 0.3, 0.3]},
              {"id": "centre", "label": "●", "color": [1.0, 0.3, 0.3]}, {"id": "right", "label": "▶", "color": [1.0, 0.3, 0.3]},
              {"id": "backward", "label": "▼", "color": [1.0, 0.3, 0.3]}]   # like the Thymio's own five buttons

FINDERS = ("faces", "markers", "blobs", "objects", "hands")
CAMERAS = ("front", "back")
MAX_ITEMS = 8               # markers, blobs, objects, hands per message
MAX_SEE_RATE = 15.0         # Hz, per kind
GESTURES = ("none", "fist", "open_palm", "pointing_up", "thumbs_down", "thumbs_up", "victory", "love")
OBJECTS = ("person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
           "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant",
           "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
           "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
           "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
           "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table", "toilet",
           "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
           "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush")   # COCO, as the model names them

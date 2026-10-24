# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""guardian — the Desk Guardian: a robot that keeps watch over a desk, as Cozmo would. Plain Python, no ROS.

The phone is its face, eyes and ears (contract atl-phone); a Thymio, when there is
one, its body (atl-thymio). guardian_node.py wires this class to their topics, so
the same guardian runs against a scripted test (mock phone, fake Thymio), the
real phone on the Thymio twin in Webots, and later a real Thymio.

    guarding  nobody there: sleepy eyes, slow look-around turns
    alert     a face it does not know: surprised, turns to it, asks who is there
    friend    the owner: a face shown together with the owner card, then known by its number (familiar)
    intruder  a stranger close for INTRUDER_AFTER s: angry, red, buzz, backs off a little
    scared    lifted (the phone's IMU, or the Thymio's ground sensors over nothing): stops, asks to be put down
    edge      one ground sensor over the desk's edge: backs off and turns away (Cozmo's cliff sense)
    petted    a long touch: love, a purr of vibration

Without "familiar" (the facilitator's choice), the owner stays a friend while a face
is in view, and for FRIEND_GRACE s after.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

OWNER_CARD = "atl-guardian:owner"   # the code on the owner card: a token, no name
CLOSE = 0.35                # a face taller than this part of the picture is close
INTRUDER_AFTER = 5.0        # s a stranger may stay close
LOST_AFTER = 30.0           # s without a face: back to guarding
FRIEND_GRACE = 10.0         # s a friend stays one after the face is gone (without familiar)
PETTED_FOR = 3.0            # s
EDGE_BACK = 1.2             # s backing off from the edge, at EDGE_SPEED (about 7 cm, as atl-bot-thymio's Explorer)
EDGE_TURN = 1.0             # s turning away from it after
EDGE_SPEED = 0.06           # m/s
GROUND_EMPTY = 120.0        # Thymio ground sensor: below this, no desk under it (atl-bot-thymio behaviours.py)
G = 9.81
TURN_GAIN = 1.5             # rad/s per unit of face x
MAX_TURN = 1.2              # rad/s

COLOURS = {"guarding": (0.25, 0.85, 1.0), "alert": (1.0, 0.8, 0.2), "friend": (0.2, 1.0, 0.4), "intruder": (1.0, 0.1, 0.1),
           "scared": (0.7, 0.5, 1.0), "edge": (1.0, 0.8, 0.2), "petted": (1.0, 0.4, 0.7)}
FACES = {"guarding": "sleepy", "alert": "surprised", "friend": "happy", "intruder": "angry", "scared": "scared",
         "edge": "surprised", "petted": "love"}
SAY = {
    "en": {"alert": "Who's there?", "known": "Back again? Show me your card.", "friend": "Hello again! I kept your desk safe.",
           "owner": "Hello, boss! I will remember you.", "intruder": "This is not your desk!", "scared": "Put me down!",
           "edge": "Whoa, the edge!", "petted": "Purr..."},
    "fr": {"alert": "Qui est là ?", "known": "Encore toi ? Montre-moi ta carte.", "friend": "Re-bonjour ! J'ai bien gardé ton bureau.",
           "owner": "Bonjour, chef ! Je vais me souvenir de toi.", "intruder": "Ce n'est pas ton bureau !", "scared": "Repose-moi !",
           "edge": "Oh là, le bord !", "petted": "Rrrr..."},
    "de": {"alert": "Wer ist da?", "known": "Schon wieder du? Zeig mir deine Karte.", "friend": "Da bist du ja wieder! Ich habe deinen Tisch bewacht.",
           "owner": "Hallo, Chef! Ich merke mir dich.", "intruder": "Das ist nicht dein Tisch!", "scared": "Stell mich wieder hin!",
           "edge": "Hoppla, die Kante!", "petted": "Schnurr..."},
}


@dataclass
class Sensors:
    faces: List[dict] = field(default_factory=list)      # the latest faces message's faces, largest first
    faces_age: float = math.inf                          # s since that message
    acc: Tuple[float, float, float] = (0.0, 0.0, G)      # the phone's IMU, m/s2 with gravity
    gyro: Tuple[float, float, float] = (0.0, 0.0, 0.0)   # rad/s
    ground: Optional[List[float]] = None                 # the Thymio's ground sensors [left, right]; None: no Thymio


@dataclass
class Events:
    touches: List[dict] = field(default_factory=list)    # touch messages since the last step
    codes: List[str] = field(default_factory=list)       # codes read since the last step


@dataclass
class Output:
    state: str = "guarding"
    expression: str = "sleepy"
    colour: Tuple[float, float, float] = COLOURS["guarding"]
    gaze: Optional[Tuple[float, float]] = None           # None: the face looks by itself (at the largest face, or around)
    say: Optional[str] = None                            # said once, when it changes state
    vibrate: int = 0                                     # ms, once
    linear: float = 0.0                                  # m/s, for the Thymio
    angular: float = 0.0                                 # rad/s, + = to the left
    doing: str = ""


def lifted(s: Sensors) -> bool:
    """Picked up or shaken: far from 1 g, or turning fast (the phone), or nothing under either ground sensor."""
    a = math.sqrt(sum(v * v for v in s.acc))
    if abs(a - G) > 3.0 or max(abs(v) for v in s.gyro) > 2.5:
        return True
    return s.ground is not None and all(v < GROUND_EMPTY for v in s.ground)


def over_edge(s: Sensors) -> Optional[int]:
    """The ground sensor over the edge: 0 left, 1 right, or None."""
    if s.ground is None:
        return None
    empty = [v < GROUND_EMPTY for v in s.ground]
    return empty.index(True) if any(empty) and not all(empty) else None


class Guardian:
    def __init__(self, lang: str = "en"):
        self.lang = lang if lang in SAY else "en"
        self.state, self.since, self.t = "guarding", 0.0, 0.0
        self.friends: set = set()           # face numbers shown with the owner card (numbers only, this session)
        self.friend_until = -math.inf       # without familiar: friend while a face stays, plus FRIEND_GRACE
        self.last_face = -math.inf
        self.met: set = set()               # face numbers from earlier visits; self.now: in this one
        self.now: set = set()
        self.close_since: Optional[float] = None
        self.lifted_since: Optional[float] = None
        self.edge_side = 0
        self.said: Dict[str, float] = {}

    def forget(self):
        """The phone forgot its faces (familiar off, page reloaded, phone gone): their numbers may go to others now."""
        self.friends, self.met, self.now = set(), set(), set()
        self.friend_until = -math.inf

    def text(self, key: str) -> str:
        return SAY[self.lang][key]

    def go(self, state: str, out: Output, say: Optional[str] = None):
        if state != self.state:
            self.state, self.since = state, self.t
            if say and self.t - self.said.get(say, -math.inf) > 8.0:  # not the same line over and over
                out.say = self.text(say)
                self.said[say] = self.t

    def step(self, s: Sensors, e: Events, dt: float) -> Output:
        self.t += dt
        out = Output()
        faces = s.faces if s.faces_age < 1.0 else []
        face = faces[0] if faces else None
        if face:
            self.last_face = self.t
        owner = OWNER_CARD in e.codes
        if owner and face:
            if face.get("familiar"):
                self.friends.add(face["familiar"])
            self.friend_until = math.inf  # until the face is gone
        if not face and self.friend_until == math.inf:
            self.friend_until = self.t + FRIEND_GRACE
        self.now |= {f["familiar"] for f in faces if f.get("familiar")}
        known = bool(face and face.get("familiar") in self.met)
        num = face.get("familiar") if face else None   # with familiar, the number decides; without, the card's time
        is_friend = bool(face) and (num in self.friends if num else self.t < self.friend_until)

        # the body first: lifted, then the edge
        if lifted(s):
            self.lifted_since = self.lifted_since if self.lifted_since is not None else self.t
        else:
            self.lifted_since = None
        side = over_edge(s)
        if self.lifted_since is not None and self.t - self.lifted_since >= 0.2:
            self.go("scared", out, "scared")
            out.vibrate = 300 if self.t - self.since < dt * 1.5 else 0
        elif self.lifted_since is not None:
            pass                                                        # a bump, or the start of a lift: hold still
        elif side is not None or (self.state == "edge" and self.t - self.since < EDGE_BACK + EDGE_TURN):
            if side is not None and self.state != "edge":
                self.edge_side = side
            self.go("edge", out, "edge")
            k = self.t - self.since
            if k < EDGE_BACK:
                out.linear = -EDGE_SPEED                                # back off
            else:
                out.angular = -1.5 if self.edge_side == 0 else 1.5      # turn away from the empty side
        elif self.state == "scared" and self.t - self.since < 1.0:
            pass                                                        # put down: a moment to settle
        elif any(x.get("kind") == "long" for x in e.touches) or (self.state == "petted" and self.t - self.since < PETTED_FOR):
            if self.state != "petted":
                out.vibrate = 150
            self.go("petted", out, "petted")
        elif face:
            if is_friend:
                self.go("friend", out, "owner" if owner else "friend")
                self.close_since = None
            else:
                close = face["size"] > CLOSE
                self.close_since = (self.close_since if self.close_since is not None else self.t) if close else None
                if self.close_since is not None and self.t - self.close_since >= INTRUDER_AFTER:
                    if self.state != "intruder":
                        out.vibrate = 600
                    self.go("intruder", out, "intruder")
                    if self.t - self.since < 0.5:
                        out.linear = -0.04
                elif self.state not in ("alert", "intruder") or (self.state == "intruder" and not close):
                    self.go("alert", out, "known" if known else "alert")
            if out.linear == 0.0 and abs(face["x"]) > 0.15:             # turn to the face (x > 0: to the face's right, the robot's left)
                out.angular = max(-MAX_TURN, min(MAX_TURN, TURN_GAIN * face["x"]))
            out.gaze = (face["x"], face["y"])
        elif self.state in ("alert", "friend", "intruder") and self.t - self.last_face < LOST_AFTER:
            pass                                                        # looking for the face that went
        else:
            self.go("guarding", out)
            self.close_since = None
            self.met |= self.now
            self.now = set()
            out.angular = 0.35 * math.sin(self.t * 2 * math.pi / 8.0)   # a slow look around
        out.state = self.state
        out.expression = FACES[self.state]
        out.colour = COLOURS[self.state]
        out.doing = self.state if self.state != "alert" or not known else "known"
        return out

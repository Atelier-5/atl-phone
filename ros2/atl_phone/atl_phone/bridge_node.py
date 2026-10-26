# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""bridge — the phone on ROS 2: serves the face page, and maps its WebSocket to the contract's topics.

    ros2 run atl_phone bridge --ros-args -p robot:=thymio_1 [-p port:=8782] [-p key:=...] [-p cert:=c.pem -p cert_key:=k.pem [-p ca:=ca.crt]]
        [-p familiar:=true]

Over USB (adb reverse) the phone opens http://localhost:8782; over Wi-Fi it needs
https (cert), or the camera and microphone stay blocked. The setup page, on this PC,
is http://localhost:8782/setup.html: it guides through connecting and testing a phone.

familiar: whether a program may ask the phone to tell faces apart (look/familiar). Off by default; the
facilitator turns it on (this parameter, or the setup page) once the people at the table agreed. While it is
off, faces reach ROS without their numbers, whatever the phone sends.
"""
import base64
import json
import re
import secrets
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import BatteryState, Imu
from std_msgs.msg import Bool, ColorRGBA, Empty, Float32, Int32, String

from . import contract as c
from . import omi
from . import phone_health
from . import protocol as p
from .registry import Registry
from .translate import Session, Translator
from .wsserver import GuestServer, PhoneServer, lan_address, web_id


class Bridge(Node):
    def __init__(self):
        super().__init__("phone_bridge")
        self.robot = self.declare_parameter("robot", "thymio_1").value
        port = self.declare_parameter("port", c.PORT).value
        bind = self.declare_parameter("bind", "0.0.0.0").value
        key = self.declare_parameter("key", "").value
        cert = self.declare_parameter("cert", "").value or None
        cert_key = self.declare_parameter("cert_key", "").value or None
        ca = self.declare_parameter("ca", "").value or None
        self.lang = self.declare_parameter("lang", "en").value
        self.allow_familiar = bool(self.declare_parameter("familiar", False).value)
        self.allow_show = bool(self.declare_parameter("show", False).value)  # the phone may show its picture to this PC (Omi)
        self.showing = False                          # the person is showing now (the phone's show tile)
        self.frame = (b"", 0.0)                       # the last show frame and when: for the setup page only, in memory only
        self.allow_translate = bool(self.declare_parameter("translate", False).value)  # Übersetzen: the phone may send its sound
        self.translator = Translator(self.declare_parameter("models", "").value or None)  # start.sh: models/ at /models
        self.talk_last = {}                           # the last Übersetzen's counts, for the setup page (never its words)
        self.note = None                              # the card a program put over the face (note): a phone that comes gets it
        self.screen = None                            # what the phone's screen shows (its screen report), for the mirrors
        self.omi = {}                                 # Omi Assist's last state (omi_assist), for the setup page
        self.look = {"on": False, "familiar": False}  # as programs ask (look, look/familiar)
        self.panel = None                             # the last panel a program set: a phone that comes gets it
        self.see = None                               # what the last program asked the camera to find (see)
        self.last_vision = {}                         # kind -> when it was last published (MAX_SEE_RATE)
        self.guardian = {}                            # the Desk Guardian's last state (guardian_node), for the setup page
        web = self.declare_parameter("web", get_package_share_directory("atl_phone") + "/web").value
        docs = self.declare_parameter("docs", "/ws/docs/architecture").value   # the architecture pack (the image has it)
        self.web_id = web_id(web)                     # the pages' fingerprint: a page from an older bridge reloads
        self.t = c.topics(self.robot)
        self.frame_id = f"{self.robot}/phone"
        self.phone = {}
        self.seen = {}      # the latest of each sense, for the setup page
        self.reports = []   # the latest phone check reports
        folder = self.declare_parameter("reports", "").value
        self.registry = Registry(folder) if folder else None  # every phone tested, on the PC (start.sh: reports/)
        self.last_imu = 0.0
        self.last_faces = 0.0
        self.key = key

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = {
            "status": self.create_publisher(String, self.t["status"], latched),
            "imu": self.create_publisher(Imu, self.t["imu"], 10),
            "heading": self.create_publisher(Float32, self.t["heading"], 10),
            "touch": self.create_publisher(String, self.t["touch"], 10),
            "battery": self.create_publisher(BatteryState, self.t["battery"], latched),
            "faces": self.create_publisher(String, self.t["faces"], 10),
            "codes": self.create_publisher(String, self.t["codes"], 10),
            "pad": self.create_publisher(String, self.t["pad"], 10),
            "panel_mode": self.create_publisher(String, self.t["panel_mode"], latched),
            **{k: self.create_publisher(String, self.t[k], 10) for k in ("menu", "note_answer", "read_result", "what_result",
                                                                          "translate_result")},
            **{k: self.create_publisher(String, self.t[k], 10) for k in p.VISION},
        }
        self.create_subscription(String, self.t["expression"], lambda m: self.out(p.face, m.data), 10)
        self.create_subscription(Point, self.t["gaze"], lambda m: self.out(p.gaze, m.x, m.y), 10)
        self.create_subscription(ColorRGBA, self.t["color"], lambda m: self.out(p.color, m.r, m.g, m.b), 10)
        self.create_subscription(String, self.t["say"], lambda m: self.out(p.say, m.data, self.lang), 10)
        self.create_subscription(Bool, self.t["torch"], lambda m: self.out(p.torch, m.data), 10)
        self.create_subscription(Int32, self.t["vibrate"], lambda m: self.out(p.vibrate, m.data), 10)
        self.create_subscription(Bool, self.t["look"], lambda m: self.set_look(on=m.data), 10)
        self.create_subscription(Bool, self.t["familiar"], lambda m: self.set_look(familiar=m.data), 10)
        self.create_subscription(Empty, self.t["forget"], lambda m: self.out(p.forget), 10)
        self.create_subscription(String, self.t["panel"], self.set_panel, 10)
        self.create_subscription(String, self.t["see"], self.set_see, 10)
        self.create_subscription(String, self.t["note"], self.set_note, 10)
        self.create_subscription(String, self.t["read"], lambda m: self.out(p.ask, "read", m.data, self.lang), 10)
        self.create_subscription(String, self.t["what"], lambda m: self.out(p.ask, "what", m.data, self.lang), 10)
        # Omi Assist (omi_assist): the setup page starts it, sets its reminders, and shows what it does
        self.create_subscription(String, f"/{self.robot}/omi/state", self.omi_state, 10)
        self.omi_pub = {"run": self.create_publisher(Bool, f"/{self.robot}/omi/run", 10),
                        "reminders": self.create_publisher(String, f"/{self.robot}/omi/reminders", 10)}
        # the Desk Guardian (guardian_node): the setup page starts and stops it, and shows what it does
        self.create_subscription(String, f"/{self.robot}/guardian/state", self.guardian_state, 10)
        self.guardian_pub = {k: self.create_publisher(Bool, f"/{self.robot}/guardian/{k}", 10) for k in ("run", "drive")}
        # the setup page's tests publish on the same topics, as any program would
        self.tests = {k: self.create_publisher(kind, self.t[k], 10) for k, kind in
                      {"expression": String, "gaze": Point, "color": ColorRGBA, "say": String, "torch": Bool, "vibrate": Int32,
                       "look": Bool, "familiar": Bool, "forget": Empty, "panel": String, "see": String, "note": String,
                       "read": String, "what": String}.items()}

        # Übersetzen: the sound is heard and translated on a worker; the words go back to the phone alone
        self.talk = Session(self.translator, send=lambda m: self.talk_send("robot", m), done=self.talk_done,
                            log=lambda s: self.get_logger().warning(s))
        # and a guest phone on the home Wi-Fi (talk.html, its own https port): its own worker, the same models
        self.guest_talk = Session(self.translator, send=lambda m: self.talk_send("guest", m), done=self.talk_done,
                                  log=lambda s: self.get_logger().warning(s))
        self.guest_key = ""                           # in the QR code on the robot's phone; new each time Übersetzen is allowed
        self.guest = None                             # its server, after the phone's (below)
        if self.allow_translate:
            self.guest_key = secrets.token_urlsafe(9)
            if self.translator.ready:
                self.talk.warm()
        self.server = PhoneServer(web, port, bind, key, on_open=self.opened, on_text=self.text, on_close=self.closed,
                                  cert=cert, cert_key=cert_key, api=self, ca=ca, on_mirror=self.mirrored, docs=docs).start()
        guest_port = int(self.declare_parameter("guest_port", 0).value)
        guest_cert = self.declare_parameter("guest_cert", "").value
        guest_cert_key = self.declare_parameter("guest_cert_key", "").value
        if guest_port and guest_cert and guest_cert_key:
            self.guest = GuestServer(web, guest_port, guest_cert, guest_cert_key, key=lambda: self.guest_key,
                                     on_open=self.guest_opened, on_text=self.guest_text, on_close=self.guest_closed,
                                     ca=self.declare_parameter("guest_ca", "").value or None).start()
        self.status()
        q = f"?key={key}" if key else ""
        self.get_logger().info(f"{c.CONTRACT} for /{self.robot}: {self.server.scheme}://<this PC>:{self.server.port}/{q}"
                               f" (USB: adb reverse tcp:{port} tcp:{port}, then {self.server.scheme}://localhost:{port}/{q})")

    def out(self, make, *args):
        try:
            msg = make(*args)
        except ValueError as e:
            self.get_logger().warning(f"not sent to the phone: {e}")
            return
        self.server.send(json.dumps(msg))

    def familiar(self) -> bool:
        return self.look["familiar"] and self.allow_familiar

    def set_look(self, **kw):
        """A program asks for the front camera (or for faces told apart): the phone hears of it when it changes."""
        before = (self.look["on"], self.familiar())
        self.look.update(kw)
        if (self.look["on"], self.familiar()) != before:
            self.out(p.look, self.look["on"], self.familiar())
            self.status()

    def set_panel(self, m):
        try:
            self.panel = p.panel(m.data)
        except ValueError as e:
            self.get_logger().warning(f"not sent to the phone: {e}")
            return
        self.server.send(json.dumps(self.panel))
        self.pub["panel_mode"].publish(String(data=self.panel["mode"]))

    def set_see(self, m):
        try:
            self.see = p.see(m.data)
        except ValueError as e:
            self.get_logger().warning(f"not sent to the phone: {e}")
            return
        self.server.send(json.dumps(self.see))

    def set_note(self, m):
        try:
            self.note = p.note(m.data)
        except ValueError as e:
            self.get_logger().warning(f"not sent to the phone: {e}")
            return
        self.server.send(json.dumps(self.note))

    def omi_state(self, m):
        try:
            self.omi = dict(json.loads(m.data), at=time.time())
        except (ValueError, TypeError):
            pass

    def set_show(self, allowed=None, stop=False):
        """The facilitator allows showing or not (show:=true, the setup page); stopped, the last frame is dropped."""
        if allowed is not None:
            self.allow_show = bool(allowed)
        if stop or not self.allow_show:
            self.showing, self.frame = False, (b"", 0.0)
        self.out(p.show, self.allow_show, self.showing)
        self.status()

    def talk_allowed(self) -> bool:
        return self.allow_translate and self.server.phone_local

    def set_translate(self, allowed: bool):
        """The facilitator allows Übersetzen or not (translate:=true, the setup page); off, what is being heard is dropped."""
        self.allow_translate = bool(allowed)
        if not self.allow_translate:
            self.talk.cancel()
            self.guest_talk.cancel()
        elif self.translator.ready:
            self.talk.warm()
        self.new_guest_key()
        self.status()

    def guest_url(self) -> str:
        if not (self.guest and self.guest_key and self.allow_translate):
            return ""
        return f"https://{lan_address()}:{self.guest.port}/talk.html?k={self.guest_key}"

    def talk_state(self):
        """Übersetzen's state to the robot's phone alone (the guest's link and key are in it: never to a mirror), and to
        the guest."""
        guest_on = bool(self.guest and self.guest.connected)
        self.server.send_phone(json.dumps(p.talk(self.talk_allowed(), self.translator.ready, self.guest_url(), guest_on)))
        if guest_on:
            self.guest.send(json.dumps(p.talk(self.allow_translate, self.translator.ready, "", True)))

    def new_guest_key(self):
        """A new guest code (allowed again, or asked for on the setup page): the guest that was there goes."""
        self.guest_key = secrets.token_urlsafe(9) if self.allow_translate else ""
        if self.guest:
            self.guest.drop()
        self.talk_state()

    def talk_send(self, who: str, m: dict):
        """What a worker heard and translated: to both phones while a guest is there (they talk with each other), an
        error to the one who spoke only. Never to a mirror, ROS or the log."""
        text = json.dumps(dict(m, who=who))
        to_robot = who == "robot" or not m.get("error")
        to_guest = bool(self.guest) and (who == "guest" or not m.get("error"))
        if to_robot:
            self.server.send_phone(text)
        if to_guest:
            self.guest.send(text)

    def guest_opened(self, link):
        self.get_logger().info("Übersetzen: a guest phone joined")
        self.talk_state()

    def guest_closed(self, link):
        self.get_logger().info("Übersetzen: the guest phone left")
        self.guest_talk.cancel()
        self.talk_state()

    def guest_text(self, raw: str):
        """The guest phone only talks: its sound, while Übersetzen is allowed; anything else is dropped."""
        try:
            m = p.parse(raw)
        except ValueError:
            return
        if m["t"] == "audio" and self.allow_translate and self.guest_key:
            self.guest_talk.audio(m)

    def talk_done(self, r: dict):
        """How one Übersetzen went, as counts: to ROS and the setup page; the log says no word of it."""
        self.pub["translate_result"].publish(String(data=json.dumps(r)))
        self.talk_last = dict(r, at=time.time())
        self.get_logger().info(f"translate: {r['from']} to {r['to']}, {r['words']} words, {r['ms']} ms")

    def show_frame(self):
        """The last frame the person showed, for the setup page: only while showing, and fresh (3 s)."""
        jpeg, at = self.frame
        return jpeg if self.showing and jpeg and time.time() - at < 3.0 else None

    def guardian_state(self, m):
        try:
            self.guardian = dict(json.loads(m.data), at=time.time())
        except (ValueError, TypeError):
            pass

    def status(self):
        s = {"contract": c.CONTRACT, "connected": self.server.connected,
             "look": self.look["on"], "familiar": self.familiar(), "familiar_allowed": self.allow_familiar,
             "show_allowed": self.allow_show, "showing": self.showing, "translate_allowed": self.allow_translate}
        if s["connected"]:
            s.update(self.phone)
        self.pub["status"].publish(String(data=json.dumps(s)))

    def mirrored(self, link):
        """A mirror came (the phone's Webots twin): what the phone has now, so its screen starts the same."""
        link.send(json.dumps(self.phone_line()))
        for m in (self.panel, self.note if self.note and self.note["text"] else None, self.screen):
            if m:
                link.send(json.dumps(m))

    def phone_line(self) -> dict:
        return {"t": "phone", "connected": self.server.connected, "model": self.phone.get("model", "")}

    def opened(self, link):
        self.phone = {"peer": link.peer}
        self.seen = {}
        self.get_logger().info(f"phone at {link.peer}")
        self.status()

    def closed(self, link):
        self.get_logger().info(f"phone at {link.peer} gone")
        self.phone = {}
        self.showing, self.frame = False, (b"", 0.0)
        self.talk.cancel()
        self.screen = None
        self.server.send_mirrors(json.dumps(self.phone_line()))
        self.status()

    def text(self, raw: str):
        try:
            m = p.parse(raw)
        except ValueError as e:
            self.get_logger().warning(f"from the phone: {e}", throttle_duration_sec=5.0)
            return
        t = m["t"]
        if t == "hello":
            self.phone.update(id=m["id"], model=m["model"] or model_of(m["ua"]), ua=m["ua"], secure=m["secure"],
                              caps=m["caps"], screen=m["screen"])
            self.get_logger().info(f"phone says hello: {self.phone['model']}")
            self.status()
            self.server.send_mirrors(json.dumps(self.phone_line()))
            self.out(p.web, self.web_id)   # first: a page an older bridge served reloads, and says hello again
            if self.look["on"]:  # a phone that comes (back) looks on, as asked
                self.out(p.look, True, self.familiar())
            if self.panel:
                self.server.send(json.dumps(self.panel))
            if self.see and self.see["find"]:
                self.server.send(json.dumps(self.see))
            if self.note and self.note["text"]:
                self.server.send(json.dumps(self.note))
            self.out(p.show, self.allow_show, False)
            self.talk_state()
        elif t == "imu":
            now = time.monotonic()
            if now - self.last_imu < 1.0 / c.MAX_IMU_RATE:
                return
            self.last_imu = now
            imu = Imu()
            imu.header.stamp = self.get_clock().now().to_msg()
            imu.header.frame_id = self.frame_id
            imu.orientation_covariance[0] = -1.0  # no orientation
            imu.linear_acceleration.x, imu.linear_acceleration.y, imu.linear_acceleration.z = m["acc"]
            imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z = m["gyro"]
            self.pub["imu"].publish(imu)
            n = self.seen.get("imu", {}).get("n", 0) + 1
            self.seen["imu"] = {"acc": m["acc"], "gyro": m["gyro"], "n": n, "at": time.time()}
        elif t == "heading":
            self.pub["heading"].publish(Float32(data=m["deg"]))
            self.seen["heading"] = {"deg": m["deg"], "at": time.time()}
        elif t == "touch":
            touch = {k: v for k, v in m.items() if k != "t"}
            self.pub["touch"].publish(String(data=json.dumps(touch)))
            self.seen["touch"] = (self.seen.get("touch", []) + [dict(touch, at=time.time())])[-20:]
        elif t == "battery":
            b = BatteryState()
            b.header.stamp = self.get_clock().now().to_msg()
            b.header.frame_id = self.frame_id
            b.percentage = m["level"]
            b.present = True
            b.power_supply_status = (BatteryState.POWER_SUPPLY_STATUS_CHARGING if m["charging"]
                                     else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING)
            self.pub["battery"].publish(b)
            self.seen["battery"] = {"level": m["level"], "charging": m["charging"], "at": time.time()}
        elif t == "camera":  # the setup page's camera test: not on ROS yet (codes come with the card scanner)
            cam = {**self.seen.get("camera", {}), **{k: v for k, v in m.items() if k != "t"}, "at": time.time()}
            if m["ok"]:
                cam.pop("error", None)
            if "code" in m:
                cam["codes"] = (cam.get("codes", []) + [m["code"]])[-5:]
            self.seen["camera"] = cam
        elif t == "look":
            self.seen["look"] = {k: v for k, v in m.items() if k != "t"} | {"at": time.time()}
        elif t == "faces":
            now = time.monotonic()
            if now - self.last_faces < 1.0 / c.MAX_FACES_RATE:
                return
            self.last_faces = now
            faces = m["faces"] if self.familiar() else [dict(f, familiar=None) for f in m["faces"]]
            self.pub["faces"].publish(String(data=json.dumps({"n": m["n"], "faces": faces, **({"period": m["period"]} if "period" in m else {})})))
            self.seen["faces"] = {"n": m["n"], "faces": faces, "at": time.time()}
        elif t in p.VISION:
            now = time.monotonic()
            if now - self.last_vision.get(t, 0.0) < 1.0 / c.MAX_SEE_RATE:
                return
            self.last_vision[t] = now
            body = {"camera": m["camera"], t: m[t]}
            self.pub[t].publish(String(data=json.dumps(body)))
            self.seen[t] = dict(body, at=time.time())
        elif t == "see":
            self.seen["see"] = {k: v for k, v in m.items() if k != "t"} | {"at": time.time()}
        elif t == "panel":  # the person picked another mode on the phone
            self.panel = dict(self.panel or p.panel(json.dumps(c.DEFAULT_PANEL)), mode=m["mode"])
            self.pub["panel_mode"].publish(String(data=m["mode"]))
        elif t == "pad":
            self.pub["pad"].publish(String(data=json.dumps({"id": m["id"]})))
            self.seen["pad"] = (self.seen.get("pad", []) + [{"id": m["id"], "at": time.time()}])[-10:]
        elif t == "code":
            self.pub["codes"].publish(String(data=json.dumps({"text": m["text"]})))
            self.seen["codes"] = (self.seen.get("codes", []) + [m["text"]])[-5:]
        elif t == "menu":
            self.pub["menu"].publish(String(data=json.dumps({"id": m["id"]})))
            self.seen["menu"] = (self.seen.get("menu", []) + [{"id": m["id"], "at": time.time()}])[-10:]
        elif t == "answer":
            body = {"note": m["note"], "id": m["id"]}
            self.pub["note_answer"].publish(String(data=json.dumps(body)))
            self.seen["answer"] = dict(body, at=time.time())
            if self.note and self.note["id"] == m["note"]:
                self.note = None  # answered: a phone that comes does not get it again
        elif t in ("read", "what"):
            body = {k: v for k, v in m.items() if k != "t"}
            self.pub[f"{t}_result"].publish(String(data=json.dumps(body)))
            self.seen[t] = dict(body, at=time.time())
        elif t == "show":  # the person starts or stops showing; refused unless allowed
            self.showing = m["on"] and self.allow_show
            if not self.showing:
                self.frame = (b"", 0.0)
            if m["on"] and not self.allow_show:
                self.out(p.show, False)
            self.get_logger().info(f"show: {'on' if self.showing else 'off'}" + ("" if self.allow_show else " (not allowed)"))
            self.status()
        elif t == "audio":  # Übersetzen's sound: to the worker, only when allowed and the link is this computer or https
            if not self.talk_allowed():
                if m["end"] or m["seq"] == 0:
                    self.server.send_phone(json.dumps(p.talk(False, False)))
                return
            self.talk.audio(m)
        elif t == "screen":  # what the phone's screen shows (keys only): for the mirrors, not for ROS
            self.screen = m
            self.server.send_mirrors(json.dumps(m))
        elif t == "frame":
            if self.showing:  # else dropped at once: nothing is kept that was not allowed
                self.frame = (m["jpeg"], time.time())
                # and to the Webots twin on this computer, while she shows (the same consent as the setup page's)
                self.server.send_mirrors(json.dumps({"t": "frame", "jpeg": base64.b64encode(m["jpeg"]).decode()}), local_only=True)

    # the setup page (wsserver api): what the bridge sees, and the tests it asks for

    def state(self) -> dict:
        q = f"?key={self.key}" if self.key else ""
        port, scheme = self.server.port, self.server.scheme
        return {"contract": c.CONTRACT, "robot": self.robot, "now": time.time(),
                "urls": {"usb": f"{scheme}://localhost:{port}/{q}", "wifi": f"{scheme}://{lan_address()}:{port}/{q}",
                         "ca": f"{scheme}://{lan_address()}:{port}/ca.crt" if self.server.ca else None},
                "secure_wifi": scheme == "https", "connected": self.server.connected,
                "phone": self.phone, "seen": self.seen, "reports": self.reports, "expressions": c.EXPRESSIONS,
                "look": self.look["on"], "familiar": self.familiar(), "familiar_allowed": self.allow_familiar,
                "panel": self.panel, "see": self.see, "guardian": self.guardian, "note": self.note, "omi": self.omi,
                "show": {"allowed": self.allow_show, "on": self.showing, "fresh": self.show_frame() is not None},
                "translate": {"allowed": self.allow_translate, "link_ok": self.server.phone_local,
                              "guest": {"port": self.guest.port if self.guest else None, "url": self.guest_url(),
                                        "connected": bool(self.guest and self.guest.connected)},
                              "models": self.translator.models(), "ready": self.translator.ready, "last": self.talk_last},
                "mirrors": self.server.mirror_count, "screen": self.screen, "web": self.web_id, "docs": bool(self.server.docs)}

    def act(self, body: dict):
        """A test from the setup page. Outputs go through ROS, on the contract's own topics, so the whole chain is tested."""
        if "guardian" in body:  # start or stop the Desk Guardian, as any program could (its own topics)
            if "drive" in body:
                self.guardian_pub["drive"].publish(Bool(data=bool(body["drive"])))
            self.guardian_pub["run"].publish(Bool(data=bool(body["guardian"])))
            return
        if "open" in body or "camera" in body:  # straight to the phone: no topic for these
            m = p.open_page(body["open"], body.get("layout", "")) if "open" in body else p.camera(body["camera"])
            if not self.server.send(json.dumps(m)):
                raise ValueError("no phone")
            return
        if "allow_show" in body or "show" in body:  # the facilitator's choice, and a stop, on this PC only
            self.set_show(body.get("allow_show"), stop=body.get("show") is False)
            return
        if "phone" in body:  # the phone's load, and lighter on request (phone_health: the host's adb server, this PC only)
            what = body["phone"]
            try:
                if what == "look":
                    return phone_health.look()
                if what == "kill":
                    phone_health.kill()
                    return phone_health.look()
                if what in ("stay_on", "stay_off"):
                    phone_health.stay_on(what == "stay_on")
                    return {"stay_on": what == "stay_on"}
                if what == "tabs":
                    return {"tabs": phone_health.tabs(self.server.port)}
                if what == "close":
                    return {"closed": phone_health.close(self.server.port, body.get("ids"))}
            except (phone_health.AdbError, OSError) as e:
                raise ValueError(str(e)) from e
            raise ValueError("phone: look, kill, stay_on, stay_off, tabs or close")
        if "prop" in body:  # the Webots twin's demo: a cup, a letter... flies in (to the mirrors only: never the phone)
            if not self.server.send_mirrors(json.dumps(p.prop(body["prop"]))):
                raise ValueError("no Webots twin")
            return
        if "omi_tour" in body:  # Omi Assist's presentation, straight to the phone, in Omi's language
            if (self.omi.get("state") != "on" or time.time() - self.omi.get("at", 0) > 3):
                raise ValueError("Omi Assist is not running")
            if not self.server.send(json.dumps(p.tour(self.omi.get("lang") or self.lang))):
                raise ValueError("no phone")
            return
        if "omi" in body or "reminders" in body:  # Omi Assist (omi_assist): start, stop, its reminders (its own topics)
            if "reminders" in body:
                self.omi_pub["reminders"].publish(String(data=json.dumps(omi.clean(body["reminders"]))))  # a bad one: 400
            if "omi" in body:
                self.omi_pub["run"].publish(Bool(data=bool(body["omi"])))
            return
        if "allow_translate" in body:  # the facilitator's choice, on this PC only (the setup page)
            self.set_translate(body["allow_translate"])
            return
        if "guest_new" in body:  # a new guest code: the guest phone that was there goes
            self.new_guest_key()
            return
        if "allow_familiar" in body:  # the facilitator's choice, on this PC only (the setup page)
            self.allow_familiar = bool(body["allow_familiar"])
            self.look["familiar"] = self.look["familiar"] and self.allow_familiar  # once refused, a program asks again
            self.out(p.look, self.look["on"], self.familiar())
            self.status()
            return
        topic, v = body.get("topic"), body.get("value")
        if not self.server.connected and topic not in ("see", "panel", "note"):  # nobody would show it: say so instead
            raise ValueError("no phone")  # (see and panel are kept for the phone that comes: they may change meanwhile)
        if topic == "expression":
            msg = String(data=p.face(v)["expression"])
        elif topic == "gaze":
            g = p.gaze(v.get("x", 0), v.get("y", 0)) if isinstance(v, dict) else p.gaze(None, None)
            msg = Point(x=g["x"], y=g["y"])
        elif topic == "color":
            if not isinstance(v, list) or len(v) != 3:
                raise ValueError("color: [r, g, b], each 0..1")
            p.color(*v)
            msg = ColorRGBA(r=float(v[0]), g=float(v[1]), b=float(v[2]), a=1.0)
        elif topic == "say":
            v = v if isinstance(v, dict) else {"text": v}
            p.say(json.dumps(v), self.lang)
            msg = String(data=json.dumps(v))
        elif topic == "torch":
            msg = Bool(data=bool(v))
        elif topic == "vibrate":
            msg = Int32(data=p.vibrate(v)["ms"])
        elif topic in ("look", "familiar"):
            msg = Bool(data=bool(v))
        elif topic == "forget":
            msg = Empty()
        elif topic in ("panel", "see", "note"):
            msg = String(data=json.dumps(v))
            {"panel": p.panel, "see": p.see, "note": p.note}[topic](msg.data)
        elif topic in ("read", "what"):
            msg = String(data=json.dumps(v if isinstance(v, dict) else {}))
            p.ask(topic, msg.data, self.lang)
        else:
            raise ValueError(f"unknown topic {topic!r}")
        self.tests[topic].publish(msg)

    def report(self, body: dict):
        model = body.get("model") if isinstance(body.get("model"), str) else ""
        r = {"id": p.phone_id(body.get("phone_id")),  # the setup page matches a report to its phone by this id
             "model": model.strip()[:40] or model_of(str(body.get("userAgent", ""))), "at": time.time(),
             "checks": {str(k)[:40]: {"ok": v.get("ok"), "note": str(v.get("note", ""))[:200], "need": v.get("need")}
                        for k, v in list(body["checks"].items())[:60] if isinstance(v, dict)}}
        self.reports = (self.reports + [r])[-10:]
        core = [k for k, v in r["checks"].items() if v["need"] == "core" and v["ok"] is False]
        self.get_logger().info(f"phone check from {r['model']}: " + (f"core missing: {', '.join(core)}" if core else "core complete"))
        return self.keep(lambda: self.registry.check(body, r["model"]))

    def summary(self, body: dict):
        """The setup page's summary (step 6), for the registry."""
        model = body.get("model") if isinstance(body.get("model"), str) and body["model"].strip() else self.phone.get("model", "")
        if not model:
            raise ValueError("which phone? none is connected and the summary names none")
        return self.keep(lambda: self.registry.summary(body, model))

    def keep(self, write):
        if not self.registry:
            return {"saved": None}
        try:
            path = write()
        except OSError as e:
            self.get_logger().warning(f"the registry could not keep it: {e}")
            return {"saved": None, "error": str(e)}
        rel = path.relative_to(self.registry.dir)
        self.get_logger().info(f"kept in the registry: reports/{rel}")
        return {"saved": f"reports/{rel}"}

    def destroy_node(self):
        self.talk.stop()
        self.guest_talk.stop()
        if self.guest:
            self.guest.stop()
        self.server.stop()
        super().destroy_node()


def model_of(ua: str) -> str:
    """'... (Linux; Android 8.0.0; SM-G950F) ...' -> 'SM-G950F'. Chrome 110+ hides it as 'K' (then: client hints)."""
    m = re.search(r"Android ([\d.]+); ([^;)]+)", ua)
    if not m:
        return "unknown"
    return f"Android {m.group(1)} phone" if m.group(2).strip() == "K" else m.group(2).strip()[:40]


def main():
    rclpy.init()
    node = Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

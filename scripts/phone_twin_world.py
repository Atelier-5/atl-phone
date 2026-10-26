#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""phone_twin_world — an atl-ide table with the phone on the Thymio: writes table_phone.wbt (or table_omi.wbt) for Webots.

    python3 scripts/phone_twin_world.py ~/atl/atl-ide/mydocs/twin [--out webots/worlds] [--phone A50] [--landscape] [--things]
    python3 scripts/phone_twin_world.py ~/atl/atl-ide/mydocs/twin --scene omi [--phone ANE-LX1] [--pi 4]

--scene omi: Omi Assist as the robot it will be, alone on a plain table: the Thymio with the Raspberry Pi's brick box,
a brick riser and the phone clamp (AtlOmiStack), the phone in it; atl-ide's objects and line are left out. The props of
webots/props.json (a cup, a letter on an easel, a letter held in a hand, a visitor) wait under the floor until the twin
flies them in. It also writes table_omi.json (atl-ide's table.json without objects) for atl-bot-thymio's launch.

It copies the table's world (table.wbt, its picture) to --out, puts the holder (AtlPhoneHolder) in the Thymio's
bodySlot and the phone (AtlPhone, named PH5v0001: 8 characters, for the Webots snap) riding on it, with the sizes of
webots/phones.json. --things adds what the phone's vision can find, for phone_twin_check: a face beyond the table's
end, to the robot's left; an ArUco marker (id 3) and a cup ahead; a red ball on the right. The PROTOs are copied
beside the world, so the Webots snap (which reads no hidden folder and no /tmp) finds them. Standard library only.
(Coordinates: x along the table, y across, z up; the robot faces +x.)
"""
import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
NAME = "PH5v0001"
# what the vision check finds: (DEF, model, translation, size of a box or None for a ball's radius, colour)
THINGS = [
    ("FACE", "face", (0.85, 0.30, 0.93), (0.02, 0.16, 0.2), (0.95, 0.75, 0.6)),
    ("MARKER", "aruco:3", (0.45, -0.05, 0.80), (0.005, 0.06, 0.06), (0.1, 0.1, 0.1)),
    ("CUP", "cup", (0.40, 0.12, 0.795), (0.07, 0.07, 0.09), (0.2, 0.4, 0.9)),
    ("BALL", "sports ball", (0.40, -0.17, 0.78), 0.03, (0.9, 0.1, 0.1)),
]


def thing(dfn, model, at, size, rgb):
    geo = f"Sphere {{ radius {size} }}" if isinstance(size, float) else f"Box {{ size {size[0]} {size[1]} {size[2]} }}"
    col = " ".join(str(v) for v in rgb)
    return f"""DEF {dfn} Solid {{
  translation {at[0]} {at[1]} {at[2]}
  name "{model} ({dfn.lower()})"
  model "{model}"
  recognitionColors [ {col} ]
  children [ Shape {{ appearance PBRAppearance {{ baseColor {col} roughness 0.8 metalness 0 }} geometry {geo} }} ]
}}
"""


def top_nodes(world: str) -> list:
    """The world's top-level nodes, each with the comments and blank lines before it (a node starts at column 0)."""
    parts, cur = [], []
    for line in world.splitlines(keepends=True):
        if line[:1].isalpha() and cur and any(l[:1].isalpha() for l in cur):
            parts.append("".join(cur))
            cur = []
        cur.append(line)
    parts.append("".join(cur))
    return parts


def look_at(eye, at) -> str:
    """A Viewpoint's orientation (axis angle) for a camera at eye looking at at, the world's z up."""
    dx, dy, dz = (at[i] - eye[i] for i in range(3))
    yaw, pitch = math.atan2(dy, dx), math.atan2(-dz, math.hypot(dx, dy))
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    R = [[cy * cp, -sy, cy * sp], [sy * cp, cy, sy * sp], [-sp, 0.0, cp]]   # Rz(yaw) Ry(pitch)
    a = math.acos(max(-1.0, min(1.0, (R[0][0] + R[1][1] + R[2][2] - 1) / 2)))
    if a < 1e-9:
        return "0 0 1 0"
    k = 2 * math.sin(a)
    return f"{(R[2][1] - R[1][2]) / k:.4f} {(R[0][2] - R[2][0]) / k:.4f} {(R[1][0] - R[0][1]) / k:.4f} {a:.4f}"


def stack_node(p: dict, pi: str) -> str:
    mm = lambda v: v / 1000.0
    s = p["size_mm"]
    arm = 0.06
    if p.get("buttons_mm"):  # the arms grip below the side buttons, or above them
        lo, hi = p["buttons_mm"]["from"]
        arm = mm(lo - 12) if lo > 45 else mm(hi + 12)
    return f"""  bodySlot [
    DEF PHONE_MOUNT AtlOmiStack {{
      pi "{pi}"
      width {mm(s[0])}
      height {mm(s[1])}
      thickness {mm(s[2])}
      phoneMass {p.get("mass_g", 160) / 1000.0}
      armAt {arm:.4f}
    }}
  ]"""


def props() -> str:
    """The demo's props, parked under the floor (webots/props.json); kinematic: the twin's controller moves them. The
    letter faces +x (the plane's u to +y, v up): put where the robot's back camera looks (behind it), it faces the phone."""
    pr = json.loads((HERE / "webots" / "props.json").read_text())
    park = " ".join(str(v) for v in pr["park"])
    rec = lambda rgb: " ".join(str(v) for v in rgb)
    paper = 'PBRAppearance { baseColor 1 1 1 roughness 0.9 metalness 0 baseColorMap ImageTexture { url [ "../textures/letter_de.png" ] } }'
    sheet = f"""Solid {{ name "the letter" model "letter" recognitionColors [ 0.98 0.97 0.94 ]
        children [ Pose {{ rotation 0.5774 0.5774 0.5774 2.0944 children [ Shape {{ appearance {paper} geometry Plane {{ size 0.148 0.21 }} }} ] }} ] }}"""
    skin = "PBRAppearance { baseColor 0.93 0.76 0.62 roughness 0.8 metalness 0 }"
    wood = "PBRAppearance { baseColor 0.55 0.38 0.22 roughness 0.8 metalness 0 }"
    out = f"""DEF {pr["cup"]["def"]} Solid {{
  translation {park}
  name "cup (prop)"
  model "cup"
  recognitionColors [ 0.2 0.45 0.85 ]
  children [
    Shape {{ appearance PBRAppearance {{ baseColor 0.2 0.45 0.85 roughness 0.4 metalness 0 }} geometry Cylinder {{ height 0.09 radius 0.038 }} }}
    Pose {{ translation 0 0.045 0 children [ Shape {{ appearance PBRAppearance {{ baseColor 0.2 0.45 0.85 roughness 0.4 metalness 0 }}
            geometry Box {{ size 0.01 0.02 0.05 }} }} ] }}
  ]
}}
DEF {pr["letter"]["def"]} Pose {{
  translation {park}
  children [
    Pose {{ translation -0.035 0 0.075 rotation 0 1 0 -0.26 children [ Shape {{ appearance {wood} geometry Box {{ size 0.01 0.16 0.15 }} }} ] }}
    Pose {{ translation 0.005 0 0.015 children [ Shape {{ appearance {wood} geometry Box {{ size 0.03 0.16 0.01 }} }} ] }}
    Pose {{ translation 0.0 0 0.125 rotation 0 1 0 -0.26 children [ {sheet} ] }}
  ]
}}
DEF {pr["hand"]["def"]} Pose {{
  translation {park}
  children [
    {sheet.replace('"the letter"', '"the held letter"')}
    Pose {{ translation 0.012 0.0 -0.115 children [ Shape {{ appearance {skin} geometry Box {{ size 0.025 0.08 0.09 }} }} ] }}
    Pose {{ translation 0.012 0.05 -0.085 rotation 1 0 0 0.6 children [ Shape {{ appearance {skin} geometry Capsule {{ height 0.04 radius 0.011 }} }} ] }}
    Pose {{ translation 0.012 0.0 -0.2 children [ Shape {{ appearance {skin} geometry Capsule {{ height 0.12 radius 0.03 }} }} ] }}
  ]
}}
DEF {pr["visitor"]["def"]} Pose {{
  translation {park}
  children [
    Solid {{ translation 0 0 0.33 name "visitor's face" model "face" recognitionColors [ {rec((0.93, 0.76, 0.62))} ]
      children [ Shape {{ appearance {skin} geometry Sphere {{ radius 0.095 subdivision 3 }} }} ] }}
    Pose {{ translation 0 0 0.2 children [ Shape {{ appearance {skin} geometry Cylinder {{ height 0.08 radius 0.04 }} }} ] }}
    Pose {{ translation 0 0 -0.2 children [ Shape {{ appearance PBRAppearance {{ baseColor 0.3 0.45 0.6 roughness 0.9 metalness 0 }}
            geometry Capsule {{ height 0.55 radius 0.16 }} }} ] }}
  ]
}}
"""
    return out


def omi_world(world: str, p: dict, phone: str, pi: str) -> str:
    """atl-ide's table without its objects and its line, seen closer; the Omi robot on it, and the props."""
    keep = []
    for node in top_nodes(world):
        if re.search(r'name "(carton box|wooden block)"', node) or re.match(r"\s*Viewpoint", node.lstrip("\n")):
            continue
        keep.append(node)
    world = "".join(keep)
    world = re.sub(r"\n(\s*)baseColorMap ImageTexture \{.*?\n\1\}", "", world, flags=re.S)   # the table top: plain, no line
    m = re.search(r"\nThymio2 \{\n(.*?)\n\}\n", world, re.S)
    if not m:
        sys.exit("no Thymio2 in table.wbt")
    world = world.replace(m.group(0), f"\nDEF THYMIO1 Thymio2 {{\n{m.group(1)}\n{stack_node(p, pi)}\n}}\n")
    protos = 'EXTERNPROTO "../protos/AtlPhone.proto"\nEXTERNPROTO "../protos/AtlOmiStack.proto"\n'
    eye = (0.62, -0.5, 1.12)
    view = f"Viewpoint {{\n  orientation {look_at(eye, (0.0, 0.0, 0.88))}\n  position {eye[0]} {eye[1]} {eye[2]}\n}}\n"
    world = world.replace("\nWorldInfo", "\n" + protos + "\nWorldInfo", 1)
    world = world.replace("\nBackground", "\n" + view + "Background", 1)
    world = world.replace('title "Atelier-5: the virtual table"', 'title "Atelier-5: Omi Assist on the table"')
    world = world.replace("GENERATED by atl/world.py", "GENERATED by atl-phone's scripts/phone_twin_world.py --scene omi from atl-ide's world")
    world += phone_node(p, "THYMIO1.PHONE_MOUNT", False)
    return world + props()


def phone_node(p: dict, follow: str, landscape: bool) -> str:
    mm = lambda v: v / 1000.0
    s, sc = p["size_mm"], p["screen_mm"]
    return f"""AtlPhone {{
  translation 0 0 1.0
  name "{NAME}"
  follow "{follow}"
  size {mm(s[0])} {mm(s[1])} {mm(s[2])}
  screenSize {mm(sc[0])} {mm(sc[1])}
  displayWidth {p["display_px"][0]}
  displayHeight {p["display_px"][1]}
  frontAt {mm(p["front"]["at_mm"][0])} {mm(p["front"]["at_mm"][1])}
  backAt {mm(p["back"]["at_mm"][0])} {mm(p["back"]["at_mm"][1])}
  frontFov {math.radians(p["front"]["fov_deg"]):.4f}
  backFov {math.radians(p["back"]["fov_deg"]):.4f}
  cameraWidth {p["front"]["px"][0]}
  cameraHeight {p["front"]["px"][1]}
}}
"""


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("twin", type=Path, help="an atl-ide twin folder (table.wbt, table.json)")
    a.add_argument("--out", type=Path, default=HERE / "webots" / "worlds")
    a.add_argument("--phone", default="A50", help="a phone of webots/phones.json")
    a.add_argument("--landscape", action="store_true", help="the phone lies across")
    a.add_argument("--things", action="store_true", help="a face, a marker, a cup and a ball to see")
    a.add_argument("--scene", choices=("table", "omi"), default="table", help="omi: the Omi robot alone, with props")
    a.add_argument("--pi", choices=("4", "5"), default="4", help="the Raspberry Pi in the brick box (--scene omi)")
    args = a.parse_args()
    if args.scene == "omi" and args.phone == "A50" and "--phone" not in sys.argv:
        args.phone = "ANE-LX1"
    phones = json.loads((HERE / "webots" / "phones.json").read_text())
    if args.phone not in phones or args.phone == "_":
        sys.exit(f"no phone {args.phone!r} in webots/phones.json")
    world = (args.twin / "table.wbt").read_text()
    if args.scene == "omi":
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "table_omi.wbt").write_text(omi_world(world, phones[args.phone], args.phone, args.pi))
        table = json.loads((args.twin / "table.json").read_text())
        table.update(objects=[], world="omi/table")
        (args.out / "table_omi.json").write_text(json.dumps(table, indent=1) + "\n")
        copy_beside(args.out)
        print(args.out / "table_omi.wbt")
        return 0
    m = re.search(r"\nThymio2 \{\n(.*?)\n\}\n", world, re.S)
    if not m:
        sys.exit("no Thymio2 in table.wbt")
    holder = f"""  bodySlot [
    DEF PHONE_MOUNT AtlPhoneHolder {{ upright {"FALSE" if args.landscape else "TRUE"} }}
  ]"""
    world = world.replace(m.group(0), f"\nDEF THYMIO1 Thymio2 {{\n{m.group(1)}\n{holder}\n}}\n")
    protos = 'EXTERNPROTO "../protos/AtlPhone.proto"\nEXTERNPROTO "../protos/AtlPhoneHolder.proto"\n'
    world = world.replace("\nWorldInfo", "\n" + protos + "\nWorldInfo", 1)
    world = world.replace("GENERATED by atl/world.py", "GENERATED by atl-phone's scripts/phone_twin_world.py from atl-ide's world")
    world += phone_node(phones[args.phone], "THYMIO1.PHONE_MOUNT", args.landscape)
    if args.things:
        world += "".join(thing(*t) for t in THINGS)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "table_phone.wbt").write_text(world)
    for f in args.twin.glob("*.png"):
        shutil.copy(f, args.out / f.name)
    copy_beside(args.out)
    print(args.out / "table_phone.wbt")
    return 0


def copy_beside(out: Path):
    """The PROTOs and textures beside the world's folder, when it is not webots/worlds."""
    for d in ("protos", "textures"):
        dest = out.parent / d
        if dest.resolve() != (HERE / "webots" / d).resolve():
            shutil.copytree(HERE / "webots" / d, dest, dirs_exist_ok=True)


if __name__ == "__main__":
    sys.exit(main())

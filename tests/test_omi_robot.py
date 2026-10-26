# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""The Omi Assist robot's ontology (webots/omi_robot.ttl, payload.ttl): it parses, its mountings match the PROTOs, and
it passes atl-ide's SHACL shapes with its library (skipped when atl-ide is not beside this repository)."""
import math
import re
from pathlib import Path

import pytest

rdflib = pytest.importorskip("rdflib")
from rdflib import Namespace, RDF  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
WEBOTS = HERE / "webots"
IDE = HERE.parent / "atl-ide"
ATL = Namespace("https://atelier-5.github.io/atl/ontology#")
OMI = Namespace("https://atelier-5.github.io/atl/phone#")
SCHEMA = Namespace("https://schema.org/")


def ours():
    g = rdflib.Graph()
    for name in ("payload.ttl", "omi_robot.ttl"):
        g.parse(WEBOTS / name, format="turtle")
    return g


def field(proto, name):
    """A PROTO field's default, as numbers."""
    m = re.search(rf"field\s+\w+\s+{name}\s+([-\d. ]+?)\s*(#|\n)", (WEBOTS / "protos" / proto).read_text())
    return [float(v) for v in m.group(1).split()]


def mounting(g, what):
    m = next(g.subjects(ATL.what, what))
    return [float(v) for v in str(g.value(m, ATL.translation)).split()], [float(v) for v in str(g.value(m, ATL.rotation)).split()]


def test_it_parses_and_every_text_is_in_three_languages():
    g = ours()
    for s in set(g.subjects(SCHEMA.description, None)):
        langs = {o.language for o in g.objects(s, SCHEMA.description)}
        assert langs == {"en", "fr", "de"}, (s, langs)
    for s in set(g.subjects(RDF.type, OMI.Constraint)):
        assert (s, OMI.source, None) in g and (s, ATL.estimated, None) in g, s


def test_the_mountings_are_the_protos_numbers():
    g = ours()
    piH, riserH, neck, tilt = 0.0256, 0.0032 * field("AtlOmiStack.proto", "riser")[0], field("AtlOmiStack.proto", "neck")[0], field("AtlOmiStack.proto", "tilt")[0]
    t, _ = mounting(g, ATL.model_omiPiBox)
    assert t == pytest.approx(field("AtlOmiStack.proto", "translation"))
    assert mounting(g, ATL.model_omiRiser)[0] == pytest.approx([0, 0, piH])
    assert mounting(g, ATL.model_phoneClamp)[0] == pytest.approx([0.02, 0, riserH + 0.0017 + neck], abs=1e-4)
    d, h = field("AtlOmiStack.proto", "thickness")[0], field("AtlOmiStack.proto", "height")[0]
    c, s = math.cos(tilt), math.sin(tilt)
    t, r = mounting(g, ATL.model_phone)
    assert t == pytest.approx([c * (-d / 2) - s * (h / 2), 0, s * (-d / 2) + c * (h / 2)], abs=1e-4)    # the clamp's ballast
    assert r == pytest.approx([0, 1, 0, -tilt])


def test_the_mass_is_the_parts_masses():
    g = ours()
    parts = [g.value(ATL[n], ATL.mass) for n in ("model_omiPiBox", "model_omiRiser", "model_phoneClamp")]
    total = 0.248 + sum(float(p) for p in parts) + field("AtlOmiStack.proto", "phoneMass")[0]
    assert float(g.value(OMI.c_mass, ATL.value)) == pytest.approx(total, abs=0.002)


def test_atl_ides_shapes_pass():
    pyshacl = pytest.importorskip("pyshacl")
    if not (IDE / "atl" / "edge" / "ontology").is_dir():
        pytest.skip("atl-ide is not beside atl-phone")
    data = ours()
    for p in sorted((IDE / "atl" / "library").glob("*.ttl")):
        data.parse(p, format="turtle")
    tbox, shapes = rdflib.Graph(), rdflib.Graph()
    for p in sorted((IDE / "atl" / "edge" / "ontology" / "tbox").glob("*.ttl")):
        tbox.parse(p, format="turtle")
    for p in sorted((IDE / "atl" / "edge" / "ontology" / "shapes").glob("*.ttl")):
        shapes.parse(p, format="turtle")
    ok, _, text = pyshacl.validate(data + tbox, shacl_graph=shapes, inference="rdfs", advanced=True, allow_warnings=True)
    assert ok, text
    assert "sh:Warning" not in text, text     # a warning too: a cable that doesn't reach

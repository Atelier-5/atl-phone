# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
import pytest

from atl_phone import guardian as g

DT = 0.05


def face(x=0.0, y=0.0, size=0.2, familiar=None):
    return {"x": x, "y": y, "size": size, "familiar": familiar}


def run(gd, seconds, faces=None, codes=(), touches=(), **sensors):
    """Steps the guardian for a while; codes and touches come with the first step. Returns every output."""
    outs = []
    for i in range(max(1, round(seconds / DT))):
        s = g.Sensors(faces=list(faces or []), faces_age=0.1 if faces else 9.0, **sensors)
        outs.append(gd.step(s, g.Events(codes=list(codes) if i == 0 else [], touches=list(touches) if i == 0 else []), DT))
    return outs


def said(outs):
    return [o.say for o in outs if o.say]


@pytest.fixture
def gd():
    return g.Guardian("en")


def test_nobody_there_it_guards_and_looks_around(gd):
    outs = run(gd, 4)
    assert {o.state for o in outs} == {"guarding"} and outs[-1].expression == "sleepy"
    assert max(o.angular for o in outs) > 0.2
    assert not said(outs)


def test_a_face_alerts_it_and_it_turns_to_the_face(gd):
    outs = run(gd, 0.5, faces=[face(x=0.6)])
    assert outs[-1].state == "alert" and outs[-1].expression == "surprised"
    assert said(outs) == ["Who's there?"]
    assert outs[-1].angular > 0.5 and outs[-1].gaze == (0.6, 0.0)  # x > 0: to the robot's left, a positive turn
    centred = run(gd, 0.2, faces=[face(x=0.05)])
    assert centred[-1].angular == 0.0


def test_the_owner_card_makes_a_friend_who_is_known_again(gd):
    run(gd, 0.5, faces=[face(familiar=1)])
    outs = run(gd, 0.5, faces=[face(familiar=1)], codes=[g.OWNER_CARD])
    assert outs[-1].state == "friend" and said(outs) == ["Hello, boss! I will remember you."]
    run(gd, g.LOST_AFTER + 1)  # gone, long enough to guard again
    assert gd.state == "guarding"
    outs = run(gd, 0.5, faces=[face(familiar=1)])
    assert outs[-1].state == "friend" and said(outs) == ["Hello again! I kept your desk safe."]
    outs = run(gd, 0.5, faces=[face(familiar=2)])
    assert outs[-1].state == "alert"


def test_another_face_right_after_the_friend_is_not_a_friend(gd):
    run(gd, 0.3, faces=[face(familiar=1)], codes=[g.OWNER_CARD])
    assert gd.state == "friend"
    assert run(gd, 0.3, faces=[face(familiar=2)])[-1].state == "alert"


def test_forget_drops_the_friends(gd):
    run(gd, 0.3, faces=[face(familiar=1)], codes=[g.OWNER_CARD])
    gd.forget()
    run(gd, g.FRIEND_GRACE + 1)
    assert run(gd, 0.3, faces=[face(familiar=1)])[-1].state == "alert"  # number 1 may be someone else now


def test_without_familiar_the_owner_stays_a_friend_only_a_while(gd):
    run(gd, 0.3, faces=[face()], codes=[g.OWNER_CARD])
    assert gd.state == "friend"
    run(gd, g.FRIEND_GRACE / 2)
    assert run(gd, 0.3, faces=[face()])[-1].state == "friend"
    run(gd, g.FRIEND_GRACE + 1)
    assert run(gd, 0.3, faces=[face()])[-1].state == "alert"


def test_a_known_face_without_the_card_is_asked_for_it(gd):
    run(gd, 0.3, faces=[face(familiar=3)])
    run(gd, g.LOST_AFTER + 1)
    assert said(run(gd, 0.3, faces=[face(familiar=3)])) == ["Back again? Show me your card."]


def test_a_stranger_close_for_long_is_an_intruder(gd):
    outs = run(gd, g.INTRUDER_AFTER - 0.5, faces=[face(size=0.5)])
    assert outs[-1].state == "alert"
    outs = run(gd, 1.0, faces=[face(size=0.5)])
    assert outs[-1].state == "intruder" and outs[-1].expression == "angry" and outs[-1].colour == g.COLOURS["intruder"]
    assert said(outs) == ["This is not your desk!"] and sum(o.vibrate for o in outs) == 600
    assert min(o.linear for o in outs) < 0  # backs off a little
    assert run(gd, 0.3, faces=[face(size=0.1)])[-1].state == "alert"  # steps back: alert again
    friendly = g.Guardian()
    run(friendly, 0.3, faces=[face(size=0.5)], codes=[g.OWNER_CARD])
    assert run(friendly, g.INTRUDER_AFTER + 1, faces=[face(size=0.5)])[-1].state == "friend"


def test_lifted_it_is_scared_and_stops(gd):
    outs = run(gd, 0.5, faces=[face(x=0.8)], acc=(0.0, 0.0, 16.0))
    assert outs[-1].state == "scared" and said(outs) == ["Put me down!"]
    assert outs[-1].angular == 0.0 and outs[-1].linear == 0.0
    assert run(gd, 0.5, ground=[40.0, 30.0])[-1].state == "scared"  # the Thymio's ground sensors over nothing
    run(gd, 2.0, ground=[700.0, 700.0])
    assert gd.state != "scared"


def test_a_bump_is_not_a_lift(gd):
    outs = run(gd, 0.05, acc=(0.0, 0.0, 20.0)) + run(gd, 1.0)
    assert all(o.state != "scared" for o in outs)


def test_at_the_edge_it_backs_off_and_turns_away(gd):
    outs = run(gd, 0.1, ground=[50.0, 700.0]) + run(gd, g.EDGE_BACK + g.EDGE_TURN + 0.5, ground=[700.0, 700.0])
    assert outs[0].state == "edge" and said(outs) == ["Whoa, the edge!"]
    assert min(o.linear for o in outs) < 0
    assert sum(o.linear for o in outs) * DT < -0.06  # backs off some 7 cm
    assert min(o.angular for o in outs) < -1.0  # left over the edge: turns right
    assert outs[-1].state == "guarding"


def test_petted_with_a_long_touch(gd):
    outs = run(gd, 0.5, touches=[{"kind": "long", "zone": "centre"}])
    assert outs[-1].state == "petted" and outs[-1].expression == "love" and sum(o.vibrate for o in outs) == 150
    run(gd, g.PETTED_FOR)
    assert gd.state == "guarding"


@pytest.mark.parametrize("lang", ["en", "fr", "de"])
def test_every_line_in_every_language(lang):
    assert set(g.SAY[lang]) == set(g.SAY["en"])
    assert all(len(v) <= 200 for v in g.SAY[lang].values())


def test_every_state_has_a_face_that_exists():
    from atl_phone import contract as c
    assert set(g.FACES) == set(g.COLOURS)
    assert all(e in c.EXPRESSIONS for e in g.FACES.values())


def test_the_setup_page_shows_the_same_owner_card():
    from pathlib import Path
    page = (Path(__file__).resolve().parent.parent / "web" / "setup.js").read_text()
    assert f"OWNER = '{g.OWNER_CARD}'" in page

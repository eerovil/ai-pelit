"""Mäkihyppy v2: a ski-jumping week of four hills, the medal ceremony only at its end (#283).

On each hill all twelve jump the first round and the hill's best ten the second; the points of
every jump add up over the week. v1's meet was one hill, and its podium came after every two jumps.
"""

import pytest

import test_makihyppy as v1
from test_makihyppy import HELPERS, open_game
# The jump, the controls, the layout and the room play as in v1: its tests run on v2 too.
from test_makihyppy import (  # noqa: F401
    test_a_guest_cannot_jump_out_of_turn_or_send_a_made_up_jump, test_doing_nothing_in_the_air_falls_or_drops_short,
    test_the_action_is_green_only_when_a_tap_is_judged_good, test_the_hill_and_the_points_follow_the_real_rules,
    test_the_menu_board_and_pads_fit, test_the_pads_steer_and_the_scene_is_the_action, test_the_take_off_is_generous_in_time,
    test_the_telemark_is_judged_by_time_before_the_snow, test_three_phones_jump_in_turns_and_every_phone_sees_the_same_meet,
    test_turning_the_phone_keeps_the_jump)

URL = "games/makihyppy/v2/"


@pytest.fixture(autouse=True)
def v2(monkeypatch):
    monkeypatch.setattr(v1, "URL", URL)


def test_a_week_alone_has_four_hills_and_one_podium_at_its_end(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[K.comp.hills, K.comp.round, roundText(K.comp)]") == [4, 1, "Mäki 1/4 · kierros 1/2"]
    titles, jumps = [], []
    for n in range(8):
        assert page.evaluate("K.ending") is None, f"a podium before jump {n + 1}"
        page.wait_for_function("th && th.mine", timeout=3000)
        titles.append(page.evaluate("K.F.title(K.comp)"))
        jumps.append(page.evaluate("strong()")["p"])
    # Every hill's two rounds, and the ceremony only now.
    assert titles == [h + " " + str(i + 1) + "/4 · " + r for i, h in enumerate(["Lahti", "Kuopio", "Rovaniemi", "Ruka"])
                      for r in ("1. kierros", "2. kierros")]
    assert page.evaluate("K.ending && K.ending.at") == 0
    me = page.evaluate("K.ending.res[0]")
    assert len(me["marks"]) == 8 and me["fin"] is True
    assert abs(me["best"] - sum(jumps)) < 0.11
    # The week's points on its own high-score list.
    assert "makihyppy|viikko" in page.evaluate("Object.keys(JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono') || '{}')).join()")
    page.evaluate("K.ending.t = 99; K.skip(); step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:makihyppy:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.errors == []


def test_the_week_goes_on_after_missing_a_hills_second_round(site, context):
    page = open_game(site, context)
    page.click("#go")
    # A fall on the first hill: no second round there, the computer jumps it at once, and the
    # player is on the next hill's first round, with no podium in between.
    page.evaluate("lazy()")
    assert page.evaluate("K.ending") is None
    assert page.evaluate("[K.comp.round, K.comp.final, th && th.mine]") == [3, None, True]
    assert page.evaluate("K.comp.throwers.filter(t => t.marks[1]).length") == 10
    assert page.evaluate("K.mine().marks.length") == 1
    # The new hill: everyone, the week's leader last.
    assert page.evaluate("K.comp.order.length === 12 && K.comp.order[11] === K.standings()[0].id")
    assert page.errors == []


def test_a_week_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    first = page.evaluate("fair()")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont").startswith("Jatka mäkiviikkoa (Mäki 1/4 · kierros ")
    page.click("#cont")
    assert page.evaluate("K.mine().marks[0].d") == first["d"]
    assert page.evaluate("[th.mine, K.comp.hills]") == [True, 4]
    assert page.errors == []


def test_a_meet_saved_by_v1_goes_on_as_its_one_hill(site, context):
    # v1's meet half done: twelve jumpers, the first round jumped, no `hills`.
    site.build(v1.ROOT / "games")
    v1page = context.new_page()
    v1page.goto(site.url + "games/makihyppy/v1/")
    v1page.evaluate(HELPERS)
    v1page.click("#go")
    v1page.evaluate("strong()")
    assert v1page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:makihyppy:kesken')).round") == 2
    v1page.close()
    page = open_game(site, context)
    assert page.inner_text("#cont") == "Jatka mäkiviikkoa (Kierros 2/2)"
    page.click("#cont")
    assert page.evaluate("[K.F.hills(K.comp), K.F.title(K.comp)]") == [1, "Toinen kierros"]
    page.evaluate("while (!K.ending) strong()")
    assert page.evaluate("K.ending.res.find(r => r.p === 'me').marks.length") == 2
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    page.click("#go")
    fair1, fair4, fair9, strong9, lazy1 = page.evaluate(
        "[meets(1, 10, fair), meets(4, 10, fair), meets(9, 10, fair), meets(9, 10, strong), meets(1, 10, lazy)]")
    print("weeks won of 10:", fair1, fair4, fair9, strong9, lazy1)
    assert fair1 >= 7           # level 1 is nearly always won by fair play
    assert 1 <= fair4 <= 9      # a middle level is a contest
    assert fair9 <= 3           # the top level is rarely won by fair play...
    assert strong9 >= 1         # ...but a clean jumper can win it
    assert lazy1 == 0           # lazy play never wins, even at level 1
    assert page.errors == []

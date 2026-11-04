"""Korkeushyppy v13 and Seiväshyppy v14 (#399): passing many heights takes two taps, and the bar
rises in bigger steps, except in Ottelu, which already takes every second height (#294).

games/korkeushyppy/v14, games/seivashyppy/v15.
"""

import pytest
from conftest import ROOT
from test_yleisurheilu_vuorot import MARK, on_turn, room

pytestmark = pytest.mark.games("korkeushyppy", "seivashyppy")

EVENTS = ["korkeushyppy/v14", "seivashyppy/v15"]
# The first heights at level 1, and in a match (where Ottelu then keeps every second one).
STEPS = {
    "korkeushyppy/v14": ([1.5, 1.6, 1.7, 1.8, 1.85, 1.9, 1.93], [1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.78]),
    "seivashyppy/v15": ([3.2, 3.4, 3.6, 3.8, 4.0, 4.2, 4.4, 4.5], [3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9]),
}
# Where this phone's buttons are: Korkeushyppy keeps all in actBoxes, Seiväshyppy in passBox and
# pickBoxes. The boxes' x is in the scene in the first, on the screen in the second.
BOX = """k => {
  const b = typeof pickBoxes !== 'undefined'
    ? (k === 'pass' ? passBox : pickBoxes.find(p => p.k === k))
    : actBoxes.map(p => Object.assign({}, p, { x: p.x + SX })).find(p => p.k === k);
  return b ? { x: b.x + b.w / 2, y: b.y + b.h / 2 } : null;
}"""


def open_event(site, browser, path, size=(360, 740)):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}games/{path}/")
    return page


def my_turn(page):
    """Waits for this phone's turn and skips the standings before it."""
    page.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')")
    page.evaluate("th.t = 99")
    page.wait_for_function("th.phase === 'ready'")


def tap(page, k):
    page.wait_for_function(f"({BOX})({k!r})")
    at = page.evaluate(f"({BOX})({k!r})")
    page.mouse.click(at["x"], at["y"])


@pytest.mark.parametrize("path", EVENTS)
def test_the_bar_rises_in_bigger_steps(site, browser, path):
    page = open_event(site, browser, path)
    want = STEPS[path][0]
    assert page.evaluate("heightsFor(1)")[: len(want)] == want


@pytest.mark.parametrize("path", EVENTS)
def test_in_a_match_the_steps_stay_as_they_were(site, browser, path):
    page = open_event(site, browser, path)
    page.evaluate(
        """p => new Promise(done => {
            window.Ottelu = {};  // what the event's page looks for in its parent
            const f = document.createElement('iframe');
            f.src = location.origin + '/games/' + p + '/';
            f.onload = done;
            document.body.append(f);
        })""",
        path,
    )
    want = STEPS[path][1]
    assert page.frames[-1].evaluate("heightsFor(1)")[: len(want)] == want


@pytest.mark.parametrize("path", EVENTS)
@pytest.mark.parametrize("size", [(360, 740), (740, 360)])
def test_two_taps_pass_eight_heights(site, browser, path, size):
    page = open_event(site, browser, path, size)
    page.click("#go")
    my_turn(page)
    start = page.evaluate("K.comp.hi")
    tap(page, "pass")
    tap(page, "to7")
    page.wait_for_function(f"K.comp.hi === {start + 8} && th && th.mine", timeout=4000)
    rec = page.evaluate("K.current().rec")
    assert rec[start : start + 8] == ["-"] * 8
    # The chosen height is a turn like any other: nothing passes it by itself.
    my_turn(page)
    assert page.evaluate("K.comp.hi") == start + 8
    assert page.evaluate("passTo") == 0
    assert page.errors == []


@pytest.mark.parametrize("path", EVENTS)
def test_the_panel_can_be_cancelled(site, browser, path):
    page = open_event(site, browser, path)
    page.click("#go")
    my_turn(page)
    seq = page.evaluate("K.comp.seq")
    tap(page, "pass")
    tap(page, "back")
    page.wait_for_function("!th.pick")
    assert page.evaluate("K.comp.seq") == seq
    assert page.evaluate("th.phase") == "ready"
    tap(page, "pass")  # the skip button is back


@pytest.mark.parametrize("path", EVENTS)
def test_a_new_meet_forgets_the_height_aimed_at(site, browser, path):
    page = open_event(site, browser, path)
    page.click("#go")
    my_turn(page)
    page.evaluate("passTo = 2.9; K.quit()")
    assert page.evaluate("passTo") == 0


@pytest.mark.parametrize("path", EVENTS)
def test_with_friends_a_phone_passes_its_turns_up_to_the_height(site, browser, path):
    relay, pages, code = room(site, browser, path, ["Eero", "Aino"])
    host, aino = pages
    me_host, me_aino = (p.evaluate("AiPelitRooms.me") for p in pages)

    def host_turn():
        n = host.evaluate("K.comp.seq")
        host.evaluate(f"K.report({n}, {MARK})")
        host.wait_for_function(f"K.comp.over || K.comp.seq > {n}", timeout=5000)

    while on_turn(host) != me_aino:
        host_turn()
    n = host.evaluate("K.comp.seq")
    aino.wait_for_function(f"K.comp && K.comp.seq === {n} && th && th.mine")
    my_turn(aino)
    hi = host.evaluate("K.comp.hi")
    aino.evaluate("pass(K.comp.heights[K.comp.hi + 3])")
    # The host jumps on; Aino's phone answers her turns under the height by itself.
    for _ in range(40):
        host.wait_for_function(
            f"K.current() && (K.current().p === {me_host!r} || K.comp.hi === {hi + 3})", timeout=6000
        )
        if host.evaluate(f"K.comp.hi === {hi + 3} && K.current().p === {me_aino!r}"):
            break
        host_turn()
    else:
        raise AssertionError("the bar never reached the height")
    rec = host.evaluate(f"K.comp.throwers.find(t => t.p === {me_aino!r}).rec")
    assert rec[hi : hi + 3] == ["-"] * 3
    aino.wait_for_function(f"th && th.mine && K.comp.hi === {hi + 3}")
    assert aino.evaluate("passTo") in (0, host.evaluate(f"K.comp.heights[{hi + 3}]"))
    assert host.errors == [] and aino.errors == []


@pytest.mark.parametrize("path", EVENTS)
def test_on_a_390_px_phone_the_panel_works_too(site, browser, path):
    page = open_event(site, browser, path, (390, 844))
    page.click("#go")
    my_turn(page)
    start = page.evaluate("K.comp.hi")
    tap(page, "pass")
    tap(page, "to11")
    page.wait_for_function(f"K.comp.hi === {start + 12} && th && th.mine", timeout=4000)


@pytest.mark.parametrize("path", EVENTS)
def test_a_reload_while_passing_gives_the_next_turn_back_to_the_player(site, browser, path):
    page = open_event(site, browser, path)
    page.click("#go")
    my_turn(page)
    start = page.evaluate("K.comp.hi")
    page.evaluate("pass(K.comp.heights[K.comp.hi + 8])")
    page.wait_for_function(f"K.comp.hi > {start}", timeout=4000)
    page.reload()
    page.click("#cont")
    my_turn(page)  # no height aimed at any more: the turn stays until the player acts
    hi = page.evaluate("K.comp.hi")
    assert start < hi <= start + 8
    assert page.evaluate("passTo") == 0
    assert page.evaluate("K.current().rec").count("-") == hi - start
    assert page.errors == []


@pytest.mark.parametrize("path", EVENTS)
def test_a_meet_saved_with_the_old_steps_goes_on_with_them(site, browser, path):
    page = open_event(site, browser, path)
    page.click("#go")
    my_turn(page)
    old = STEPS[path][1]
    page.evaluate(
        """old => { const k = K.load('kesken', null); k.heights = old.concat(k.heights.slice(old.length)); K.save('kesken', k); }""",
        old,
    )
    page.reload()
    page.click("#cont")
    my_turn(page)
    assert page.evaluate("K.comp.heights")[: len(old)] == old
    tap(page, "pass")
    assert page.evaluate("nextHeights()")[0] == old[page.evaluate("K.comp.hi") + 1]


@pytest.mark.parametrize("path", EVENTS)
def test_a_failure_before_the_pass_still_counts(site, browser, path):
    page = open_event(site, browser, path)
    page.click("#go")
    my_turn(page)
    start = page.evaluate("K.comp.hi")
    page.evaluate("K.report(K.comp.seq, 'X')")
    page.wait_for_function(f"th && th.mine && K.current() && (K.current().rec[{start}] || '') === 'X'", timeout=4000)
    my_turn(page)
    page.evaluate("pass(K.comp.heights[K.comp.hi + 3])")
    page.wait_for_function(f"K.comp.hi === {start + 3} && th && th.mine", timeout=4000)
    me = page.evaluate("(({ rec, run, out }) => ({ rec, run, out }))(K.current())")
    assert me["rec"][start : start + 3] == ["X-", "-", "-"]
    assert me["run"] == 1 and me["out"] is False

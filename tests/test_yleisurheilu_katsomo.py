"""The friends watching an athletics meet stand in the background (#341, yleisurheilu-7): drawn
before the athlete, in a stadium behind the boards, and a spectator's tap on the scene walks its own
figure there on every phone.

The events' versions on yleisurheilu-7: games/pituushyppy/v13, games/keihas/v12, games/kuula/v6,
games/korkeushyppy/v9, games/seivashyppy/v10, games/moukari/v9, games/makihyppy/v6.
"""

import json

import pytest
from test_yleisurheilu_vuorot import MARK, on_turn, room

# Each event and the function that draws its athlete on the runway or in the circle.
EVENTS = {
    "pituushyppy/v13": "drawJumper",
    "keihas/v12": "drawAthlete",
    "kuula/v6": "drawPutter",
    "korkeushyppy/v9": "drawAthlete",
    "seivashyppy/v10": "drawRunner",
    "moukari/v9": "drawThrower",
    "makihyppy/v6": "drawJumper",
}
# The events in a stadium: the friends stand behind the boards in front of the stands.
STADIUM = {"pituushyppy/v13", "keihas/v12", "kuula/v6", "korkeushyppy/v9", "seivashyppy/v10"}


def watching(site, browser, path):
    """A room of three on the first turn: the phone on turn and the two watching (a guest first)."""
    relay, pages, code = room(site, browser, path, ["Eero", "Aino", "Ville"])
    host = pages[0]
    pid = on_turn(host)
    for p in pages:
        p.wait_for_function(f"K.current() && K.current().p === {json.dumps(pid)}", timeout=5000)
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    athlete = ids[pid]
    fans = sorted((p for p in pages if p is not athlete), key=lambda p: p is host)
    for p in pages:
        p.wait_for_function("K.fanSpots.length === 2", timeout=5000)
    return relay, pages, athlete, fans


def tap_scene(page, x):
    """Taps the scene at x (CSS px from the screen's left), below the HUD and above the controls."""
    y = page.evaluate("ctrlTop - 40")
    page.mouse.click(x, y)


@pytest.mark.parametrize("path", EVENTS)
def test_the_friends_watching_are_drawn_behind_the_athlete(site, browser, path):
    relay, pages, athlete, fans = watching(site, browser, path)
    fan = fans[0]
    fan.evaluate(
        """name => {
          window.__order = [];
          const fans = K.drawFans, draw = window[name];
          K.drawFans = (x, b) => { __order.push('fans'); return fans(x, b); };
          window[name] = function () { __order.push('athlete'); return draw.apply(this, arguments); };
        }""",
        EVENTS[path],
    )
    fan.wait_for_function("__order.length >= 6", timeout=5000)
    order = fan.evaluate("__order.slice(0, 6)")
    assert order[0] == "fans" and "athlete" in order
    # In every frame the friends come first, the athlete over them.
    assert order == ["fans", "athlete"] * 3
    if path in STADIUM:
        # Their feet behind the boards, above the runway.
        assert fan.evaluate("K.fanSpots.every(f => f.y < groundY - 10)")
    for p in pages:
        assert p.errors == []
        p.context.close()


@pytest.mark.parametrize("path", EVENTS)
def test_a_tap_walks_my_own_figure_there_on_every_phone(site, browser, path):
    relay, pages, athlete, fans = watching(site, browser, path)
    fan, other = fans
    me = fan.evaluate("K.mine().id")
    them = other.evaluate("K.mine().id")
    before = {p: p.evaluate(f"K.fanSpots.find(f => f.id === {json.dumps(them)}).x") for p in pages}
    # Nobody walks by themselves.
    fan.wait_for_timeout(600)
    for p in pages:
        assert p.evaluate(f"K.fanSpots.find(f => f.id === {json.dumps(them)}).x") == before[p]
    x0 = fan.evaluate(f"K.fanSpots.find(f => f.id === {json.dumps(me)}).x")
    target = 60 if x0 > 150 else 280
    tap_scene(fan, target)
    want = fan.evaluate(f"K.spot[{json.dumps(me)}]")
    assert want is not None
    for p in pages:
        p.wait_for_function(f"K.spot[{json.dumps(me)}] === {want}", timeout=5000)
    # It walks there (not a jump), on every phone to the same place.
    fan.wait_for_timeout(150)
    mid = fan.evaluate(f"K.fanSpots.find(f => f.id === {json.dumps(me)}).x")
    assert abs(mid - target) > 10
    for p in pages:
        p.wait_for_function(
            f"Math.abs(K.fanSpots.find(f => f.id === {json.dumps(me)}).x - {target}) < 6", timeout=8000
        )
        assert p.evaluate(f"K.fanSpots.find(f => f.id === {json.dumps(them)}).x") == before[p]
    # A tap on the phone on turn does not move anyone; the turn is its own.
    assert athlete.evaluate("K.tapFans(100)") is False
    for p in pages:
        assert p.errors == []
        p.context.close()


@pytest.mark.parametrize("path", ["pituushyppy/v13", "moukari/v9"])
def test_both_watching_tap_at_once_and_a_reloaded_phone_gets_the_spots(site, browser, path):
    relay, pages, athlete, fans = watching(site, browser, path)
    fan, host = fans
    me = fan.evaluate("K.mine().id")
    hid = host.evaluate("K.mine().id")
    # The guest and the host tap at the same moment: each walks to its own spot on every phone.
    fan.evaluate("K.tapFans(40)")
    host.evaluate("K.tapFans(300)")
    mine = fan.evaluate(f"K.spot[{json.dumps(me)}]")
    want = host.evaluate(f"K.spot[{json.dumps(hid)}]")
    for p in pages:
        p.wait_for_function(
            f"K.spot[{json.dumps(me)}] === {mine} && K.spot[{json.dumps(hid)}] === {want}", timeout=5000
        )
    fan.evaluate("K.cheer()")
    for p in pages:
        p.wait_for_function(f"K.cheers[{json.dumps(me)}]", timeout=5000)
    # The guest reloads: the host gives it the spots back with the meet.
    fan.reload()
    fan.wait_for_function("K.comp && K.comp.seq >= 0 && !K.comp.wait", timeout=10000)
    fan.wait_for_function(
        f"K.spot[{json.dumps(hid)}] === {want} && K.spot[{json.dumps(me)}] === {mine}", timeout=5000
    )
    for p in pages:
        assert p.errors == []
        p.context.close()


def xs(page):
    return page.evaluate("Object.fromEntries(K.fanSpots.map(f => [f.id, f.x]))")


@pytest.mark.parametrize("path", ["pituushyppy/v13", "korkeushyppy/v9"])
def test_nobody_moves_as_the_turn_goes_round_or_a_new_meet_starts(site, browser, path):
    relay, pages, athlete, fans = watching(site, browser, path)
    host = pages[0]
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    seen = {}  # friend id -> where it stood while watching, on the host's screen

    def note():
        host.wait_for_timeout(700)  # long enough to walk a good way, had it started to
        for k, v in xs(host).items():
            assert seen.setdefault(k, v) == v, "a friend nobody tapped moved"

    note()
    # Two turn changes, nobody tapping: each friend watches from the same place every time.
    for _ in range(2):
        pid = on_turn(host)
        n = host.evaluate("K.comp.seq")
        ids[pid].evaluate(f"K.report({n}, {MARK})")
        host.wait_for_function(f"K.comp.seq > {n} && K.current() && K.current().p !== {json.dumps(pid)}")
        host.wait_for_function("K.fanSpots.length === 2", timeout=5000)
        note()
    assert len(seen) == 3
    # A friend walks away, then the host starts a new meet in the same room: everyone starts from
    # their own place again, without walking there from where they stood before.
    fan = next(p for p in pages if p.evaluate("K.fans().some(f => f.p === AiPelitRooms.me)") and p is not host)
    fid = fan.evaluate("K.mine().id")
    tap_scene(fan, 30)
    for p in pages:  # it has walked to the row's left end
        p.wait_for_function(f"Math.abs(K.fanSpots.find(f => f.id === {json.dumps(fid)}).x - 30) < 3", timeout=8000)
    room0 = host.evaluate("K.comp.room")
    host.evaluate("AiPelitRooms.endRound(); AiPelitRooms.backToRoom('', 'win')")
    host.wait_for_selector("#aipr-start", state="visible", timeout=5000)
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function(
            f"K.comp && K.comp.room !== {json.dumps(room0)} && K.comp.seq >= 0 && K.fanSpots.length === 2", timeout=8000
        )
        assert p.evaluate("Object.keys(K.spot).length") == 0
        # K.fanSpots is what the last frame drew, and the game draws the old meet's friends behind
        # the room screen too: wait for frames drawn with the new meet before reading it (#362).
        p.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    first = xs(host)
    host.wait_for_timeout(700)
    assert xs(host) == first
    # Each stands on its own place: its order among the friends, along the row (h 40 from the box).
    for p in pages:
        assert p.evaluate("""(() => {
          const all = K.comp.throwers.filter(t => t.p !== null), l = 12 + 16, r = SW - 12 - 16;
          return K.fanSpots.every(f => Math.abs(f.x - (l + (all.findIndex(t => t.id === f.id) + 0.5) / all.length * (r - l))) < 1);
        })()""")
    for p in pages:
        assert p.errors == []
        p.context.close()

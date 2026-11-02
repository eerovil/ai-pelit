"""The friends watching an athletics meet stand in the background (#341, yleisurheilu-7): drawn
before the athlete, in a stadium behind the boards, and a spectator's tap on the scene walks its own
figure there on every phone.

The events' versions on yleisurheilu-7: games/pituushyppy/v13, games/keihas/v12, games/kuula/v6,
games/korkeushyppy/v9, games/seivashyppy/v10, games/moukari/v9, games/makihyppy/v6.
"""

import json

import pytest
from test_yleisurheilu_vuorot import on_turn, room

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


def test_a_cheer_still_shows_and_a_reloaded_phone_gets_the_spots(site, browser):
    path = "pituushyppy/v13"
    relay, pages, athlete, fans = watching(site, browser, path)
    fan, host = fans
    me = fan.evaluate("K.mine().id")
    tap_scene(host, 300)
    hid = host.evaluate("K.mine().id")
    want = host.evaluate(f"K.spot[{json.dumps(hid)}]")
    fan.wait_for_function(f"K.spot[{json.dumps(hid)}] === {want}", timeout=5000)
    fan.evaluate("K.cheer()")
    for p in pages:
        p.wait_for_function(f"K.cheers[{json.dumps(me)}]", timeout=5000)
    # The guest reloads: the host gives it the spots back with the meet.
    fan.reload()
    fan.wait_for_function("K.comp && K.comp.seq >= 0 && !K.comp.wait", timeout=10000)
    fan.wait_for_function(f"K.spot[{json.dumps(hid)}] === {want}", timeout=5000)
    for p in pages:
        assert p.errors == []
        p.context.close()

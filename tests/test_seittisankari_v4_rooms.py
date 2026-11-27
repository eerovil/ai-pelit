"""Seittisankari v3 with friends (#529, #560): the host runs the round, each phone moves its own hero.
The race is to a random building's roof (Eero's choice), everyone from the same spot; the host
decides who stood on it first."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/seittisankari/v4/"
READY = "mode === 'netplay' && net && net.ready && world && world.hero"
ON_ROOF = """() => { const b = goalBox(), t = roofTop(b), h = world.hero;
  Object.assign(h, { x: t.x, y: b.h, z: t.z, vx: 0, vy: 0, vz: 0, st: 'ground', anchor: null }); }"""


@pytest.fixture
def phone(site, browser):
    shutil.copytree(ROOT / "games" / "seittisankari", site.games / "seittisankari")
    site.build()
    relay = Relay()
    contexts = []

    def make(name, width=360, height=740):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        p.errors = []
        p.on("pageerror", lambda e: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.wait_for_function("typeof mode !== 'undefined'")
        return p

    make.relay = relay
    yield make
    for c in contexts:
        c.close()


def room(phone, n=2):
    host = phone("Testi1")
    host.click("#friends")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    pages = [host]
    for i in range(1, n):
        p = phone("Testi" + str(i + 1))
        p.click("#friends")
        p.fill("#aipr-codeIn", code)
        p.click("#aipr-joinBtn")
        p.wait_for_function("AiPelitRooms.inRoom")
        pages.append(p)
    host.wait_for_function(f"AiPelitRooms.members.filter(p => p.on).length === {n}")
    return pages


def start(pages):
    pages[0].click("#aipr-start")
    for p in pages:
        p.wait_for_function(READY, timeout=15000)


def test_every_phone_races_to_the_same_roof_from_the_same_spot(phone):
    pages = room(phone, 3)
    start(pages)
    goals = [p.evaluate("net.goal") for p in pages]
    assert goals[0] >= 0 and len(set(goals)) == 1
    b = pages[0].evaluate("(() => { const b = goalBox(); return [b.h, b.tower || false]; })()")
    assert 30 <= b[0] <= 140 and not b[1]
    spots = pages[0].evaluate("net.players.map(p => [p.x, p.z])")
    assert len(spots) == 3
    xs, zs = [s[0] for s in spots], [s[1] for s in spots]
    assert max(xs) - min(xs) <= 3.1 and max(zs) - min(zs) <= 3.1          # one spot, side by side
    for p in pages:
        d = p.evaluate("Math.hypot(world.hero.x - roofTop(goalBox()).x, world.hero.z - roofTop(goalBox()).z)")
        assert 180 < d < 260
        assert p.evaluate("world.flag && world.flag.x === roofTop(goalBox()).x")
    assert all(p.errors == [] for p in pages)


def test_every_start_spot_is_on_a_street_for_any_roof_and_side(phone):
    host = phone("Testi1")
    # The spots as startSpot() gives them, before a frame could push a hero out of a wall.
    bad = host.evaluate("""(() => { const r = rng(7), bad = [];
      const ok = CITY.filter(b => !b.tower && b.h >= 30 && b.h <= 140 &&
        Math.max(Math.abs((b.x0 + b.x1) / 2), Math.abs((b.z0 + b.z1) / 2)) < EDGE - RACE_R - 20);
      for (let k = 0; k < 400; k++) {
        const g = ok[Math.floor(r() * ok.length)], a = r() * TAU;
        for (const [mode, goal] of [['kilpa', g], ['vapaa', null]])
          for (let i = 0; i < 8; i++) { const s = startSpot(i, 8, mode, goal, a);
            if (supportAt(s.x, s.z, 0.5) > 0) bad.push([mode, k, i, s.x, s.z]); }
      } return bad; })()""")
    assert bad == []


def test_the_guest_on_the_roof_wins_and_every_phone_ends_on_one_result(phone):
    host, guest = room(phone, 2)
    start([host, guest])
    gid = guest.evaluate("AiPelitRooms.me")
    # Standing below the roof claims nothing.
    host.evaluate(f"hostClaim({json.dumps(gid)})")
    assert host.evaluate("net.over") is False
    guest.evaluate(ON_ROOF)
    for p in (host, guest):
        p.wait_for_function("result && result.net", timeout=10000)
    assert host.evaluate("result.winRow.id") == gid == guest.evaluate("result.winRow.id")
    assert guest.evaluate("result.won") is True and host.evaluate("result.won") is False
    assert host.evaluate("result.rows.map(r => r.id)") == guest.evaluate("result.rows.map(r => r.id)")
    assert guest.evaluate("result.rows[0].t") is not None and host.evaluate("result.rows[1].t") is None
    assert "voitit" in guest.locator("#endTitle").inner_text().lower() or guest.locator("#end").is_visible()
    assert host.errors == [] and guest.errors == []


def test_the_free_mode_has_no_goal_and_starts_by_the_tower(phone):
    host, guest = room(phone, 2)
    host.click("#ss-room button[data-m='vapaa']")
    start([host, guest])
    for p in (host, guest):
        assert p.evaluate("net.mode") == "vapaa"
        assert p.evaluate("world.flag") is None and p.evaluate("goalBox()") is None
        assert not p.evaluate("world.crooks && world.crooks.length")   # robber missions are solo (v4, #561)
        assert p.evaluate("Math.hypot(world.hero.x - roofTop(T_BOX).x, world.hero.z - roofTop(T_BOX).z)") < 60   # 30 m out, then onto the street
    assert host.errors == [] and guest.errors == []


def test_a_guest_who_reloads_comes_back_where_it_was(phone):
    host, guest = room(phone, 2)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    # Onto another building's roof, a spot the game keeps (a street spot moved by hand may be in a wall).
    guest.evaluate("""() => { const b = CITY.find(b => b !== goalBox() && b.h > 20), h = world.hero;
      Object.assign(h, { x: (b.x0 + b.x1) / 2, y: b.h, z: (b.z0 + b.z1) / 2, vx: 0, vy: 0, vz: 0, st: 'ground', anchor: null }); }""")
    guest.wait_for_function("world.hero.st === 'ground'")
    x0 = guest.evaluate("world.hero.x")
    host.wait_for_function(f"Math.abs(playerOf({gid}).x - {x0}) < 1")
    guest.reload()
    guest.wait_for_function(READY, timeout=15000)
    assert abs(guest.evaluate("world.hero.x") - x0) < 1
    assert guest.evaluate("net.goal") == host.evaluate("net.goal")
    assert host.errors == [] and guest.errors == []


def test_touches_during_a_pause_do_nothing_when_it_ends(phone):
    host, guest = room(phone, 2)
    start([host, guest])
    host.evaluate("() => { stick = { id: 9, x0: 50, y0: 500, x: 50, y: 440 }; webPtr = 8; }")   # thumbs held
    phone.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused", timeout=10000)
    host.wait_for_function("stick === null && webPtr === null")   # held ones are let go
    b = host.evaluate("buttons()")
    host.evaluate("""([x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent('pointerdown',
      { pointerId: 3, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))""", [b["jump"]["x"], b["jump"]["y"]])
    assert host.evaluate("[jumpQ, webPtr, stick]") == [False, None, None]
    assert host.errors == []


def test_the_others_see_a_pulling_heros_web(phone):
    # Veto (#560): a pull sends its state and its web's end like a swing does.
    host, guest = room(phone, 2)
    start([host, guest])
    guest.evaluate("""() => { const h = world.hero;
      h.st = 'pull'; h.pull = { x: h.x, y: h.y + 300, z: h.z, kind: 'roof', box: -1, nx: 0, nz: 0 }; h.pullT = 0;
      h.anchor = { x: h.x, y: h.y + 300, z: h.z, box: -1 }; }""")
    host.wait_for_function("""net.players.some(p => p !== net.me && p.st === 'pull' && p.a && p.a.y > 100)""", timeout=8000)
    assert host.errors == [] and guest.errors == []


def test_a_room_draws_the_veto_crosshair_and_hint(phone):
    # Helper check on #562: the room's screen drew neither, and the hint was marked seen unseen.
    host, guest = room(phone, 2)
    start([host, guest])
    r = guest.evaluate("""() => {
      const calls = { aim: 0, hint: 0 }, a = drawAim, d = drawHints3;
      drawAim = h => { calls.aim++; return a(h); }; drawHints3 = () => { calls.hint++; return d(); };
      hintT = 99; hint3T = 0;
      drawNetHUD(world);
      drawAim = a; drawHints3 = d;
      return calls;
    }""")
    assert r == {"aim": 1, "hint": 1}
    assert host.errors == [] and guest.errors == []

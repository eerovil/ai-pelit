"""Pilkkiminen v3 (#291): a nibble felt at the jig, so a fish is noticed without a sounder; and
everything of v2 (#289): walking on the ice, the sounder chosen in the menu, baits, and fish that
school, fear the pike, and one giant pike.

The world steps by hand (`run()`); each phone in a room is its own Chromium context, and the room
relay is `Relay` from test_rooms_lib.
"""

import json
import math

import pytest

from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/pilkki/v3/"

RUN = "() => { window.run = (cond, max = 30) => { for (let t = 0; t < max && cond(); t += DT) { update(DT); closing(DT); } }; }"

# Plays a fight as a careful player: reel while the line is easy, let go when it gets tight.
FIGHT = """() => {
  for (let t = 0; t < 180 && phase === 'fight'; t += DT) {
    holding = fight.T > 0.85 ? 0 : fight.T < 0.6 ? 1 : holding;
    update(DT);
  }
  holding = 0;
  return phase;
}"""

# Twitches the jig on the beat until the fish bites (or n twitches go by).
ON_BEAT = """(n) => {
  let k = 0;
  for (let i = 0; i < 60 / DT && phase === 'jig' && k < n; i++) {
    const before = Math.floor(beat);
    update(DT);
    if (Math.floor(beat) !== before) { twitch(); k++; }
  }
  return [phase, k];
}"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def start(site, context, radar="ei"):
    page = open_game(site, context)
    page.click(f'#gear button[data-t="{radar}"]')
    page.click("#go")
    return page


# The angler at a hole in the middle of the lake, the lake's only fish waiting at 2 m beside the jig.
def ready(page, sp="ahven", g=200, bait=None):
    page.evaluate(f"""() => {{
      rivals = []; schools = [];
      stand(LAKE_W / 2, LAKE_H / 2);
      const h = hole(me.x, me.y, 'me', true); holes.push(h); atHole(h); jigD = 2;
      const f = newFish(lake.spots[0], '{sp}'); f.g = {g}; f.d = 2; f.lx = f.wx = f.gx = me.x + 0.4; f.ly = f.wy = f.gy = me.y; f.linger = 999;
      pond = [f]; sight();
      {f"bait = '{bait}';" if bait else ""}
      run(() => !target, 3);
    }}""")


def tap(page, b):
    page.mouse.click(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)


def test_a_contest_starts_on_the_ice_by_the_shore(site, context):
    page = start(site, context)
    assert page.evaluate("[phase, holes.length, left > 299]") == ["ice", 0, True]
    assert 0.8 < page.evaluate("shoreOf(me.x, me.y)") < 0.9
    # The lake is far bigger than the screen.
    assert page.evaluate("LAKE_W * icePx > 4 * W && LAKE_H * icePx > 2 * H")
    assert page.errors == []


def test_a_tap_walks_there_and_the_button_drills_a_hole_where_the_angler_stands(site, context):
    page = start(site, context)
    page.evaluate("stand(LAKE_W / 2, LAKE_H / 2)")
    # A tap 10 m to the right of the angler: it walks there.
    page.mouse.click(180 + 10 * page.evaluate("icePx"), 370)
    page.evaluate("run(() => !standing(), 5)")
    assert abs(page.evaluate("me.x - LAKE_W / 2") - 10) < 0.6 and abs(page.evaluate("me.y - LAKE_H / 2")) < 2
    tap(page, page.evaluate("actBtn"))
    assert page.evaluate("phase") == "drill"
    page.evaluate("turnAuger(TURNS * Math.PI * 2)")
    assert page.evaluate("[phase, holes.length, spot.drilled, Math.abs(spot.x - me.x) < 0.01, spot.depth === depthAt(me.x, me.y)]") == ["jig", 1, True, True, True]
    # Up onto the ice, a walk away and back: the old hole needs no drilling.
    tap(page, page.evaluate("walkBtn"))
    assert page.evaluate("phase") == "ice"
    page.evaluate("me.tx = me.x + 8; run(() => !standing(), 5); me.tx = me.x - 8.3; run(() => !standing(), 5)")
    assert page.evaluate("holeHere() === holes[0]") is True
    tap(page, page.evaluate("actBtn"))
    assert page.evaluate("[phase, holes.length]") == ["jig", 1]
    assert page.errors == []


def test_pinching_the_ice_zooms_the_view_but_never_shows_the_whole_lake(site, context):
    page = start(site, context)
    page.evaluate("stand(LAKE_W / 2, LAKE_H / 2)")
    base = page.evaluate("icePx")
    pinch = """([d0, d1]) => {
      const ev = (type, id, px) => c.dispatchEvent(new PointerEvent(type, { pointerId: id, clientX: px, clientY: 370, bubbles: true }));
      ev('pointerdown', 1, 180 - d0 / 2); ev('pointerdown', 2, 180 + d0 / 2);
      for (let k = 1; k <= 5; k++) { const d = d0 + (d1 - d0) * k / 5; ev('pointermove', 1, 180 - d / 2); ev('pointermove', 2, 180 + d / 2); }
      ev('pointerup', 1, 180 - d1 / 2); ev('pointerup', 2, 180 + d1 / 2);
    }"""
    page.evaluate(pinch, [100, 200])
    assert abs(page.evaluate("icePx") - 2 * base) < 0.5
    # A pinch is not a walk.
    assert page.evaluate("standing()") is True
    page.evaluate(pinch, [300, 10])
    assert page.evaluate("zoom") == 0.35
    assert page.evaluate("LAKE_W * icePx > W && LAKE_H * icePx > H * 0.5") is True
    # And a tap still walks, at the new scale.
    page.mouse.click(180 + 10 * page.evaluate("icePx"), 370)
    page.evaluate("run(() => !standing(), 5)")
    assert abs(page.evaluate("me.x - LAKE_W / 2") - 10) < 0.6


def test_the_fish_show_through_the_ice_only_in_the_debug_address(site, context):
    page = start(site, context)
    assert page.evaluate("DEBUG") is False
    page.goto(site.url + URL + "?kalat")
    assert page.evaluate("DEBUG") is True


def test_the_angler_cannot_walk_off_the_lake(site, context):
    page = start(site, context)
    page.evaluate("stand(LAKE_W - 10, LAKE_H / 2)")
    page.mouse.click(359, 370)
    page.evaluate("run(() => !standing(), 10)")
    assert page.evaluate("shoreOf(me.x, me.y)") <= 0.951


def test_without_a_sounder_no_fish_show_and_the_depth_is_found_by_the_jig(site, context):
    page = start(site, context)
    ready(page)
    page.evaluate("spot.known = false")
    assert page.evaluate("shownFish()") == []
    # The jig let down to the bottom tells the depth.
    page.evaluate("jigGoal = 99; run(() => jigGoal !== null, 10)")
    assert page.evaluate("spot.known") is True
    # A new hole with a sounder: the depth is known at once.
    page.evaluate("radar = 'kaiku'; toIce(); me.x = me.tx = me.x + 5; iceAction()")
    assert page.evaluate("[phase, spot.known]") == ["drill", True]


def test_the_flasher_shows_only_what_is_under_the_hole_and_roughly_its_size(site, context):
    page = start(site, context, "kaiku")
    ready(page)
    page.evaluate("""() => {
      const near = newFish(lake.spots[0], 'lahna'); near.g = 2000; near.lx = near.wx = spot.x + 0.3; near.ly = near.wy = spot.y; near.d = 4; near.school = 0; near.linger = 999;
      const off = newFish(lake.spots[0], 'ahven'); off.lx = off.wx = spot.x + 3; off.ly = off.wy = spot.y; off.school = 0; off.linger = 999;
      pond.push(near, off); sight(); window.near = near;
    }""")
    shown = page.evaluate("shownFish()")
    ids = page.evaluate("[pond[0].id, near.id]")
    assert sorted(m["id"] for m in shown) == sorted(ids)
    big = next(m for m in shown if m["id"] == ids[1])
    assert abs(big["d"] - 4) < 0.3 and 0.8 < big["size"] < 1.7


def test_the_sonar_shows_the_fish_round_the_hole_but_not_exactly(site, context):
    page = start(site, context, "tutka")
    ready(page)
    page.evaluate("for (let i = 0; i < 8; i++) { const f = newFish(lake.spots[0], 'ahven'); f.lx = f.wx = spot.x + i - 4; f.ly = f.wy = spot.y; f.school = 0; f.linger = 999; pond.push(f); } sight()")
    page.evaluate("run(() => true, 2)")
    real = page.evaluate("Object.fromEntries(fish.map(f => [f.id, [f.x, f.d]]))")
    shown = page.evaluate("shownFish()")
    assert len(shown) == len(real)
    offs = [math.hypot(m["x"] - real[str(m["id"])][0], m["d"] - real[str(m["id"])][1]) for m in shown]
    assert max(offs) < 1.5 and sum(o > 0.05 for o in offs) >= len(offs) // 2


def test_a_fish_coming_to_the_jig_is_felt_as_a_nibble_without_a_sounder(site, context):
    page = start(site, context)
    page.evaluate("navigator.vibrate = ms => (window.buzz = (window.buzz || []).concat(ms), true)")
    # No fish near: no nibble.
    page.evaluate("""() => { rivals = []; schools = []; pond = []; stand(LAKE_W / 2, LAKE_H / 2);
      const h = hole(me.x, me.y, 'me', true); holes.push(h); atHole(h); jigD = 2; nibN = 0; run(() => true, 5); }""")
    assert page.evaluate("[nibN, shownFish().length]") == [0, 0]
    # A perch comes to look: the rod tip dips, the phone buzzes, and it keeps nibbling.
    page.evaluate("""() => { const f = newFish(lake.spots[0], 'ahven'); f.d = 2; f.lx = f.wx = f.gx = me.x + 0.4; f.ly = f.wy = f.gy = me.y; f.linger = 999;
      pond = [f]; sight(); update(DT); window.first = [nibN, nib, rodPull()]; }""")
    n, nib, pull = page.evaluate("first")
    assert n == 1 and nib > 0.3 and pull > 0.15
    assert page.evaluate("buzz.length") >= 1
    page.evaluate("run(() => true, 8)")
    assert page.evaluate("nibN") >= 3
    # Keener, stronger: halfway and nearly there give firmer nibbles.
    page.evaluate("nibN = 0")
    page.evaluate(ON_BEAT, 4)
    assert page.evaluate("nibN") >= 1 and max(v for v in page.evaluate("buzz") if v) >= 18


def test_twitching_on_the_beat_with_the_right_bait_makes_a_fish_bite(site, context):
    page = start(site, context)
    ready(page)
    phase, n = page.evaluate(ON_BEAT, 10)
    assert phase == "bite" and 4 <= n <= 6
    page.mouse.click(180, 500)
    assert page.evaluate("[phase, fight.fish.sp]") == ["fight", "ahven"]


def test_a_fish_bites_slowly_on_a_bait_it_cares_little_for_and_not_at_all_on_one_it_does_not_want(site, context):
    page = start(site, context)
    ready(page, bait="kalanpala")
    phase, n = page.evaluate(ON_BEAT, 20)
    assert phase == "bite" and n >= 10
    # A burbot does not come to a bright jig at all.
    ready(page, "made", 800, bait="kirkas")
    assert page.evaluate("target") is None
    page.evaluate("bait = 'kalanpala'; pond[0].d = jigD; run(() => !target, 3)")
    assert page.evaluate("target && target.sp") == "made"


def test_changing_the_bait_in_the_water_takes_a_moment_on_the_ice_none(site, context):
    page = start(site, context)
    ready(page)
    tap(page, page.evaluate("baitBtn"))
    assert page.evaluate("baitOpen") is True
    row = page.evaluate("baitRows().find(r => r.k === 'mormyska')")
    tap(page, row)
    assert page.evaluate("[phase, bait, baitOpen]") == ["bait", "mormyska", False]
    assert page.evaluate("localStorage.getItem('ai-pelit:pilkki:syotti')") == '"mormyska"'
    page.evaluate("run(() => phase === 'bait', 5)")
    page.evaluate("run(() => jigGoal !== null, 5)")
    assert page.evaluate("phase") == "jig" and abs(page.evaluate("jigD") - 2) < 0.05
    page.evaluate("toIce(); pickBait('kirkas')")
    assert page.evaluate("[phase, bait]") == ["ice", "kirkas"]


@pytest.mark.parametrize("sp,bait", [("ahven", "kirkas"), ("kuha", "tasapaino")])
def test_the_biggest_fish_can_be_landed_by_letting_go_in_time(site, context, sp, bait):
    page = start(site, context)
    big = page.evaluate(f"SPECIES['{sp}'].w[1]")
    ready(page, sp, big, bait)
    page.evaluate(ON_BEAT, 12)
    page.evaluate("strike()")
    assert page.evaluate(FIGHT) == "caught"
    assert page.evaluate("[myG, pond.length]") == [big, 0]


def test_a_pike_bites_the_line_off_if_it_is_held_tight_in_a_rush(site, context):
    page = start(site, context)
    ready(page, "hauki", 3000)
    page.evaluate(ON_BEAT, 12)
    page.evaluate("strike(); Math.random = () => 0.01; holding = 1; run(() => phase === 'fight', 30)")
    assert page.evaluate("[phase, snapWhy]") == ["snap", "Hauki katkaisi siiman hampaillaan!"]
    assert page.evaluate("pond.length") == 1


def test_the_giant_pike_can_be_landed_with_patience(site, context):
    page = start(site, context)
    ready(page, "hauki", 14000)
    page.evaluate("pond[0].giant = true")
    page.evaluate(ON_BEAT, 12)
    # Let go in every rush (the game says when): its teeth never get the line.
    page.evaluate("strike()")
    assert page.evaluate(FIGHT.replace("fight.T > 0.85 ?", "fight.burst > 0 || fight.T > 0.85 ?")) == "caught"
    assert page.evaluate("myG") == 14000
    page.evaluate("phaseT = 0.6")
    assert page.evaluate("landed.g >= GIANT[0]") is True


def test_the_lake_has_schools_lone_pike_and_burbot_and_one_giant(site, context):
    page = start(site, context)
    res = page.evaluate("""() => ({
      giants: pond.filter(f => f.giant).length,
      giantKind: pond.find(f => f.giant).sp,
      kinds: [...new Set(pond.map(f => f.sp))],
    })""")
    assert res["giants"] == 1 and res["giantKind"] == "hauki"
    # Each fish steers itself; the schooling ones still end up in schools after a while.
    page.evaluate("rivals = []; run(() => true, 40)")
    together = page.evaluate("""() => {
      buildGrid();
      const sch = pond.filter(f => schooling(f.sp));
      const ok = sch.filter(f => near(f, 5, []).filter(q => q.sp === f.sp).length >= 2).length;
      return ok / sch.length;
    }""")
    assert together > 0.7
    # And they keep moving: not one block standing still.
    moving = page.evaluate("pond.filter(f => schooling(f.sp) && Math.hypot(f.mx, f.my) > 0.05).length / pond.filter(f => schooling(f.sp)).length")
    assert moving > 0.5


def test_fish_keep_away_from_a_pike(site, context):
    page = start(site, context)
    page.evaluate("rivals = []; run(() => true, 20)")
    page.evaluate("""() => {
      const f = pond.find(q => q.sp === 'sarki' || q.sp === 'ahven');
      const p = newFish(lake.spots[0], 'hauki'); p.lx = p.wx = p.hx = f.lx + 2; p.ly = p.wy = p.hy = f.ly; p.linger = 999; p.go = false;
      pond.push(p); window.pk = p; buildGrid();
      window.close = pond.filter(q => q !== p && Math.hypot(q.lx - p.lx, q.ly - p.ly) < 5);
      window.before = close.reduce((a, q) => a + Math.hypot(q.lx - p.lx, q.ly - p.ly), 0) / close.length;
    }""")
    page.evaluate("pk.dart = 0; Math.random = () => 0.99; run(() => true, 3)")
    after = page.evaluate("close.filter(q => pond.includes(q)).reduce((a, q) => a + Math.hypot(q.lx - pk.lx, q.ly - pk.ly), 0) / close.length")
    assert after > page.evaluate("before") + 2


def test_a_caught_fish_is_gone_and_the_others_swim_between_spots(site, context):
    page = start(site, context)
    page.evaluate("rivals = []; pond.forEach(f => f.was = f.tgt)")
    n = page.evaluate("pond.length")
    page.evaluate("run(() => true, 200)")
    assert page.evaluate("pond.length") == n
    assert page.evaluate("pond.filter(f => f.tgt !== f.was).length") > n * 0.3


def test_the_computer_anglers_walk_drill_and_their_holes_can_be_fished(site, context):
    page = start(site, context)
    page.evaluate("run(() => !rivals.some(r => r.holes.length), 60)")
    h = page.evaluate("const h = rivals.find(r => r.holes.length).holes[0]; [h.x, h.y]")
    page.evaluate(f"stand({h[0]}, {h[1]})")
    assert page.evaluate("holeHere() && holeHere().by !== 'me'") is True
    tap(page, page.evaluate("actBtn"))
    assert page.evaluate("[phase, holes.length]") == ["jig", 0]


def test_the_computer_anglers_get_better_level_by_level(site, context):
    page = open_game(site, context)
    means = page.evaluate("""() => [1, 6].map(l => {
      level = l; const best = [];
      for (let k = 0; k < 10; k++) {
        save(SAVE, null); newContest();
        run(() => true, CONTEST - 1);
        best.push(Math.max(...rivals.map(r => r.g)));
      }
      // The median: one big pike or bream must not decide it.
      best.sort((a, b) => a - b);
      return (best[4] + best[5]) / 2;
    })""")
    assert 50 < means[0] < 2500 and means[1] > means[0] * 1.3


def test_a_reload_keeps_the_contest_the_lake_and_v1_s_save(site, context):
    page = start(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:pilkki:kisa', '\"v1\"')")
    page.evaluate("stand(LAKE_W / 2, LAKE_H / 2); iceAction(); turnAuger(99); toIce(); me.tx = me.x + 6; run(() => !standing(), 3); myG = 700; myN = 3; left = 200; keepContest()")
    before = page.evaluate("[r1(me.x), r1(me.y), holes.length, pond.length, pond.map(f => f.sp + f.g).sort().join()]")
    page.reload()
    page.evaluate(RUN)
    assert "3:20" in page.locator("#resume").inner_text()
    page.click("#resume")
    assert page.evaluate("[r1(me.x), r1(me.y), holes.length, pond.length, pond.map(f => f.sp + f.g).sort().join()]") == before
    assert page.evaluate("[phase, myG, myN]") == ["ice", 700, 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:pilkki:kisa')") == '"v1"'


def test_the_contest_ends_and_a_win_raises_the_level(site, context):
    page = start(site, context)
    page.evaluate("myG = 2500; myN = 9; rivals.forEach(r => r.g = 1000); left = 0.5; run(() => phase !== 'done', 2)")
    assert page.locator("#result").inner_text() == "Voitit kisan! 🏆 2,50 kg"
    assert page.evaluate("localStorage.getItem('ai-pelit:pilkki:taso')") == "2"


def test_the_sounder_choice_is_kept(site, context):
    page = open_game(site, context)
    page.click('#gear button[data-t="tutka"]')
    page.reload()
    page.evaluate(RUN)
    assert page.evaluate("radar") == "tutka"
    assert page.locator('#gear button[data-t="tutka"]').get_attribute("class") == "on"


# ---------- Playing with friends ----------

@pytest.fixture
def room(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.evaluate(RUN)
        return page

    def play(*names):
        host = phone(names[0])
        host.click("#multi")
        host.click("#aipr-create")
        host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
        code = host.evaluate("AiPelitRooms.code")
        guests = []
        for n in names[1:]:
            g = phone(n)
            g.click("#multi")
            g.fill("#aipr-codeIn", code)
            g.click("#aipr-joinBtn")
            g.wait_for_function("AiPelitRooms.inRoom")
            guests.append(g)
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
        host.click("#aipr-start")
        for p in [host, *guests]:
            p.wait_for_function("net.on && phase === 'ice'")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


def test_friends_see_each_other_on_the_ice_and_fish_each_other_s_holes(room):
    host, [guest] = room("Eero", "Aino")
    # Each starts at its own point by the shore of the same lake.
    assert host.evaluate("JSON.stringify(lake.spots)") == guest.evaluate("JSON.stringify(lake.spots)")
    assert host.evaluate("[r1(me.x), r1(me.y)]") != guest.evaluate("[r1(me.x), r1(me.y)]")
    # Aino walks out and drills: the host sees her there, and her hole.
    guest.evaluate("stand(LAKE_W / 2, LAKE_H / 2); iceAction(); turnAuger(99); sendMe()")
    host.wait_for_function("others().some(o => o.name === 'Aino' && Math.abs(o.x - LAKE_W / 2) < 0.2) && allHoles().length === 1", timeout=4000)
    # The host walks to it and fishes it without drilling.
    host.evaluate("stand(LAKE_W / 2 + 0.5, LAKE_H / 2)")
    assert host.evaluate("holeHere() && holeHere().by !== 'me'") is True
    host.evaluate("iceAction()")
    assert host.evaluate("[phase, holes.length]") == ["jig", 0]
    # The fish are still shared: one Aino lands is gone on the host too.
    guest.wait_for_function("pond.length > 50", timeout=5000)
    caught = guest.evaluate("""() => {
      const f = pond[0]; claim(f);
      fight = { fish: f, L: 0, T: 0, over: 0, burst: 0, next: 9, t: 0, sway: 0 }; phase = 'fight';
      land(); return [f.id, f.g];
    }""")
    host.wait_for_function(f"!pond.some(f => f.id === {caught[0]})", timeout=4000)
    guest.wait_for_function(f"myG === {caught[1]}", timeout=4000)
    assert host.errors == guest.errors == []


# ---------- Screens ----------

@pytest.mark.parametrize("size", [(740, 360), (640, 360), (360, 640), (390, 844)])
def test_the_menu_the_ice_and_the_hole_fit_the_screen(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    for sel in ["#go", "#multi", "h1", "#gear"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1] and b["x"] >= 0 and b["x"] + b["width"] <= size[0], sel
    page.click("#go")
    inside = "b => b.x >= 0 && b.y >= 0 && b.x + b.w <= W && b.y + b.h <= H"
    assert page.evaluate(f"[actBtn, baitBtn].every({inside})") is True
    page.evaluate("stand(LAKE_W / 2, LAKE_H / 2); iceAction(); turnAuger(99)")
    assert page.evaluate(f"[walkBtn, baitBtn].every({inside}) && walkBtn.x + walkBtn.w < holeX - 60") is True
    assert page.evaluate("baitRows().every(b => b.y >= 0 && b.y + b.h <= H)") is True
    ctx.close()


def test_turning_the_phone_on_the_ice_keeps_the_contest(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    page.evaluate("stand(LAKE_W / 2, LAKE_H / 2); myG = 400")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("wide === true")
    assert page.evaluate("[phase, r1(me.x), myG]") == ["ice", page.evaluate("r1(LAKE_W / 2)"), 400]
    ctx.close()

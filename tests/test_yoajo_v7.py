"""Yöajo v7 (#266 "Mitä kuopille mahtaa?"): the potholes are seen and explained. Each bad
stretch has a 50 limit, a pale rim on each hole, a warning on the screen, a menu tip, and the
burst-tyre screen says how to get over them; up to 55 km/h they do nothing."""

from conftest import ROOT
from test_yoajo_v4 import BOT as BOT_V4

URL = "games/yoajo/v7/"

# The careful driver of v4, now slowing only for the signs (v1–v6: it also looked for holes
# ahead), and waiting behind a slow car before it turns into a rest area.
BOT = BOT_V4.replace("const lim = holey ? 45 :", "const lim =", 1).replace(
    "if (rest) want = 7;", "if (rest && !(slow && slow.lat > 0 && slow.s - P.s < 25)) want = 7;", 1)
assert BOT != BOT_V4

# Leg n with nobody else on the road, the clock held, the car kept in its lane at kmh.
RUN = """([n, setup, kmh, secs]) => { HOLD = true; maxLeg = 8; newLeg(n); things = []; events = []; road.cams = [];
  const seen = []; eval(setup);
  for (let i = 0; i < 60 * secs && mode === 'drive'; i++) { P.v = kmh / KMH; P.lat = LANE; P.vl = 0; step(1 / 60);
    for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }
  return { mode, why: crashWhy, points, damage: P.damage, tally: Object.assign({}, tally), seen }; }"""

# Every string the 2D canvas draws, in window.drawn.
SPY = """() => { window.drawn = []; const f = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (t, ...a) { drawn.push(String(t)); return f.call(this, t, ...a); }; }"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def run(page, setup, kmh, secs=2.0, n=1):
    return page.evaluate(RUN, [n, setup, kmh, secs])


def test_every_leg_can_still_be_driven(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    assert all(r["mode"] == "done" for r in legs), [(r["n"], r["why"]) for r in legs]
    # Keeping to the limits, the new 50s over the potholes too, the holes do nothing.
    assert all(r["tally"]["hurjastelu"] == 0 for r in legs), legs
    assert all(r["tally"]["kuopat"] == 0 for r in legs), legs
    assert page.errors == []


def test_every_bad_stretch_has_a_50_limit_over_its_holes(site, context):
    page = open_game(site, context)
    for n in range(3, 9):
        r = page.evaluate("""(n) => { newLeg(n); mode = 'menu';
          return { bad: road.bad.length, legBad: leg.bad,
            holes50: road.holes.every(h => limitAt(h.s) === 50),
            back: road.bad.map(b => [limitAt(b.s0 - 1), limitAt(b.s1 + 1)]),
            signs: road.bad.map(b => road.signs.filter(s => s.kind === 'raja' && s.s >= b.s0 && s.s <= b.s1).map(s => s.v)) }; }""", n)
        assert r["bad"] == r["legBad"] and r["holes50"], (n, r)
        # The limit after the stretch is a real one, and a 50 sign then the old limit's sign stand on it.
        assert all(after in (60, 80, 100) for _, after in r["back"]), (n, r)
        assert all(s[0] == 50 and len(s) == 2 for s in r["signs"]), (n, r)
    assert page.errors == []


def test_at_the_limit_the_holes_do_nothing_and_fast_they_burst_the_tyre(site, context):
    page = open_game(site, context)
    holes = ("road.holes = []; for (let k = 1; k <= 8; k++) for (const d of [-0.75, 0.75]) "
             "road.holes.push({ s: P.s + 10 + k * 9, lat: LANE + d, r: 0.6 }); "
             "road.bad = [{ s0: P.s + 10, s1: P.s + 100, told: false }];")
    r = run(page, holes, 55, 6)
    assert r["mode"] == "drive" and r["tally"]["kuopat"] == 0 and r["points"] == 0, r
    assert "Kuoppia: hidasta alle 50 km/h" in r["seen"], r
    r = run(page, holes, 85, 4)
    assert r["mode"] == "crash" and "Rengas" in r["why"], r
    assert page.errors == []


def test_the_menu_and_the_burst_tyre_screen_tell_how(site, context):
    page = open_game(site, context)
    page.evaluate(SPY)
    page.evaluate("() => { maxLeg = 8; sel = 3; drawn.splice(0); draw(); }")
    assert "Kuoppamerkin jälkeen hidasta alle 50 km/h." in page.evaluate("drawn")
    page.evaluate("() => { sel = 1; drawn.splice(0); draw(); }")
    assert "Pitkät pois, kun joku tulee vastaan." in page.evaluate("drawn")
    page.evaluate("() => { HOLD = true; newLeg(3); crash('Rengas puhkesi kuoppaan.'); drawn.splice(0); draw(); }")
    assert "Kuoppien kohdalla hidasta alle 50 km/h." in page.evaluate("drawn")
    assert page.errors == []


def test_each_hole_has_a_pale_rim_in_3d(site, context):
    page = open_game(site, context)
    page.wait_for_function("V3 && V3.scene || no3d", timeout=15000)
    r = page.evaluate("""() => { maxLeg = 8; newLeg(3); mode = 'menu'; if (typeof buildWorld === 'function') buildWorld();
      let rims = 0; V3.scene.traverse(o => { if (o.geometry && o.geometry.type === 'RingGeometry') rims++; });
      return { rims, holes: road.holes.length }; }""")
    assert r["holes"] > 0 and r["rims"] >= r["holes"], r
    assert page.errors == []

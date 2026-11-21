"""Jäälautta v1 (#478): seals shoving each other off an ice floe, alone against the computer.

The rules are tested on fresh worlds built in the page (world.js is plain functions), the screen
and the saves by playing the game itself."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/jaalautta/v1/"
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# One whole match of four computer seals; seal 0 plays by `policy`: 'cpu' (with `skill`, or the
# floe's own), 'still' (never touches anything) or 'spam' (lunges whenever it can, no stick).
SIM = """([floe, policy, seed, skill]) => {
  const players = [0, 1, 2, 3].map(i => ({ id: 'p' + i, name: 'p' + i, hat: i, kind: 'cpu' }));
  const w = newWorld(floe, players, seed), F = FLOES[floe - 1];
  const brains = w.seals.map((s, i) => cpuBrain(i === 0 && skill ? skill : F.cpu, seed * 7 + i));
  const eras = []; let minFrac = 1, guard = 0;
  while (!w.over && guard++ < 120 * 60 * 20) {
    w.seals.forEach((s, i) => {
      if (i === 0 && policy === 'still') { s.ix = s.iy = 0; return; }
      if (i === 0 && policy === 'spam') { s.ix = s.iy = 0; if (s.cd <= 0) s.want = s.lunges + 1; return; }
      cpuThink(w, s, brains[i], STEP);
    });
    const ph = w.ph; tick(w, STEP);
    for (const p of w.parts) for (const r of p.r) minFrac = Math.min(minFrac, r / p.r0);
    if (ph === 'play' && w.ph !== 'play') eras.push(w.t);
  }
  return { win: w.winner, over: w.over, eras, minFrac };
}"""
# Every other seal falls in, erä after erä, until the match is over.
WIN_MATCH = """() => { for (let k = 0; k < 3 && !world.over; k++) {
  world.ph = 'play'; world.seals.slice(1).forEach(s => fall(world, s)); step(world, ERA_PAUSE + 0.2); } }"""
LOSE_MATCH = """() => { for (let k = 0; k < 3 && !world.over; k++) {
  world.ph = 'play'; world.seals.filter((s, i) => i !== 1).forEach(s => fall(world, s)); step(world, ERA_PAUSE + 0.2); } }"""


def open_game(site, context, width=360, height=740):
    if not (site.games / "jaalautta").exists():
        shutil.copytree(ROOT / "games" / "jaalautta", site.games / "jaalautta")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof mode !== 'undefined' && (mode === 'menu' || mode === 'play')")
    return page


def go(page):
    page.click("#go")
    page.wait_for_function("mode === 'play' && world && world.ph === 'play'", timeout=8000)


def test_the_menu_opens_the_first_floe_only(site, context):
    page = open_game(site, context)
    floes = page.locator("#floes button")
    assert floes.count() == 5
    assert [floes.nth(i).is_disabled() for i in range(5)] == [False, True, True, True, True]
    assert "🔒" in floes.nth(4).inner_text()
    assert page.locator("#friends").is_visible()
    # The hat colour changes on a tap and is kept.
    page.click("#hat")
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:jaalautta:hattu'))") == 1
    assert page.errors == []


def test_a_seal_falls_only_when_its_middle_leaves_the_ice(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const w = newWorld(1, [{ id: 'a', name: 'a', hat: 0, kind: 'cpu' }, { id: 'b', name: 'b', hat: 1, kind: 'cpu' }], 1);
      w.ph = 'play'; const a = w.seals[0], e = edgeAt(w.parts[0], 0);
      a.x = e - 0.2; a.y = 0; w.seals[1].x = -5; w.seals[1].y = 0;   // more than half over the edge
      tick(w, STEP); const half = !a.out;
      a.x = e + 0.1; tick(w, STEP);
      return [half, !!a.out, w.ph];
    }""")
    assert r == [True, True, "erä"]


def test_a_lunge_throws_another_seal_further_than_a_bump(site, context):
    page = open_game(site, context)
    dist = """(lunge) => {
      const w = newWorld(1, [{ id: 'a', name: 'a', hat: 0, kind: 'cpu' }, { id: 'b', name: 'b', hat: 1, kind: 'cpu' }], 1);
      w.ph = 'play'; const [a, b] = w.seals;
      Object.assign(a, { x: -3, y: 0, vx: 3, vy: 0, face: 0 }); Object.assign(b, { x: 0, y: 0, vx: 0, vy: 0 });
      if (lunge) a.want = 1;
      for (let i = 0; i < 120 * 0.8; i++) tick(w, STEP);
      return [b.x, a.x];
    }"""
    bumped, _ = page.evaluate(dist, False)
    lunged, a_after = page.evaluate(dist, True)
    assert lunged > bumped + 1.5
    assert lunged > a_after   # the lunger stops behind the one it hit


def test_the_floe_breaks_no_smaller_than_a_third_and_every_round_ends(site, context):
    page = open_game(site, context)
    for floe in range(1, 6):
        for seed in (3, 11):
            r = page.evaluate(SIM, [floe, "cpu", seed, None])
            assert r["over"] and r["win"]
            assert r["minFrac"] >= 1 / 3 - 1e-9
            assert max(r["eras"]) < 90, (floe, seed, r["eras"])


def test_lazy_play_does_not_win_and_the_hardest_floe_can_be_won(site, context):
    page = open_game(site, context)
    for policy in ("still", "spam"):
        wins = [page.evaluate(SIM, [1, policy, s, None])["win"] for s in range(1, 7)]
        assert "p0" not in wins, policy
    # A quick, sure player beats the two-floe level (the simulator won 7 of 20 with this one).
    strong = {"react": 0.15, "err": 4}
    for floe in range(1, 6):
        wins = [page.evaluate(SIM, [floe, "cpu", s, strong])["win"] for s in range(1, 13)]
        assert "p0" in wins, floe


def test_the_four_power_ups(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const mk = n => newWorld(1, Array.from({ length: n }, (_, i) => ({ id: 'p' + i, name: 'p' + i, hat: i, kind: 'cpu' })), 5);
      const out = {};
      // Jätti: bigger and heavier; Pikkuinen: smaller and lighter; both wear off after 8 s.
      let w = mk(2); w.ph = 'play'; const [a, b] = w.seals;
      givePower(a, 'jatti'); givePower(b, 'pikku');
      out.size = [radiusOf(a) > SEAL_R, massOf(a) > 1, radiusOf(b) < SEAL_R, massOf(b) < 1];
      Object.assign(a, { x: -4, y: 0 }); Object.assign(b, { x: 4, y: 0 });
      for (let i = 0; i < 120 * 8.1; i++) { a.x = -4; b.x = 4; a.y = b.y = 0; tick(w, STEP); }
      out.worn = [a.size, b.size];
      // Ukkonen: passed on a touch, not straight back (grace), and stuns the others at the end.
      w = mk(3); w.ph = 'play'; const [c, d, e] = w.seals;
      Object.assign(c, { x: 0, y: 0 }); Object.assign(d, { x: 1.7, y: 0 }); Object.assign(e, { x: -6, y: 0 });
      givePower(c, 'ukko'); tick(w, STEP);
      out.grace = [!!c.fuse, !d.fuse];
      for (let i = 0; i < 120 * 0.6; i++) { c.x = 0; d.x = 1.7; c.y = d.y = 0; tick(w, STEP); }
      out.passed = [!c.fuse, d.fuse && d.fuse.k];
      for (let i = 0; i < 120 * 0.3; i++) { c.x = 0; d.x = 1.7; c.y = d.y = 0; tick(w, STEP); }
      out.notBack = !!d.fuse && !c.fuse;
      d.fuse.t = 0.001; d.x = 6; c.x = 0; tick(w, STEP);
      out.stun = [c.stun > 0, e.stun > 0, d.stun === 0];
      // Lohkare: its last holder goes through the ice.
      w = mk(3); w.ph = 'play'; const f = w.seals[0];
      w.seals[1].x = 5; w.seals[2].x = -5; f.x = 0; f.y = 0;
      givePower(f, 'lohk'); f.fuse.t = 0.001; tick(w, STEP);
      out.crush = [!!f.out, !!f.crushed];
      // The crush is that fall's only: the next erä and an ordinary fall show none (#479 review).
      resetEra(w); out.reset = f.crushed; f.crushed = true; fall(w, f); out.plain = f.crushed;
      // The gull's ring: a seal on it once it glows gets a power-up, and the ring is gone.
      w = mk(2); w.ph = 'play'; const g = w.seals[0];
      Object.assign(g, { x: 2, y: 1 }); Object.assign(w.seals[1], { x: -6, y: 0 });
      w.ring = { x: 2, y: 1, come: 0, open: RING_OPEN }; tick(w, STEP);
      out.ring = [!!(g.size || g.fuse), w.ring];
      return out;
    }""")
    assert r["size"] == [True, True, True, True]
    assert r["worn"] == [None, None]
    assert r["grace"] == [True, True]
    assert r["passed"] == [True, "ukko"]
    assert r["notBack"]
    assert r["stun"] == [True, True, True]
    assert r["crush"] == [True, True]
    assert r["reset"] is False and r["plain"] is False
    assert r["ring"] == [True, None]


def test_the_floe_starts_breaking_after_twenty_seconds(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const w = newWorld(1, [0, 1, 2, 3].map(i => ({ id: 'p' + i, name: 'p' + i, hat: i, kind: 'cpu' })), 4);
      w.ph = 'play'; w.t = 0; w.ringNext = 1e9;
      const whole = () => w.parts.every(p => p.r.every(r => r === p.r0));
      while (w.t < SHRINK_AT - 0.1) tick(w, STEP);
      const before = whole();
      while (w.t < SHRINK_AT + SHRINK_WARN + 0.5) tick(w, STEP);
      return [before, whole()];
    }""")
    assert r == [True, False]


def test_the_stick_slides_my_seal_and_the_button_lunges(site, context):
    page = open_game(site, context)
    go(page)
    x0 = page.evaluate("me.x")
    page.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    page.evaluate(TOUCH, ["pointermove", 7, 160, 560])
    page.wait_for_timeout(500)
    assert page.evaluate("me.x") > x0 + 0.3
    # A second finger that misses the button leaves the first one steering (#479 review).
    page.evaluate(TOUCH, ["pointerdown", 9, 250, 400])
    page.evaluate(TOUCH, ["pointerup", 9, 250, 400])
    assert page.evaluate("stick && stick.id") == 7
    page.evaluate(TOUCH, ["pointerup", 7, 160, 560])
    b = page.evaluate("button()")
    page.evaluate(TOUCH, ["pointerdown", 8, b["x"], b["y"]])
    page.wait_for_function("me.lunges === 1 && me.cd > 0")
    assert page.errors == []


def test_a_solo_win_counts_once_opens_the_next_floe_and_survives_a_reload(site, context):
    page = open_game(site, context)
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    go(page)
    page.evaluate(WIN_MATCH)
    page.wait_for_function("mode === 'end'")
    assert page.evaluate("sent") == [1]
    assert page.locator("#endTitle").inner_text() == "Voitit ottelun!"
    assert "Pieni lautta" in page.locator("#endOpen").inner_text()
    assert page.evaluate("localStorage.getItem('ai-pelit:jaalautta:kesken1')") is None
    page.reload()
    page.wait_for_function("mode === 'menu'")
    assert not page.locator("#floes button").nth(1).is_disabled()
    assert page.locator("#floes button").nth(2).is_disabled()
    # A lost match: nothing sent, nothing opened.
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    page.click("#floes button >> nth=0")
    go(page)
    page.evaluate(LOSE_MATCH)
    page.wait_for_function("mode === 'end'")
    assert page.evaluate("sent") == []
    assert page.locator("#endTitle").inner_text() == "Hävisit ottelun"
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:jaalautta:voitot'))") == 1
    assert page.errors == []


def test_a_won_match_counts_before_the_end_screen_so_a_reload_keeps_it(site, context):
    page = open_game(site, context)
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    go(page)
    # Two erät won, then the deciding one: won, but its pause before the end screen still running.
    page.evaluate("""() => { for (let k = 0; k < 2; k++) {
      world.ph = 'play'; world.seals.slice(1).forEach(s => fall(world, s)); step(world, ERA_PAUSE + 0.2); }
      world.ph = 'play'; world.seals.slice(1).forEach(s => fall(world, s)); step(world, 0.05); }""")
    page.wait_for_function("sent.length === 1")
    assert page.evaluate("[mode, world.over]") == ["play", False]
    assert page.evaluate("['voitot', 'auki', 'kesken1'].map(k => localStorage.getItem('ai-pelit:jaalautta:' + k))") == ["1", "2", None]
    page.reload()
    page.wait_for_function("mode === 'menu'")
    assert not page.locator("#floes button").nth(1).is_disabled()
    assert page.errors == []


def test_a_reload_mid_match_restarts_the_era_with_the_stars_kept(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { world.seals.slice(1).forEach(s => fall(world, s)); }")
    page.wait_for_function("world.era === 2 && world.ph === 'count'", timeout=8000)
    page.reload()
    page.wait_for_function("mode === 'play' && world")
    assert page.evaluate("[world.era, world.ph, me.stars, world.seals.slice(1).map(s => s.stars)]") == [2, "count", 1, [0, 0, 0]]
    # A save that does not read is dropped and the menu shows.
    page.evaluate("localStorage.setItem('ai-pelit:jaalautta:kesken1', '{\"f\": 9, \"stars\": 3}')")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360)])
def test_the_menu_and_the_floe_fit_upright_and_sideways(site, context, size):
    w, h = size
    page = open_game(site, context, w, h)
    for sel in ("#go", "#friends", "#hat", "#floes button >> nth=4"):
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= h + 0.5, sel
    go(page)
    # Every seal, eight of them too, and the button are on the screen, and the button is off the floe.
    page.evaluate("""() => {
      const ps = Array.from({ length: 8 }, (_, i) => ({ id: i ? 'c' + i : 'me', name: 'n' + i, hat: i, kind: i ? 'cpu' : 'me' }));
      world = newWorld(1, ps, 2); me = world.seals[0]; brains = world.seals.map((s, i) => i ? cpuBrain(FLOES[0].cpu, i) : null);
    }""")
    page.wait_for_timeout(300)
    r = page.evaluate("""() => {
      const b = button(), p = world.parts[0];
      return { seals: world.seals.map(s => [X(s.x), Y(s.y)]), b: [b.x, b.y, b.r],
               floe: [X(p.x - p.r0), X(p.x + p.r0), Y(p.y - p.r0), Y(p.y + p.r0)] };
    }""")
    for x, y in r["seals"]:
        assert 0 < x < w and 0 < y < h
    bx, by, br = r["b"]
    assert bx + br <= w and by + br <= h
    fx0, fx1, fy0, fy1 = r["floe"]
    assert fx0 >= 0 and fx1 <= w and fy0 >= 0 and fy1 <= h
    assert not (fx0 < bx < fx1 and fy0 < by < fy1 and ((bx - (fx0 + fx1) / 2) ** 2 + (by - (fy0 + fy1) / 2) ** 2) ** 0.5 < (fx1 - fx0) / 2)
    assert page.errors == []


def test_turning_the_phone_keeps_the_match(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("me.stars = 1")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND")
    assert page.evaluate("[mode, me.stars]") == ["play", 1]
    assert page.errors == []

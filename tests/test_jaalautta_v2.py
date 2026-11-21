"""Jäälautta v1 (#478): seals shoving each other off an ice floe, alone against the computer.

The rules are tested on fresh worlds built in the page (world.js is plain functions), the screen
and the saves by playing the game itself."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/jaalautta/v2/"
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
    if (w.ph === 'play' && w.t < SUDDEN_AT) for (const p of w.parts) for (const r of p.r) minFrac = Math.min(minFrac, r / p.r0);
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
      a.x = e + 0.1; a.vx = TEETER_V + 1; tick(w, STEP);   // fast over the edge: no wobble, straight in
      return [half, !!a.out, w.ph];
    }""")
    assert r == [True, True, "erä"]


# Two seals on floe 1, `a` just over the edge on the right, still: it wobbles there.
TEETER = """() => {
  const w = newWorld(1, [{ id: 'a', name: 'a', hat: 0, kind: 'cpu' }, { id: 'b', name: 'b', hat: 1, kind: 'cpu' }], 1);
  w.ph = 'play'; const [a, b] = w.seals, e = edgeAt(w.parts[0], 0);
  Object.assign(a, { x: e + 0.1, y: 0, vx: 1, vy: 0 }); Object.assign(b, { x: -5, y: 0, vx: 0, vy: 0 });
  tick(w, STEP); return w;
}"""


def test_a_slow_seal_wobbles_on_the_edge_and_five_presses_bring_it_back(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(T) => {
      const w = eval(T)(), a = w.seals[0], out = [a.teeter > 0, !!a.out];
      for (let k = 0; k < 4; k++) { a.want = a.lunges + 1; for (let i = 0; i < 24; i++) tick(w, STEP); }
      out.push(a.teeter > 0, a.mash, a.lungeT);          // four presses: still wobbling, no lunge
      a.want = a.lunges + 1; tick(w, STEP);
      out.push(a.teeter, onIce(w, a.x, a.y), a.vx < 0, a.saved);
      for (let i = 0; i < 120; i++) tick(w, STEP);
      out.push(!!a.out, onIce(w, a.x, a.y));
      return out;
    }""", TEETER)
    assert r == [True, False, True, 4, 0, 0, True, True, 1, False, True]


def test_a_wobbling_seal_goes_in_on_time_on_a_touch_or_stunned(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(T) => {
      const res = {};
      // Nobody presses: in once its time is up, not before.
      let w = eval(T)(), a = w.seals[0];
      for (let i = 0; i < 120 * (TEETER_T - 0.1); i++) tick(w, STEP);
      res.before = !a.out;
      for (let i = 0; i < 120 * 0.2; i++) tick(w, STEP);
      res.after = !!a.out;
      // Another seal walking into it tips it in at once, presses or not.
      w = eval(T)(); a = w.seals[0]; const b = w.seals[1];
      Object.assign(b, { x: a.x - 2.2, y: 0, vx: 4, vy: 0 });
      a.want = a.lunges + 2;
      for (let i = 0; i < 30 && !a.out; i++) tick(w, STEP);
      res.touched = !!a.out && !b.out;
      // A seal standing by is only moved off.
      w = eval(T)(); a = w.seals[0];
      Object.assign(w.seals[1], { x: a.x - 1.7, y: 0, vx: 0, vy: 0 }); tick(w, STEP);
      res.standing = a.teeter > 0;
      // Stunned (Ukkonen) it cannot press its way back.
      w = eval(T)(); a = w.seals[0]; a.stun = 5;
      for (let i = 0; i < 120 * 2; i++) { a.want = a.lunges + 1; tick(w, STEP); }
      res.stunned = !!a.out;
      // Over an open hole: straight in.
      w = eval(T)(); a = w.seals[0]; a.teeter = 0; a.x = 0; a.y = 3; a.vx = 0;
      w.holes = [{ x: 0, y: 3, r: 1.5, warn: 0, open: 3 }]; tick(w, STEP);
      res.hole = !!a.out;
      // The ice going from under it (the melt): in, presses or not.
      w = eval(T)(); a = w.seals[0]; w.t = SUDDEN_AT;
      w.parts[0].r = w.parts[0].r.map(() => 1);
      for (let i = 0; i < 3; i++) { a.want = a.lunges + 1; tick(w, STEP); }
      res.melted = !!a.out;
      return res;
    }""", TEETER)
    assert r == {"before": True, "after": True, "touched": True, "standing": True, "stunned": True,
                 "hole": True, "melted": True}


def test_computer_seals_press_their_way_back_the_sharper_the_more_often(site, context):
    page = open_game(site, context)
    saved = page.evaluate("""(T) => [1, 5].map(floe => {
      let n = 0;
      for (let s = 1; s <= 30; s++) {
        const w = eval(T)(), a = w.seals[0], br = cpuBrain(FLOES[floe - 1].cpu, s);
        for (let i = 0; i < 120 * 2 && a.teeter > 0; i++) { cpuThink(w, a, br, STEP); tick(w, STEP); }
        if (!a.out) n++;
      }
      return n;
    })""", TEETER)
    assert 3 <= saved[0] <= 27 and saved[1] >= 25 and saved[1] > saved[0], saved


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


def test_an_era_ends_even_when_nobody_touches_the_screen(site, context):
    # Four phones in a room whose players all put them down: the melt still ends every erä, and a
    # tie in the melt goes to one of the seals by lot, so the match ends (#479 review).
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const w = newWorld(1, [0, 1, 2, 3].map(i => ({ id: 'p' + i, name: 'p' + i, hat: i, kind: 'net' })), 9);
      const eras = []; let guard = 0;
      while (!w.over && guard++ < 120 * 60 * 15) {
        const ph = w.ph; tick(w, STEP);
        if (ph === 'play' && w.ph !== 'play') eras.push(w.t);
      }
      const melted = (() => { const v = newWorld(1, [{ id: 'a', name: 'a', hat: 0, kind: 'net' }, { id: 'b', name: 'b', hat: 1, kind: 'net' }], 3);
        v.ph = 'play'; v.t = SUDDEN_AT; v.seals.forEach(s => { s.x = 0; s.y = 0; s.out = 1; }); v.seals[0].out = 0;
        tick(v, 1); return v.parts[0].r.every(r => r < v.parts[0].r0 * (1 - MELT * 0.9)); })();
      return { over: w.over, winner: w.winner, eras, melted };
    }""")
    assert r["over"] and r["winner"]
    assert len(r["eras"]) >= 3 and max(r["eras"]) <= 60 + 20 + 1, r["eras"]
    assert r["melted"]


def test_no_lunge_is_kept_for_the_next_era(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("mode === 'play' && world && world.ph === 'count'")
    b = page.evaluate("button()")
    # A press during the countdown does nothing, and does not lunge when the erä starts.
    page.evaluate(TOUCH, ["pointerdown", 8, b["x"], b["y"]])
    assert page.evaluate("me.want === me.lunges")
    page.wait_for_function("world.ph === 'play' && world.t > 0.2")
    assert page.evaluate("[me.lunges, me.lungeT]") == [0, 0]
    # A press left pending when an erä ends is dropped by the next one.
    assert page.evaluate("() => { me.want = me.lunges + 1; resetEra(world); return me.want === me.lunges; }")
    assert page.errors == []


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
      // They wear off over the last second, not at once.
      const at = t => { a.size.t = b.size.t = t; return [radiusOf(a), massOf(a), radiusOf(b), massOf(b)]; };
      const full = at(2), half = at(0.5);
      out.ease = [half[0] < full[0] && half[0] > SEAL_R, half[1] < full[1] && half[1] > 1,
                  half[2] > full[2] && half[2] < SEAL_R, half[3] > full[3] && half[3] < 1];
      at(SIZE_T);
      for (let i = 0; i < 120 * 8.1; i++) { a.x = -4; b.x = 4; a.y = b.y = 0; tick(w, STEP); }
      out.worn = [a.size, b.size];
      // Ukkonen: passed on the first touch, whoever pushes whom (#478), and stuns the others at the end.
      w = mk(3); w.ph = 'play'; const [c, d, e] = w.seals;
      const park = () => { Object.assign(c, { x: 0, y: 0, vx: 0, vy: 0 }); Object.assign(d, { x: 6, y: 0, vx: 0, vy: 0 }); Object.assign(e, { x: -6, y: 0, vx: 0, vy: 0 }); };
      // The mover slides into the one standing still, until they touch.
      const bump = (mover, still) => { for (let i = 0; i < 240; i++) { mover.vx = 4 * Math.sign(still.x - mover.x); mover.vy = 0; tick(w, STEP); if (Math.hypot(mover.x - still.x, mover.y - still.y) <= radiusOf(mover) + radiusOf(still) + 0.01) break; } };
      park(); givePower(c, 'ukko'); c.fuse.t = 99;
      bump(d, c); out.pushedIntoHolder = [!c.fuse, !!d.fuse];
      park(); c.fuse = d.fuse; d.fuse = null; c.fuse.from = null;
      bump(c, d); out.holderPushes = [!c.fuse, !!d.fuse];
      // Held together, it stays with the one that took it; once parted, the next touch passes it back.
      for (let i = 0; i < 120; i++) { c.x = 0; d.x = 1.7; c.y = d.y = 0; tick(w, STEP); }
      out.oneTouchOnce = [!c.fuse, !!d.fuse];
      d.x = 6; tick(w, STEP); d.x = 1.7; c.x = 0; tick(w, STEP);
      out.back = [!!c.fuse, !d.fuse];
      // A third seal takes it at once.
      out.third = [passFuse(c, e), !c.fuse && !!e.fuse];
      c.fuse = e.fuse; e.fuse = null; Object.assign(e, { x: -6, y: 0 });
      d.fuse = c.fuse; c.fuse = null; d.fuse.from = null;
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
    assert r["pushedIntoHolder"] == [True, True]
    assert r["holderPushes"] == [True, True]
    assert r["oneTouchOnce"] == [True, True]
    assert r["back"] == [True, True]
    assert r["third"] == [True, True]
    assert r["ease"] == [True, True, True, True]
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


def test_my_seal_wobbling_on_the_edge_comes_back_with_the_button(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("""() => { brains = brains.map(() => null);
      world.seals.forEach((s, i) => { if (s !== me) Object.assign(s, { x: -3 + i * 0.1, y: -3 + i * 2, vx: 0, vy: 0, ix: 0, iy: 0 }); });
      Object.assign(me, { x: edgeAt(world.parts[0], 0) + 0.1, y: 0, vx: 1, vy: 0 }); }""")
    page.wait_for_function("me.teeter > 0")
    b = page.evaluate("button()")
    for k in range(5):
        page.evaluate(TOUCH, ["pointerdown", 30 + k, b["x"], b["y"]])
        page.evaluate(TOUCH, ["pointerup", 30 + k, b["x"], b["y"]])
        page.wait_for_timeout(60)
    page.wait_for_function("me.saved === 1 && !me.teeter && !me.out")
    assert page.evaluate("me.lungeT") == 0
    # Left alone on the edge, it goes in.
    page.evaluate("Object.assign(me, { x: edgeAt(world.parts[0], 0) + 0.1, y: 0, vx: 1, vy: 0 })")
    page.wait_for_function("me.teeter > 0")
    page.wait_for_function("me.out > 0", timeout=4000)
    assert page.errors == []


def test_computer_seals_keep_ukkonen_and_go_for_whoever_holds_it(site, context):
    # As in the genre's model: Ukkonen's holder gains when it ends (the others are stunned), so a
    # computer seal keeps it and the others come to take it; Lohkare is still passed on.
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const res = { flee: 0, chase: 0, giver: 0, pass: 0, n: 0 };
      for (let s = 1; s <= 40; s++) {
        const w = newWorld(3, [0, 1, 2].map(i => ({ id: 'p' + i, name: 'p' + i, hat: i, kind: 'cpu' })), s);
        w.ph = 'play'; const [c, d, e] = w.seals;
        Object.assign(c, { x: 0, y: 0 }); Object.assign(d, { x: 2, y: 0 }); Object.assign(e, { x: 0, y: 3 });
        givePower(c, 'ukko'); c.fuse.from = e.id;
        const think = sl => { const b = cpuBrain(FLOES[2].cpu, s); decide(w, sl, b); return b.slip > 0 ? null : b; };
        const bc = think(c), bd = think(d), be = think(e);
        if (!bc || !bd || !be) continue;
        res.n++;
        if (bc.tx < -0.5) res.flee++;                       // away from d, its nearest
        if (Math.hypot(bd.tx - c.x, bd.ty - c.y) < 0.01) res.chase++;
        if (Math.hypot(be.tx - c.x, be.ty - c.y) > 0.01) res.giver++;   // e just gave it: no chase
        c.fuse.k = 'lohk'; const bl = think(c);
        if (bl && bl.tx > 1.5) res.pass++;                  // to d, the nearest it may pass to
      }
      return res;
    }""")
    n = r["n"]
    assert n >= 30, r
    assert r["flee"] == n and r["chase"] == n and r["giver"] == n, r
    assert r["pass"] >= n - 4, r


# ---- v2: the 3D picture and the pause button (#478) ----

def ice_brightness(page, x, y):
    """Mean brightness of a 9 × 9 patch of the screen around (x, y), from a real screenshot."""
    from io import BytesIO
    from PIL import Image
    img = Image.open(BytesIO(page.screenshot(clip={"x": x - 4, "y": y - 4, "width": 9, "height": 9}))).convert("L")
    return sum(img.tobytes()) / (img.width * img.height)


@pytest.mark.parametrize("size", [(360, 740), (740, 360)])
def test_the_floe_and_every_seal_are_drawn_in_3d_on_the_screen(site, context, size):
    w, h = size
    page = open_game(site, context, w, h)
    page.wait_for_function("J3D.ready || J3D.failed", timeout=15000)
    if page.evaluate("J3D.failed"):
        pytest.skip("this Chromium has no WebGL")
    go(page)
    page.evaluate("""() => {
      const ps = Array.from({ length: 8 }, (_, i) => ({ id: i ? 'c' + i : 'me', name: 'n' + i, hat: i, kind: i ? 'cpu' : 'me' }));
      world = newWorld(1, ps, 2); me = world.seals[0]; brains = world.seals.map(() => null);
    }""")
    page.wait_for_timeout(300)
    r = page.evaluate("""() => {
      const p = world.parts[0], b = playBox();
      return { gl: getComputedStyle(document.getElementById('g')).display,
               seals: world.seals.map(s => J3D.project(s.x, 0, s.y)),
               floe: [J3D.project(p.x - p.r0, 0, p.y), J3D.project(p.x + p.r0, 0, p.y), J3D.project(p.x, 0, p.y - p.r0), J3D.project(p.x, 0, p.y + p.r0)],
               mid: J3D.project(p.x, 0, p.y), box: [b.x0, b.y0, b.x1, b.y1] };
    }""")
    assert r["gl"] == "block"
    x0, y0, x1, y1 = r["box"]
    for x, y in r["seals"] + r["floe"]:
        assert x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1, (x, y, r["box"])
    # The ice shows white-ish beside its middle, where no seal stands at the start (they ring the edge).
    mx, my = r["mid"]
    assert ice_brightness(page, mx, my) > 170
    assert page.errors == []


def test_a_phone_without_3d_plays_on_the_2d_drawing(site, context):
    page = open_game(site, context)
    page.wait_for_function("J3D.ready || J3D.failed", timeout=15000)
    page.evaluate("J3D.ready = false; J3D.failed = true")
    go(page)
    page.wait_for_timeout(300)
    assert page.evaluate("getComputedStyle(document.getElementById('g')).display") == "none"
    mx, my = page.evaluate("() => { const p = world.parts[0]; return [X(p.x), Y(p.y)]; }")
    assert ice_brightness(page, mx, my) > 170
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 740), (740, 360)])
def test_pause_stops_the_round_and_quit_ends_the_match(site, context, size):
    page = open_game(site, context, *size)
    assert not page.is_visible("#pauseBtn")      # not on the menu
    go(page)
    btn = page.locator("#pauseBtn").bounding_box()
    assert btn["x"] + btn["width"] <= size[0] and btn["y"] >= 0
    page.evaluate("me.stars = 1; saveMatch()")
    page.tap("#pauseBtn")
    t0 = page.evaluate("world.t")
    page.wait_for_timeout(500)
    assert page.evaluate("[mode, world.t]") == ["pause", t0]
    assert page.is_visible("#resume") and page.is_visible("#quit")
    page.tap("#resume")
    page.wait_for_function(f"mode === 'play' && world.t > {t0}")
    assert page.evaluate("me.stars") == 1
    page.tap("#pauseBtn")
    page.tap("#quit")
    assert page.evaluate("mode") == "menu" and page.is_visible("#menu")
    assert not page.is_visible("#pauseBtn")
    # The quit match does not come back on the next open.
    assert page.evaluate("localStorage.getItem('ai-pelit:jaalautta:kesken1')") is None
    page.reload()
    page.wait_for_function("typeof mode !== 'undefined' && mode === 'menu'")
    assert page.errors == []


def test_leaving_the_app_pauses_a_round_alone(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("""() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange')); }""")
    assert page.evaluate("mode") == "pause"
    assert page.errors == []


def test_an_open_hole_and_a_seal_in_it_show_on_the_3d_ice(site, context):
    page = open_game(site, context)
    page.wait_for_function("J3D.ready || J3D.failed", timeout=15000)
    if page.evaluate("J3D.failed"):
        pytest.skip("this Chromium has no WebGL")
    go(page)
    page.wait_for_function("world.t > 1")      # past the "TÖNI!" over the floe
    # A hole held open beside the middle, with the seals kept away from it and the clock stopped.
    mx, my = page.evaluate("""() => {
      const p = world.parts[0], h = { x: p.x + 3, y: p.y, r: 1.5 * world.scale, warn: 0, open: 1e9 };
      world.holes = [h]; world.holeNext = 1e9; world.ring = null; world.ringNext = 1e9;
      world.seals.forEach((s, i) => { s.x = p.x - 4; s.y = p.y - 5 + i * 3; s.vx = s.vy = 0; });
      brains = world.seals.map(() => null);
      return J3D.project(h.x, 0.14, h.y);
    }""")
    page.wait_for_timeout(300)
    assert ice_brightness(page, mx, my) < 120      # dark water, not white ice over it
    # A seal that goes in through it bobs there with its hat above the ice.
    page.evaluate("() => { const s = world.seals[1], h = world.holes[0]; s.x = h.x; s.y = h.y; }")
    page.wait_for_function("world.seals[1].out > 0")
    hx, hy = page.evaluate("J3D.project(world.seals[1].outX, 0.6, world.seals[1].outY)")
    page.wait_for_timeout(200)
    assert ice_brightness(page, hx, hy) < 150
    assert page.errors == []


@pytest.mark.parametrize("size", [(320, 568), (360, 740)])
def test_the_pause_button_leaves_the_stars_room_on_a_narrow_phone(site, context, size):
    page = open_game(site, context, *size)
    go(page)
    btn = page.locator("#pauseBtn").bounding_box()
    # The right end of the last seal's three stars (drawHUD: x + 16 + 2 × 12, a 12 px star) and the row's bottom.
    right, bottom = page.evaluate("""() => {
      const n = world.seals.length, x0 = SAFE_L + 92, x1 = W - SAFE_R - (LAND || W < 360 ? 12 : 52);
      const cw = Math.min(78, (x1 - x0) / Math.min(n, 4));
      return [x0 + 3 * cw + 16 + 2 * 12 + 12, SAFE_T + 14 + 14];
    }""")
    assert right <= btn["x"] or bottom <= btn["y"], (right, bottom, btn)
    assert right <= size[0]
    assert page.errors == []


@pytest.mark.parametrize("d3", [True, False])
def test_lohkare_drops_on_its_holder_and_presses_it_through_the_ice(site, context, d3):
    page = open_game(site, context)
    page.wait_for_function("J3D.ready || J3D.failed", timeout=15000)
    if d3 and page.evaluate("J3D.failed"):
        pytest.skip("this Chromium has no WebGL")
    if not d3:
        page.evaluate("J3D.ready = false; J3D.failed = true")
    go(page)
    page.wait_for_function("world.t > 1")
    page.evaluate("""() => {
      const p = world.parts[0]; world.ring = null; world.ringNext = 1e9;
      world.seals.forEach((s, i) => { s.x = p.x - 4; s.y = p.y - 5 + i * 3; s.vx = s.vy = 0; });
      brains = world.seals.map(() => null);
      const c = world.seals[1]; c.x = p.x + 3; c.y = p.y; givePower(c, 'lohk'); c.fuse.t = 0.02;
    }""")
    page.wait_for_function("world.seals[1].out > 0")
    # Mid-crush (the block through, the hole open) the spot is dark water; every step draws.
    ms = [0.05, 0.15, 0.3, 0.6, 0.9, 1.2, 1.5]
    for t in ms:
        page.evaluate(f"() => {{ world.seals[1].out = {t}; }}")
        page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        if t == 0.9:
            if d3:
                x, y = page.evaluate("J3D.project(world.seals[1].outX, 0.14, world.seals[1].outY + 0.9)")
            else:
                x, y = page.evaluate("[X(world.seals[1].outX), Y(world.seals[1].outY) + 0.9 * V.s]")
            assert ice_brightness(page, x, y) < 120, t
    assert page.errors == []

"""Pulkkamäki v6 (#475, #480, #517): a 3D sledding hill, alone. Steering, a trick off a jump, a whole run, saves,
the steep hills with drops, no trick begun too late, the hand push, the bends and tunnels (v6)."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/pulkkamaki/v7/"
# A touch on the play area, as a finger makes it.
TOUCH = """([t, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: 9, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# The rest of my run at once, driven by the computer's best sledder, then the end screen.
FINISH = """() => {
  me.cpu = cpuBrain(CPU_SKILL[2], 7);
  for (let i = 0; i < 120 * 240 && !me.fin; i++) { cpuDrive(hill, me, DT); step(hill, me, DT); }
  me.cpu = null; endT = 0.05;
  return me.points;
}"""


def open_game(site, context, width=360, height=740):
    if not (site.games / "pulkkamaki").exists():
        shutil.copytree(ROOT / "games" / "pulkkamaki", site.games / "pulkkamaki")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("V3 || no3d", timeout=20000)
    return page


def go(page):
    page.click("#go")
    page.wait_for_function("mode === 'run'", timeout=8000)


def test_the_menu_opens_the_first_hill_only(site, context):
    page = open_game(site, context)
    assert page.evaluate("!!V3")
    hills = page.locator("#hills button")
    assert hills.count() == 7
    assert [hills.nth(i).is_disabled() for i in range(7)] == [False, True, True, True, True, True, True]
    assert "🔒" in hills.nth(1).inner_text()
    assert page.locator("#friends").is_visible()
    assert page.errors == []


def test_the_sled_keeps_its_heading_when_the_finger_lifts(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate(TOUCH, ["pointerdown", 150, 500])
    page.evaluate(TOUCH, ["pointermove", 260, 500])
    page.wait_for_timeout(700)
    # Lift the finger and read the heading in the same moment: a frame between the two (a busy
    # host) would still be steered and count as a turn after the lift.
    held = page.evaluate("""() => { const y = me.yaw; document.getElementById('c').dispatchEvent(new PointerEvent('pointerup',
      { pointerId: 9, clientX: 260, clientY: 500, bubbles: true, pointerType: 'touch' })); return y; }""")
    assert held > 0.4
    page.wait_for_timeout(600)
    # It is not turned back down the hill by itself (Eero's choice).
    assert page.evaluate("me.yaw") == pytest.approx(held, abs=0.15)
    assert page.errors == []


def test_a_swipe_in_the_air_is_a_flip_that_scores(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("(() => { const k = hill.kicks[0]; me.s = k.s - 25; me.x = k.x; me.y = groundAt(hill, me.s, me.x); me.v = 13; me.yaw = 0; })()")
    page.wait_for_function("me.air", timeout=6000)
    page.evaluate(TOUCH, ["pointerdown", 180, 500])
    page.evaluate(TOUCH, ["pointermove", 180, 430])
    page.evaluate(TOUCH, ["pointerup", 180, 430])
    assert page.evaluate("me.trick && me.trick.type") == "front"
    page.wait_for_function("!me.air && me.pop", timeout=6000)
    assert page.evaluate("me.pop.text").startswith("Etuvoltti")
    assert page.evaluate("me.points") >= 300
    assert page.errors == []


def test_a_whole_run_saves_the_record_and_can_open_the_next_hill(site, context):
    page = open_game(site, context)
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    go(page)
    pts = page.evaluate(FINISH)
    page.wait_for_function("mode === 'end'", timeout=8000)
    assert page.locator("#end").is_visible()
    assert page.locator("#endPts").inner_text() == f"{pts} p"
    assert page.locator("#endList li").count() == 4
    assert page.evaluate("+localStorage.getItem('ai-pelit:pulkkamaki:ennatys-1')") == pts
    assert page.evaluate("sent") == [pts]
    opened = pts >= page.evaluate("HILLS[1].open")
    assert page.evaluate("+localStorage.getItem('ai-pelit:pulkkamaki:auki')") == (2 if opened else 0)
    assert page.locator("#toMenu").is_visible()
    page.click("#toMenu")
    assert page.locator("#hills button").nth(1).is_disabled() == (not opened)
    assert page.errors == []


def test_the_view_choice_is_saved(site, context):
    page = open_game(site, context)
    assert page.locator("#view").inner_text() == "📷 Silmistä"
    page.click("#view")
    assert page.locator("#view").inner_text() == "📷 Takaa"
    page.reload()
    page.wait_for_function("V3 || no3d", timeout=20000)
    assert page.evaluate("V3.view") == "back"
    assert page.errors == []


@pytest.mark.parametrize("width,height", [(360, 640), (390, 844), (740, 360)])
def test_menu_and_end_fit_without_scrolling(site, context, width, height):
    page = open_game(site, context, width, height)
    for b in page.locator("#menu button").all():
        box = b.bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= height, b.inner_text()
    go(page)
    page.evaluate(FINISH)
    page.wait_for_function("mode === 'end'", timeout=8000)
    for b in page.locator("#end button").all():
        box = b.bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= height, b.inner_text()
    assert page.errors == []


def test_turning_the_phone_keeps_the_run(site, context):
    page = open_game(site, context)
    go(page)
    page.wait_for_timeout(500)
    s = page.evaluate("me.s")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(500)
    assert page.evaluate("mode") == "run"
    assert page.evaluate("me.s") > s
    assert page.evaluate("LAND")
    assert page.errors == []


def test_landing_mid_trick_or_into_a_spruce_is_a_fall(site, context):
    page = open_game(site, context)
    go(page)
    # A flip barely begun when the snow comes: a fall, no points, the streak gone.
    got = page.evaluate("""() => {
      me.streak = 3; me.air = true; me.trick = { type: 'front', t: 0.1 }; me.y = groundAt(hill, me.s, me.x);
      land(hill, me); return [me.fallT > 0, me.points, me.streak, me.pop.bad];
    }""")
    assert got == [True, 0, 0, True]
    # Steered into a spruce on the snow.
    got = page.evaluate("""() => {
      me.fallT = 0; me.hitWait = {};
      const o = hill.obst.find(o => o.kind === 'kuusi');
      me.s = o.s - 0.3; me.x = o.x; me.y = groundAt(hill, me.s, me.x); me.air = false; me.v = 8; me.yaw = 0;
      step(hill, me, DT); return [me.fallT > 0, me.pop.text];
    }""")
    assert got == [True, "Kuusi!"]
    assert page.errors == []


def test_the_record_and_opened_hills_survive_a_reload(site, context):
    page = open_game(site, context)
    page.evaluate("() => { localStorage.setItem('ai-pelit:pulkkamaki:ennatys-1', '3100'); localStorage.setItem('ai-pelit:pulkkamaki:auki', '2'); localStorage.setItem('ai-pelit:pulkkamaki:maki', '2'); }")
    page.reload()
    page.wait_for_function("V3 || no3d", timeout=20000)
    hills = page.locator("#hills button")
    assert [hills.nth(i).is_disabled() for i in range(7)] == [False, False, True, True, True, True, True]
    assert "3100" in hills.nth(0).inner_text()
    assert page.evaluate("hillN") == 2
    assert page.errors == []


# Each hill run through by the computer's best sledder and by a sled nobody touches, in game time.
RUNS = """() => HILLS.map((_, i) => i + 1).map(n => {
  const h = buildHill(n), runs = [];
  // The best of three good computer runs (one run's score swings by a third with its luck), and idle.
  for (const brain of [cpuBrain(CPU_SKILL[2], 7), cpuBrain(CPU_SKILL[2], 11), cpuBrain(CPU_SKILL[2], 13), null]) {
    const sl = newSled('t', 't'); placeSled(h, sl, 0); sl.cpu = brain;
    let t = 0;
    for (; t < 150 && !sl.fin; t += DT) { if (brain) cpuDrive(h, sl, DT); step(h, sl, DT); }
    runs.push([sl.fin, Math.round(t), sl.points]);
  }
  const best = runs.slice(0, 3).filter(r => r[0]).sort((a, b) => b[2] - a[2])[0] || runs[0];
  return [best, runs[3]];
})"""


def test_every_hill_can_be_finished_and_doing_nothing_scores_little(site, context):
    page = open_game(site, context)
    runs = page.evaluate(RUNS)
    opens = page.evaluate("HILLS.map(h => h.open)")
    for n, (best, idle) in enumerate(runs, 1):
        assert best[0], (n, runs)   # a good run reaches the bottom
        assert 30 <= best[1] <= 120, (n, runs)   # about a minute down
        assert idle[2] < best[2] / 4, (n, runs)
        if n < len(runs):
            assert best[2] >= opens[n], (n, runs)   # the next hill can be opened
    assert page.errors == []


def test_a_second_run_after_a_finished_one_starts_fresh(site, context):
    page = open_game(site, context)
    page.evaluate("() => { AiPelitScores.submit = () => {}; }")
    go(page)
    first = page.evaluate(FINISH)
    page.wait_for_function("mode === 'end'", timeout=8000)
    page.click("#again")
    page.wait_for_function("mode === 'run'", timeout=8000)
    assert page.evaluate("[me.points, me.fin, me.streak, me.gifts.length, me.s < 10]") == [0, False, 0, 0, True]
    assert page.evaluate("sleds.every(s => !s.fin && s.points === 0)")
    page.evaluate(FINISH)
    page.wait_for_function("mode === 'end'", timeout=8000)
    assert page.evaluate("+localStorage.getItem('ai-pelit:pulkkamaki:ennatys-1')") >= first
    assert page.errors == []


def test_the_score_chip_opens_the_chosen_hills_list_right_away(site, context):
    asked = []
    context.route("**/api/scores?*", lambda route: (asked.append(route.request.url), route.fulfill(
        status=200, content_type="application/json", body='{"rows": [], "mine": null}')))
    page = open_game(site, context)
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_function("document.getElementById('ai-pelit-tulokset')")
    box = page.locator("#ai-pelit-tulokset")
    box.get_by_text("Listalla ei ole vielä ketään.").wait_for(timeout=5000)
    assert "Kotimäki" in box.inner_text()
    assert "Ei verkkoyhteyttä" not in box.inner_text()
    assert any("board=maki-1" in u for u in asked), asked
    assert not any("board=main" in u for u in asked), asked
    assert page.errors == []


def test_a_handover_lets_go_of_a_grab_and_counts_it_only_when_long_enough(site, context):
    # v2 (#475): one rule for a sled changing hands in the air, safe to repeat.
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("mode === 'run'", timeout=8000)
    got = page.evaluate("""() => {
      const air = t => { me.air = true; me.fallT = 0; me.jump = [{ type: 'front', pts: 300 }]; me.grab = true; me.grabT = t; };
      // Then it lands: a grab still held would be a fall that loses the jump's points.
      const landed = () => { const p0 = me.points; land(hill, me); return [me.fallT, me.points > p0]; };
      air(0.1); handOver(me); const short = [me.grab, me.grabT, me.jump.map(j => j.type).join(), ...landed()];
      air(0.6); handOver(me); handOver(me); const long = [me.grab, me.grabT, me.jump.map(j => j.type).join(), ...landed()];
      return [short, long];
    }""")
    assert got == [[False, 0, "front", 0, True], [False, 0, "front,grab", 0, True]]
    assert page.errors == []


def test_the_new_hills_have_steep_stretches_and_drops_that_throw_a_fast_sled(site, context):
    page = open_game(site, context)
    got = page.evaluate("""() => [4, 5].map(n => {
      const h = buildHill(n);
      // The steepest metre of the track, and the drops.
      let steepest = 0;
      for (let s = 1; s < h.len; s++) steepest = Math.max(steepest, h.base[s - 1] - h.base[s]);
      // A fast sled straight at each drop flies off it.
      const flies = h.drops.map(d => {
        const sl = newSled('t', 't'); sl.s = d.s - 3; sl.x = 0; sl.y = groundAt(h, sl.s, 0); sl.v = 14;
        for (let t = 0; t < 1 && !sl.air; t += DT) step(h, sl, DT);
        return sl.air && sl.s < d.s + 2;
      });
      return [h.drops.length, steepest, flies];
    })""")
    for drops, steepest, flies in got:
        assert drops >= 5
        assert steepest >= 2   # a 4 m drop in 2 m
        assert all(flies), flies
    assert page.errors == []


def test_the_steep_stretches_keep_the_sled_on_the_snow(site, context):
    # Down each new hill straight and fast: the sled leaves the snow only at a jump's lip or a drop,
    # never on a steep stretch by itself (the lip test before v4 would have thrown it all the way).
    page = open_game(site, context)
    got = page.evaluate("""() => [4, 5].map(n => {
      const h = buildHill(n), off = [], steep = HILLS[n - 1].steep;
      const sl = newSled('t', 't'); placeSled(h, sl, 0.3); sl.v = 12;
      sl.onEvent = e => { if (e === 'jump') off.push(sl.s); };
      for (let t = 0; t < 150 && !sl.fin; t += DT) { sl.yaw = 0; sl.x = 0.3; step(h, sl, DT); }   // clear of every jump's side edge
      const lip = s => h.drops.some(d => s > d.s - 1 && s < d.s + 2) || h.kicks.some(k => Math.abs(0.3 - k.x) <= k.w / 2 && s > k.s + k.len - 1 && s < k.s + k.len + 1);
      return [sl.fin, off.filter(s => !lip(s)), steep.length];
    })""")
    for fin, stray, steep in got:
        assert fin
        assert stray == []
        assert steep >= 3
    assert page.errors == []


def test_a_swipe_too_near_the_landing_starts_no_trick(site, context):
    page = open_game(site, context)
    go(page)
    # Off a jump: just after the lip there is time for a flip; just before the snow, none.
    page.evaluate("(() => { const k = hill.kicks[0]; me.s = k.s - 25; me.x = k.x; me.y = groundAt(hill, me.s, me.x); me.v = 13; me.yaw = 0; })()")
    page.wait_for_function("me.air", timeout=6000)
    page.evaluate("() => { mode = 'pause'; }")   # held still while the test moves it
    left = page.evaluate("timeToLand(hill, me)")
    assert left > TRICK_FRONT_DONE + 0.05, left
    # Moved to its last fifth of a second in the air, a swipe is refused and says so.
    page.evaluate("""() => { while (timeToLand(hill, me) > 0.2) { me.vy -= G * DT; me.s += me.v * DT; me.y += me.vy * DT; } mode = 'run'; wake(); }""")
    # wake(): a paused game stops drawing after three frames, and a busy host takes longer than that
    # between the pause above and here, so setting the mode alone left the sled hanging in the air.
    page.evaluate(TOUCH, ["pointerdown", 180, 500])
    page.evaluate(TOUCH, ["pointermove", 180, 430])
    page.evaluate(TOUCH, ["pointerup", 180, 430])
    assert page.evaluate("me.trick") is None
    assert page.evaluate("lateT") > 0
    page.wait_for_function("!me.air", timeout=6000)
    assert page.evaluate("me.fallT") == 0
    # The same rule in the numbers: a flip fits only with LAND_DONE of it left before the snow,
    # a second one only after what is left of the first, and no grab in the last moment.
    got = page.evaluate("""() => {
      const sl = newSled('t', 't'); sl.air = true; sl.s = 100; sl.x = 0; sl.v = 0;   // straight down: t = √(2h / G)
      const at = t => { sl.y = groundAt(hill, sl.s, sl.x) + 0.5 * G * t * t; sl.vy = 0; };
      at(0.3); const late = startTrick(sl, 'front', hill), grabLate = setGrab(sl, true, hill);
      at(1.2); const early = startTrick(sl, 'front', hill), second = startTrick(sl, 'back', hill);
      return [late, grabLate, early, second, sl.queue];
    }""")
    assert got == [False, False, True, False, None]
    assert page.errors == []


TRICK_FRONT_DONE = 0.72 * 0.8


def test_a_stopped_sled_is_pushed_on_with_the_hands(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { me.v = 0.6; me.fallT = 0; }")
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    page.evaluate(TOUCH, ["pointerdown", 180, 500])
    page.evaluate(TOUCH, ["pointerup", 180, 500])
    v = page.evaluate("me.v")
    assert v > 2.8, v
    assert page.evaluate("me.pushT") > 0
    # A few pushes add up to a good speed (v5, Eero: "pitää päästä ihan hyvään vauhtiin käsillä") and no more;
    # a sled going well is not pushed.
    got = page.evaluate("""() => {
      const sl = newSled('t', 't'); sl.v = 0.6;
      const a = []; for (let i = 0; i < 6; i++) a.push(pushOff(sl));
      const top = sl.v; sl.v = 10.5; const fast = pushOff(sl);
      sl.v = 0.6; sl.air = true; const air = pushOff(sl);
      return [a, top, fast, air];
    }""")
    assert got[0] == [True, True, True, True, False, False]
    assert got[1] == 10
    assert got[2:] == [False, False]
    # Off the course, in the deep snow, pushes stop at v4's 4.2 m/s, so leaving the course still costs its speed.
    off = page.evaluate("""() => {
      const sl = newSled('t', 't'); placeSled(hill, sl, 0); sl.x = hill.width; sl.v = 0.6;
      for (let i = 0; i < 6; i++) pushOff(sl, hill);
      return sl.v;
    }""")
    assert off == 4.2
    # A steering drag on the snow is no push, nor a drag back to where it began, nor a quick swipe up or down,
    # nor a long press: only a short tap is (v5).
    page.evaluate("() => { me.v = 4; me.fallT = 0; me.air = false; }")
    for path in ([(260, 500)], [(260, 500), (182, 500)], [(180, 420)], [(180, 580), (180, 505)]):
        page.evaluate(TOUCH, ["pointerdown", 180, 500])
        for x, y in path:
            page.evaluate(TOUCH, ["pointermove", x, y])
        page.evaluate(TOUCH, ["pointerup", *path[-1]])
    page.evaluate(TOUCH, ["pointerdown", 180, 500])
    page.wait_for_timeout(400)
    page.evaluate(TOUCH, ["pointerup", 180, 500])
    assert page.evaluate("me.v") < 5.5   # the hill adds well under a push (+2.5) in the 0.4 s
    assert page.errors == []


def test_a_hand_push_is_sent_to_the_other_phones(site, context):
    # The arms of a push go with the sled's message (net.js pack/unpack), so friends see it too.
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const a = newSled('a', 'a'); a.v = 0.6; pushOff(a);
      const b = newSled('b', 'b'); unpack(b, pack(a));
      const c = newSled('c', 'c'); unpack(c, pack(newSled('d', 'd')));
      return [b.pushT, c.pushT];
    }""")
    assert got == [0.35, 0]
    assert page.errors == []


def test_the_v6_hills_bend_sharply_and_go_through_tunnels(site, context):
    # #517 v6: "Lisää kenttiä. Voisi olla tunneleita jne", "Mutkia voisi olla".
    page = open_game(site, context)
    got = page.evaluate("""() => [1, 2, 3, 4, 5, 6, 7].map(n => {
      const h = buildHill(n);
      let bend = 0;   // the sharpest turn of the course, radians per metre
      for (let s = 1; s < h.len; s++) bend = Math.max(bend, Math.abs(courseDir(h, s + 1) - courseDir(h, s - 1)) / 2);
      // Nothing throws a sled into a roof: no jump or drop inside a tunnel or in the 40 m before it,
      // and nothing to hit inside one.
      const clear = h.tunnels.every(t =>
        h.kicks.every(k => k.s + k.len < t.s - 40 || k.s > t.s + t.len) &&
        h.drops.every(d => d.s < t.s - 40 || d.s > t.s + t.len) &&
        h.obst.every(o => o.s < t.s - 3 || o.s > t.s + t.len + 3));
      return [h.name, h.tunnels.length, bend, clear];
    })""")
    names = [g[0] for g in got]
    assert names[5:] == ["Mutkamäki", "Luolasto"]
    for name, tunnels, bend, clear in got[:5]:
        assert tunnels == 0 and bend < 0.01, (name, bend)   # the older hills stay as they were
    for name, tunnels, bend, clear in got[5:]:
        assert tunnels >= 2 and bend > 0.015 and clear, (name, tunnels, bend, clear)
    assert got[6][1] >= 3
    assert page.errors == []


def test_a_tunnels_walls_keep_the_sled_in_and_its_roof_keeps_it_low(site, context):
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const h = buildHill(7), t = h.tunnels[1], lim = h.width / 2 + WALL;
      // Steered hard at the right wall all through the tunnel.
      const sl = newSled('t', 't'); sl.s = t.s + 2; sl.x = 0; sl.y = groundAt(h, sl.s, 0); sl.v = 14;
      let walls = 0, widest = 0; sl.onEvent = e => { if (e === 'wall') walls++; };
      while (sl.s < t.s + t.len - 2) { sl.steer = 1; step(h, sl, DT); widest = Math.max(widest, Math.abs(sl.x)); }
      // Thrown up hard inside it: it stays under the roof.
      const up = newSled('u', 'u'); up.s = t.s + 10; up.x = 0; up.y = groundAt(h, up.s, 0) + 0.5; up.v = 12;
      up.air = true; up.vy = 14;
      let over = -99;
      for (let i = 0; i < 240 && up.air; i++) { step(h, up, DT); over = Math.max(over, up.y - (baseAt(h, up.s) + ROOF)); }
      // Out in the open the same throw goes far higher.
      const out = newSled('o', 'o'); out.s = t.s - 60; out.x = 0; out.y = groundAt(h, out.s, 0) + 0.5; out.v = 12;
      out.air = true; out.vy = 14;
      let high = 0;
      for (let i = 0; i < 240 && out.air; i++) { step(h, out, DT); high = Math.max(high, out.y - baseAt(h, out.s)); }
      return { walls, widest, lim, v: sl.v, over, high, fell: sl.fallT > 0 };
    }""")
    assert got["widest"] <= got["lim"], got
    assert got["walls"] >= 1 and not got["fell"], got   # it knocks the wall but does not fall
    assert got["v"] > 5, got   # and slides on
    assert got["over"] < 0, got   # under the roof all the time
    assert got["high"] > 6, got
    assert page.errors == []


def test_an_unsteered_sled_keeps_its_world_heading_through_a_sharp_bend(site, context):
    # Review of #525: the old fix kept course + yaw, but the real heading is atan(slope + tan(yaw)),
    # so on Mutkamäki an unsteered sled turned some 17 degrees by itself.
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const h = buildHill(6), dir = sl => Math.atan(courseSlope(h, sl.s) + Math.tan(sl.yaw));
      const air = newSled('a', 'a'); air.s = 20; air.x = 0; air.yaw = 0.45; air.v = 15;
      air.y = groundAt(h, 20, 0) + 60; air.air = true; air.vy = 0;
      const a0 = dir(air); let aMax = 0;
      while (air.s < 50 && air.air) { step(h, air, DT); aMax = Math.max(aMax, Math.abs(dir(air) - a0)); }
      const snow = newSled('g', 'g'); snow.s = 20; snow.x = 0; snow.yaw = 0.2; snow.v = 6; snow.y = groundAt(h, 20, 0);
      const g0 = dir(snow); let gMax = 0;
      for (let i = 0; i < 40; i++) { step(h, snow, DT); gMax = Math.max(gMax, Math.abs(dir(snow) - g0)); }
      const bend = Math.abs(courseDir(h, 50) - courseDir(h, 20));
      return { aMax, gMax, bend, s: air.s, air: air.air };
    }""")
    assert got["bend"] > 0.2, got   # the course really bends there
    assert got["air"] or got["s"] >= 50, got
    assert got["aMax"] < 0.01, got
    assert got["gMax"] < 0.03, got   # on the snow only the banks and slopes turn it a little
    assert page.errors == []


def test_a_sled_beside_the_track_stops_at_a_tunnels_mound_not_through_it(site, context):
    # Helper find on #525: a sled out beside the track reaching a tunnel was set onto the wall line,
    # moving it metres sideways through the snow mound in one step.
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const h = buildHill(7), t = h.tunnels[0], lim = h.width / 2 + WALL - 0.4;
      const sl = newSled('m', 'm'); sl.s = t.s - 6; sl.x = lim + 4; sl.y = groundAt(h, sl.s, sl.x); sl.v = 12;
      let jump = 0, fell = false, inside = 0;
      for (let i = 0; i < 120 * 20 && sl.s < t.s + 20; i++) {
        const x = sl.x; step(h, sl, DT); jump = Math.max(jump, Math.abs(sl.x - x));
        fell = fell || sl.fallT > 0;
        if (tunnelAt(h, sl.s)) inside = Math.max(inside, Math.abs(sl.x));
      }
      return { jump, fell, inside, lim, s: sl.s, end: t.s + 20, v: sl.v, x: sl.x };
    }""")
    assert got["jump"] < 0.5, got   # never moved sideways in one leap
    assert got["fell"], got   # it hit the mound
    assert got["inside"] <= got["lim"] + 1e-6, got
    assert got["s"] >= got["end"], got   # and found its way into the tunnel
    assert page.errors == []


def test_a_fast_sled_rides_up_the_outer_curve_of_a_bend_and_back(site, context):
    # Eero, v6: "Voisko olla mahdollista että mutkassa voi nousta sinne ulkokurviin ylös".
    page = open_game(site, context)
    got = page.evaluate("""() => [6, 7].map(n => {
      const h = buildHill(n);
      // The highest berm with no jump or drop near it, and which side it is on.
      // (and no tunnel mouth within 70 m after it: a sled still out wide there hits its mound)
      const near = s => h.kicks.some(k => Math.abs(k.s - s) < 45) || h.drops.some(d => Math.abs(d.s - s) < 45)
        || h.tunnels.some(t => t.s > s && t.s - s < 70);
      let at = 0;
      for (let s = 60; s < h.len - 40; s++) if (!near(s) && Math.abs(h.berm[s]) > Math.abs(h.berm[at])) at = s;
      const out = Math.sign(h.berm[at]);
      // Fast, nobody steering, a little towards the outside: it rides up the outer curve.
      h.obst = [];   // only the bank here: a spruce by the track on its way back is luck
      const sl = newSled('t', 't'); sl.s = at - 20; sl.x = 0; sl.y = groundAt(h, sl.s, sl.x); sl.v = 20;
      sl.yaw = out * 0.2;
      let up = 0, back = false, flew = false, t = 0;
      for (; t < 7 && !back; t += DT) {
        step(h, sl, DT);
        flew = flew || sl.air;
        up = Math.max(up, sl.y - baseAt(h, sl.s));
        back = up > 1 && Math.abs(sl.x) < h.width / 2 - 1;
      }
      // The inner side of the bend stays flat, and the old hills have no berms.
      const inner = bermAt(h, at, -out * h.width / 2);
      return { berm: Math.abs(h.berm[at]), up, back, flew, fell: sl.fallT > 0, inner,
        old: Math.max(...[1, 2, 3, 4, 5].map(k => Math.max(...buildHill(k).berm.map(Math.abs)))) };
    })""")
    for g in got:
        assert g["berm"] > 1, g
        assert g["up"] > 1, g   # it rides up the outer curve
        assert g["back"] and not g["fell"] and not g["flew"], g   # and comes back down onto the track, on the snow
        assert g["inner"] == 0 and g["old"] == 0, g
    assert page.errors == []

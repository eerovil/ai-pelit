"""Pulkkamäki v1 (#475): a 3D sledding hill, alone. Steering, a trick off a jump, a whole run, saves."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/pulkkamaki/v1/"
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
    assert hills.count() == 3
    assert [hills.nth(i).is_disabled() for i in range(3)] == [False, True, True]
    assert "🔒" in hills.nth(1).inner_text()
    assert page.locator("#friends").is_visible()
    assert page.errors == []


def test_the_sled_keeps_its_heading_when_the_finger_lifts(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate(TOUCH, ["pointerdown", 150, 500])
    page.evaluate(TOUCH, ["pointermove", 260, 500])
    page.wait_for_timeout(700)
    held = page.evaluate("me.yaw")
    assert held > 0.4
    page.evaluate(TOUCH, ["pointerup", 260, 500])
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
    assert [hills.nth(i).is_disabled() for i in range(3)] == [False, False, True]
    assert "3100" in hills.nth(0).inner_text()
    assert page.evaluate("hillN") == 2
    assert page.errors == []


# Each hill run through by the computer's best sledder and by a sled nobody touches, in game time.
RUNS = """() => [1, 2, 3].map(n => {
  const h = buildHill(n), out = [];
  for (const brain of [cpuBrain(CPU_SKILL[2], 11), null]) {
    const sl = newSled('t', 't'); placeSled(h, sl, 0); sl.cpu = brain;
    let t = 0;
    for (; t < 150 && !sl.fin; t += DT) { if (brain) cpuDrive(h, sl, DT); step(h, sl, DT); }
    out.push([sl.fin, Math.round(t), sl.points]);
  }
  return out;
})"""


def test_every_hill_can_be_finished_and_doing_nothing_scores_little(site, context):
    page = open_game(site, context)
    runs = page.evaluate(RUNS)
    opens = page.evaluate("HILLS.map(h => h.open)")
    for n, (best, idle) in enumerate(runs, 1):
        assert best[0], (n, runs)   # a good run reaches the bottom
        assert 30 <= best[1] <= 120, (n, runs)   # about a minute down
        assert idle[2] < best[2] / 4, (n, runs)
        if n < 3:
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

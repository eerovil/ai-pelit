"""Voimistelu v11: recorded sounds from the shared library public/lib/aanet-2/ (#233, #205)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/voimistelu/v12/"
SOUNDS = ["onnistui", "valinta", "suhahdus", "lyonti", "tomahdys", "voitto", "tappio"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

# Drop the body onto the mat from a standstill at angle phi, and play the routine to its score board.
DROP = """([phi, lv]) => { newRoutine(); level = lv; hold = false;
  launchAir({ x: -1.5, y: -1.2, phi });
  for (let t = 0; t < 4 && mode !== 'result'; t += 1 / 60) step(1 / 60);
  return [mode, result.stuck, result.fall, result.passed]; }"""

# From just before the handstand on one side of the high bar, over it, to the other side: a Tkatchev.
OVER = """(T) => { newRoutine(); const a = Math.PI - 0.6, r = R_EXT;
  launchAir({ x: r * Math.sin(a), y: -r * Math.cos(a), vx: -2 * r * Math.sin(a) / T, vy: G * T / 2, phi: a, w: 1.2 / T });
  for (let t = 0; t < 2 && mode === 'air'; t += 1 / 240) step(1 / 240);
  return [mode, elements.map(e => e.name)]; }"""


@pytest.fixture
def voim_site(site, tmp_path):
    # Only this game is built: other games' half-done versions cannot break this test.
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "voimistelu", games / "voimistelu")
    site.build(games)
    return site


def open_game(site, context, sound=True):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof newRoutine === 'function'")
    page.evaluate(SPY)
    if sound:
        page.mouse.click(180, 500)  # the first tap turns sound on
        page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("newRoutine(); hold = false; heard.splice(0)")
    return page, errors


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_stuck_landing_thuds_and_blips(voim_site, context):  # #337: no applause
    page, errors = open_game(voim_site, context)
    mode, stuck, fall, passed = page.evaluate(DROP, [0, 1])
    assert (mode, stuck, fall, passed) == ("result", True, False, True)
    assert played(page) == ["valinta", "tomahdys", "onnistui", "voitto"]
    assert errors == []


def test_a_fall_thuds_and_the_task_fails(voim_site, context):  # #337: no crowd's ooh
    page, errors = open_game(voim_site, context)
    mode, stuck, fall, passed = page.evaluate(DROP, [1.8, 1])
    assert (mode, fall, passed) == ("result", True, False)
    assert played(page) == ["valinta", "tomahdys", "tappio"]
    assert errors == []


def test_letting_go_and_a_twist_whoosh_and_a_catch_hits_the_bar(voim_site, context):
    page, errors = open_game(voim_site, context)
    page.evaluate("release()")
    assert played(page) == ["suhahdus"]
    page.evaluate("twist(1)")
    assert played(page) == ["suhahdus"]
    mode, names = page.evaluate(OVER, 0.7)
    assert mode == "bar" and names == ["Tkatchev"]
    assert played(page) == ["valinta", "lyonti"]
    assert errors == []


def test_a_giant_swing_whooshes_quietly(voim_site, context):
    page, errors = open_game(voim_site, context)
    names = page.evaluate("""() => { th = 0; Lb = 9 * (icBar(0) + R_EXT * R_EXT); syncBar();
      for (let t = 0; t < 3; t += 1 / 60) step(1 / 60); return elements.map(e => e.name); }""")
    assert names and all(n.startswith("Jättikierto") for n in names)
    got = page.evaluate("heard.splice(0).filter(h => h[1])")
    assert [n for n, _ in got[:2]] == ["suhahdus", "valinta"]
    assert errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(voim_site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page, errors = open_game(voim_site, ctx, sound=False)
        page.mouse.click(180, 500)
        mode, stuck, fall, passed = page.evaluate(DROP, [0, 1])
        assert (mode, passed) == ("result", True)
        assert played(page) == []
        assert errors == []
    finally:
        ctx.close()


def test_v10_saves_are_read_as_they_are(voim_site, context):
    page = context.new_page()
    page.add_init_script("""for (const [k, v] of [['taso', 23], ['paras', 12.345], ['suoritukset', 40]])
      localStorage.setItem('ai-pelit:voimistelu:' + k, JSON.stringify(v));""")
    page.goto(voim_site.url + URL)
    page.wait_for_function("typeof newRoutine === 'function'")
    assert page.evaluate("[level, best, routines]") == [23, 12.345, 40]


def test_before_the_first_tap_it_is_silent_and_the_next_routine_sounds_again(voim_site, context):
    # The online list asks once for a nickname on the first score: asked already, so the board is the game's.
    context.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:kysytty', 'true')")
    page, errors = open_game(voim_site, context, sound=False)
    page.evaluate(DROP, [0, 1])
    assert played(page) == []
    # The tap on the score board starts the next routine and turns sound on; it then sounds as the first.
    page.evaluate("resultT = 1")
    page.mouse.click(180, 500)
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    assert page.evaluate("mode") == "bar"
    page.evaluate("heard.splice(0)")
    page.evaluate(DROP, [1.8, 2])
    assert played(page) == ["valinta", "tomahdys", "tappio"]
    assert errors == []


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/voimistelu/v12")

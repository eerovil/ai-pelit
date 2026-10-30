"""Jään alla v3 (#106): chapter 2, the rescue of Aurora's crew from the ice at the northern shore."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/jaan-alla/v3/"
SAVE = "ai-pelit:jaan-alla:peli"
# A save from v1 or v2 with chapter 1 just finished: no crew, no warmth yet.
CHAPTER1_DONE = ("{v: 1, t: 900, flags: {stationLog: true, nordlysLog: true, jaavuoriLog: true, radio: true},"
                 " inv: {ruoka: 3, romu: 1, antenni: 1, kristalli: 1}, m: {power: 90, food: 70, hull: 80, air: 100},"
                 " sub: {x: 150, y: -12, z: 150, yaw: -0.8}}")

RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"
OVERFLOW = """() => {
  const bad = [];
  for (const el of document.querySelectorAll('#panel:not(.hidden) .card, #panel:not(.hidden) .txt, #menu:not(.hidden) .card'))
    if (el.scrollHeight > el.clientHeight + 1) bad.push('scrolls ' + el.className);
  for (const el of document.querySelectorAll('#panel:not(.hidden) button, #menu:not(.hidden) button')) {
    const r = el.getBoundingClientRect();
    if (r.width && (r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth)) bad.push('out ' + el.textContent);
  }
  return bad;
}"""

_opened = []


@pytest.fixture(autouse=True)
def _close_pages():
    yield
    while _opened:
        try:
            _opened.pop().close()
        except Exception:
            pass


def open_game(site, browser, w=360, h=740, save=CHAPTER1_DONE):
    shutil.copytree(ROOT / "games" / "jaan-alla", site.games / "jaan-alla")
    site.build()
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    _opened.append(ctx)
    if save:
        ctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded', '1');"
                            f" localStorage.setItem('{SAVE}', JSON.stringify({save})); }}")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    page.evaluate(RUN)
    return page


def go(page):
    """Continues the saved game and stops the clock: the tests step it themselves."""
    page.click("#jatka")
    page.evaluate("G.hold = true; input.x = input.y = 0; input.up = input.down = false")


def on_ice(page):
    go(page)
    page.evaluate("sub.pos.set(HOLE.x, -8, HOLE.z + 3); drawHud()")
    assert page.inner_text("#act") == "Nouse jäälle"
    page.click("#act")
    page.click("#card button:has-text('Lähde')")


def test_a_chapter_1_save_from_an_older_version_goes_on_to_chapter_2(site, browser):
    page = open_game(site, browser)
    assert "Luku 2" in page.inner_text("#menuText")
    go(page)
    page.evaluate("drawHud()")
    assert page.inner_text("#goal").startswith("Tavoite: Aja pohjoiseen avantoon")
    assert page.evaluate("[G.s.crew.length, crewAt('ice'), G.s.m.warm, G.s.inv.romu]") == [12, 12, 100, 1]
    assert page.errors == []


def test_fixing_the_radio_in_chapter_1_starts_chapter_2(site, browser):
    page = open_game(site, browser, save=None)
    page.click("#uusi")
    page.click("#card button:has-text('Sukella!')")
    page.evaluate("G.hold = true; Object.assign(G.s.flags, { stationLog: true, nordlysLog: true, jaavuoriLog: true });"
                  "Object.assign(G.s.inv, { antenni: 1, kristalli: 1, romu: 2 }); dock()")
    page.click("#card button:has-text('Radiomasto: korjaa')")
    assert "Luku 2 alkaa" in page.inner_text("#card")
    assert page.evaluate("[G.s.crew.length, crewAt('ice')]") == [12, 12]


def test_surfacing_puts_the_walker_on_the_ice_with_a_warmth_meter(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("drawHud()")
    assert page.evaluate("G.mode") == "ice"
    assert page.is_visible("#mWarm") and page.is_hidden("#mAir") and page.is_hidden("#up") and page.is_hidden("#bag")
    assert page.inner_text("#goal") == "Tavoite: Etsi Aino rannan leiristä."
    page.evaluate("input.y = 1; run(() => true, 2); input.y = 0")
    assert page.evaluate("[walker.pos.z < -5, G.s.m.warm < 100]") == [True, True]
    assert page.errors == []


def test_aino_tells_the_story_and_only_four_follow_at_a_time(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("walker.pos.set(CAMP.x, 0, CAMP.z + 1.5); step(1 / 60)")
    assert page.evaluate("G.s.flags.aino") is True
    assert "punaiset soihdut" in page.inner_text("#card")
    page.click("#card button:has-text('Selvä')")
    # Walk past the whole camp: four join, the rest wait for the next trip.
    page.evaluate("for (const c of G.s.crew.slice(0, 7)) { walker.pos.set(c.x, 0, c.z + 0.5); step(1 / 60); }")
    assert page.evaluate("[crewAt('follow'), crewAt('ice')]") == [4, 8]
    page.evaluate("drawHud()")
    assert "Vie mukanasi olevat (4)" in page.inner_text("#goal")
    # Back at the hole they board, and the goal turns to the station.
    page.evaluate("walker.pos.set(0, 0, 3); drawHud()")
    assert page.inner_text("#act") == "Palaa SISUun (4 mukana)"
    page.click("#act")
    page.evaluate("drawHud()")
    assert page.evaluate("[G.mode, crewAt('sub')]") == ["sub", 4]
    assert "Vie kyydissä olevat (4) Aurora-asemalle" in page.inner_text("#goal")
    assert "kyydissä 4/4" in page.inner_text("#where")
    page.evaluate("dock()")
    assert "4 ihmistä pääsi turvaan asemalle (4/12)" in page.inner_text("#card")
    assert page.evaluate("[crewAt('station'), crewAt('sub')]") == [4, 0]


def test_followers_keep_up_and_the_storm_grows_with_each_trip(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("G.s.flags.aino = true; const c = G.s.crew[7]; walker.pos.set(c.x, 0, c.z + 0.5); step(1 / 60)")
    page.evaluate("walker.yaw = Math.PI / 2; input.y = 1; run(() => true, 3); input.y = 0")
    assert page.evaluate("Math.hypot(G.s.crew[7].x - walker.pos.x, G.s.crew[7].z - walker.pos.z)") < 2.5
    s0 = page.evaluate("storm()")
    page.evaluate("G.s.crew.slice(0, 6).forEach(c => c.at = 'station')")
    assert page.evaluate("storm()") > s0


def test_the_fire_warms_and_the_cold_sends_you_back_with_followers_left_waiting(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("G.s.flags.aino = true; G.s.m.warm = 30; walker.pos.set(FIRE.x + 3, 0, FIRE.z); run(() => true, 2)")
    assert page.evaluate("G.s.m.warm") > 70
    page.evaluate("const c = G.s.crew[8]; walker.pos.set(c.x, 0, c.z + 0.5); step(1 / 60)")
    assert page.evaluate("crewAt('follow')") == 1
    page.evaluate("G.s.m.warm = 0.5; run(() => G.mode === 'ice', 2)")
    assert page.evaluate("[G.mode, crewAt('follow'), crewAt('ice')]") == ["sub", 0, 12]
    assert "Kylmä yllätti" in page.inner_text("#card")


def test_the_polar_bear_chases_slowly_and_its_shove_costs_warmth(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("walker.pos.set(20, 0, -20); bear.state = 'walk'; bear.pos.set(30, 0, -20); G.s.m.warm = 100")
    page.evaluate("run(() => bear.state !== 'away', 10)")
    assert page.evaluate("[bear.state, Math.round(G.s.m.warm)]")[0] == "away"
    assert page.evaluate("G.s.m.warm") < 75
    # Walking away outruns it.
    page.evaluate("bear.state = 'walk'; walker.pos.set(20, 0, -20); bear.pos.set(20, 0, -14); walker.yaw = 0; input.y = 1; run(() => true, 3); input.y = 0")
    assert page.evaluate("Math.hypot(bear.pos.x - walker.pos.x, bear.pos.z - walker.pos.z)") > 6


def test_the_last_trip_ends_chapter_2_and_saves_it(site, browser):
    page = open_game(site, browser)
    go(page)
    page.evaluate("G.s.crew.forEach((c, i) => c.at = i < 8 ? 'station' : 'sub'); dock()")
    assert page.inner_text("#card h2") == "Kaikki turvassa!"
    assert "Luku 2 päättyi" in page.inner_text("#card")
    assert page.evaluate("[G.s.flags.rescued, localStorage.getItem('ai-pelit:jaan-alla:luku2') !== null]") == [True, True]
    page.click("#card button:has-text('Jatka tutkimista')")
    page.evaluate("drawHud()")
    assert "Kaikki on pelastettu" in page.inner_text("#goal")
    # Docking again is just docking.
    page.evaluate("document.getElementById('panel').classList.add('hidden'); G.paused = false; dock()")
    assert page.inner_text("#card h2") == "Aurora-asema A-3"
    page.reload()
    page.wait_for_function("window.drawn === true")
    assert "Luvut 1 ja 2" in page.inner_text("#menuText")


def test_a_reload_on_the_ice_resumes_in_sisu_by_the_hole_and_followers_wait(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("G.s.flags.aino = true; const c = G.s.crew[9]; walker.pos.set(c.x, 0, c.z + 0.5); step(1 / 60); saveGame()")
    assert page.evaluate("crewAt('follow')") == 1
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    assert page.evaluate("[G.mode, crewAt('follow'), crewAt('ice')]") == ["sub", 0, 12]
    assert page.evaluate("Math.hypot(sub.pos.x - HOLE.x, sub.pos.z - HOLE.z)") < 6


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844), (740, 360)])
def test_the_ice_screen_and_its_cards_fit_upright_and_sideways(site, browser, w, h):
    page = open_game(site, browser, w, h)
    page.click("#jatka")
    page.evaluate("G.hold = true; sub.pos.set(HOLE.x, -8, HOLE.z + 3); drawHud()")
    page.click("#act")
    assert page.evaluate(OVERFLOW) == [], "surface card"
    page.click("#card button:has-text('Lähde')")
    page.evaluate("walker.pos.set(CAMP.x, 0, CAMP.z + 1.5); step(1 / 60)")
    assert page.evaluate(OVERFLOW) == [], "Aino"
    page.click("#card button:has-text('Selvä')")
    page.evaluate("walker.pos.set(0, 0, 3); drawHud()")
    r = page.evaluate("""() => {
        const b = id => document.getElementById(id).getBoundingClientRect();
        return { goal: b('goalbar'), act: b('act'), stick: b('stick'), w: innerWidth, h: innerHeight };
    }""")
    for k in ("act", "stick"):
        assert r[k]["left"] >= 0 and r[k]["right"] <= r["w"] and r[k]["bottom"] <= r["h"], k
        assert r[k]["top"] > r["goal"]["bottom"], k
    page.evaluate("G.s.crew.forEach((c, i) => c.at = i < 8 ? 'station' : 'sub'); boardSisu(); dock()")
    assert page.evaluate(OVERFLOW) == [], "ending"
    assert page.errors == []


def test_turning_the_phone_on_the_ice_keeps_the_walk(site, browser):
    page = open_game(site, browser)
    on_ice(page)
    page.evaluate("walker.pos.set(10, 0, -10)")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert page.evaluate("[G.mode, Math.round(walker.pos.x), Math.round(walker.pos.z)]") == ["ice", 10, -10]

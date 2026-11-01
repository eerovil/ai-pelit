"""Jään alla v5 (#214): recorded sounds and background loops from lib/aanet-2 instead of beeps."""

import shutil

import pytest

from conftest import ROOT

URL = "games/jaan-alla/v5/"
SAVE = "ai-pelit:jaan-alla:peli"
CHAPTER1_DONE = ("{v: 1, t: 900, flags: {stationLog: true, nordlysLog: true, jaavuoriLog: true, radio: true},"
                 " inv: {ruoka: 3, romu: 1, antenni: 1, kristalli: 1}, m: {power: 90, food: 70, hull: 80, air: 100, warm: 100},"
                 " crew: Array.from({length: 12}, (_, i) => ({n: i ? 'x' + i : 'Aino', at: 'ice', x: 40, z: 40})),"
                 " sub: {x: 150, y: -12, z: 150, yaw: -0.8}}")
# Records what the game asks the library to play, and the loops' latest settings.
SPY = """() => {
  window.played = [];
  const play = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { played.push(name); return play(name, o); };
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


def open_game(site, browser):
    shutil.copytree(ROOT / "games" / "jaan-alla", site.games / "jaan-alla")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    _opened.append(ctx)
    ctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded', '1');"
                        f" localStorage.setItem('{SAVE}', JSON.stringify({CHAPTER1_DONE})); }}")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    page.evaluate(SPY)
    page.click("#jatka")
    page.evaluate("G.hold = true; input.x = input.y = 0; input.up = input.down = false")
    return page


def test_the_library_loads_the_sounds_the_issue_names(site, browser):
    page = open_game(site, browser)
    # The first tap unlocked sound, so the library decodes what the game named.
    page.wait_for_function("['valinta', 'onnistui', 'naksu', 'metalli', 'tomahdys', 'karhu', 'halytys', 'kaiku',"
                           " 'kupla', 'lumi', 'syvyys', 'sukellusvene', 'kuplat', 'tuuli'].every(AiPelitAanet.ready)",
                           timeout=15000)
    page.evaluate("sfx('pick'); sfx('story'); sfx('alarm')")
    assert page.evaluate("played") == ["valinta", "onnistui", "halytys"]
    assert page.errors == []


def test_each_moment_plays_its_sound(site, browser):
    page = open_game(site, browser)
    page.wait_for_function("['kaiku', 'kupla', 'metalli', 'lumi', 'tomahdys'].every(AiPelitAanet.ready)", timeout=15000)
    page.evaluate("played.length = 0; G.pingT = 0.01; step(1 / 60)")
    assert "kaiku" in page.evaluate("played"), "sonar"
    page.evaluate("played.length = 0; enterSite('nordlys')")
    assert page.evaluate("played") == ["kupla"], "diving out"
    page.evaluate("played.length = 0; leaveSite(); G.s.m.hull = 100; G.warnT = 9; hurt(5, 'x')")
    assert page.evaluate("played") == ["kupla", "metalli"], "back aboard, a knock on the hull"
    page.evaluate("played.length = 0; surface(); G.hold = true;"
                  " walker.pos.set(0, 0, -11); walker.yaw = Math.PI; input.y = 1; for (let i = 0; i < 60; i++) step(1 / 60); input.y = 0")
    assert page.evaluate("played.filter(n => n === 'lumi').length") >= 2, "steps in the snow"
    page.evaluate("played.length = 0; bear.state = 'walk'; bear.pos.set(walker.pos.x + 1, 0, walker.pos.z); step(1 / 60)")
    assert page.evaluate("played") == ["tomahdys", "karhu"], "the bear's shove"
    assert page.errors == []


def test_the_background_follows_where_the_player_is(site, browser):
    page = open_game(site, browser)
    page.wait_for_function("loops && loops.deep.playing() && loops.engine.playing()", timeout=15000)
    vols = "() => Object.fromEntries(Object.entries(loops).map(([k, l]) => [k, l.vol]))"
    page.evaluate("sub.vel.set(0, 0, 0)")
    page.wait_for_timeout(100)
    idle = page.evaluate(vols)
    assert idle["deep"] > 0 and idle["engine"] > 0 and idle["bubbles"] == 0 and idle["wind"] == 0
    page.evaluate("sub.vel.set(12, 0, 0)")
    page.wait_for_timeout(100)
    assert page.evaluate(vols)["engine"] > idle["engine"]
    assert page.evaluate("loops.engine.rate") > 1
    page.evaluate("enterSite('nordlys')")
    page.wait_for_timeout(100)
    dive = page.evaluate(vols)
    assert dive["deep"] > 0 and dive["bubbles"] > 0 and dive["engine"] == 0 and dive["wind"] == 0
    page.evaluate("leaveSite(); surface(); G.hold = true")
    page.wait_for_timeout(100)
    on_ice = page.evaluate(vols)
    assert on_ice["wind"] > 0 and on_ice["deep"] == 0 and on_ice["engine"] == 0
    assert page.errors == []


def test_with_no_library_the_game_still_plays(site, browser):
    """Offline on the very first open the library may be missing: the game plays on with its beeps."""
    shutil.copytree(ROOT / "games" / "jaan-alla", site.games / "jaan-alla")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    _opened.append(ctx)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.route("**/aanet.js", lambda r: r.abort())
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    page.click("#uusi")
    page.click("#card button:has-text('Sukella')")
    page.evaluate("G.hold = true; sfx('pick'); sfx('bear'); sfx('snow'); G.pingT = 0.01; step(1 / 60); enterSite('nordlys')")
    page.wait_for_timeout(200)
    assert page.evaluate("G.mode") == "dive"
    assert page.errors == []

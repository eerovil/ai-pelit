"""Vauvan syöttäminen v3: recorded sounds from the shared library public/lib/aanet-2/ (#232)."""

import shutil

from conftest import ROOT

URL = "games/vauvan-syotto/v3/"
NAMES = ["valinta", "nams", "litsahdus", "lusikka", "vauva", "royhtays", "pruut", "suhahdus"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


def open_game(site, context):
    shutil.copytree(ROOT / "games" / "vauvan-syotto", site.games / "vauvan-syotto")
    site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(SPY)
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def start(page):
    page.click("#go")
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def test_each_moment_plays_its_recorded_sound(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("mood = 100; bite(false)")
    assert played(page) == ["nams"]
    page.evaluate("mood = 10; videoT = 0; Math.random = () => 0.1; bite(false)")
    assert played(page) == ["pruut"]
    page.evaluate("mood = 100; miss()")
    assert played(page) == ["litsahdus"]
    page.evaluate("give(true, 0)")
    assert played(page) == ["vauva"]
    page.evaluate("power.plane = 1; usePower('plane')")
    assert played(page) == ["suhahdus"]
    page.evaluate("gainPower()")
    assert played(page) == ["valinta", "valinta"]
    # The song and the video keep their own tunes.
    page.evaluate("power.song = 1; power.video = 1; usePower('song'); usePower('video')")
    assert played(page) == []
    page.evaluate("lose()")
    assert played(page) == ["vauva", "vauva"]
    assert page.errors == []


def test_a_level_won_ends_with_a_burp(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("mood = 100; tummy = goal - 1; bite(false)")
    assert played(page) == ["nams", "royhtays"]
    assert page.errors == []


def test_a_dropped_spoon_clatters_on_the_floor(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("give(false, 0); for (let i = 0; i < 300 && spoon.where !== 'floor'; i++) step(0.02)")
    assert page.evaluate("spoon.where") == "floor"
    assert "lusikka" in played(page)
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        page.evaluate("mood = 100; tummy = goal - 1; bite(false); miss(); lose()")
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_the_saves_of_v2_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:vauvan-syotto:taso', '4'); location.reload()")
    page.wait_for_load_state()
    assert page.evaluate("level") == 4

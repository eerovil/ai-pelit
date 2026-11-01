"""Kirkkis v8: recorded sounds from the shared library public/lib/aanet-2/ (#219)."""

import shutil

from conftest import ROOT

URL = "games/kirkkis/v8/"
NAMES = ["valinta", "onnistui", "tappio", "voitto", "ruoho"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


def start(site, browser, silent=False):
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis", dirs_exist_ok=True)
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    if silent:
        ctx.route("**/*.mp3", lambda route: route.abort())
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(SPY)
    page.click("#modes button[data-mode=kirkkis]")
    page.click("#hide")
    return ctx, page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_each_moment_has_its_own_sound(site, browser):
    ctx, page = start(site, browser)
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")
    page.evaluate("""() => { const b = people.indexOf(bots[0]);
      show(['ready']); show(['spot', b]); show(['save', b]); show(['kirk', [b]]); show(['all', b]); }""")
    assert played(page) == ["valinta", "onnistui", "onnistui", "tappio", "voitto"]
    # Someone heard running: steps on grass.
    page.evaluate("sfx.step(); sfx.step()")
    assert played(page) == ["ruoho", "ruoho"]
    assert page.errors == []
    ctx.close()


def test_the_other_games_and_a_second_round_sound_too(site, browser):
    ctx, page = start(site, browser)
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    # Piilosta: found is the seen sound; Hippa: a tag is the named sound.
    page.evaluate("pickMode('piilosta')")
    page.evaluate("newRound('hide'); heard.splice(0); show(['found', people.indexOf(bots[0])])")
    assert played(page) == ["onnistui"]
    page.evaluate("pickMode('hippa')")
    page.evaluate("""() => { newRound('hide'); heard.splice(0);
      show(['tag', people.indexOf(bots[0]), people.indexOf(seeker === bots[0] ? bots[1] : seeker)]); }""")
    assert played(page) == ["tappio"]
    # Back to Kirkkis: a whole round to the end, then the next one; two events at once both sound.
    page.evaluate("pickMode('kirkkis')")
    page.evaluate("""() => { newRound('hide'); let t = 0; while (phase !== 'menu' && t < 260) { step(1 / 30); t += 1 / 30; }
      newRound('seek'); heard.splice(0); const a = people.indexOf(bots[0]), b = people.indexOf(bots[1]);
      show(['save', a]); show(['kirk', [b]]); }""")
    assert played(page) == ["onnistui", "tappio"]
    assert page.errors == []
    ctx.close()


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx, page = start(site, browser, silent=True)
    page.evaluate("""() => { const b = people.indexOf(bots[0]);
      show(['ready']); show(['spot', b]); show(['all', b]); }""")
    assert page.evaluate("heard.length") >= 3 and played(page) == []
    r = page.evaluate("""() => { let t = 0; while (phase !== 'menu' && t < 260) { step(1 / 30); t += 1 / 30; } return phase; }""")
    assert r == "menu"
    assert page.errors == []
    ctx.close()

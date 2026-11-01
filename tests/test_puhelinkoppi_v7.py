"""Puhelinkoppi v6: recorded sounds from the shared library public/lib/aanet-2/ (#226)."""

import shutil

from conftest import ROOT

URL = "games/puhelinkoppi/v7/"
FLY = """(seconds) => { for (let t = 0; t < seconds && (state === 'air' || state === 'drop' || state === 'settle'); t += 1 / 60) step(1 / 60); return state; }"""

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""
SOUNDS = ["suhahdus", "osuma", "tomahdys", "lasi", "voitto", "tappio"]


def open_game(site, browser):
    shutil.copytree(ROOT / "games" / "puhelinkoppi", site.games / "puhelinkoppi")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    # A nickname, so the first catch does not open the scores panel's name question.
    ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    page.evaluate("noise = 0")
    page.evaluate(SPY)
    return ctx, page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_throw_a_catch_a_drop_and_a_wrong_side_each_sound(site, browser):
    ctx, page = open_game(site, browser)
    page.mouse.click(180, 100)  # the first tap turns sound on
    page.wait_for_function(f"{SOUNDS!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('osuma', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")

    page.evaluate("newRound(); launch({ v0: 3 })")
    assert page.evaluate(FLY, 3) == "result"
    assert page.evaluate("result.kind") == "win"
    assert played(page) == ["suhahdus", "osuma", "voitto"]

    page.evaluate("noise = 0; newRound(); launch({ v0: 3, vx: 0.5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "drop"
    assert played(page) == ["suhahdus", "suhahdus", "tomahdys", "lasi"]

    page.evaluate("noise = 0; newRound(); launch({ v0: 3, wx: 5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "down"
    assert played(page) == ["suhahdus", "osuma", "tappio"]
    assert page.errors == []
    ctx.close()


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    shutil.copytree(ROOT / "games" / "puhelinkoppi", site.games / "puhelinkoppi")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    ctx.route("**/*.mp3", lambda route: route.abort())
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    page.evaluate(SPY)
    page.mouse.click(180, 100)
    page.evaluate("noise = 0; newRound(); launch({ v0: 3, vx: 0.5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "drop"
    assert played(page) == []
    assert page.errors == []
    ctx.close()


def test_v5_saves_are_read_as_they_are(site, browser):
    ctx, page = open_game(site, browser)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 4], ['paras', 6], ['kopit', 9], ['haasteet', 2]]) localStorage.setItem('ai-pelit:puhelinkoppi:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    assert page.evaluate("[level, best, catches, challenges]") == [4, 6, 9, 2]
    assert page.errors == []
    ctx.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/puhelinkoppi/v7")

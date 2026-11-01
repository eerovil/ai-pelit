"""Trampoliini v7: recorded sounds from the shared library public/lib/aanet-2/ (#231)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/trampoliini/v7/"
NAMES = ['tomahdys', 'jousi', 'boing', 'nousu', 'onnistui', 'ohhoo', 'voitto', 'tappio']

# Every AiPelitAanet.play() call, with whether it played, in window.heard; every beep in window.beeps.
SPY = """() => {
  window.heard = []; window.beeps = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
  const realBeep = beep;
  beep = (k, v) => { beeps.push(k); realBeep(k, v); };
}"""


@pytest.fixture
def tramp_site(site, tmp_path):
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "trampoliini", games / "trampoliini")
    site.build(games)
    return site


def open_game(browser, site, block_mp3=False):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    if block_mp3:
        ctx.route("**/*.mp3", lambda route: route.abort())
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(SPY)
    return ctx, page, errors


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def ready(page):
    page.click("#go")
    page.wait_for_function(f"{NAMES!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('onnistui', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0); beeps.splice(0)")


def test_each_moment_has_its_recorded_sound(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    ready(page)
    page.evaluate("step = () => {}")   # the round stands still: only the sounds asked here play
    for call, want in [
        ("sound('thump')", ["tomahdys"]),
        ("sound('boing', 4)", ["jousi"]),
        ("sound('boing', 11)", ["boing"]),
        ("sound('spring')", ["nousu"]),
        ("sound('trick')", ["onnistui"]),
        ("sound('task')", ["onnistui"]),
        ("sound('crash')", ["tomahdys", "ohhoo"]),
        ("sound('win')", ["voitto"]),
        ("sound('fail')", ["tappio"]),
    ]:
        page.evaluate(call)
        assert played(page) == want, call
    assert page.evaluate("beeps") == []
    assert errors == []
    ctx.close()


def test_a_push_on_the_mat_sounds_and_the_round_plays(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    ready(page)
    page.evaluate("phase = 'mat'; J.pumpT = null; tap()")
    assert "tomahdys" in played(page)
    page.wait_for_timeout(600)
    assert page.evaluate("phase") in ("mat", "air")
    assert errors == []
    ctx.close()


def test_without_the_sound_files_it_beeps_as_before(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site, block_mp3=True)
    page.click("#go")
    page.wait_for_timeout(300)
    page.evaluate("step = () => {}; sound('thump'); sound('crash'); sound('win')")
    assert played(page) == []
    assert page.evaluate("beeps") == ["thump", "crash", "win"]
    assert errors == []
    ctx.close()


def test_v6_saves_are_read_as_they_are(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 3], ['ennatys', 456]]) localStorage.setItem('ai-pelit:trampoliini:' + k, JSON.stringify(v));
      localStorage.setItem('ai-pelit:_asut:trampoliini', '"noita"');
    }""")
    page.reload()
    assert page.evaluate("[level, best, outfit.id]") == [3, 456, "noita"]
    assert errors == []
    ctx.close()

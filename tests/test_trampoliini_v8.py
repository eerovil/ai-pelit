"""Trampoliini v8: a well-timed push is a soft whoosh, not v7's arcade power-up (#298)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/trampoliini/v8/"
NAMES = ['tomahdys', 'jousi', 'boing', 'suhahdus', 'onnistui', 'ohhoo', 'voitto', 'tappio']

# Every AiPelitAanet.play() call, with its options and whether it played, in window.heard;
# every beep in window.beeps.
SPY = """() => {
  window.heard = []; window.beeps = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok, o || {}]); return ok; };
  const realBeep = beep;
  beep = (k, v) => { beeps.push(k); realBeep(k, v); };
}"""


@pytest.fixture
def tramp_site(site, tmp_path):
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "trampoliini", games / "trampoliini")
    site.build(games)
    return site


def open_game(browser, site):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(SPY)
    page.click("#go")
    page.wait_for_function(f"{NAMES!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('onnistui', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0); beeps.splice(0)")
    return ctx, page, errors


def test_a_well_timed_push_whooshes_softly(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    # A push right at the bottom of the bounce, through the round's own take-off.
    page.evaluate("step = () => {}; phase = 'mat'; J.vin = 6; J.pumpT = CONTACT / 2; takeoff()")
    heard = page.evaluate("heard.splice(0)")
    names = [n for n, ok, _ in heard if ok]
    assert names == ["suhahdus"]
    assert heard[0][2]["vol"] <= 0.4
    assert page.evaluate("beeps") == []
    assert errors == []
    ctx.close()


def test_the_arcade_power_up_is_gone(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    page.evaluate("step = () => {}")
    for k in ["'thump'", "'boing', 4", "'boing', 11", "'spring', 1", "'spring', 0.5", "'trick'", "'task'",
              "'crash'", "'win'", "'fail'"]:
        page.evaluate(f"sound({k})")
    page.wait_for_timeout(100)
    assert "nousu" not in [n for n, _, _ in page.evaluate("heard")]
    assert "nousu" not in (ROOT / "games/trampoliini/v8/index.html").read_text()
    assert errors == []
    ctx.close()


def test_a_poor_push_makes_no_whoosh(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    page.evaluate("step = () => {}; phase = 'mat'; J.vin = 6; J.pumpT = CONTACT / 2 + 0.25; takeoff()")
    assert [n for n, ok, _ in page.evaluate("heard") if ok] == []
    assert errors == []
    ctx.close()


def test_v7_saves_are_read_as_they_are(tramp_site, browser):
    ctx, page, errors = open_game(browser, tramp_site)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 3], ['ennatys', 456]]) localStorage.setItem('ai-pelit:trampoliini:' + k, JSON.stringify(v));
      localStorage.setItem('ai-pelit:_asut:trampoliini', '"noita"');
    }""")
    page.reload()
    assert page.evaluate("[level, best, outfit.id]") == [3, 456, "noita"]
    assert errors == []
    ctx.close()

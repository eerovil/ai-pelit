"""Last Signal v11 (#221): recorded sounds from the shared library public/lib/aanet-2/ instead of the game's own
beeps. Otherwise v11 plays as v10: v10's tests (and through them v9's to v4's) run here on v11 too."""

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v6 as v6
import test_last_signal_v7 as v7
import test_last_signal_v8 as v8
import test_last_signal_v9 as v9
import test_last_signal_v10 as v10
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v11/"


@pytest.fixture(autouse=True)
def _v11(monkeypatch):
    for m in (v4, v5, v6, v7, v8, v9, v10):
        monkeypatch.setattr(m, "URL", URL)


@pytest.fixture(autouse=True)
def _helpers(monkeypatch):
    monkeypatch.setattr(v4, "act", v9.act)
    monkeypatch.setattr(v4, "dive_at", v7.dive_at)


for _name in dir(v10):
    if _name.startswith("test_"):
        globals()[_name + ("" if _name.endswith(("_v9", "_v10")) else "_v10")] = getattr(v10, _name)

# Every AiPelitAanet.play() call, with whether it played, in window.heard; every own beep in window.beeps.
SPY = """() => {
  window.heard = []; window.beeps = 0;
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
  const t = tone;
  tone = (...a) => { beeps++; return t(...a); };
}"""
NAMES = ['syvyys', 'sukellusvene', 'humina', 'tuuli', 'kaiku', 'metalli', 'onnistui', 'nousu', 'valinta', 'virhe',
         'kuplat', 'loiskis', 'osuma', 'narina', 'halytys', 'naksu', 'lumi', 'jaa']


def sounding(site, browser):
    """A new game held still, with every sound it uses loaded and sound on."""
    page = v4.open_game(site, browser)
    v6.ready(page)
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=15000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate(SPY)
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_the_loops_follow_where_the_person_is_and_how_fast_sisu_goes(site, browser):
    page = sounding(site, browser)
    page.evaluate("soundStep(0.01)")
    page.wait_for_function("BED.sea.playing() && BED.engine.playing()", timeout=5000)
    still = page.evaluate("({ sea: BED.sea.vol, engine: BED.engine.vol, rate: BED.engine.rate, wind: BED.wind.vol })")
    assert still["sea"] > 0.3 and still["engine"] > 0 and still["wind"] == 0
    page.evaluate("sub.vx = SUB_SPEED; soundStep(0.01)")
    fast = page.evaluate("({ engine: BED.engine.vol, rate: BED.engine.rate })")
    assert fast["engine"] > still["engine"] and fast["rate"] > still["rate"]
    page.evaluate("sub.vx = 0; sub.y = 30")
    v4.inside(page)
    page.evaluate("soundStep(0.01)")
    assert page.evaluate("BED.hum.vol") > 0.2
    page.evaluate("closeHome()")
    v6.surface(page)
    v6.out_on_the_ice(page)
    page.evaluate("soundStep(0.01)")
    assert page.evaluate("BED.wind.vol") > 0.2 and page.evaluate("BED.sea.vol") == 0
    assert page.errors == []


def test_the_sonar_dives_answers_and_warnings_play_the_library_sounds(site, browser):
    page = sounding(site, browser)
    page.evaluate("G.pingCd = 0; doPing()")
    assert "kaiku" in played(page)
    for k, name in (("eat", "onnistui"), ("up", "nousu"), ("got", "valinta"), ("no", "virhe")):
        page.evaluate(f"snd('{k}')")
        assert played(page) == [name]
    page.evaluate("bump(9)")
    assert played(page) == ["metalli"]
    page.evaluate("G.warnCd = 0; sub.y = RATING[G.s.up.hull] - 10; pressure(0.01)")
    assert played(page) == ["narina"]
    page.evaluate("G.warnCd = 0; sub.y = RATING[G.s.up.hull] + 40; pressure(0.01)")
    assert played(page) == ["halytys"]
    page.evaluate("sub.y = 30")
    v4.dive_at(page, "nordvik")
    got = played(page)
    assert "loiskis" in got and "kuplat" in got, got
    page.evaluate("G.warnCd = 0; diver.air = 5; stepDive(0.01)")
    assert "halytys" in played(page)
    assert page.errors == []


def test_steps_crunch_in_the_snow_on_the_ice(site, browser):
    page = sounding(site, browser)
    v6.surface(page)
    v6.out_on_the_ice(page)
    page.evaluate("heard.splice(0); input.x = 1; run(() => true, 2); input.x = 0")
    assert played(page).count("lumi") >= 2
    assert page.errors == []


def test_without_the_sound_files_it_plays_with_its_own_beeps(site, browser):
    page = v4.open_game(site, browser)
    page.context.route("**/*.mp3", lambda route: route.abort())
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(v4.RUN)
    v6.ready(page)
    page.evaluate(SPY)
    page.evaluate("G.pingCd = 0; doPing(); snd('up'); bump(9)")
    assert played(page) == []
    assert page.evaluate("beeps") >= 3
    page.evaluate("soundStep(0.01)")
    assert page.evaluate("BED.sea.playing()") is False
    assert page.errors == []


def test_after_a_reload_jatka_brings_the_loops_back_and_the_save_is_kept(site, browser):
    page = sounding(site, browser)
    page.evaluate("sub.x += 20; G.s.day = 3; save()")
    day = page.evaluate("G.s.day")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    page.evaluate("G.hold = true; input.x = input.y = 0")
    assert page.evaluate("G.s.day") == day
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("soundStep(0.01)")
    page.wait_for_function("BED.sea.playing() && BED.engine.playing()", timeout=5000)
    assert page.errors == []

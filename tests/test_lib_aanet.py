"""The shared sound effects in public/lib/aanet-1/ and aanet-2/ (#205), on a test-only game."""

import re
from pathlib import Path

import pytest

from conftest import ROOT, game_page, make_game, wait_for_worker

LIB = ROOT / "public" / "lib" / "aanet-1"
TAG = '<script src="../../../lib/aanet-1/aanet.js"></script>'
TAG2 = TAG.replace("aanet-1", "aanet-2")


def sounds(lib=LIB):
    """The name -> file list at the top of aanet.js."""
    text = (lib / "aanet.js").read_text()
    return dict(re.findall(r"^\s+(\w+): '([\w-]+\.mp3)',", text, re.M))


@pytest.mark.parametrize("folder", ["aanet-1", "aanet-2"])
def test_every_sound_is_there_small_and_its_source_named(folder):
    lib = LIB.parent / folder
    listed = sounds(lib)
    assert len(listed) >= 20
    source = (lib / "SOURCE").read_text()
    assert "CC0" in (lib / "LICENSE").read_text()
    for name, file in listed.items():
        path = lib / file
        assert path.is_file(), file
        assert path.stat().st_size < 60_000, file
        assert re.search(rf"^{re.escape(file)}\s", source, re.M), f"{file} is not in SOURCE"
    # No file is left out of the list either.
    assert {p.name for p in lib.glob("*.mp3")} == set(listed.values())


def test_aanet_2_keeps_every_sound_of_aanet_1_as_it_is():
    one, two = sounds(LIB), sounds(LIB.parent / "aanet-2")
    for name, file in one.items():
        assert two[name] == file
        assert (LIB / file).read_bytes() == (LIB.parent / "aanet-2" / file).read_bytes()


def open_demo(site, context, names, tag=TAG):
    make_game(site.games, "aanidemo", [game_page("Äänet", tag, f"AiPelitAanet.load({names!r});")])
    site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/aanidemo/v1/")
    return page


def test_sounds_play_only_after_a_tap_and_never_throw(site, context):
    page = open_demo(site, context, ["askel", "aplodit"])
    page.wait_for_function("AiPelitAanet.ready('askel') && AiPelitAanet.ready('aplodit')", timeout=10000)
    # Before any tap the browser keeps sound off: nothing plays, nothing breaks.
    assert page.evaluate("AiPelitAanet.play('askel')") is False
    page.mouse.click(180, 400)
    page.wait_for_function("AiPelitAanet.play('askel') === true", timeout=5000)
    assert page.evaluate("AiPelitAanet.play('aplodit', { vol: 0.5, rate: 1.2, delay: 0.1 })") is True
    # A sound the game did not load, or one that does not exist, is silent.
    assert page.evaluate("AiPelitAanet.play('hiekka')") is False
    assert page.evaluate("AiPelitAanet.play('ei-ole')") is False
    assert page.evaluate("AiPelitAanet.muted = true; AiPelitAanet.play('askel')") is False
    assert page.errors == []


def test_a_game_downloads_only_the_sounds_it_names_and_plays_them_offline(site, context):
    asked = []
    context.on("request", lambda r: asked.append(r.url) if r.url.endswith(".mp3") else None)
    page = open_demo(site, context, ["hiekka"])
    page.wait_for_function("AiPelitAanet.ready('hiekka')", timeout=10000)
    # The page asks, and the service worker asks the network once for its cache.
    assert {Path(u).name for u in asked} == {"hiekka.mp3"}
    context.set_offline(True)
    try:
        page.goto(f"{site.url}games/aanidemo/v1/")
        page.wait_for_function("AiPelitAanet.ready('hiekka')", timeout=10000)
        page.mouse.click(180, 400)
        page.wait_for_function("AiPelitAanet.play('hiekka') === true", timeout=5000)
    finally:
        context.set_offline(False)
    assert page.errors == []


def test_a_missing_file_is_silent(site, browser):
    # Without the service worker, so that the blocked download is not answered from its cache.
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        make_game(site.games, "aanidemo", [game_page("Äänet", TAG, "AiPelitAanet.load(['askel']);")])
        site.build()
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("**/*.mp3", lambda route: route.abort())
        page.goto(f"{site.url}games/aanidemo/v1/")
        page.mouse.click(180, 400)
        page.wait_for_timeout(300)
        assert page.evaluate("AiPelitAanet.play('askel')") is False
        assert errors == []
    finally:
        ctx.close()


def test_a_loop_waits_for_its_sound_follows_set_and_stops(site, context):
    page = open_demo(site, context, ["moottori", "pilli"], TAG2)
    page.evaluate("window.engine = AiPelitAanet.loop('moottori', { vol: 0.2 }); window.none = AiPelitAanet.loop('ei-ole')")
    # Before a tap it waits, and set() is kept for when it starts.
    assert page.evaluate("engine.playing()") is False
    page.evaluate("engine.set({ rate: 1.5, vol: 0.4 })")
    page.wait_for_function("AiPelitAanet.ready('moottori')", timeout=10000)
    page.mouse.click(180, 400)
    page.wait_for_function("engine.playing()", timeout=5000)
    assert page.evaluate("[engine.rate, engine.vol]") == [1.5, 0.4]
    assert page.evaluate("AiPelitAanet.play('pilli')") is True
    page.evaluate("engine.set({ rate: 0.7 }); engine.stop(); engine.set({ vol: 1 })")
    assert page.evaluate("engine.playing()") is False
    assert page.evaluate("none.set({ rate: 2 }).playing()") is False
    assert page.errors == []


def test_two_loops_at_once_and_sound_sleeps_while_the_page_is_hidden(site, context):
    page = open_demo(site, context, ["tuuli", "sade"], TAG2)
    page.wait_for_function("AiPelitAanet.ready('tuuli') && AiPelitAanet.ready('sade')", timeout=10000)
    page.mouse.click(180, 400)
    page.evaluate("window.a = AiPelitAanet.loop('tuuli'); window.b = AiPelitAanet.loop('sade', { vol: 0.3 })")
    page.wait_for_function("a.playing() && b.playing()", timeout=5000)
    # Stopping one leaves the other.
    page.evaluate("a.stop()")
    assert page.evaluate("[a.playing(), b.playing()]") == [False, True]
    # The page hidden (the phone locked, another app): the sound context sleeps, and wakes again.
    states = page.evaluate("""async () => {
      const wait = () => new Promise(r => setTimeout(r, 200));
      const hide = h => { Object.defineProperty(document, 'hidden', { value: h, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); };
      const seen = [];
      const probe = AiPelitAanet.loop('sade', { vol: 0 });
      hide(true); await wait(); seen.push(AiPelitAanet.play('sade', { vol: 0 }));
      hide(false); await wait(); seen.push(AiPelitAanet.play('sade', { vol: 0 }));
      probe.stop();
      return seen;
    }""")
    assert states == [False, True]
    assert page.errors == []

"""The shared sound effects in public/lib/aanet-1/ (#205), on a test-only game."""

import re
from pathlib import Path

from conftest import ROOT, game_page, make_game, wait_for_worker

LIB = ROOT / "public" / "lib" / "aanet-1"
TAG = '<script src="../../../lib/aanet-1/aanet.js"></script>'


def sounds():
    """The name -> file list at the top of aanet.js."""
    text = (LIB / "aanet.js").read_text()
    return dict(re.findall(r"^\s+(\w+): '([\w-]+\.mp3)',", text, re.M))


def test_every_sound_is_there_small_and_its_source_named():
    listed = sounds()
    assert len(listed) >= 20
    source = (LIB / "SOURCE").read_text()
    assert "CC0" in (LIB / "LICENSE").read_text()
    for name, file in listed.items():
        path = LIB / file
        assert path.is_file(), file
        assert path.stat().st_size < 60_000, file
        assert re.search(rf"^{re.escape(file)}\s", source, re.M), f"{file} is not in SOURCE"
    # No file is left out of the list either.
    assert {p.name for p in LIB.glob("*.mp3")} == set(listed.values())


def open_demo(site, context, names):
    make_game(site.games, "aanidemo", [game_page("Äänet", TAG, f"AiPelitAanet.load({names!r});")])
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

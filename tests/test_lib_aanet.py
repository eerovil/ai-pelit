"""The shared sound effects in public/lib/aanet-1/, aanet-2/ (#205), aanet-3/ (#330) and aanet-4/ (#337), on a test-only game."""

import re
from pathlib import Path

import pytest

from conftest import ROOT, game_page, make_game, wait_for_worker

LIB = ROOT / "public" / "lib" / "aanet-1"
TAG = '<script src="../../../lib/aanet-1/aanet.js"></script>'
TAG2 = TAG.replace("aanet-1", "aanet-2")
TAG4 = TAG.replace("aanet-1", "aanet-4")
CROWD = {"aplodit", "yleiso", "ohhoo", "jee"}


def sounds(lib=LIB):
    """The name -> file list at the top of aanet.js."""
    text = (lib / "aanet.js").read_text()
    return dict(re.findall(r"^\s+(\w+): '([\w-]+\.mp3)',", text, re.M))


@pytest.mark.parametrize("folder", ["aanet-1", "aanet-2", "aanet-3", "aanet-4"])
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


@pytest.mark.parametrize("old,new", [("aanet-1", "aanet-2"), ("aanet-2", "aanet-3")])
def test_each_folder_keeps_every_sound_of_the_one_before_as_it_is(old, new):
    a, b = LIB.parent / old, LIB.parent / new
    one, two = sounds(a), sounds(b)
    for name, file in one.items():
        assert two[name] == file
        assert (a / file).read_bytes() == (b / file).read_bytes()
    # The code beside the sounds is the same too, but for its comments and the list.
    if new == "aanet-3":
        code = lambda p: [l for l in (p / "aanet.js").read_text().splitlines() if not l.strip().startswith("//") and "mp3'" not in l]
        assert code(a) == code(b)


def test_aanet_4_is_aanet_3_without_the_crowd_sounds():
    a, b = LIB.parent / "aanet-3", LIB.parent / "aanet-4"
    three, four = sounds(a), sounds(b)
    assert set(three) - set(four) == CROWD
    assert set(four) <= set(three)
    for name, file in four.items():
        assert three[name] == file
        assert (a / file).read_bytes() == (b / file).read_bytes()
    assert not any(re.match(rf"{c}\.mp3", line) for c in CROWD for line in (b / "SOURCE").read_text().splitlines())


def newest_versions():
    for game in sorted((ROOT / "games").iterdir()):
        versions = [d for d in game.glob("v*") if d.name[1:].isdigit()]
        if versions:
            yield max(versions, key=lambda d: int(d.name[1:]))


def test_no_game_plays_a_crowd_or_loads_an_older_library_for_one():
    # #337 (Eero's choice): no applause, shouting crowd, crowd's "ooh" or cheer in any game's newest
    # version, and a field event's "📣 Kannusta" is its own quiet sound, not kisa.js's "jee!".
    for v in newest_versions():
        code = "\n".join(p.read_text() for p in v.rglob("*") if p.suffix in (".html", ".js"))
        found = set(re.findall(r"'(\w+)'", code)) & CROWD
        assert not found, f"{v.relative_to(ROOT)} plays {sorted(found)}"
        if "lib/yleisurheilu-" in code and "AiPelitKisa.meet(" in code:
            assert "cheerSound:" in code, f"{v.relative_to(ROOT)} cheers with kisa.js's own sound"


def test_a_version_on_aanet_4_loads_every_sound_it_plays_by_name():
    # A sound the game did not load never plays (#337: the quiet blip that took the crowd's place
    # was first left out of some games' lists).
    for v in newest_versions():
        code = "\n".join(p.read_text() for p in v.rglob("*") if p.suffix in (".html", ".js"))
        lists = re.findall(r"\.load\(\[([^\]]*)\]", code)
        if "lib/aanet-4/" not in code or not any("'" in l for l in lists):
            continue
        loaded = {n for l in lists for n in re.findall(r"'(\w+)'", l)}
        played = set(re.findall(r"\b(?:play|snd)\('(\w+)'", code)) & set(sounds(LIB.parent / "aanet-4"))
        assert played <= loaded, f"{v.relative_to(ROOT)} plays {sorted(played - loaded)} without loading it"


def test_a_version_on_aanet_4_plays_its_success_blip_quietly():
    # #337: a good moment is a quiet short blip, about 0.3, wherever the game plays it.
    for v in newest_versions():
        code = "\n".join(p.read_text() for p in v.rglob("*") if p.suffix in (".html", ".js"))
        if "lib/aanet-4/" not in code:
            continue
        levels = re.findall(r"'onnistui', \{[^}]*?\bvol: (\d+(?:\.\d+)?)", code)
        levels += re.findall(r"'onnistui', (\d+(?:\.\d+)?)\b", code)
        loud = [float(x) for x in levels if float(x) > 0.3]
        assert not loud, f"{v.relative_to(ROOT)} plays onnistui at {loud}"
        # A play of it with no volume given would be at full volume.
        assert not re.search(r"'onnistui'\)", code), f"{v.relative_to(ROOT)} plays onnistui at full volume"


def test_aanet_4_plays_the_loudest_sounds_quieter(site, context):
    page = open_demo(site, context, ["pilli", "tappio", "askel"], TAG4)
    assert page.evaluate("AiPelitAanet.level('pilli', 0.8)") == pytest.approx(0.28)
    assert page.evaluate("AiPelitAanet.level('pilli')") == pytest.approx(0.35)
    # The losing tune and the ordinary sounds play as loud as the game asks.
    assert page.evaluate("[AiPelitAanet.level('tappio', 0.8), AiPelitAanet.level('askel')]") == [0.8, 1]
    assert not CROWD & set(page.evaluate("AiPelitAanet.names()"))
    page.wait_for_function("AiPelitAanet.ready('pilli')", timeout=10000)
    page.mouse.click(180, 400)
    page.wait_for_function("AiPelitAanet.play('pilli', { vol: 0.8 }) === true", timeout=5000)
    page.evaluate("window.w = AiPelitAanet.loop('pilli', { vol: 0.6 })")
    page.wait_for_function("w.playing() && Math.abs(w.gain.gain.value - 0.21) < 0.01", timeout=3000)
    assert page.errors == []


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


def test_muting_silences_running_loops_and_unmuting_starts_the_waiting_ones(site, context):
    page = open_demo(site, context, ["tuuli", "sade"], TAG2)
    page.wait_for_function("AiPelitAanet.ready('tuuli') && AiPelitAanet.ready('sade')", timeout=10000)
    page.mouse.click(180, 400)
    page.evaluate("window.wind = AiPelitAanet.loop('tuuli', { vol: 0.6 })")
    page.wait_for_function("wind.playing()", timeout=5000)
    # Muted, a loop the game never set()s again goes quiet anyway; one made now waits.
    page.evaluate("AiPelitAanet.muted = true; window.rain = AiPelitAanet.loop('sade', { vol: 0.4 })")
    page.wait_for_function("wind.gain.gain.value < 0.01", timeout=3000)
    assert page.evaluate("rain.playing()") is False
    assert page.evaluate("AiPelitAanet.play('tuuli')") is False
    page.evaluate("AiPelitAanet.muted = false")
    page.wait_for_function("rain.playing() && wind.gain.gain.value > 0.55 && rain.gain.gain.value > 0.35", timeout=3000)
    assert page.evaluate("AiPelitAanet.muted") is False
    assert page.errors == []

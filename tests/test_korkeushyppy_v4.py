"""Korkeushyppy v4: recorded sounds from the shared library public/lib/aanet-2/ (#220)."""

import json

from conftest import ROOT

import test_korkeushyppy_v2 as v2
import test_korkeushyppy_v3 as v3

URL = "games/korkeushyppy/v4/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

ALL = ["valinta", "askel", "askel2", "ponnistus", "suhahdus", "rima", "onnistui", "aplodit", "ohhoo", "tomahdys", "mitali"]


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(v2.SEEDED % 1)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    for k, v in (saved or {}).items():
        page.add_init_script(f"localStorage.setItem('ai-pelit:korkeushyppy:{k}', {json.dumps(json.dumps(v))})")
    page.goto(site.url + URL)
    page.evaluate(v2.HELPERS)
    page.evaluate(SPY)
    return page


def start(page):
    """Start a meet with sound on and every file decoded, at this phone's first run-up."""
    page.click("#go")
    page.wait_for_function(f"{json.dumps(ALL)}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_clear_sounds_from_the_turn_to_the_mat(site, context):
    # A record far above, so the clear is not one: the crowd does not clap.
    page = open_game(site, context, {"ennatys": 2.9})
    start(page)
    page.evaluate("th.t = 99; step(0.001)")
    assert played(page) == ["valinta"]
    page.evaluate("press(1); press(2)")
    assert played(page) == ["askel", "askel2"]
    page.evaluate("go(1.05, 8, 0.3, 0.46)")
    assert played(page) == ["ponnistus", "suhahdus", "suhahdus", "suhahdus"]
    page.evaluate("quick()")
    assert played(page) == ["tomahdys", "onnistui"]
    assert page.errors == []


def test_a_record_gets_applause(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("go(1.05, 8, 0.3, 0.46); heard.splice(0); quick()")
    assert played(page) == ["tomahdys", "aplodit"]
    assert page.errors == []


def test_a_knocked_bar_clatters_and_the_crowd_goes_ooh(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("go(1.05, 8, null, null); heard.splice(0); quick()")
    assert played(page) == ["rima", "tomahdys", "ohhoo"]
    assert page.errors == []


def test_running_past_the_bar_goes_ooh(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("ready(); th.phase = 'run'; th.v = 6; th.x = RUN_PAST - 0.01; heard.splice(0); step(1 / 60)")
    assert played(page) == ["ohhoo"]
    assert page.errors == []


def test_the_medals_ring_on_the_podium(site, context):
    page = open_game(site, context)
    v3.win_meet(page)
    page.wait_for_function(f"{json.dumps(ALL)}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("K.ending.t = 0; heard.splice(0); for (let i = 0; i < 60 * 15; i++) step(1 / 60)")
    got = played(page)
    assert got.count("mitali") == 3 and "aplodit" in got, got
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx, {"ennatys": 2.9})
        # Every beep the game asks for, by its first frequency, in window.beeps.
        page.evaluate("""() => {
          window.beeps = [];
          const real = window.tone;
          window.tone = (f, ...rest) => { beeps.push(f); return real(f, ...rest); };
        }""")
        beeps = lambda: page.evaluate("beeps.splice(0)")
        page.click("#go")
        page.evaluate("th.t = 99; step(0.001)")
        assert beeps() == [660]                      # the turn
        page.evaluate("press(1); press(2)")
        assert beeps() == [190, 230]                 # the run-up's steps
        page.evaluate("go(1.05, 8, 0.3, 0.46)")
        assert beeps() == [300, 520, 700]            # take-off, arch, legs
        page.evaluate("quick()")
        assert beeps() == [880]                      # a clear (its second note follows by timer)
        for _ in range(80):  # v3.win_meet without its click: this meet is already on
            if page.evaluate("K.comp.over"):
                break
            page.evaluate("ready(); if (soleWinner(mine()) && bestOf(mine()) >= 1.95) { stopMeet(); quick(); } else good()")
        assert page.evaluate("K.comp.over && K.ending.place === 1")
        page.evaluate("beeps.splice(0); for (let i = 0; i < 60 * 15; i++) step(1 / 60)")
        assert sorted(set(beeps())) == [523, 659, 784]   # a chime per medal
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_without_the_sound_files_a_knocked_bar_and_running_past_still_beep(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.evaluate("""() => {
          window.beeps = [];
          const real = window.tone;
          window.tone = (f, ...rest) => { beeps.push(f); return real(f, ...rest); };
        }""")
        page.click("#go")
        page.evaluate("go(1.05, 8, null, null); beeps.splice(0); quick()")
        assert page.evaluate("beeps.splice(0)") == [150]   # the bar falls
        page.evaluate("for (let i = 0; i < 600 && !(th && th.mine && th.phase === 'wait'); i++) step(1 / 60)")
        page.evaluate("ready(); th.phase = 'run'; th.v = 6; th.x = RUN_PAST - 0.01; beeps.splice(0); step(1 / 60)")
        assert page.evaluate("beeps.splice(0)") == [160]   # running past
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v3_saves_are_read_as_they_are(site, context):
    page = open_game(site, context, {"kisat": 5, "voitot": 3, "ennatys": 2.04})
    assert page.inner_text("#stats") == "Kisat 5 · Voitot 3 · Ennätys 2,04 m"
    assert page.errors == []


def test_the_podium_still_stays_until_a_tap(site, context):
    old = v3.URL
    v3.URL = URL
    try:
        v3.test_the_medals_are_hung_and_the_podium_stays_until_a_tap(site, context)
    finally:
        v3.URL = old


def test_in_a_room_the_watching_phone_hears_the_bar_and_the_mat_and_after_a_reload_too(site, browser):
    old = v2.URL
    v2.URL = URL
    try:
        relay, pages = v2.room(site, browser, ["Eero", "Aino"])
    finally:
        v2.URL = old
    try:
        first = v2.jumper_page(pages)
        other = next(p for p in pages if p is not first)
        # Sound sleeps on a hidden page, and only one page of the browser is shown: the watcher.
        other.bring_to_front()
        other.evaluate(SPY)
        other.mouse.click(180, 150)  # a tap on the sky turns sound on and does nothing else
        other.wait_for_function(f"{json.dumps(ALL)}.every(AiPelitAanet.ready)", timeout=10000)
        other.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
        first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
        other.evaluate("heard.splice(0)")
        first.evaluate("go(1.05, 8, null, null); quick()")
        other.wait_for_function("heard.some(h => h[0] === 'tomahdys')", timeout=5000)
        # The jumper's crowd (ohhoo) is its own phone's; every phone hears the bar and the mat.
        assert played(other) == ["rima", "tomahdys"]
        # A watcher that lands its own copy before the jumper's 'done' arrives thuds once
        # (counted by the calls, as this watcher may be a phone without sound on).
        jumper = v2.jumper_page(pages)
        watcher = next(p for p in pages if p is not jumper)
        watcher.evaluate("if (!window.heard) (" + SPY + ")(); heard.splice(0)")
        jumper.wait_for_function("th && th.mine && th.phase === 'ready'", timeout=8000)
        jumper.evaluate("go(1.05, 8, 0.3, 0.46)")
        watcher.wait_for_function("th && th.f && th.phase === 'air'", timeout=5000)
        watcher.evaluate("th.f.acc = 99; step(0.001)")
        assert watcher.evaluate("th.phase") == "land"
        seq = jumper.evaluate("K.comp.seq")
        jumper.evaluate("quick()")
        watcher.wait_for_function(f"K.comp.seq > {seq}", timeout=5000)
        assert [n for n, _ in watcher.evaluate("heard.splice(0)")].count("tomahdys") == 1
        # A guest reloads mid-meet: after its next tap the sounds play again.
        guest = pages[1]
        guest.bring_to_front()
        guest.reload()
        guest.evaluate(v2.HELPERS)
        guest.wait_for_function("K.comp", timeout=10000)
        guest.mouse.click(180, 150)
        guest.wait_for_function("['rima', 'tomahdys'].every(AiPelitAanet.ready)", timeout=10000)
        guest.wait_for_function("AiPelitAanet.play('tomahdys', { vol: 0 })", timeout=5000)
        assert all(p.errors == [] for p in pages)
    finally:
        for p in pages:
            p.context.close()

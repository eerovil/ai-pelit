"""Tikanheitto v4: recorded sounds from the shared library public/lib/aanet-2/ (#230)."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/tikka/v6/"
NAMES = "['onnistui', 'suhahdus', 'puu', 'virhe', 'voitto']"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


# Steps the game by hand, 1/60 s at a time, until cond() is false or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"


def open_plain(site, context, saved=None):
    """The game with its saves set and run() defined, without the sound spy."""
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    for k, v in (saved or {}).items():
        page.evaluate(f"localStorage.setItem('ai-pelit:tikka:{k}', '{v}')")
    if saved:
        page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def open_game(site, context, saved=None):
    page = open_plain(site, context, saved)
    page.evaluate(SPY)
    return page


def sound_on(page):
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('puu', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def throw(page, mx, my):
    page.evaluate(f"throwAt({mx}, {my}); run(() => flying !== null, 2)")


# ---- With friends ----

def room(site, browser, names):
    """The first phone makes a room, the others join it, and the game starts."""
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        pages.append(page)
    host = pages[0]
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for guest in pages[1:]:
        guest.click("#multi")
        guest.fill("#aipr-codeIn", code)
        guest.click("#aipr-joinBtn")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
    return relay, pages


def start(pages):
    pages[0].click("#aipr-start")
    for p in pages:
        p.wait_for_function("phase === 'play' && players.length > 1", timeout=8000)


def throw_turn(page, mx, my, host):
    """The phone whose turn it is throws its three darts at (mx, my) mm, waiting for each to land."""
    page.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    for k in range(3):
        page.evaluate(f"release({mx}, {my})")
        host.wait_for_function(f"dartsLeft === {2 - k} && !flying", timeout=5000)


def test_a_throw_whooshes_and_hits_wood_and_a_full_turn_gets_a_blip(site, context):
    page = open_game(site, context)
    page.click("#go")
    sound_on(page)
    throw(page, 0, 0)
    assert played(page) == ["suhahdus", "puu"]
    throw(page, 0, 0)
    throw(page, 0, 0)   # 30, the most there is: a quiet blip (#337: no crowd)
    assert played(page) == ["suhahdus", "puu", "suhahdus", "puu", "onnistui"]
    # Off the board: the same wood, only quieter.
    page.evaluate("run(() => pause > 0, 3)")
    throw(page, 0, 300)
    assert page.evaluate("heard.filter(h => h[1]).map(h => h[0])") == ["suhahdus", "puu"]
    assert page.evaluate("players[0].score") == 30
    assert page.errors == []


def test_501_bust_buzzes_and_the_win_plays_its_tune(site, context):
    page = open_game(site, context, {"vastus": "kova"})
    page.click("#go501")
    sound_on(page)
    page.evaluate("players[0].score = turnStart = 70")
    throw(page, 0, -135)   # 20, 50 left
    throw(page, 0, -103)   # T20 would go under nought
    assert played(page) == ["suhahdus", "puu", "suhahdus", "puu", "virhe"]
    # Exactly nought wins: the tune.
    page = open_game(site, context)
    page.click("#go501")
    sound_on(page)
    page.evaluate("players[0].score = turnStart = 32")
    throw(page, *page.evaluate("[spotOf(16, 2).x, spotOf(16, 2).y]"))   # D16
    assert played(page)[-1] == "voitto"
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        for _ in range(3):
            throw(page, 0, 0)
        assert page.evaluate("players[0].score") == 30
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_without_the_sound_script_it_still_starts_and_plays(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/aanet.js", lambda route: route.abort())
        page = open_plain(site, ctx)
        assert page.evaluate("typeof AiPelitAanet") == "undefined"
        page.click("#go")
        for _ in range(3):
            throw(page, 0, 0)
        assert page.evaluate("players[0].score") == 30
        assert page.errors == []
    finally:
        ctx.close()


def test_v3_saves_are_read_as_they_are(site, context):
    page = open_game(site, context, {"mokki": 231, "ennatys": 412, "voitot": 3, "vapaa": "darts"})
    assert page.inner_text("#stats") == "Ennätykset: Mökkitikka 231 p · Pistekisa 412 p · Voittoja tietokoneesta 3"
    page.click("#frees button[data-b=darts]")
    assert page.evaluate("freeBoard") == "darts"
    assert page.errors == []


def test_a_friends_phone_in_a_room_hears_the_hits_the_misses_and_the_blip(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    start(pages)
    for p in pages:
        p.evaluate(SPY.replace("heard.push([name, ok])", "heard.push([name, ok, (o || {}).vol])"))
        p.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
        p.wait_for_function("AiPelitAanet.play('puu', { vol: 0 })", timeout=5000)
        p.evaluate("heard.splice(0)")
    # The host throws three tens: Aino's phone hears each dart and then the blip for the 30.
    # Each dart lands on Aino's phone before the next one goes: a dart thrown while the one before
    # is still flying there skips that one's hit (seen in CI once every test of the game ran, #346).
    host.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    for k in range(3):
        host.evaluate("release(0, 0)")
        host.wait_for_function(f"dartsLeft === {2 - k} && !flying", timeout=5000)
        aino.wait_for_function(f"heard.filter(h => h[0] === 'puu').length === {k + 1} && !flying", timeout=5000)
    aino.wait_for_function("cur === 1 && mine() && heard.some(h => h[0] === 'onnistui')", timeout=8000)
    got = [(n, v) for n, ok, v in aino.evaluate("heard.splice(0)") if ok]
    assert [n for n, _ in got].count("puu") == 3 and ("onnistui", 0.3) in got, got
    assert all(v == 1 or v is None for n, v in got if n == "puu"), got
    # Aino misses the board: her own phone plays the quiet knock, not the hit.
    aino.wait_for_function("!banner && !flying && dartsLeft === 3", timeout=8000)
    aino.evaluate("release(0, 300)")
    aino.wait_for_function("heard.some(h => h[0] === 'puu')", timeout=5000)
    assert [(n, v) for n, ok, v in aino.evaluate("heard.splice(0)") if ok and n == "puu"] == [("puu", 0.25)]
    for p in pages:
        assert p.errors == []
        p.context.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/tikka/v6")

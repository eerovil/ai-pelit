"""Ottelu v7: a "👕 Asu" button on the menu; the outfit picked is worn in every event (#311).

The athletics events and Ottelu share one outfit choice (outfits.js data-share="yleisurheilu"),
so each event of the match, loaded in its frame, wears what was picked here.

Ottelu plays each event's newest version by itself (from v6, #303), so these tests also run when
any event's game changes (the marker below): a new event version that does not play in the match
fails its own pull request.
"""

import json

import pytest
from conftest import ROOT, turn

EVENTS = ["aitajuoksu", "pituushyppy", "kuula", "korkeushyppy", "seivashyppy", "keihas", "moukari"]
pytestmark = pytest.mark.games("ottelu", *EVENTS)

URL = "games/ottelu/v7/"
SHARED = "ai-pelit:_asut:yleisurheilu"

# play() takes this phone's turn in the event in its frame, once per turn: a set mark in the
# throws and the long jump, and over the bar up to a height (then misses) in the jumps over a bar.
# Alone it also skips the event's results, and leaves the match's ceremony (to its end, then the
# tap that goes on) unless window.leavePodium is false. run() is the computer's taps and jumps for
# this phone's runner in the hurdles.
HELPERS = """() => {
  const MARK = { pituushyppy: 6.5, keihas: 60, moukari: 55, kuula: 15 }, UPTO = { korkeushyppy: 1.8, seivashyppy: 4.2 };
  window.play = () => {
    if (window.leavePodium !== false && typeof cer !== 'undefined' && cer && cer.K.ending) {
      const tap = () => document.getElementById('pallit').dispatchEvent(new Event('pointerdown'));
      tap(); tap();
      return 'podium';
    }
    if (M && M.events[M.at] === 'aitajuoksu') return run();
    const K = Ottelu.K;
    if (!K || !K.comp || !M) return 'none';
    if (K.ending) { K.skip(); return 'end'; }
    const t = K.current(), me = M.mode === 'net' ? AiPelitRooms.me : 'me';
    if (!t || t.p !== me || window.done === K.comp.room + ':' + K.comp.seq) return 'wait';
    window.done = K.comp.room + ':' + K.comp.seq;
    const slug = M.events[M.at];
    K.report(K.comp.seq, slug in MARK ? MARK[slug] : K.comp.heights[K.comp.hi] <= UPTO[slug] + 1e-9 ? 'O' : 'X');
    return 'me';
  };
  window.run = () => {
    const f = document.getElementById('laji'), w = f && f.contentWindow;
    if (!w || !frameReady) return 'none';
    return w.eval("(() => { if (!race || !me) return 'none'; me.rate = 8.5; think(me, 0.05); return race.phase; })()");
  };
}"""


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.add_init_script("addEventListener('DOMContentLoaded', () => { if (window.top === window) (" + HELPERS + ")(); })")
    page.goto(site.url + URL)
    if saved:
        for k, v in saved.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:ottelu:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    return page


def in_frame(page, js):
    return page.evaluate("(js) => document.getElementById('laji').contentWindow.eval(js)", js)


def finish_event(page, timeout=60000):
    for _ in range(timeout // 20):
        page.evaluate("play()")
        if page.evaluate("frameAt === -1 && !document.getElementById('board').classList.contains('hidden')"):
            return
        page.wait_for_timeout(20)
    raise AssertionError("the event did not end")


def play_event(pages, timeout=60000):
    """Every phone plays its turns until the event's results are done and the board shows."""
    host = pages[0]
    at = host.evaluate("M.at")
    for _ in range(timeout // 50):
        for p in pages:
            p.evaluate("play()")
        if all(p.evaluate(f"!document.getElementById('board').classList.contains('hidden') && frameAt === -1 && M && M.at === {at}") for p in pages):
            return
        host.wait_for_timeout(50)
    raise AssertionError("the event did not end")


def podium_up(page):
    return page.evaluate("!document.getElementById('pallit').classList.contains('hidden') && !!cer")


def play_to_podium(pages):
    for p in pages:
        p.evaluate("window.leavePodium = false")
    for _ in range(1500):
        for p in pages:
            p.evaluate("play()")
        if all(podium_up(p) for p in pages):
            return
        pages[0].wait_for_timeout(20)
    raise AssertionError("no ceremony at the end of the match")


def newest(slug):
    return max(v["n"] for v in json.loads((ROOT / "games" / slug / "game.json").read_text())["versions"] if v.get("ottelu") is not False)


def ready(page):
    """Waits until the match has read the catalog."""
    page.evaluate("newest.then(() => true)")


def test_every_event_plays_its_newest_version(site, context):
    page = open_game(site, context, saved={"lajit": EVENTS})
    ready(page)
    assert page.evaluate("NEWEST") == {s: newest(s) for s in EVENTS}
    page.click("#go")
    page.wait_for_function("frameReady && frameAt === 0", timeout=10000)
    assert page.evaluate("M.v") == {s: newest(s) for s in EVENTS}
    assert in_frame(page, "document.baseURI").endswith(f"/games/aitajuoksu/v{newest('aitajuoksu')}/")
    assert page.errors == []


def test_a_match_alone_with_the_hurdles_and_the_shot_put(site, context):
    page = open_game(site, context, saved={"lajit": ["aitajuoksu", "kuula"]})
    page.evaluate("localStorage.setItem('ai-pelit:aitajuoksu:taso', '4')")
    page.click("#go")
    # The race: the match's eight athletes, 100 m with ten hurdles, the race's menu out of sight.
    page.wait_for_function("frameReady && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    race = in_frame(page, "({ n: race.runners.length, d: race.dist, h: HURDLES.length, ids: race.runners.map(r => r.mid).join(), me: me.name })")
    assert race == {"n": 8, "d": 100, "h": 10, "ids": "h0,c0,c1,c2,c3,c4,c5,c6", "me": "Sinä"}
    assert in_frame(page, "getComputedStyle(document.getElementById('menu')).display") == "none"
    finish_event(page)
    assert page.inner_text("#bTitle") == "100 m aidat · laji 1/2"
    me = page.evaluate("M.rows.find(r => r.p === 'me')")
    assert 10 < me["marks"][0] < 20 and me["pts"][0] == page.evaluate(f"LAJIT.aitajuoksu.pts({me['marks'][0]})")
    assert " s" in page.inner_text("#rows") and len(page.evaluate("M.rows")) == 8
    with page.expect_navigation():
        page.click("#next")
    # The shot put: the same eight, by the same ids.
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    assert page.evaluate("Ottelu.K.comp.throwers.map(t => t.id + t.name).sort().join()") \
        == page.evaluate("M.rows.map(r => r.id + r.name).sort().join()")
    finish_event(page)
    me = page.evaluate("M.rows.find(r => r.p === 'me')")
    assert me["marks"][1] == 15 and me["pts"][1] == 790
    assert page.inner_text("#bTitle") == "Lopputulokset"
    # Aitajuoksu's own saves are left alone.
    assert page.evaluate("Object.keys(localStorage).filter(k => /^ai-pelit:(aitajuoksu|kuula):/.test(k))") == ["ai-pelit:aitajuoksu:taso"]
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (390, 844), (740, 360)])
def test_the_menu_and_the_board_fit(site, context, size):
    page = open_game(site, context, saved={"lajit": ["keihas", "moukari"]})
    turn(page, {"width": size[0], "height": size[1]})
    fits = """() => [...document.querySelectorAll('#%s button:not(.hidden), #%s h1, #%s h2, #%s table')]
      .filter(e => e.offsetParent).every(e => { const r = e.getBoundingClientRect();
        return r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth; })"""
    assert page.evaluate(fits.replace("%s", "menu"))
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    play_event([page])
    assert page.evaluate(fits.replace("%s", "board"))
    assert page.errors == []


@pytest.mark.parametrize("slug", ["pituushyppy", "aitajuoksu"])
def test_the_outfit_picked_on_the_menu_is_worn_in_the_events(site, context, slug):
    page = open_game(site, context, saved={"lajit": [slug, "kuula"]})
    assert page.text_content("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    assert page.locator("#ai-pelit-asut .asu").count() == 16  # 7 kits, 6 Halloween, 3 Tylypahka (#321)
    page.click("[data-asu=vampyyri]")
    page.click("#ai-pelit-asut-valmis")
    assert page.text_content("#asu") == "👕 Asu: Vampyyri"
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
    page.click("#go")
    page.wait_for_function("frameReady && frameAt === 0", timeout=10000)
    assert in_frame(page, "outfit.id") == "vampyyri"
    if slug == "aitajuoksu":
        page.wait_for_function("document.getElementById('laji').contentWindow.eval('race && race.runners.length > 1')", timeout=10000)
        assert in_frame(page, "race.runners.find(r => r.kind === 'me').asu") == "vampyyri"
    else:
        page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
        assert page.evaluate("Ottelu.K.comp.throwers.find(t => t.p === 'me').fit") == "vampyyri"
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_with_the_outfit_button_fits(site, context, size):
    w, h = size
    page = open_game(site, context, saved={"lajit": ["keihas", "moukari"]})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    sels = ["#go", "#multi", "#asu", "#stats", "#lajit"]
    boxes = {s: page.locator(s).bounding_box() for s in sels}
    for s, b in boxes.items():
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, s
    a = boxes["#asu"]
    for s, b in boxes.items():
        if s != "#asu":
            assert not (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
                        and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]), s
    page.click("#asu")
    done = page.locator("#ai-pelit-asut-valmis").bounding_box()
    assert done["y"] >= 0 and done["y"] + done["height"] <= h
    assert page.errors == []


def test_the_player_wears_the_outfit_on_the_podium_at_the_end_of_the_match(site, context):
    # Review of #315: the match's own medal ceremony drew everyone in the plain kit.
    context.add_init_script(f"localStorage.setItem('{SHARED}', JSON.stringify('noita'))")
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"]})
    assert page.text_content("#asu") == "👕 Asu: Noita"
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    finish_event(page)
    with page.expect_navigation():
        page.click("#next")
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    play_to_podium([page])
    rows = page.evaluate("cer.K.ending.res.map(r => [r.p, (podiumLook(r) || {}).head || null])")
    assert [h for p, h in rows if p == "me"] == ["witch"]
    assert all(h is None for p, h in rows if p != "me")
    page.wait_for_function("cer.K.ending.t > 2", timeout=8000)
    page.screenshot(path="/var/tmp/i311/ottelu-podium.png")
    assert page.errors == []


def test_a_kept_match_with_the_outfit_button_fits_a_short_phone(site, context):
    # CI on #315: at 360 × 640 the fourth button pushed the menu off the screen.
    page = open_game(site, context, saved={"lajit": ["keihas", "moukari"]})
    turn(page, {"width": 360, "height": 640})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    page.reload()
    assert page.is_visible("#cont") and page.is_visible("#asu")
    for s in ("#menu h1", "#go", "#cont", "#multi", "#asu", "#stats"):
        b = page.locator(s).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= 640, s
    assert page.errors == []


def last(slug):
    return json.loads((ROOT / "games" / slug / "game.json").read_text())["versions"][-1]["n"]


# Each game's newest version: only that folder is kept (#346).
GAMES = {s: f"games/{s}/v{last(s)}/" for s in ["ottelu", *EVENTS]}


@pytest.mark.parametrize("order", [
    ["kuula", "ottelu", "pituushyppy", "keihas", "aitajuoksu", "moukari"],
    ["ottelu", "aitajuoksu", "kuula", "korkeushyppy", "keihas", "seivashyppy"],
])
def test_choices_made_before_in_different_games_become_one_whichever_opens_first(site, browser, order):
    # Review of #315: a phone with Noita in Keihäs and Kulta in Kuula (and Neon in Aitajuoksu)
    # showed three outfits. The first game opened takes Keihäs's (the fixed order), and every
    # game shows it, with no pick in between.
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    ctx.add_init_script("""if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');
      if (!localStorage.getItem('seeded')) { localStorage.setItem('seeded', '1');
        localStorage.setItem('ai-pelit:_asut:keihas', '"noita"');
        localStorage.setItem('ai-pelit:_asut:kuula', '"kulta"');
        localStorage.setItem('ai-pelit:_asut:aitajuoksu', '"neon"'); } }""")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for slug in order:
        page.goto(site.url + GAMES[slug])
        assert page.text_content("#asu") == "👕 Asu: Noita", slug
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"noita"'
    # The older versions' own keys are left as they were until the next pick.
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:kuula')") == '"kulta"'
    assert errors == []
    ctx.close()

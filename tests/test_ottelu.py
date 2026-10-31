"""Ottelu v1: several athletics events in one match, points by the combined-event tables (#168)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/ottelu/v1/"

# play() takes this phone's turn in the event in its frame, once per turn: a set mark in the
# throws and the long jump, and over the bar up to a height (then misses) in the jumps over a bar.
# Alone it also skips the event's results.
HELPERS = """() => {
  const MARK = { pituushyppy: 6.5, keihas: 60, moukari: 55 }, UPTO = { korkeushyppy: 1.8, seivashyppy: 4.2 };
  window.play = () => {
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
}"""


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    if saved:
        for k, v in saved.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:ottelu:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


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


def test_points_follow_the_combined_event_tables(site, context):
    page = open_game(site, context)
    pts = page.evaluate("""[LAJIT.pituushyppy.pts(7), LAJIT.pituushyppy.pts(8.95), LAJIT.korkeushyppy.pts(2),
      LAJIT.seivashyppy.pts(5), LAJIT.keihas.pts(60), LAJIT.keihas.pts(7), LAJIT.moukari.pts(60), LAJIT.korkeushyppy.pts(0.7)]""")
    # World Athletics: 7.00 m 814, 8.95 m 1312, 2.00 m 803, 5.00 m 910, 60.00 m 738; nothing under the table's start.
    assert pts[:6] == [814, 1312, 803, 910, 738, 0]
    assert 800 < pts[6] < 900 and pts[7] == 0
    assert page.errors == []


def test_events_are_picked_in_the_order_tapped(site, context):
    page = open_game(site, context)
    assert page.evaluate("picked.join()") == "pituushyppy,korkeushyppy,seivashyppy,keihas,moukari"
    assert page.inner_text("#go") == "Viisiotteluun!"
    for s in ["pituushyppy", "korkeushyppy", "seivashyppy", "keihas", "moukari"]:
        page.click(f".laji[data-slug={s}]")
    assert page.is_disabled("#go")
    for s in ["keihas", "pituushyppy", "moukari"]:
        page.click(f".laji[data-slug={s}]")
    assert page.inner_text("#go") == "Kolmiotteluun!"
    assert page.evaluate("[...document.querySelectorAll('.laji.on')].map(b => b.dataset.slug + b.querySelector('b').textContent).join()") == "pituushyppy2,keihas1,moukari3"
    page.reload()
    assert page.evaluate("picked.join()") == "keihas,pituushyppy,moukari"
    assert page.errors == []


def test_a_match_alone_adds_up_saves_and_leaves_the_events_own_saves_alone(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:pituushyppy:taso', '5')")
    page.click(".laji[data-slug=seivashyppy]")
    page.click(".laji[data-slug=moukari]")
    page.click(".laji[data-slug=korkeushyppy]")
    page.click("#go")
    # The long jump: the event's own page in the frame, eight athletes and three rounds.
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    assert page.evaluate("[Ottelu.K.comp.throwers.length, Ottelu.K.F.ROUNDS, Ottelu.K.level]") == [8, 3, 1]
    play_event([page])
    assert "Pituushyppy · laji 1/2" in page.inner_text("#board")
    assert page.evaluate("M.rows.find(r => r.p === 'me').pts") == [697]
    page.click("#next")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    play_event([page])
    me = page.evaluate("M.rows.find(r => r.p === 'me')")
    assert me["marks"] == [6.5, 60] and me["pts"] == [697, 738]
    assert page.inner_text("#bTitle") == "Lopputulokset"
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:ottelu:ennatys'))") == {"2": 1435}
    assert page.evaluate("localStorage.getItem('ai-pelit:ottelu:ottelut')") == "1"
    assert page.evaluate("localStorage.getItem('ai-pelit:ottelu:kesken')") is None
    # The events' own saves are untouched: the match keeps its own.
    assert page.evaluate("localStorage.getItem('ai-pelit:pituushyppy:taso')") == "5"
    assert page.evaluate("Object.keys(localStorage).filter(k => /^ai-pelit:(pituushyppy|keihas):/.test(k))") == ["ai-pelit:pituushyppy:taso"]
    page.evaluate("document.getElementById('next').click()")
    assert page.is_visible("#menu") and "Ottelu" in page.inner_text("#menu")
    assert page.errors == []


def test_a_match_goes_on_after_a_reload(site, context):
    page = open_game(site, context, saved={"lajit": ["korkeushyppy", "pituushyppy"]})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.heights", timeout=10000)
    play_event([page])
    page.click("#next")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && M.at === 1 && Ottelu.K.comp.seq > 0", timeout=10000)
    for _ in range(40):
        page.evaluate("play()")
        if page.evaluate("Ottelu.K.comp.round >= 2"):
            break
        page.wait_for_timeout(50)
    seq = page.evaluate("Ottelu.K.comp.seq")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont") == "Jatka ottelua (laji 2/2)"
    page.click("#cont")
    page.wait_for_function(f"Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq === {seq}", timeout=10000)
    assert 1.7 < page.evaluate("M.rows.find(r => r.p === 'me').marks[0]") <= 1.8
    play_event([page])
    assert page.inner_text("#bTitle") == "Lopputulokset"
    assert page.errors == []


def test_a_reload_while_an_events_results_show_keeps_its_points(site, context):
    page = open_game(site, context, saved={"lajit": ["pituushyppy", "keihas"]})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    # Play the long jump without skipping its results, and reload while they show.
    for _ in range(400):
        if page.evaluate("!!(Ottelu.K && Ottelu.K.ending)"):
            break
        page.evaluate("Ottelu.K.ending || play()")
        page.wait_for_timeout(20)
    page.wait_for_function("M.phase === 'board'", timeout=3000)
    assert page.evaluate("!!Ottelu.K.ending && !document.getElementById('laji').classList.contains('hidden')")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont") == "Jatka ottelua (laji 2/2)"
    page.click("#cont")
    assert page.inner_text("#bTitle") == "Pituushyppy · laji 1/2"
    assert page.evaluate("M.rows.find(r => r.p === 'me').pts") == [697]
    page.click("#next")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    play_event([page])
    assert page.evaluate("M.rows.find(r => r.p === 'me').pts") == [697, 738]
    assert page.errors == []


def test_the_event_pages_are_fetched_ahead_for_offline_play(site, context):
    page = open_game(site, context)
    urls = []
    page.on("request", lambda r: urls.append(r.url))
    page.reload()
    page.wait_for_timeout(2500)
    for slug, v in [("pituushyppy", 4), ("korkeushyppy", 2), ("seivashyppy", 2), ("keihas", 4), ("moukari", 2)]:
        assert any(u.endswith(f"/games/{slug}/v{v}/") for u in urls), slug
    assert any(u.endswith("/lib/yleisurheilu-1/korkeus.js") for u in urls)


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


# ---- With friends ----

def room(site, browser, names, events):
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
        page.evaluate(HELPERS)
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
    # The host picks the events in the room screen.
    assert host.evaluate("document.getElementById('pick').closest('#aipr') !== null")
    for s in ["pituushyppy", "korkeushyppy", "seivashyppy", "keihas", "moukari"]:
        if s not in events:
            host.click(f".laji[data-slug={s}]")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && Ottelu.K.comp.throwers.length === 8", timeout=10000)
    return relay, pages


def test_two_phones_play_a_match_and_see_the_same_points(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"], ["pituushyppy", "keihas"])
    host, aino = pages
    assert aino.evaluate("M.events.join()") == "pituushyppy,keihas"
    assert all(p.evaluate("Ottelu.K.comp.throwers.filter(t => t.p).map(t => t.name).join()") == "Eero,Aino" for p in pages)
    play_event(pages)
    # Between events the host goes on, and the guest waits for it.
    assert aino.is_visible("#waiting") and not aino.is_visible("#next")
    assert host.evaluate("JSON.stringify(M.rows)") == aino.evaluate("JSON.stringify(M.rows)")
    host.click("#next")
    for p in pages:
        p.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    # Aino reloads in the middle of the javelin and gets the match and the meet back.
    for _ in range(100):
        for p in pages:
            p.evaluate("play()")
        if host.evaluate("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq >= 10"):
            break
        host.wait_for_timeout(50)
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function("M && M.at === 1 && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq > 0", timeout=15000)
    play_event(pages)
    rows = [p.evaluate("JSON.stringify(M.rows)") for p in pages]
    assert rows[0] == rows[1]
    for p, name in zip(pages, ["Eero", "Aino"]):
        me = p.evaluate("mine()")
        assert me["name"] == name and me["marks"] == [6.5, 60] and me["pts"] == [697, 738]
        assert p.inner_text("#bTitle") == "Lopputulokset"
        assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:ottelu:ennatys'))") == {"2": 1435}
    for p in pages:
        p.click("#next")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.errors == []
        p.context.close()


def test_an_away_phone_is_played_for_in_this_event_and_the_next(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"], ["pituushyppy", "keihas"])
    host, aino = pages
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    host.click("#aipr-goOn")
    host.wait_for_function("M.bots.length === 1", timeout=5000)
    play_event([host])
    host.click("#next")
    host.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    host.wait_for_function("Ottelu.K.comp.throwers.find(t => t.name === 'Aino').bot", timeout=5000)
    play_event([host])
    assert host.inner_text("#bTitle") == "Lopputulokset"
    assert host.evaluate("M.rows.find(r => r.name === 'Aino').pts.every(p => p >= 0)")
    for p in pages:
        assert p.errors == []
        p.context.close()

"""Ottelu v4: the shot put and the 100 m hurdles join the match, the newest event versions, and
no medal ceremony after each event (#287)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

import test_ottelu as v1
# v1's checks that still hold: the field events' points, and the menu and the board on a phone.
from test_ottelu import test_the_menu_and_the_board_fit  # noqa: F401

URL = "games/ottelu/v4/"

# v1's helpers, with the shot put, and run() for the hurdles: the computer's taps and jumps for
# this phone's runner, alone or with friends.
HELPERS = """() => {
  const MARK = { pituushyppy: 6.5, keihas: 60, moukari: 55, kuula: 15 }, UPTO = { korkeushyppy: 1.8, seivashyppy: 4.2 };
  window.play = () => {
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


@pytest.fixture(autouse=True)
def v4(monkeypatch):
    monkeypatch.setattr(v1, "URL", URL)
    monkeypatch.setattr(v1, "HELPERS", HELPERS)


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


def finish_event(page, timeout=60000):
    for _ in range(timeout // 20):
        page.evaluate("play()")
        if page.evaluate("frameAt === -1 && !document.getElementById('board').classList.contains('hidden')"):
            return
        page.wait_for_timeout(20)
    raise AssertionError("the event did not end")


def in_frame(page, js):
    return page.evaluate("(js) => document.getElementById('laji').contentWindow.eval(js)", js)


def test_the_new_events_score_by_the_combined_event_tables(site, context):
    page = open_game(site, context)
    # World Athletics: 100 m hurdles 13.85 s 1000, 15.00 s 842; shot put 16.00 m 851, 15.00 m 790.
    assert page.evaluate("[LAJIT.aitajuoksu.pts(13.85), LAJIT.aitajuoksu.pts(15), LAJIT.aitajuoksu.pts(30), LAJIT.kuula.pts(16), LAJIT.kuula.pts(15)]") \
        == [1000, 842, 0, 851, 790]
    assert page.evaluate("[LAJIT.pituushyppy.pts(7), LAJIT.keihas.pts(60)]") == [814, 738]
    assert page.evaluate("Object.entries(LAJIT).map(([s, l]) => s + l.v).join()") \
        == "aitajuoksu7,pituushyppy7,kuula1,korkeushyppy4,seivashyppy4,keihas6,moukari4"
    assert page.errors == []


def test_all_seven_events_can_be_picked(site, context):
    page = open_game(site, context)
    assert page.evaluate("picked.join()") == "aitajuoksu,pituushyppy,kuula,korkeushyppy,seivashyppy,keihas,moukari"
    assert page.inner_text("#go") == "Seitsenotteluun!"
    page.click(".laji[data-slug=moukari]")
    assert page.inner_text("#go") == "Kuusiotteluun!"
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


def test_an_event_ends_on_its_results_not_a_podium(site, context):
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"]})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    for _ in range(1000):
        if page.evaluate("!!Ottelu.K.ending"):
            break
        page.evaluate("play()")
        page.wait_for_timeout(20)
    # The results board, not the ceremony, and the match moves on by itself.
    drawn = page.evaluate("""() => { const K = Ottelu.K, x = document.getElementById('laji').contentDocument.getElementById('c').getContext('2d');
      const said = []; const ft = x.fillText; x.fillText = function (s, ...a) { said.push(s); return ft.call(this, s, ...a); };
      K.drawPodium(x, { left: 8, top: 44, w: 344, bottom: 730 }); x.fillText = ft; return said; }""")
    assert "Lopputulokset" in drawn
    page.wait_for_function("frameAt === -1 && !document.getElementById('board').classList.contains('hidden')", timeout=10000)
    assert page.inner_text("#bTitle") == "Kuulantyöntö · laji 1/2"
    assert page.errors == []


def test_a_red_card_alone_leaves_the_runner_out_and_the_match_on(site, context):
    page = open_game(site, context, saved={"lajit": ["aitajuoksu", "kuula"]})
    page.click("#go")
    page.wait_for_function("frameReady && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    in_frame(page, "me.card = 1; race.cdT = 1.2; falseStart(me)")
    page.wait_for_function("document.getElementById('laji').contentWindow.eval('race.phase') === 'cd'", timeout=6000)
    finish_event(page)
    me = page.evaluate("M.rows.find(r => r.p === 'me')")
    assert me["marks"] == [None] and me["pts"] == [0]
    assert page.evaluate("M.rows.filter(r => r.marks[0] > 0).length") == 7
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
    host.evaluate(f"picked.splice(0); {json.dumps(events)}.forEach(s => picked.push(s)); drawPick()")
    host.click("#aipr-start")
    return relay, pages


def test_two_phones_run_the_hurdles_and_see_the_same_points(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"], ["aitajuoksu", "kuula"])
    host, aino = pages
    for p in pages:
        p.wait_for_function("frameReady && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    assert all(in_frame(p, "race.runners.map(r => r.name).slice(0, 2).join() + race.runners.length") == "Eero,Aino8" for p in pages)
    assert in_frame(host, "race.runners.slice(2).every(r => r.kind === 'cpu')")
    assert in_frame(aino, "race.runners.slice(2).every(r => r.kind === 'net')")
    v1.play_event(pages)
    assert host.evaluate("JSON.stringify(M.rows)") == aino.evaluate("JSON.stringify(M.rows)")
    assert all(host.evaluate(f"M.rows.find(r => r.name === '{n}').marks[0] > 0") for n in ["Eero", "Aino"])
    host.click("#next")
    for p in pages:
        p.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    v1.play_event(pages)
    assert host.evaluate("JSON.stringify(M.rows)") == aino.evaluate("JSON.stringify(M.rows)")
    for p, name in zip(pages, ["Eero", "Aino"]):
        me = p.evaluate("mine()")
        assert me["name"] == name and me["marks"][1] == 15 and me["pts"][1] == 790
        assert p.inner_text("#bTitle") == "Lopputulokset"
    for p in pages:
        assert p.errors == []
        p.context.close()


@pytest.mark.parametrize("size", [(360, 640), (740, 360)])
def test_the_race_and_its_results_fit(site, context, size):
    page = open_game(site, context, saved={"lajit": ["aitajuoksu", "kuula"]})
    turn(page, {"width": size[0], "height": size[1]})
    page.click("#go")
    page.wait_for_function("frameReady && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    for _ in range(3000):
        if in_frame(page, "race && race.phase === 'done'"):
            break
        page.evaluate("play()")
        page.wait_for_timeout(20)
    # The results of all eight inside the screen, above the pads.
    page.wait_for_timeout(100)
    box = in_frame(page, "({ ...race.resultsBox, H, ctrlTop })")
    assert box["top"] >= 0 and box["bottom"] <= min(box["H"], box["ctrlTop"])
    assert page.errors == []


def test_a_reload_mid_race_runs_the_race_again_and_keeps_the_points(site, context):
    page = open_game(site, context, saved={"lajit": ["kuula", "aitajuoksu"]})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    finish_event(page)
    with page.expect_navigation():
        page.click("#next")
    page.wait_for_function("frameReady && M.at === 1 && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    for _ in range(200):
        page.evaluate("play()")
        if in_frame(page, "race.phase === 'run' && me.x > 20"):
            break
        page.wait_for_timeout(20)
    page.reload()
    # A reload shows the menu with the match to go on; the race starts again from the gun.
    assert page.inner_text("#cont") == "Jatka ottelua (laji 2/2)"
    page.click("#cont")
    page.wait_for_function("frameReady && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    assert in_frame(page, "[race.phase, me.x, race.runners.length].join()") == "cd,0,8"
    finish_event(page)
    me = page.evaluate("M.rows.find(r => r.p === 'me')")
    assert me["marks"][0] == 15 and me["pts"][0] == 790 and me["marks"][1] > 10
    assert page.inner_text("#bTitle") == "Lopputulokset"
    assert page.errors == []

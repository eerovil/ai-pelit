"""Athletics meets with friends on yleisurheilu-5 (#297): the meet waits only for the phone whose
turn it is, the host skips an away phone's turn, a phone that leaves keeps its competitor and comes
back with "Palaa kierrokseen", and the friends not on turn stand by as spectators and cheer.

Each event's newest version, all on the same library: games/pituushyppy/v8, games/keihas/v7,
games/kuula/v2, games/moukari/v5, games/korkeushyppy/v5, games/seivashyppy/v5, games/makihyppy/v3.
"""

import json

import pytest
from conftest import ROOT
from test_rooms_lib import Relay

EVENTS = ["pituushyppy/v8", "keihas/v7", "kuula/v2", "moukari/v5", "korkeushyppy/v5", "seivashyppy/v5", "makihyppy/v3"]

# A turn's mark that counts in each format: a jump of 5 (rounds), a clearance (bar heights) or a
# ski jump of 110 m for 90 points (Mäkihyppy's week).
MARK = "(K.F.missed === 'X' ? 'O' : typeof K.F.missed === 'object' ? { d: 110, p: 90 } : 5)"


def new_phone(site, browser, relay, path, name, ctx=None):
    if ctx is None:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
    relay.attach(page)
    page.goto(f"{site.url}games/{path}/")
    return page


def room(site, browser, path, names):
    site.build(ROOT / "games")
    relay = Relay()
    pages = [new_phone(site, browser, relay, path, n) for n in names]
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
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("K.comp && K.comp.throwers.length > 3 && K.comp.seq >= 0", timeout=8000)
    return relay, pages, code


def on_turn(host):
    return host.evaluate("K.current() && K.current().p")


def play(host, phones, until):
    """Takes the turns of the phones in `phones` (id -> page) until `until(id on turn)` holds."""
    for _ in range(80):
        pid = on_turn(host)
        if pid is None or until(pid):
            return pid
        page = phones[pid]
        n = host.evaluate("K.comp.seq")
        page.wait_for_function(f"K.comp && K.comp.seq === {n}", timeout=5000)
        page.evaluate(f"K.report({n}, {MARK})")
        host.wait_for_function(f"K.comp.over || K.comp.seq > {n}", timeout=5000)
    raise AssertionError("the turn never came")


@pytest.mark.parametrize("path", EVENTS)
def test_an_away_friend_stops_the_meet_only_on_their_own_turn(site, browser, path):
    relay, pages, code = room(site, browser, path, ["Eero", "Aino", "Ville"])
    host, aino, ville = pages
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    me_aino = aino.evaluate("AiPelitRooms.me")
    # Aino is not on turn when she closes the game.
    play(host, ids, lambda pid: pid != me_aino)
    ctx = aino.context
    relay.drop(aino)  # the page's socket goes as the game is closed
    aino.close()
    relay.blocked.discard(me_aino)
    host.wait_for_function(f"!AiPelitRooms.members.find(m => m.id === {json.dumps(me_aino)}).on")
    # The others play on: nothing waits for her while it is not her turn.
    assert host.evaluate("AiPelitRooms.paused") is False
    del ids[me_aino]
    seq = host.evaluate("K.comp.seq")
    play(host, ids, lambda pid: pid == me_aino)
    assert host.evaluate("K.comp.seq") > seq or on_turn(host) == me_aino
    # Her turn: everyone waits, and the host may skip it. The computer never takes her.
    for p in (host, ville):
        p.wait_for_function("document.getElementById('aipr-pauseText').textContent === '⏸ Odotetaan: Aino'", timeout=5000)
    assert host.inner_text("#aipr-goOn") == "Ohita vuoro"
    assert ville.locator("#aipr-goOn").is_hidden()
    before = host.evaluate("K.comp.seq")
    host.click("#aipr-goOn")
    host.wait_for_function(f"K.comp.seq > {before}")
    t = host.evaluate(f"K.comp.throwers.find(t => t.p === {json.dumps(me_aino)})")
    assert t["bot"] is False
    missed = host.evaluate("K.F.missed === undefined ? -1 : K.F.missed")
    assert missed in t.get("marks", []) or "X" in json.dumps(t.get("rec", []))
    # On with the others (at a bar height her next attempt may come straight after).
    if on_turn(host) != me_aino:
        host.wait_for_function("!AiPelitRooms.paused", timeout=2000)
        # She stands among the spectators, faded, while she is away.
        assert me_aino in host.evaluate("K.fans().map(f => f.p)")
    # She opens the game again, and one tap takes her back into the meet where it is.
    aino = new_phone(site, browser, relay, path, "Aino", ctx)
    aino.click("#multi")
    assert aino.inner_text("#aipr-again") == f"↩ Palaa kierrokseen {code}"
    aino.click("#aipr-again")
    seq = host.evaluate("K.comp.seq")
    aino.wait_for_function(f"K.comp && K.comp.seq === {seq}", timeout=8000)
    ids[me_aino] = aino
    for p in pages[:1] + [ville, aino]:
        assert p.errors == []
    for p in (host, ville, aino):
        p.context.close()


@pytest.mark.parametrize("path", EVENTS)
def test_friends_not_on_turn_stand_by_and_cheer(site, browser, path):
    relay, pages, code = room(site, browser, path, ["Eero", "Aino", "Ville"])
    host = pages[0]
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    pid = on_turn(host)
    jumper = ids[pid]
    fans = [p for p in pages if p is not jumper]
    for p in pages:
        p.wait_for_function(f"K.current() && K.current().p === {json.dumps(pid)}", timeout=5000)
    # The two others stand by on every phone; the one on turn has no cheer button.
    names = sorted(host.evaluate("K.fans().map(f => f.name)"))
    assert names == sorted(p.evaluate("AiPelitRooms.name()") for p in fans)
    jumper.wait_for_timeout(300)
    assert not jumper.locator("#kisa-cheer").is_visible()
    fan = next(p for p in fans if p is not host)  # a guest: its cheer goes through the host
    fan.wait_for_selector("#kisa-cheer", state="visible", timeout=5000)
    assert fan.inner_text("#kisa-cheer") == "📣 Kannusta"
    # Each phone counts the crowd sounds it plays.
    for p in pages:
        p.evaluate("window.yleisoHeard = 0; const play = AiPelitAanet.play; AiPelitAanet.play = (n, o) => { if (n === 'yleiso') yleisoHeard++; return play(n, o); }")
    fan.click("#kisa-cheer")
    tid = fan.evaluate("K.mine().id")
    name = host.evaluate("K.current().name")
    for p in pages:
        p.wait_for_function(f"K.cheers[{json.dumps(tid)}]", timeout=5000)
        text = p.evaluate(f"K.cheers[{json.dumps(tid)}].text")
        assert name in text and text.endswith("!")
    # One tap is one crowd sound on every phone, the tapping guest's own too (not again on the echo).
    fan.wait_for_timeout(500)
    assert [p.evaluate("yleisoHeard") for p in pages] == [1, 1, 1]
    # Both spectators cheer at the same moment: every phone shows both.
    tids = [p.evaluate("K.mine().id") for p in fans]
    for p in fans:
        p.evaluate("K.cheer()")
    for p in pages:
        p.wait_for_function(f"{json.dumps(tids)}.every(id => K.cheers[id] && performance.now() - K.cheers[id].at < 1500)", timeout=5000)
    # Once the turn is over, the next one on turn loses the button.
    n = host.evaluate("K.comp.seq")
    jumper.evaluate(f"K.report({n}, {MARK})")
    host.wait_for_function(f"K.comp.seq > {n}")
    nxt = ids[on_turn(host)]
    nxt.wait_for_function("K.current() && K.current().p === AiPelitRooms.me", timeout=5000)
    nxt.wait_for_function("(b => !b || b.style.display === 'none')(document.getElementById('kisa-cheer'))", timeout=3000)
    for p in pages:
        assert p.errors == []
        p.context.close()


@pytest.mark.parametrize("path", EVENTS)
def test_alone_the_meet_plays_as_before_with_no_spectators(site, context, path):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}games/{path}/")
    page.click("#go")
    page.wait_for_function("K.comp && K.current() && K.current().p === 'me'")
    n = page.evaluate("K.comp.seq")
    page.evaluate(f"K.report({n}, {MARK})")
    page.wait_for_function(f"K.comp.seq > {n}")
    assert page.evaluate("[K.fans().length, !!document.getElementById('kisa-cheer')]") == [0, False]
    assert page.errors == []

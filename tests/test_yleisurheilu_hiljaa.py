"""The field events without crowd noise (#337): on aanet-4, "📣 Kannusta" is a quiet blip from the
game (cheerSound), not kisa.js's "jee!" (#330, which this file replaces) nor a shouting crowd.

games/pituushyppy/v12, games/keihas/v11, games/kuula/v5, games/moukari/v8, games/korkeushyppy/v8,
games/seivashyppy/v9, games/makihyppy/v5.
"""

import json

import pytest
from conftest import ROOT
from test_yleisurheilu_vuorot import MARK, on_turn, room

EVENTS = ["pituushyppy/v12", "keihas/v11", "kuula/v5", "moukari/v8", "korkeushyppy/v8", "seivashyppy/v9", "makihyppy/v5"]
pytestmark = pytest.mark.games(*sorted({e.split("/")[0] for e in EVENTS}))


@pytest.mark.parametrize("path", EVENTS)
def test_the_version_loads_the_quiet_library(path):
    page = (ROOT / "games" / path / "index.html").read_text()
    assert "lib/yleisurheilu-6/kisa.js" in page and "lib/yleisurheilu-5/" not in page
    assert "lib/aanet-4/aanet.js" in page and "lib/aanet-3/" not in page and "lib/aanet-2/" not in page


@pytest.mark.parametrize("path", EVENTS)
def test_a_cheer_is_one_quiet_blip_on_every_phone(site, browser, path):
    relay, pages, code = room(site, browser, path, ["Eero", "Aino", "Ville"])
    host = pages[0]
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    pid = on_turn(host)
    for p in pages:
        p.wait_for_function(f"K.current() && K.current().p === {json.dumps(pid)}", timeout=5000)
    fan = next(p for p in pages if p is not host and p is not ids[pid])
    fan.wait_for_selector("#kisa-cheer", state="visible", timeout=5000)
    for p in pages:
        p.wait_for_function("AiPelitAanet.ready('onnistui')", timeout=10000)
        p.evaluate("window.heard = []; const play = AiPelitAanet.play; AiPelitAanet.play = (n, o) => { heard.push([n, (o || {}).vol]); return play(n, o); }")
    fan.click("#kisa-cheer")
    tid = fan.evaluate("K.mine().id")
    for p in pages:
        p.wait_for_function(f"K.cheers[{json.dumps(tid)}]", timeout=5000)
    fan.wait_for_timeout(500)
    for p in pages:
        assert p.evaluate("heard.filter(h => h[0] === 'onnistui' || h[0] === 'jee')") == [["onnistui", 0.25]]
        # The library never fetched its own cheer.
        assert not p.evaluate("AiPelitAanet.ready('jee')")
        assert p.errors == []
    for p in pages:
        p.context.close()


@pytest.mark.parametrize("path", EVENTS)
def test_alone_the_meet_plays_as_before(site, context, path):
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

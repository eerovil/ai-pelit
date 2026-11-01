"""The cheer on yleisurheilu-6 (#330): "📣 Kannusta" plays a short "jee!" from aanet-3, not four
seconds of a shouting crowd (aanet-2 yleiso), which Eero found awful.

Each event's newest version, all on the same library: games/pituushyppy/v11, games/keihas/v10,
games/kuula/v4, games/moukari/v7, games/korkeushyppy/v7, games/seivashyppy/v8, games/makihyppy/v4.
"""

import json

import pytest
from conftest import ROOT
from test_yleisurheilu_vuorot import MARK, on_turn, room

EVENTS = ["pituushyppy/v11", "keihas/v10", "kuula/v4", "moukari/v7", "korkeushyppy/v7", "seivashyppy/v8", "makihyppy/v4"]


@pytest.mark.parametrize("path", EVENTS)
def test_the_version_loads_the_new_libraries(path):
    page = (ROOT / "games" / path / "index.html").read_text()
    assert "lib/yleisurheilu-6/kisa.js" in page and "lib/yleisurheilu-5/" not in page
    assert "lib/aanet-3/aanet.js" in page and "lib/aanet-1/" not in page and "lib/aanet-2/" not in page


@pytest.mark.parametrize("path", EVENTS)
def test_a_cheer_plays_jee_on_every_phone(site, browser, path):
    relay, pages, code = room(site, browser, path, ["Eero", "Aino", "Ville"])
    host = pages[0]
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    pid = on_turn(host)
    for p in pages:
        p.wait_for_function(f"K.current() && K.current().p === {json.dumps(pid)}", timeout=5000)
    fan = next(p for p in pages if p is not host and p is not ids[pid])
    fan.wait_for_selector("#kisa-cheer", state="visible", timeout=5000)
    # The sound is loaded with the meet, so it is ready by the first cheer.
    for p in pages:
        p.wait_for_function("AiPelitAanet.ready('jee')", timeout=10000)
        p.evaluate("window.heard = []; const play = AiPelitAanet.play; AiPelitAanet.play = (n, o) => { heard.push(n); return play(n, o); }")
    fan.click("#kisa-cheer")
    tid = fan.evaluate("K.mine().id")
    for p in pages:
        p.wait_for_function(f"K.cheers[{json.dumps(tid)}]", timeout=5000)
    fan.wait_for_timeout(500)
    # One tap is one "jee" on every phone, and the crowd is not heard.
    for p in pages:
        assert p.evaluate("heard.filter(n => n === 'jee' || n === 'yleiso')") == ["jee"]
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

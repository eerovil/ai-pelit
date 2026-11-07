"""The games' versions without crowd noise and with the loudest sounds quieter (#337), and softer (#355).

Each is its previous version with the sounds changed: it loads aanet-5 (#355: the sounds Eero
still found too loud swapped for softer ones or played quieter; aanet-4 before), opens, starts on
a tap and throws nothing. Each version's own tests/test_<slug>_v<N>.py runs this check, so that a pull
request on it runs that file and not every older version's tests. What a version may play is
checked for every game's newest version in test_lib_aanet.py.
"""

import re

import pytest

from conftest import ROOT, Site, wait_for_worker

VERSIONS = [
    "games/aitajuoksu/v12", "games/areena/v8", "games/curling/v4", "games/hiihto/v12",
    "games/jaan-alla/v7", "games/jalkapallo/v4", "games/kaahari/v6", "games/kaaosrata/v5",
    "games/keihas/v16", "games/kirkkis/v11", "games/korkeushyppy/v14", "games/kuula/v10",
    "games/lentopallo/v7", "games/makihyppy/v11", "games/molkky/v4", "games/moukari/v12",
    "games/orava/v6", "games/pallorata/v5", "games/pilkki/v6", "games/pituushyppy/v17",
    "games/puhelinkoppi/v9", "games/seivashyppy/v15", "games/skuutti/v5", "games/sormiskeitti/v10",
    "games/tikka/v7", "games/trampoliini/v11", "games/voimistelu/v13", "games/vuoristorata/v4",
    "games/yoajo/v12", "games/last-signal/v16", "games/vauvan-syotto/v4",
]

# The field events' newest versions, whose "📣 Kannusta" chime Eero found too loud (#355).
EVENTS = ["keihas", "korkeushyppy", "kuula", "makihyppy", "moukari", "pituushyppy", "seivashyppy"]

# Records every sound the game asks for, from before its own script runs.
SPY = """
Object.defineProperty(window, 'AiPelitAanet', { configurable: true, set(a) {
  window.__played = [];
  const play = a.play;
  a.play = (name, o) => { window.__played.push(name); return play(name, o); };
  Object.defineProperty(window, 'AiPelitAanet', { value: a, writable: true, configurable: true });
} });
"""


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """The real site, built once for the whole file."""
    s = Site(tmp_path_factory.mktemp("site"))
    s.build(ROOT / "games")
    yield s
    s.close()


def opens_and_plays_with_the_quiet_library(site, context, version):
    context.add_init_script(SPY)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}{version}/")
    page.wait_for_function("window.AiPelitAanet && window.__played", timeout=10000)
    assert "aplodit" not in page.evaluate("AiPelitAanet.names()")
    assert page.evaluate("[...document.scripts].some(s => s.src.includes('/lib/aanet-5/aanet.js'))")
    for x, y in [(180, 400), (180, 600), (180, 300)]:
        page.mouse.click(x, y)
        page.wait_for_timeout(400)
    page.wait_for_timeout(1000)
    assert not {"aplodit", "yleiso", "ohhoo", "jee"} & set(page.evaluate("window.__played"))
    assert errors == []


def cheer_is_quiet(version):
    """#355: the cheer plays aanet-5's soft chime at 0.08 at most, never pitched up."""
    code = (ROOT / version / "index.html").read_text()
    m = re.search(r"cheerSound: \(\) => \w+\.play\('onnistui', \{([^}]*)\}\)", code)
    assert m, f"{version} has no onnistui cheerSound"
    vol = re.search(r"\bvol: (\d+(?:\.\d+)?)", m.group(1))
    rate = re.search(r"\brate: (\d+(?:\.\d+)?)", m.group(1))
    assert vol and float(vol.group(1)) <= 0.08, m.group(0)
    assert not rate or float(rate.group(1)) <= 1, m.group(0)

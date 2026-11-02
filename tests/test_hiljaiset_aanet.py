"""The games' versions without crowd noise and with the loudest sounds quieter (#337).

Each is its previous version with the sounds changed: it loads aanet-4, opens, starts on a tap
and throws nothing. Each version's own tests/test_<slug>_v<N>.py runs this check, so that a pull
request on it runs that file and not every older version's tests. What a version may play is
checked for every game's newest version in test_lib_aanet.py.
"""

import pytest

from conftest import ROOT, Site, wait_for_worker

VERSIONS = [
    "games/aitajuoksu/v11", "games/areena/v7", "games/curling/v3", "games/hiihto/v11",
    "games/jaan-alla/v6", "games/jalkapallo/v3", "games/kaahari/v5", "games/kaaosrata/v4",
    "games/keihas/v12", "games/kirkkis/v9", "games/korkeushyppy/v9", "games/kuula/v6",
    "games/lentopallo/v6", "games/makihyppy/v6", "games/molkky/v3", "games/moukari/v9",
    "games/orava/v5", "games/pallorata/v4", "games/pilkki/v4", "games/pituushyppy/v13",
    "games/puhelinkoppi/v7", "games/seivashyppy/v10", "games/skuutti/v3", "games/sormiskeitti/v8",
    "games/tikka/v5", "games/trampoliini/v9", "games/voimistelu/v12", "games/vuoristorata/v3",
    "games/yoajo/v9",
]

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
    for x, y in [(180, 400), (180, 600), (180, 300)]:
        page.mouse.click(x, y)
        page.wait_for_timeout(400)
    page.wait_for_timeout(1000)
    assert not {"aplodit", "yleiso", "ohhoo", "jee"} & set(page.evaluate("window.__played"))
    assert errors == []

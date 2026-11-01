"""Last Signal v14 (#300): Eero still heard a loud hiss inside SISU in v13. It was the shared library's 'humina' loop
(the reactor's hum), which is nearly all hiss; v14 keeps it silent everywhere. Otherwise v14 plays as v13."""

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v13 as v13
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v14/"


@pytest.fixture(autouse=True)
def _v14(monkeypatch):
    for m in (v4, v5):
        monkeypatch.setattr(m, "URL", URL)


@pytest.mark.parametrize("mode", ["home", "sub", "dive"])
def test_no_hiss_inside_sisu_at_the_helm_or_on_a_dive(site, browser, mode):
    page = v13.game(site, browser)
    page.evaluate(f"""(() => {{ const vols = {{}}; window.heard14 = vols;
      window.BED = {{}}; for (const k of ['sea', 'engine', 'hum', 'wind']) BED[k] = {{ set: o => {{ vols[k] = o.vol; }}, playing: () => true }}; BED.next = 99;
      AC = {{ state: 'running' }}; G.mode = '{mode}'; soundStep(0.01); }})()""")
    v = page.evaluate("heard14")
    assert v["hum"] == 0
    assert page.errors == []


def test_v14_still_plays_as_v13(site, browser):
    page = v13.game(site, browser)
    v13.surface_at(page, 0)
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); run(() => true, 0.1); drawHud()")
    assert page.inner_text("#act") == "🚪 Aurora-asemalle"
    assert page.errors == []

"""The podium of yleisurheilu-10 in every athletics event, for every outfit (#469).

Every event's newest version draws its medal ceremony with the shared front-facing figure. Each
outfit (the athletics kits, the Halloween costumes and the Tylypahka robes) stands on it, through
the hops, the medals and the cheer, upright and sideways, with no page error.
"""

import json

import pytest

from conftest import ROOT

EVENTS = ["korkeushyppy/v15", "pituushyppy/v18", "seivashyppy/v16", "keihas/v17", "kuula/v11",
          "moukari/v13", "makihyppy/v12"]

pytestmark = pytest.mark.games(*sorted({e.split("/")[0] for e in EVENTS}))

DRAW = """([w, h]) => {
  const ids = AiPelitOutfits.list().map(o => o.id);
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const x = cv.getContext('2d');
  const box = { left: 8, top: 44, w: w - 16, bottom: h - 8 };
  const COLS = ['#e63946', '#2a9d8f', '#f4a261', '#457b9d'];
  const drawn = [];
  // Twelve at a time, so every outfit takes each podium place at least once.
  for (let start = 0; start < ids.length; start += 3) {
    const res = [];
    for (let i = 0; i < 12; i++) {
      const fit = ids[(start + i) % ids.length];
      res.push({ id: 'a' + i, p: i === 0 ? 'me' : null, name: 'Urheilija ' + i, col: COLS[i % 4],
        best: 10 - i * 0.3, place: i + 1, marks: [10 - i * 0.3], fin: true, fit });
    }
    for (const t of [0, 1.2, 3, 4.8, 6.5]) {
      K.ending = { t, res, at: 0, place: 1, mark: 10, fin: true };
      x.clearRect(0, 0, w, h);
      K.drawPodium(x, box);
      drawn.push(res.slice(0, 3).map(r => r.fit).join());
    }
  }
  K.ending = null;
  return { ids, drawn: drawn.length, top: [...new Set(drawn.join().split(','))].length };
}"""


@pytest.mark.parametrize("event", EVENTS)
def test_every_outfit_stands_on_the_podium(site, context, event):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + "games/" + event + "/")
    page.wait_for_function("typeof K !== 'undefined' && K.drawPodium && window.AiPelitOutfits", timeout=5000)
    for size in ([360, 740], [740, 360]):
        out = page.evaluate(DRAW, size)
        assert len(out["ids"]) == 16, out["ids"]
        assert out["top"] == 16, "an outfit never stood on the podium"
    assert errors == []

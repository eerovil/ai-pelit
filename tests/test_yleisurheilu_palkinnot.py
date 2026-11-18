"""The podium of yleisurheilu-10 and -11 in every athletics event, for every outfit (#469).

Every event's newest version draws its medal ceremony with the shared front-facing figure. Each
outfit (the athletics kits, the Halloween costumes and the Tylypahka robes) stands on it, through
the hops, the medals and the cheer, upright and sideways, with no page error.
"""

import json

import pytest

from conftest import ROOT

EVENTS = ["korkeushyppy/v16", "pituushyppy/v19", "seivashyppy/v17", "keihas/v18", "kuula/v12",
          "moukari/v14", "makihyppy/v13"]

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


REACH = """([w, h]) => {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const x = cv.getContext('2d'), box = { left: 8, top: 44, w: w - 16, bottom: h - 8 };
  const res = [];
  for (let i = 0; i < 12; i++) res.push({ id: 'a' + i, p: null, name: 'U' + i, col: '#e63946', best: 10 - i * 0.3,
    place: i + 1, marks: [10 - i * 0.3], fin: true, fit: null });
  const real = AiPelitOutfits.figure, seen = [];
  AiPelitOutfits.figure = function (c, L, fx, fy, hh, p) { seen.push({ off: L.top === '#1f2f55', reach: p && p.reach || null }); return real.apply(this, arguments); };
  const out = {};
  // The bronze, the silver and the gold are being hung at these times (MEDAL_T + 0.3 of HANG).
  for (const t of [2.7, 3.8, 4.9, 6.5]) {
    seen.length = 0; K.ending = { t, res, at: 0, place: 1, mark: 10, fin: true }; K.drawPodium(x, box);
    out[t] = seen.filter(s => s.off).map(s => s.reach);
  }
  AiPelitOutfits.figure = real; K.ending = null;
  return out;
}"""


@pytest.mark.parametrize("event", EVENTS)
def test_the_official_hangs_the_medal_with_its_own_arms(site, context, event):
    """#469: Eero saw the official keep its arms down while two extra arms held the ribbon."""
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + "games/" + event + "/")
    page.wait_for_function("typeof K !== 'undefined' && K.drawPodium && window.AiPelitOutfits", timeout=5000)
    out = page.evaluate(REACH, [360, 740])
    for t in ("2.7", "3.8", "4.9"):
        assert len(out[t]) == 1 and out[t][0], (t, out[t])
        (lx, ly), (rx, ry) = out[t][0]
        assert lx < rx and abs(ly - ry) < 1, out[t][0]
    assert out["6.5"] == [], "the official leaves after the gold"

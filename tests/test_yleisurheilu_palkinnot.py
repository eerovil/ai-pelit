"""The podium of yleisurheilu-10 and -11 in every athletics event, for every outfit (#469).

Every event's newest version draws its medal ceremony with the shared front-facing figure. Each
outfit (the athletics kits, the Halloween and Christmas costumes and the Tylypahka robes) stands on it, through
the hops, the medals and the cheer, upright and sideways, with no page error.
"""

import json

import pytest

from conftest import ROOT

EVENTS = ["korkeushyppy/v17", "pituushyppy/v20", "seivashyppy/v18", "keihas/v19", "kuula/v13",
          "moukari/v15", "makihyppy/v13", "saappaanheitto/v2", "uimahyppy/v1"]

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
        assert len(out["ids"]) == 21, out["ids"]  # Christmas (#473) is in the list all year
        assert out["top"] == 21, "an outfit never stood on the podium"
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
        assert lx < rx and abs(ly - ry) < 4, out[t][0]  # a far hand may stop at arm's length
    assert out["6.5"] == [], "the official leaves after the gold"


@pytest.mark.parametrize("event", EVENTS)
def test_the_players_outfit_reaches_the_podium_rows(site, context, event):
    """#469: the bar-height format (korkeus.js) gave its rows no `fit`, so a high jumper or a pole
    vaulter stood on the podium in the plain kit instead of their outfit."""
    import yleisurheilu_asut as A
    page = A.open_game(site, context, "games/" + event + "/", {A.SHARED: "noita"})
    page.wait_for_function("typeof K !== 'undefined' && window.AiPelitOutfits", timeout=5000)
    page.click("#go")
    page.wait_for_function("K.comp && K.results", timeout=5000)
    mine = page.evaluate("K.results().filter(r => r.p === 'me').map(r => r.fit)")
    assert mine == ["noita"]
    assert page.errors == []


SWEEP = """([w, h, places]) => {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const x = cv.getContext('2d'), box = { left: 8, top: 44, w: w - 16, bottom: h - 8 };
  const res = [];
  for (let i = 0; i < 12; i++) res.push({ id: 'a' + i, p: null, name: 'U' + i, col: '#e63946', best: 10 - i * 0.3,
    place: (places || [])[i] || i + 1, marks: [10 - i * 0.3], fin: true, fit: null });
  const real = AiPelitOutfits.figure, out = [];
  let hands = null, others = [];
  AiPelitOutfits.figure = function (c, L, fx, fy, hh, p) {
    if (L.top !== '#1f2f55') others.push(fx);
    else {
      const lw = Math.max(2, hh * 0.075), sh = d => [fx + d * (hh * 0.14 - lw * 0.4), fy - hh * 0.72 + lw * 0.3];
      // Without reach, the hands hang at the sides (figure()'s arms down).
      const at = p && p.reach || [[fx - hh * 0.21, fy - hh * 0.46], [fx + hh * 0.21, fy - hh * 0.46]];
      hands = { h: hh, at, rel: at.map(([ax, ay]) => [ax - fx, ay - fy]), arm: Math.max(...[-1, 1].map((d, k) => Math.hypot(at[k][0] - sh(d)[0], at[k][1] - sh(d)[1]))) };
    }
    return real.apply(this, arguments);
  };
  for (let t = 2.2; t < 5.6; t += 0.01) {
    hands = null; others = []; K.ending = { t, res, at: 0, place: 1, mark: 10, fin: true }; K.drawPodium(x, box);
    out.push(hands && Object.assign(hands, { others }));
  }
  AiPelitOutfits.figure = real; K.ending = null;
  return out;
}"""


@pytest.mark.parametrize("places", [None, [1, 2, 3, 3], [1, 1, 3]])
@pytest.mark.parametrize("size", [[360, 740], [740, 360]])
def test_the_officials_arms_never_stretch_or_snap(site, context, size, places):
    """#469 helper checks: the hands rise to the ribbon and drop back smoothly, and the ribbon is
    carried no higher than the official's arms reach."""
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + "games/pituushyppy/v20/")
    page.wait_for_function("typeof K !== 'undefined' && K.drawPodium && window.AiPelitOutfits", timeout=5000)
    seen = page.evaluate(SWEEP, [*size, places])
    on = [s for s in seen if s]
    assert len(on) > 200
    assert max(s["arm"] / s["h"] for s in on) <= 0.451
    for a, b in zip(seen, seen[1:]):
        if a and b:
            # A hand on the ribbon stays put while the official walks, and a hand at its side walks
            # with it, so one of the two frames sees it move smoothly. Raising or dropping the hands
            # eases over about 0.12 s, at most 0.09 h per 0.01 s; the old switch on and off
            # the ribbon moved them about 0.8 h in one step.
            step = min(max(abs(a[w][k][i] - b[w][k][i]) for k in (0, 1) for i in (0, 1)) for w in ("at", "rel"))
            assert step < 0.12 * a["h"], (a, b)


@pytest.mark.parametrize("places", [[1, 2, 3, 3], [1, 1, 3], [1, 2, 2, 2]])
def test_the_official_reaches_every_medallist_of_a_shared_place(site, context, places):
    """#471 review: medallists sharing a place stand side by side, and the official steps along to
    each, so its hands reach the ribbon rather than stop short at arm's length."""
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + "games/korkeushyppy/v17/")
    page.wait_for_function("typeof K !== 'undefined' && K.drawPodium && window.AiPelitOutfits", timeout=5000)
    MEDAL_T, HANG = [4.6, 3.5, 2.4], 0.9
    for size in ([360, 740], [740, 360]):
        seen = page.evaluate(SWEEP, [*size, places])
        for i in {p - 1 for p in places}:
            n = places.count(i + 1)
            for j in range(n):
                # The middle of this medallist's share: the hands hold the ribbon's two ends, either
                # side of a medallist's middle, rather than one stopping short at arm's length.
                s = seen[round((MEDAL_T[i] + (j + 0.5) * HANG / n - 2.2) / 0.01)]
                mid = (s["at"][0][0] + s["at"][1][0]) / 2
                assert min(abs(mid - fx) for fx in s["others"]) < 0.5, (size, i, j, s)
                assert abs(s["at"][0][1] - s["at"][1][1]) < 0.5, (size, i, j, s)
    assert errors == []

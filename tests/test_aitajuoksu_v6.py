"""Aitajuoksu v6: the legs run forwards, the knee bending as the leg swings forward (#170)."""

import shutil

from conftest import ROOT

URL = "games/aitajuoksu/v6/"

# Draws the runner through a recording context at many points of the stride and returns, for
# each leg, how far its thigh moves forward next and how bent its knee is (radians).
STRIDE = """() => {
  const s = 100, px = 200, base = 400, hipY = base - 0.92 * s, out = [];
  const draw = ph => {
    const paths = []; let cur = null;
    const g = new Proxy({}, { get: (_, k) => k === 'beginPath' ? () => { cur = []; paths.push(cur); }
      : k === 'moveTo' || k === 'lineTo' ? (a, b) => { if (cur) cur.push([a, b]); } : () => {}, set: () => true });
    body(g, { y: 0, v: 8, ph, stum: 0, color: '#f00' }, OUTFITS[0], px, base, s, false);
    // The legs: hip, knee, foot. The far leg is drawn first.
    const legs = paths.filter(q => q.length === 3 && Math.abs(q[0][0] - px) < 1e-6 && Math.abs(q[0][1] - hipY) < 1e-6);
    return legs.reverse().map(([h, k, f]) => {
      const a1 = Math.atan2(k[0] - h[0], k[1] - h[1]), a2 = Math.atan2(f[0] - k[0], f[1] - k[1]);
      return [a1, a1 - a2];
    });
  };
  for (let i = 0; i < 48; i++) {
    const ph = i / 48 * 2 * Math.PI / 2.2, a = draw(ph), b = draw(ph + 0.005);
    a.forEach(([a1, bend], j) => out.push({ fwd: b[j][0] - a1, bend }));
  }
  return out;
}"""


def test_the_knee_bends_while_the_leg_swings_forward(site, browser):
    if not (site.games / "aitajuoksu").exists():
        shutil.copytree(ROOT / "games" / "aitajuoksu", site.games / "aitajuoksu")
        site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    legs = page.evaluate(STRIDE)
    fwd = [q["bend"] for q in legs if q["fwd"] > 0.001]
    back = [q["bend"] for q in legs if q["fwd"] < -0.001]
    assert len(fwd) > 20 and len(back) > 20
    # Swinging forward the knee is well bent; pushing back along the ground the leg is near straight.
    assert sum(fwd) / len(fwd) > sum(back) / len(back) + 0.4
    assert max(back) < 0.3
    assert errors == []
    ctx.close()

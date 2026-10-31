"""Pituushyppy v3: the legs run forwards, the knee bending as the leg swings forward (#170)."""

from conftest import ROOT

URL = "games/pituushyppy/v3/"

# Draws the run-up at many points of the stride with figure() replaced by a recorder, and returns
# for each leg how far its thigh moves forward next and how bent its knee is (radians).
STRIDE = """() => {
  const real = figure, out = [];
  let legs = null;
  figure = (hx, hy, s, p) => { legs = p.legs; return [hx, hy]; };
  const draw = ph => { drawJumper({ phase: 'run', v: 8, ph, x: 0, mine: false }, 40, () => 180, () => 400, '#f00', ''); return legs.map(l => l.slice()); };
  try {
    for (let i = 0; i < 48; i++) {
      const ph = i / 48 * 2 * Math.PI / 2.2, a = draw(ph), b = draw(ph + 0.005);
      a.forEach(([a1, a2], j) => out.push({ fwd: b[j][0] - a1, bend: a1 - a2 }));
    }
  } finally { figure = real; }
  return out;
}"""


def test_the_knee_bends_while_the_leg_swings_forward(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
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

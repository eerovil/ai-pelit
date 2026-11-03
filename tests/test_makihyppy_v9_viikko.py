"""Mäkihyppy v9: the ski-jumping week is half as long, two hills (#387).

A new week is Lahti and Kuopio, two rounds on each; a four-hill week saved by v8 goes on as its
four. The two-hill week has its own best ('viikko2-ennatys') and high-score list ('viikko2').
"""

import json

from conftest import ROOT

URL = "games/makihyppy/v9/"

HELPERS = """() => {
  window.gs = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
  // A clean jumper: springs just before the edge, steers four times a second, sets the telemark.
  window.strong = () => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    action();
    let next = 0, teleDone = false, tapped = false;
    for (let i = 0; i < 2000 && th.phase !== 'land'; i++) {
      if (th.phase === 'inrun' && !tapped && (IN - th.s) / Math.max(1, th.v) <= Math.max(-0.05, 0.06 + gs() * 0.03)) { action(); tapped = true; }
      if (th.phase === 'fly') {
        if (th.ft >= next) { next = th.ft + 0.15; th.inp = th.pos > 0.05 ? -1 : th.pos < -0.05 ? 1 : 0; }
        if (!teleDone && th.ft > 0.6 && timeToLand(th) <= 0.3) { action(); teleDone = true; }
      }
      step(1 / 60);
    }
    const r = th.res;
    th.t = 99; step(0.001);
    return r;
  };
}"""

SEEDED = """(() => {
  let s = 7 >>> 0;
  Math.random = () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
})();"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(SEEDED)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def stored(page, key):
    return page.evaluate(f"JSON.parse(localStorage.getItem('ai-pelit:makihyppy:{key}'))")


def queued(page):
    return page.evaluate("Object.keys(JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono') || '{}')).join()")


def test_a_new_week_is_two_hills_with_one_podium_at_its_end(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:makihyppy:viikko-ennatys', '2100.5')")
    page.reload()
    page.evaluate(HELPERS)
    assert "Mäkiviikko: kaksi mäkeä" in page.inner_text(".help")
    page.click("#go")
    assert page.evaluate("[K.comp.hills, roundText(K.comp)]") == [2, "Mäki 1/2 · kierros 1/2"]
    titles, jumps = [], []
    for n in range(4):
        assert page.evaluate("K.ending") is None, f"a podium before jump {n + 1}"
        page.wait_for_function("th && th.mine", timeout=3000)
        titles.append(page.evaluate("K.F.title(K.comp)"))
        jumps.append(page.evaluate("strong()")["p"])
    assert titles == [h + " " + str(i + 1) + "/2 · " + r for i, h in enumerate(["Lahti", "Kuopio"])
                      for r in ("1. kierros", "2. kierros")]
    assert page.evaluate("K.ending && K.ending.at") == 0
    me = page.evaluate("K.ending.res.find(r => r.p === 'me')")
    assert len(me["marks"]) == 4 and abs(me["best"] - sum(jumps)) < 0.11
    # Its own list and its own best; the four-hill best is left as it was.
    assert "makihyppy|viikko2" in queued(page) and "makihyppy|viikko," not in queued(page) + ","
    assert stored(page, "viikko2-ennatys") == me["best"]
    assert stored(page, "viikko-ennatys") == 2100.5
    page.evaluate("K.ending.t = 99; K.skip(); step(0.01)")
    assert "Paras viikko " + f"{me['best']:.1f}".replace(".", ",") + " p" in page.inner_text("#stats")
    assert page.errors == []


def test_a_four_hill_week_saved_by_v8_goes_on_as_four(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("strong()")
    # As v8 saved it: the same meet with four hills.
    kept = stored(page, "kesken")
    kept["hills"] = 4
    page.evaluate(f"localStorage.setItem('ai-pelit:makihyppy:kesken', {json.dumps(json.dumps(kept))})")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont").startswith("Jatka mäkiviikkoa (Mäki 1/4 · kierros ")
    page.click("#cont")
    page.evaluate("while (!K.ending) strong()")
    me = page.evaluate("K.ending.res.find(r => r.p === 'me')")
    assert page.evaluate("K.comp.hills") == 4 and len(me["marks"]) == 8
    assert page.evaluate("K.F.title(K.comp)").startswith("Ruka 4/4")
    # The four-hill list and best; the two-hill best is not touched.
    assert "makihyppy|viikko" in queued(page).split(",")
    assert stored(page, "viikko-ennatys") == me["best"]
    assert stored(page, "viikko2-ennatys") is None
    assert page.errors == []

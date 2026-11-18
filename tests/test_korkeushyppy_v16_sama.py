"""Korkeushyppy v15 draws the jump anew and jumps the same (#469, looks only).

`tests/fixtures/korkeushyppy_v14_hypyt.json` holds 180 jumps (take-off spot, speed, bar, arch and
kick times) as v14's own code judged them: cleared or not, the margin, and why it failed. v14's
code was run for it from `git show origin/main:games/korkeushyppy/v14/index.html` before v15
merged. v15's drawing adds points of its own; the bar must still meet the same body.
"""

import json

from conftest import ROOT

URL = "games/korkeushyppy/v15/"


def test_every_jump_ends_as_in_v14(site, context):
    want = json.loads((ROOT / "tests" / "fixtures" / "korkeushyppy_v14_hypyt.json").read_text())
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.wait_for_function("typeof jumpResult === 'function'")
    got = page.evaluate("""rows => rows.map(([d, v, bar, a, k]) => {
      const r = jumpResult(d, v, bar, a, k);
      return [d, v, bar, a, k, r.ok, +r.min.toFixed(6), r.why];
    })""", want)
    assert got == want

"""Areena in a phone-sized Chromium."""

import pytest

from conftest import ROOT


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_the_countdown_shows_3_2_1_then_fight(site, context, version):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/areena/{version}/")
    page.fill("#name", "Testi")
    page.click("#go")
    seen = []
    for _ in range(60):
        label = page.evaluate("state === 'count' ? countText() : state")
        if not seen or seen[-1] != label:
            seen.append(label)
        if label == "fight":
            break
        page.wait_for_timeout(100)
    assert seen == ["3", "2", "1", "TAISTELE!", "fight"]
    assert page.evaluate("me.name") == "Testi"


def test_v2_is_easier_than_v1_on_the_same_level(site, context):
    site.build(ROOT / "games")
    found = {}
    for version in ("v1", "v2"):
        page = context.new_page()
        page.goto(f"{site.url}games/areena/{version}/")
        page.evaluate("localStorage.setItem('ai-pelit:areena:taso', '3')")
        page.reload()
        page.click("#go")
        found[version] = page.evaluate("[foe.max, foe.speed]")
        page.close()
    assert found["v2"][0] < found["v1"][0]
    assert found["v2"][1] < found["v1"][1]

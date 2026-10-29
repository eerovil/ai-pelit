"""Areena in a phone-sized Chromium."""

from conftest import ROOT


def test_the_countdown_shows_3_2_1_then_fight(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/areena/v1/")
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

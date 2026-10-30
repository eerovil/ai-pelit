"""three.js, the shared 3D library in public/lib/ (#99), on a test-only game (tests/fixtures/three-demo.html)."""

import io
from pathlib import Path

import pytest
from PIL import Image

import build
from conftest import ROOT, game_page, make_game, wait_for_worker

DEMO = (Path(__file__).parent / "fixtures" / "three-demo.html").read_text()
BACKGROUND = (0x11, 0x22, 0x33)


def middle_pixel(page):
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    return img.getpixel((img.width // 2, img.height // 2))


def assert_draws_the_cube(page):
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    # Headless Chromium draws WebGL in software (SwiftShader); without it the page says so instead.
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    pixel = middle_pixel(page)
    assert max(abs(a - b) for a, b in zip(pixel, BACKGROUND)) > 40, pixel


def test_a_game_draws_3d_with_the_shared_three_js_also_offline(site, context):
    make_game(site.games, "kuutio", [DEMO])
    site.build()
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/kuutio/v1/")
    assert_draws_the_cube(page)
    assert errors == []
    context.set_offline(True)
    try:
        page.goto(f"{site.url}games/kuutio/v1/")
        assert_draws_the_cube(page)
    finally:
        context.set_offline(False)
    assert errors == []


def test_the_library_is_in_its_own_cache_that_outlives_builds(site, context):
    make_game(site.games, "kuutio", [DEMO])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/kuutio/v1/")
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    cached = page.evaluate(
        "caches.open('ai-pelit-lib').then(c => c.keys()).then(k => k.map(r => new URL(r.url).pathname))"
    )
    assert "/lib/three-r187/three.module.js" in cached
    assert "/lib/three-r187/three.core.js" in cached


def test_a_3d_game_still_plays_offline_after_a_site_update(site, context):
    make_game(site.games, "kuutio", [DEMO])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/kuutio/v1/")
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    first = page.evaluate("caches.keys().then(k => k.find(n => n.startsWith('ai-pelit-shell-')))")

    make_game(site.games, "toka", [game_page("toka")])
    site.build()
    page.goto(site.url)
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    # The new worker has taken over once the old shell cache is gone; the library's cache stays.
    page.wait_for_function(
        f"caches.keys().then(k => !k.includes({first!r}) && k.some(n => n.startsWith('ai-pelit-shell-')))",
        timeout=15000,
    )
    context.set_offline(True)
    try:
        page.goto(f"{site.url}games/kuutio/v1/")
        assert_draws_the_cube(page)
    finally:
        context.set_offline(False)


@pytest.mark.parametrize(
    "tag",
    [
        "<script type=\"module\">import * as THREE from '../../../lib/three-r999/three.module.js';</script>",
        '<script src="../../../lib/three-r999/three.module.js"></script>',
    ],
)
def test_the_build_refuses_a_version_loading_a_library_that_is_not_there(tmp_path, tag):
    make_game(tmp_path, "peli", [game_page("a").replace("<script></script>", tag)])
    with pytest.raises(build.GameError, match="lib/three-r999/three.module.js"):
        build.build_catalog(tmp_path)


def test_the_build_accepts_the_real_library(tmp_path):
    make_game(tmp_path, "kuutio", [DEMO])
    assert build.build_catalog(tmp_path)["games"][0]["slug"] == "kuutio"


def test_the_copy_is_three_js_r187_unchanged():
    lib = ROOT / "public" / "lib" / "three-r187"
    assert "const REVISION = '187';" in (lib / "three.core.js").read_text()
    assert "from './three.core.js'" in (lib / "three.module.js").read_text()
    assert "MIT" in (lib / "LICENSE").read_text()

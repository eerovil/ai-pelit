import json
import subprocess

import pytest

import build
from check_immutable import problems
from conftest import ROOT, game_page, make_game


def test_catalog_lists_every_game_newest_first(tmp_path):
    make_game(tmp_path, "vanha", [game_page("a")], dates=["2026-01-01"])
    make_game(tmp_path, "uusi", [game_page("a"), game_page("b")], dates=["2026-01-02", "2026-03-01"])
    catalog = build.build_catalog(tmp_path)
    assert [g["slug"] for g in catalog["games"]] == ["uusi", "vanha"]
    assert [v["n"] for v in catalog["games"][0]["versions"]] == [1, 2]


@pytest.mark.parametrize(
    "breakage, message",
    [
        (lambda d: (d / "v1" / "index.html").write_text("<html></html>"), "must include"),
        (lambda d: (d / "v3").mkdir(), "folders without a game.json version"),
        (lambda d: (d / "v2" / "index.html").unlink(), "v2/index.html is missing"),
    ],
)
def test_build_refuses_a_broken_game(tmp_path, breakage, message):
    make_game(tmp_path, "peli", [game_page("a"), game_page("b")])
    breakage(tmp_path / "peli")
    with pytest.raises(build.GameError, match=message):
        build.build_catalog(tmp_path)


def test_version_numbers_must_run_in_order(tmp_path):
    make_game(tmp_path, "peli", [game_page("a")])
    meta = json.loads((tmp_path / "peli" / "game.json").read_text())
    meta["versions"][0]["n"] = 2
    (tmp_path / "peli" / "game.json").write_text(json.dumps(meta))
    with pytest.raises(build.GameError, match="numbered"):
        build.build_catalog(tmp_path)


def test_the_real_games_build(tmp_path):
    catalog = build.build(ROOT / "games", ROOT / "public", tmp_path / "out")
    assert any(g["slug"] == "sormiskeitti" for g in catalog["games"])
    sw = (tmp_path / "out" / "sw.js").read_text()
    assert "__BUILD_ID__" not in sw


def test_build_id_changes_when_the_catalog_changes(tmp_path):
    games = tmp_path / "games"
    make_game(games, "yksi", [game_page("a")])
    build.build(games, ROOT / "public", tmp_path / "a")
    make_game(games, "kaksi", [game_page("b")])
    build.build(games, ROOT / "public", tmp_path / "b")
    assert (tmp_path / "a" / "sw.js").read_text() != (tmp_path / "b" / "sw.js").read_text()


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    make_game(tmp_path / "games", "peli", [game_page("a")])
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "v1")
    return tmp_path


def test_a_new_version_passes(repo):
    make_game(repo / "games", "peli", [game_page("a"), game_page("b")])
    make_game(repo / "games", "toinen", [game_page("c")])
    assert problems("main", cwd=str(repo)) == []


def test_editing_a_published_version_fails(repo):
    (repo / "games" / "peli" / "v1" / "index.html").write_text(game_page("muutettu"))
    assert "make a new version" in problems("main", cwd=str(repo))[0]


def test_rewriting_a_published_entry_fails(repo):
    meta = json.loads((repo / "games" / "peli" / "game.json").read_text())
    meta["versions"][0]["note"] = "toinen"
    (repo / "games" / "peli" / "game.json").write_text(json.dumps(meta))
    assert "only append" in problems("main", cwd=str(repo))[0]

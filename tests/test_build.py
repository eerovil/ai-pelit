import base64
import json
import subprocess

import pytest

import build
from check_immutable import problems
from conftest import ROOT, THUMB, game_page, make_game


def test_catalog_lists_every_game_newest_first(tmp_path):
    make_game(tmp_path, "vanha", [game_page("a")], dates=["2026-01-01"])
    make_game(tmp_path, "uusi", [game_page("a"), game_page("b")], dates=["2026-01-02", "2026-03-01"])
    catalog = build.build_catalog(tmp_path)
    assert [g["slug"] for g in catalog["games"]] == ["uusi", "vanha"]
    assert [v["n"] for v in catalog["games"][0]["versions"]] == [1, 2]


def test_a_group_gathers_its_games_and_is_listed_only_when_used(tmp_path):
    make_game(tmp_path, "yksin", [game_page("a")])
    assert build.build_catalog(tmp_path)["groups"] == []
    make_game(tmp_path, "hyppy", [game_page("a")], group="yleisurheilu")
    catalog = build.build_catalog(tmp_path)
    assert [g["slug"] for g in catalog["groups"]] == ["yleisurheilu"]
    assert {g["slug"]: g.get("group") for g in catalog["games"]} == {"yksin": None, "hyppy": "yleisurheilu"}


def test_an_unknown_group_or_a_game_named_like_a_group_is_refused(tmp_path):
    make_game(tmp_path, "hyppy", [game_page("a")], group="talviurheilu")
    with pytest.raises(build.GameError, match="unknown group"):
        build.build_catalog(tmp_path)
    (tmp_path / "hyppy" / "game.json").unlink()
    make_game(tmp_path, "hyppy", [game_page("a")])
    make_game(tmp_path, "yleisurheilu", [game_page("a")])
    with pytest.raises(build.GameError, match="group's address"):
        build.build_catalog(tmp_path)


def small_webp():
    # A real 3 x 4 WebP: the build reads the size from its header, without Pillow.
    return bytes.fromhex("524946463c000000574542505650382030000000f001009d012a0300040001402625a00274ba01f800044c0000feec70dffd26cf136789b3e491ffcec1b12ed780000000")


@pytest.mark.parametrize(
    "breakage, message",
    [
        (lambda d: (d / "v1" / "index.html").write_text("<html></html>"), "must include"),
        (lambda d: (d / "v3").mkdir(), "folders without a game.json version"),
        (lambda d: (d / "v2" / "index.html").unlink(), "v2/index.html is missing"),
        (lambda d: (d / "thumb.webp").unlink(), "thumb.webp is missing"),
        (lambda d: (d / "thumb.webp").write_bytes(b"ei kuva"), "not a WebP image"),
        (lambda d: (d / "thumb.webp").write_bytes(small_webp()), "found 3 x 4"),
        # The right size in its header, but cut short.
        (lambda d: (d / "thumb.webp").write_bytes(THUMB[:-4]), "not a WebP image"),
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


def test_the_site_is_ready_for_cloudflare_pages(tmp_path):
    build.build(ROOT / "games", ROOT / "public", tmp_path / "out")
    # Pages answers a missing file with 404.html; without one it sends the shelf with a 200.
    assert (tmp_path / "out" / "404.html").is_file()
    # Pages redirects index.html to './', and the service worker cannot answer a page load
    # with a redirected response, so it caches the shelf as './' only.
    assert "'index.html'" not in (tmp_path / "out" / "sw.js").read_text()


def test_build_id_changes_when_the_catalog_changes(tmp_path):
    games = tmp_path / "games"
    make_game(games, "yksi", [game_page("a")])
    build.build(games, ROOT / "public", tmp_path / "a")
    make_game(games, "kaksi", [game_page("b")])
    build.build(games, ROOT / "public", tmp_path / "b")
    assert (tmp_path / "a" / "sw.js").read_text() != (tmp_path / "b" / "sw.js").read_text()


def test_each_game_has_its_picture_under_a_name_that_changes_with_it(tmp_path):
    games = tmp_path / "games"
    make_game(games, "peli", [game_page("a")])
    first = build.build(games, ROOT / "public", tmp_path / "a")["games"][0]["thumb"]
    assert first.startswith("thumbs/peli-") and first.endswith(".webp")
    assert (tmp_path / "a" / first).read_bytes() == (games / "peli" / "thumb.webp").read_bytes()
    # Served from thumbs/ only: under games/ the service worker would keep an old one forever.
    assert not (tmp_path / "a" / "games" / "peli" / "thumb.webp").exists()
    # A version's own file of the same name is part of the game and is published.
    (games / "peli" / "v1" / "thumb.webp").write_bytes(b"pelin oma kuva")
    (games / "peli" / "thumb.webp").write_bytes(base64.b64decode("UklGRi4AAABXRUJQVlA4TCEAAAAvZ8F3AAdQniIXpf8BAkmb98+/7RH9z93/+3//7//9ZwwA"))
    assert (tmp_path / "a" / "games" / "peli" / "v1").is_dir()
    second = build.build(games, ROOT / "public", tmp_path / "b")
    assert (tmp_path / "b" / "games" / "peli" / "v1" / "thumb.webp").read_bytes() == b"pelin oma kuva"
    assert second["games"][0]["thumb"] != first


def test_make_thumb_crops_a_screenshot_to_3_by_4(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    import make_thumb

    Image.new("RGB", (360, 740), (10, 20, 30)).save(tmp_path / "shot.png")
    make_thumb.make_thumb(tmp_path / "shot.png", tmp_path / "thumb.webp")
    with Image.open(tmp_path / "thumb.webp") as img:
        assert (img.format, img.size) == ("WEBP", (360, 480))


def test_every_real_game_has_a_picture_that_opens():
    Image = pytest.importorskip("PIL.Image")
    for game_dir in (ROOT / "games").iterdir():
        assert build.webp_size((game_dir / "thumb.webp").read_bytes()) == (360, 480), game_dir.name
        with Image.open(game_dir / "thumb.webp") as img:
            img.load()
            assert (img.format, img.size) == ("WEBP", (360, 480)), game_dir.name


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


def withdraw_v2(repo):
    make_game(repo / "games", "peli", [game_page("a"), game_page("b")])
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "v2")
    import shutil
    shutil.rmtree(repo / "games" / "peli" / "v2")
    make_game(repo / "games", "peli", [game_page("a")])


def test_a_withdrawn_version_may_be_deleted_whole(repo):
    withdraw_v2(repo)
    assert problems("main", cwd=str(repo), withdrawn={"games/peli/v2/"}) == []
    # Without the owner's word it is still refused.
    assert any("make a new version" in p for p in problems("main", cwd=str(repo), withdrawn=set()))


def test_a_withdrawn_version_may_not_be_edited_and_others_stay_put(repo):
    make_game(repo / "games", "peli", [game_page("a"), game_page("b")])
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "v2")
    (repo / "games" / "peli" / "v2" / "index.html").write_text(game_page("muutettu"))
    assert "make a new version" in problems("main", cwd=str(repo), withdrawn={"games/peli/v2/"})[0]
    (repo / "games" / "peli" / "v2" / "index.html").write_text(game_page("b"))
    import shutil
    shutil.rmtree(repo / "games" / "peli" / "v1")
    assert any("v1 is published" in p for p in problems("main", cwd=str(repo), withdrawn={"games/peli/v2/"}))


def test_a_withdrawn_version_may_not_be_deleted_in_part(repo):
    make_game(repo / "games", "peli", [game_page("a"), game_page("b")])
    (repo / "games" / "peli" / "v2" / "muu.js").write_text("// toinen tiedosto")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "v2")
    (repo / "games" / "peli" / "v2" / "muu.js").unlink()  # one file gone, the folder stays
    assert "delete it whole" in problems("main", cwd=str(repo), withdrawn={"games/peli/v2/"})[0]


def test_a_withdrawn_folder_and_its_entry_go_together(repo):
    make_game(repo / "games", "peli", [game_page("a"), game_page("b")])
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "v2")
    import shutil
    shutil.rmtree(repo / "games" / "peli" / "v2")  # the folder goes, its game.json entry stays
    assert any("remove its entry too" in p for p in problems("main", cwd=str(repo), withdrawn={"games/peli/v2/"}))


def test_a_withdrawn_number_is_never_published_again(repo):
    make_game(repo / "games", "peli", [game_page("a"), game_page("b")])
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "v2")
    import shutil
    shutil.rmtree(repo / "games" / "peli" / "v2")
    make_game(repo / "games", "peli", [game_page("a")])
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "v2 withdrawn")
    # A later change tries a new game at the old v2 address.
    make_game(repo / "games", "peli", [game_page("a"), game_page("uusi")])
    assert any("never used again" in p for p in problems("main", cwd=str(repo), withdrawn={"games/peli/v2/"}))


def test_the_build_skips_a_withdrawn_number(tmp_path):
    import build
    make_game(tmp_path, "peli", [game_page("a"), game_page("b"), game_page("c")])
    import shutil
    meta = json.loads((tmp_path / "peli" / "game.json").read_text())
    shutil.move(tmp_path / "peli" / "v2", tmp_path / "peli" / "v-old")
    shutil.rmtree(tmp_path / "peli" / "v-old")
    meta["versions"] = [meta["versions"][0], meta["versions"][2]]
    (tmp_path / "peli" / "game.json").write_text(json.dumps(meta))
    # v1 then v3: fine only when v2 was withdrawn.
    assert [v["n"] for v in build.load_game(tmp_path / "peli", withdrawn={"games/peli/v2/"})["versions"]] == [1, 3]
    with pytest.raises(build.GameError):
        build.load_game(tmp_path / "peli", withdrawn=set())


def test_rewriting_a_published_entry_fails(repo):
    meta = json.loads((repo / "games" / "peli" / "game.json").read_text())
    meta["versions"][0]["note"] = "toinen"
    (repo / "games" / "peli" / "game.json").write_text(json.dumps(meta))
    assert "only append" in problems("main", cwd=str(repo))[0]


def add_lib(repo, folder, text):
    d = repo / "public" / "lib" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "kirjasto.js").write_text(text)


def test_a_published_library_file_never_changes(repo):
    add_lib(repo, "kirjasto-r1", "export const a = 1;\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "lib")
    add_lib(repo, "kirjasto-r1", "export const a = 2;\n")
    assert "library file never changes" in problems("main", cwd=str(repo))[0]
    (repo / "public" / "lib" / "kirjasto-r1" / "kirjasto.js").unlink()
    assert "library file never changes" in problems("main", cwd=str(repo))[0]


def test_a_new_library_release_is_a_new_folder(repo):
    add_lib(repo, "kirjasto-r1", "export const a = 1;\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "lib")
    add_lib(repo, "kirjasto-r2", "export const a = 2;\n")
    assert problems("main", cwd=str(repo)) == []

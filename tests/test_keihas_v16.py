"""keihas v11: no crowd noise, the loudest sounds quieter (#337)."""

from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401

URL = "games/keihas/v16"


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, URL)


from test_hiljaiset_aanet import cheer_is_quiet  # noqa: E402


def test_the_cheer_chime_is_quiet():
    # #355: Eero found the cheer's chime too loud.
    cheer_is_quiet("games/keihas/v16")

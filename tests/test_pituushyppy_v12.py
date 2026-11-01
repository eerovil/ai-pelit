"""pituushyppy v12: no crowd noise, the loudest sounds quieter (#337)."""

from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401

URL = "games/pituushyppy/v12"


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, URL)

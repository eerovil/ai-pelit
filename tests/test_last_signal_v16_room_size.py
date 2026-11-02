"""Last Signal v15 (and v16, #355) with friends, from a save that has been played (#375): once SISU has explored anything, the save
carries the chart and the cave as bitmaps of a fixed size, so the whole game the host sends a friend's phone is over
20 000 characters. The room dropped any message over 16 000 characters without a word, and the friend's phone said
"Odotetaan huoneen tekijää…" for good while the host played on."""

import base64
import json

from test_last_signal_v16 import room, save_with
from test_rooms_lib import MSG_MAX

# Every square of the chart (677 × 74) and of the cave map (21 600) seen, packed as world.js's pack() does.
CHART = base64.b64encode(bytes([255]) * -(-677 * 74 // 8)).decode()
CAVE = base64.b64encode(bytes([255]) * (21600 // 8)).decode()


def test_a_friend_joins_a_host_whose_chart_is_explored(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"), saves=[save_with(w12=1, w13=1, w15=1, chart=CHART, cave=CAVE), None])
    size = host.evaluate("JSON.stringify({ t: 's', s: G.s, to: 'x'.repeat(16) }).length")
    assert size > 16000
    assert size * 2 < MSG_MAX  # room to grow as the game goes on
    assert aino.evaluate("G.s.chart") == host.evaluate("G.s.chart")
    assert not host.errors and not aino.errors


def test_a_friend_who_reloads_gets_the_explored_game_again(site, browser):
    """The host sends the whole game again to a phone that comes back (`on('hello')`), just as big."""
    host, aino = room(site, browser, names=("Eero", "Aino"), saves=[save_with(w12=1, w13=1, w15=1, chart=CHART, cave=CAVE), None])
    aino.reload()
    aino.wait_for_function("window.drawn === true")
    aino.wait_for_function("G.s && G.mode !== 'wait' && G.mode !== 'menu'")
    assert aino.evaluate("G.s.chart") == host.evaluate("G.s.chart")
    assert not host.errors and not aino.errors

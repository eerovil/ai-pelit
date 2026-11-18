"""Games the owner removed from the site whole, each with the issue that decided it.

A published game is never removed (rule 1, #346), except one named here. `check_immutable.py`
lets such a game's folders and game.json go, but only all of them at once. `build.py` lists the
slugs in catalog.json's `removed` and sends the game's addresses to the shelf in `_redirects`;
`public/sw.js` reads that list to drop the game's cached files and send a saved shortcut to the
shelf. A slug here may not come back as a game: phones would keep sending it to the shelf.
"""

REMOVED = {
    "ottelu": "#469",  # Ottelu, the athletics match: "Poistetaan koko "ottelu" peli tässä" (Eero)
}

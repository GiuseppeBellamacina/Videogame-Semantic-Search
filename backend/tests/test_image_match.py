"""Ranking of the Wikipedia pages offered as a cover (no network): uv run --with pytest python -m pytest backend/tests"""

from backend.services.image_store import match

NAME = "Grand Theft Auto: San Andreas \u2013 The Definitive Edition"
# the pages Wikipedia returns for this game, in its own order
HITS = [
    "Grand Theft Auto: The Trilogy \u2013 The Definitive Edition",
    "Grand Theft Auto III",
    "Grand Theft Auto: San Andreas",
    "Grand Theft Auto",
    "Grand Theft Auto Online",
]


def _ranked(name: str, titles: list[str]) -> list[str]:
    scored = [(not match(name, t)[0], -match(name, t)[1], i, t) for i, t in enumerate(titles)]
    return [t for *_, t in sorted(scored)]


def test_the_right_game_comes_before_its_sibling():
    ranked = _ranked(NAME, HITS)
    assert ranked.index("Grand Theft Auto: San Andreas") < ranked.index("Grand Theft Auto III")
    assert match(NAME, "Grand Theft Auto III")[0] is False  # a different game is not "related"


def test_exact_and_dated_titles_match():
    assert match("God of War", "God of War (2018 video game)")[0]
    assert match("Doom", "Doom (video game)")[0]
    assert not match("Doom", "Mario Kart")[0]


def test_other_scripts_fall_back_to_containment():
    assert match("\u30bc\u30eb\u30c0\u306e\u4f1d\u8aac", "\u30bc\u30eb\u30c0\u306e\u4f1d\u8aac")[0]

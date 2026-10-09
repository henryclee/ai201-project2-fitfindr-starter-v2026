"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    # {
    #     # A user with nothing saved. One of unit 4's three failure modes.
    #     "name": "empty wardrobe",
    #     "query": "denim jacket under $50",
    #     "wardrobe": "empty",
    #     "criterion": None,
    # },
    {
        # A query that matches at least one listing. Criterion 3 - state.
        "name": "selected item is correctly passed to suggest_outfit",
        "query": "vintage blue jeans under $40",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # A query that matches at least one listing. Criterion 4 - fit card.
        "name": "fit card contains the item's price",
        "query": "oversized sweatshirt under $25",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # A query with a size should be able to match. Criterion 5 - search listings.
        "name": "query with a size successfully matches",
        "query": "small denim jacket under $50",
        "wardrobe": "example",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems

"""
What to say when the search came back empty.

The branch itself is one line and it lives in `agent.py::run_agent`, where the
loop can be read. This file is everything behind it: working out *why* nothing
matched, which is the part the user actually asked for. "No results" is not a
message — the brief is explicit that the error has to name what to change, and
you can't name it without finding out which constraint did the damage.

So re-run the search with one constraint lifted at a time and read the answer
off the results:

    size_probe        description + size, no ceiling → still empty = the size is the wall
    price_probe       description + ceiling, no size → still empty = the ceiling is the wall
    description_only  the words alone                → what exists at all, and the evidence
                                                       the message quotes back: real sizes,
                                                       the real cheapest price

`search_listings()` makes no model call, so three probes cost a file read each —
no quota, no rate limit, no extra model latency. They call `tools.search_listings`
directly rather than through `mcp_client.call_tool` on purpose: the MCP route
spawns a fresh Python process and a handshake per call, and paying for three of
those on a path that is already a dead end buys nothing. The happy path in
`run_agent()` stays on MCP — that's the Milestone 1 seam, and it stays visible.

Split out of the loop for one reason: a diagnosis you can only reach by spending
a model call is not one you will ever re-run. Here it is a terminal command.

    python no_results.py    every empty case, its cause, and its message
"""

from tools import search_listings

# How many real sizes to name in a "try one of those" hint. Six keeps the message
# a sentence when the catalog has forty of them.
SIZE_HINT_LIMIT = 6


# ── reading results ───────────────────────────────────────────────────────────


def _tried(description: str, size: str | None, max_price: float | None) -> str:
    """The search as the user would repeat it: 'tee' in size M under $30."""
    tried = f"'{description}'"
    if size:
        tried += f" in size {size}"
    if max_price is not None:
        tried += f" under ${max_price:g}"
    return tried


def _sizes(items: list[dict]) -> list[str]:
    """The sizes actually on file, sorted and deduped."""
    return sorted({str(item["size"]) for item in items if item.get("size")})


def _cheapest(items: list[dict]) -> dict | None:
    """
    The lowest-priced listing, or None when none carry a usable price.

    The filter has to skip non-numeric prices rather than let min() compare None
    with a float — one listing missing a price would otherwise turn a helpful
    message into a TypeError on the way to telling the user there were no
    results, which is the exact failure this whole module exists to avoid.
    """
    priced = [item for item in items if isinstance(item.get("price"), (int, float))]
    return min(priced, key=lambda item: item["price"]) if priced else None


# Public alias. relax.py writes a user-facing sentence out of the same reading
# diagnose() uses; one definition keeps the two honest about the same numbers.
sizes_on_file = _sizes


# ── the probes ────────────────────────────────────────────────────────────────


def _probe(description: str, size: str | None, max_price: float | None) -> dict:
    """
    The three searches that separate "we don't have that" from "we don't have
    that *at that size*" and "*at that price*".

    Returns:
        {"size_probe", "price_probe", "description_only"}, each a list of
        listings. A probe that can't be run — no size given, no ceiling given —
        comes back as an empty list, which is what `_hints` expects.
    """
    return {
        "size_probe": (
            search_listings(description=description, size=size, max_price=None)
            if size
            else []
        ),
        "price_probe": (
            search_listings(description=description, max_price=max_price)
            if max_price is not None
            else []
        ),
        "description_only": search_listings(description=description),
    }


# ── the hints ─────────────────────────────────────────────────────────────────


def _hints(probes: dict, description: str, size: str | None, max_price) -> list:
    """
    What to change, each one tagged with the constraint that caused it.

    A hint is only written when a probe proved it, so the message quotes the
    data instead of guessing. Both a size hint and a price hint can fire at once
    — two constraints can both be impossible.

    Returns:
        A list of (cause, hint) pairs in reading order, empty when every probe
        found something. `diagnose` turns that empty case into "unknown".
    """
    size_probe = probes["size_probe"]
    price_probe = probes["price_probe"]
    found = probes["description_only"]

    if not found:
        return [
            (
                "no_match",
                f"nothing in the listings matches '{description}' at all, whatever "
                "the size or price — loosen the wording (try 'tee' or 'top' on its "
                "own) and keep the rest as it is",
            )
        ]

    closest = _cheapest(found)
    sizes_on_file = _sizes(found)
    hints = []

    if size and not size_probe:
        hints.append(
            (
                "size",
                f"nothing comes in size {size} — '{description}' does exist in "
                f"{', '.join(sizes_on_file[:SIZE_HINT_LIMIT]) or 'other sizes'}, so try "
                "one of those or leave the size out",
            )
        )

    if max_price is not None and not price_probe:
        if closest:
            hints.append(
                (
                    "price",
                    f"nothing is under ${max_price:g} — the cheapest match is "
                    f"{closest['title']} at ${closest['price']:g} on "
                    f"{closest.get('platform', 'the listings')}, so raise max_price to about "
                    f"${closest['price']:g}",
                )
            )
        else:
            hints.append(("price", f"nothing is under ${max_price:g}"))

    if not hints and size and max_price is not None and size_probe and price_probe:
        # Each half is fine alone and impossible together — say so, with the
        # price of one and the sizes of the other.
        cheapest_in_size = _cheapest(size_probe)
        if cheapest_in_size:
            hints.append(
                (
                    "size_and_price",
                    f"size {size} exists but starts at ${cheapest_in_size['price']:g} "
                    f"({cheapest_in_size['title']}), and under ${max_price:g} it only "
                    f"comes in {', '.join(_sizes(price_probe)[:SIZE_HINT_LIMIT]) or 'other sizes'} "
                    "— you'll have to relax one of the two",
                )
            )

    return hints


def _message(tried: str, hints: list) -> str:
    """Join the hints into one sentence, first letter capitalised."""
    tidy = [hints[0][1][0].upper() + hints[0][1][1:]] + [hint[1] for hint in hints[1:]]
    return f"No listings matched {tried}. " + ". Also, ".join(tidy) + "."


# ── the public call ───────────────────────────────────────────────────────────


def diagnose(
    description: str, size: str | None = None, max_price: float | None = None
) -> dict:
    """
    Why a search for `description` (+ size + ceiling) returned nothing, in words
    the user can act on.

    Args:
        description: the keywords that were searched — required, same as
                     search_listings'.
        size:        the size that was filtered on, or None.
        max_price:   the ceiling that was filtered on, or None.

    Returns:
        A dict with:
            "cause":          "no_match" | "size" | "price" | "size_and_price"
                              | "unknown" — the constraint that did it, taken from
                              the first hint a probe proved
            "message":        the sentence for session["error"]
            "tried":          what was searched for, as the user would repeat it
            "probes":         how many listings each probe found, e.g.
                              {"size": 0, "price": 4, "description": 6}
            "closest":        the cheapest description-only match, or None
            "sizes_on_file":  every size that description comes in

        **Never raises, and never returns an empty message.** When all three
        probes found something — which the search that led here says cannot
        happen — cause is "unknown" and the message still names both constraints
        worth dropping.

    Makes no model call: three reads of the listings data, nothing more.
    """
    probes = _probe(description, size, max_price)
    hints = _hints(probes, description, size, max_price)

    if not hints:
        # Every probe came back with something, which the search above says it
        # shouldn't. Fall back rather than hand back an empty error.
        hints = [
            (
                "unknown",
                "the match is close but not exact — try dropping either the size or "
                "the price limit",
            )
        ]

    found = probes["description_only"]
    tried = _tried(description, size, max_price)

    return {
        "cause": hints[0][0],
        "message": _message(tried, hints),
        "tried": tried,
        "probes": {
            "size": len(probes["size_probe"]),
            "price": len(probes["price_probe"]),
            "description": len(found),
        },
        "closest": _cheapest(found),
        "sizes_on_file": _sizes(found),
    }


def explain(
    description: str, size: str | None = None, max_price: float | None = None
) -> str:
    """Just the sentence — `diagnose()["message"]`, for callers that don't want the why."""
    return diagnose(description, size=size, max_price=max_price)["message"]


# ── running it directly ───────────────────────────────────────────────────────

# Each case is a search the data can't satisfy for a different reason, which is
# the point: `python no_results.py` costs no model calls, so a hint can be
# reworded and re-read in seconds.

EMPTY_CASES = [
    ("designer ballgown", "XXS", 5.0),      # nothing like it exists
    ("vintage graphic tee", "XXS", None),   # exists, not in that size
    ("vintage graphic tee", None, 1.0),     # exists, not at that price
    ("vintage graphic tee", "XXS", 1.0),    # each half fine, not together
    ("quantum flux capacitor", None, None),  # not clothing
]


if __name__ == "__main__":
    for description, size, max_price in EMPTY_CASES:
        diagnosis = diagnose(description, size=size, max_price=max_price)
        print(diagnosis["tried"])
        print(f"  cause:  {diagnosis['cause']}  probes: {diagnosis['probes']}")
        print(f"  {diagnosis['message']}\n")

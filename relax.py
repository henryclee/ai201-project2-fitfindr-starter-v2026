"""
relax.py — Stretch Feature 2: retry a size-blocked search without the size filter.

The rule this module encodes, in one sentence: when a search that had a size filter
came back empty, ask for it again without the size — once — and say out loud that
that is what happened.

Two things this module deliberately does not do:
  * It does not call the search. The agent loop owns MCP calls, so the retry shows up
    in the trace as a tool call and the tool's contract stays exactly as published.
  * It does not drop the price ceiling. The brief says "without the size filter", and
    a run that loosened two constraints at once could not be described honestly.

Every function here is pure, so the failure modes are testable without a model or the
agent loop — see test_relaxed_retry.py.
"""

import config
from no_results import sizes_on_file


def should_attempt(size) -> bool:
    """
    Retry without the size? Yes whenever a size was actually applied and the feature
    is on.

    Deliberately not gated on diagnose()'s probes: an attempted retry that comes back
    empty tells the user something the diagnosis alone does not — that the size was
    not the only thing stopping it, proven rather than inferred. The cost is one extra
    MCP spawn (~0.3-1s) on searches that were always going to fail.

    The size-is-None guard is load-bearing. Without it every empty search re-runs the
    identical query and gets the identical nothing.
    """
    return bool(size) and config.RETRY_WITHOUT_SIZE


def sizes_found(items: list[dict]) -> list[str]:
    """The sizes actually on offer, deduped and sorted — for the disclosure."""
    return sizes_on_file(items)


def note(requested_size, item: dict | None, found: int) -> str:
    """
    The sentence that goes to the user when the retry worked.

    It has to carry three things or it is not a disclosure: the size that was dropped,
    the size the item actually is, and the fact that they differ. Naming only the count
    would let somebody read the result as a match.

    It is built from the item that got selected, not from the whole relaxed list,
    because a relaxed search surfaces accessories too — 'vintage graphic tee' without
    a size returns a belt and a bucket hat at ranks 6 and 7, and a six-size list of
    them would bury the one number that matters. The full size spread still goes in
    the session as evidence (see agent.py's session["relaxed"]); it just does not go
    in this sentence.
    """
    if not requested_size or not item:
        return ""

    price = item.get("price")
    price_text = f"${price:g}" if isinstance(price, (int, float)) else "?"
    plural = "es" if found != 1 else ""

    return (
        f"Nothing on FitFindr comes in size {requested_size}, so I dropped the size "
        f"filter and found {found} match{plural}. The pick below is size "
        f"{item.get('size')} — {item.get('title')}, {price_text} on "
        f"{item.get('platform')}. It is not the size you asked for."
    )


def tried_anyway() -> str:
    """
    The sentence that goes on the end of the error when the retry did not help.

    It adds exactly one fact, because that is all it owns: the agent performed the
    search this message has been telling the user to perform. diagnose() already names
    the wall — measured, for these three cases:

        size       "…does exist in L, M, … so try one of those or leave the size out."
        size+price "…nothing is under $1 — the cheapest match is Leather Belt at $12
                    on thredUp, so raise max_price to about $12."
        no_match   "…matches 'designer ballgown' at all, whatever the size or price."

    So this sentence does NOT re-state a price or a size. It says the size was tried,
    and it failed, which turns the diagnosis from a guess into something proven — and
    stops the reader going off to do the retry themselves and get the same nothing.
    """
    return (
        "(I searched again without the size filter and still found nothing, so the "
        "size is not what is blocking this — everything above still stands.)"
    )


def call_failed_note() -> str:
    """
    The sentence for the one failure mode tried_anyway() must not cover: the retry call
    itself raised, so no relaxed search ever happened.

    The difference matters. "Retried and found nothing" is a finding about the data;
    this is a finding about our own plumbing, and reporting it as the first would tell
    the user their size does not exist when all we know is that a subprocess died. The
    diagnosis above this line was computed by direct tool calls and is still sound.
    """
    return (
        "(I tried searching again without the size filter and that call failed, so "
        "nothing here was loosened — the size you asked for is still the one in effect.)"
    )

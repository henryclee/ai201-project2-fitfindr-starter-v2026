"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import json
import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card, compare_price
from generate import ModelUnavailable, generate


# ── session state ─────────────────────────────────────────────────────────────


def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,  # what the user typed
        "parsed": {},  # description / size / max_price you pulled out of it
        "search_results": [],  # everything search_listings returned
        "selected_item": None,  # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,  # the user's wardrobe
        "outfit_suggestion": None,  # what suggest_outfit returned
        "fit_card": None,  # what create_fit_card returned
        "error": None,  # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.
    """

    #   1. Start a session with new_session().
    session = new_session(query, wardrobe)

    #   2. Count the times round the loop, and call trace.check_iterations(count)
    #      on each one before you go again. It raises when the count passes
    #      MAX_ITERATIONS in config.py — see trace.py.

    count = 0

    #   3. Parse the query into a description, a size, and a max_price. Regex,
    #      string splitting, or asking the model are all fine — say which you
    #      chose in your README. Put the result in session["parsed"].

    parse_query = (
        f"Parse the following query for a description, a size, and a max_price: {query}."
        "Return a JSON object with keys 'description', 'size', and 'max_price'. If any of these are "
        "not present in the query, set their value to null."
    )

    description = size = max_price = None

    while True:
        count += 1
        trace.check_iterations(count)

        raw_result = generate(parse_query)
        # The model often wraps JSON in a ```json ... ``` fence — strip it.
        cleaned_result = re.sub(r"^```(?:json)?|```$", "", raw_result.strip()).strip()

        try:
            parsed_result = json.loads(cleaned_result)
            description = parsed_result["description"]
            size = parsed_result["size"]
            max_price = parsed_result["max_price"]

        except (json.JSONDecodeError, KeyError, TypeError):
            continue  # If the generated result isn't the JSON shape we asked for, try again

        break

    # Normalise what came back before any tool sees it. The model sometimes sends
    # max_price back as "30" or "$30", and `"30"` compared against a listing price
    # raises a TypeError inside search_listings instead of returning an empty list —
    # a crash here would swallow the message the branch below exists to write.
    if isinstance(max_price, str):
        found_price = re.search(r"\d+(?:\.\d+)?", max_price)
        max_price = float(found_price.group()) if found_price else None
    elif max_price is not None:
        try:
            max_price = float(max_price)
        except (TypeError, ValueError):
            max_price = None

    size = str(size).strip() if size is not None and str(size).strip() else None
    description = str(description).strip() if description is not None else None

    session["parsed"]["description"] = description
    session["parsed"]["size"] = size
    session["parsed"]["max_price"] = max_price

    #   4. Call search_listings() with what you parsed.
    #      Put the results in session["search_results"].

    # A description is the one thing search_listings cannot run without, and the
    # model is allowed to answer null. Catch that before the call, so it reads as
    # a message to the user instead of an AttributeError out of the tool.
    if not description:
        session["error"] = (
            "I couldn't read a description out of that query, so there was nothing "
            "to search for. Name the item, e.g. 'vintage graphic tee under $30'."
        )
        return session

    search_results = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )
    session["search_results"] = search_results

    #      ⚠️ THIS IS THE BRANCH. If nothing came back:
    #           - put a message in session["error"] saying what the user could
    #             change — "No results" is not that message
    #           - return the session
    #           - do NOT call suggest_outfit with nothing
    #
    #      Saying *what* to change means finding out which constraint did it, so
    #      instead of guessing we re-run the search with one constraint lifted at
    #      a time and read the answer off the results. search_listings() makes no
    #      model call, so the probes cost a file read each — no quota, no rate
    #      limit, no extra model latency.

    if len(search_results) == 0:
        tried = f"'{description}'"
        if size:
            tried += f" in size {size}"
        if max_price is not None:
            tried += f" under ${max_price:g}"

        # Probe 1 — lift the price ceiling. Still empty means price was innocent
        # and the size is what nothing exists in.
        size_probe = (
            search_listings(description=description, size=size, max_price=None)
            if size
            else []
        )
        # Probe 2 — lift the size. Still empty means the ceiling is too low.
        price_probe = (
            search_listings(description=description, max_price=max_price)
            if max_price is not None
            else []
        )
        # Probe 3 — lift both. What the words alone can find, and the evidence
        # (real sizes, real prices) the message quotes back at the user.
        description_only = search_listings(description=description)

        priced = [
            item for item in description_only if isinstance(item.get("price"), (int, float))
        ]
        closest = min(priced, key=lambda item: item["price"]) if priced else None
        sizes_on_file = sorted(
            {str(item["size"]) for item in description_only if item.get("size")}
        )

        hints = []

        if not description_only:
            hints.append(
                f"nothing in the listings matches '{description}' at all, whatever "
                "the size or price — loosen the wording (try 'tee' or 'top' on its "
                "own) and keep the rest as it is"
            )
        else:
            if size and not size_probe:
                hints.append(
                    f"nothing comes in size {size} — '{description}' does exist in "
                    f"{', '.join(sizes_on_file[:6]) or 'other sizes'}, so try one of those or leave "
                    "the size out"
                )

            if max_price is not None and not price_probe:
                if closest:
                    hints.append(
                        f"nothing is under ${max_price:g} — the cheapest match is "
                        f"{closest['title']} at ${closest['price']:g} on "
                        f"{closest.get('platform', 'the listings')}, so raise max_price to about "
                        f"${closest['price']:g}"
                    )
                else:
                    hints.append(f"nothing is under ${max_price:g}")

            if not hints and size and max_price is not None and size_probe and price_probe:
                # Each half is fine alone and impossible together — say so, with
                # the price of one and the sizes of the other.
                cheapest_in_size = min(size_probe, key=lambda item: item["price"])
                sizes_in_budget = sorted(
                    {str(item["size"]) for item in price_probe if item.get("size")}
                )
                hints.append(
                    f"size {size} exists but starts at ${cheapest_in_size['price']:g} "
                    f"({cheapest_in_size['title']}), and under ${max_price:g} it only "
                    f"comes in {', '.join(sizes_in_budget[:6]) or 'other sizes'} — you'll have to relax "
                    "one of the two"
                )

        if not hints:
            # Every probe came back with something, which the search above says
            # it shouldn't. Fall back rather than hand back an empty error.
            hints.append(
                "the match is close but not exact — try dropping either the size or "
                "the price limit"
            )

        tidy = [hints[0][0].upper() + hints[0][1:]] + hints[1:]
        session["error"] = f"No listings matched {tried}. " + ". Also, ".join(tidy) + "."
        return session

    #   5. Choose an item — the first result is fine. Put it in
    #      session["selected_item"].

    #   Stretch tool call -- We can use the compare_price tool to try to filter out
    #   "overpriced" items. If all of the items are overpriced, return the best match

    for item in search_results:
        price_comparison = compare_price(new_item=item)
        if price_comparison["verdict"] != "overpriced":
            session["selected_item"] = item
            break

    if not session["selected_item"]:
        session["selected_item"] = search_results[0]

    #   6. Call suggest_outfit() with the selected item and the wardrobe.
    #      Put the result in session["outfit_suggestion"].

    outfit_suggestion = suggest_outfit(
        new_item=session["selected_item"], wardrobe=wardrobe
    )
    session["outfit_suggestion"] = outfit_suggestion

    #   7. Call create_fit_card() with the outfit and the item.
    #      Put the result in session["fit_card"].

    fit_card = create_fit_card(
        outfit=session["outfit_suggestion"], new_item=session["selected_item"]
    )
    session["fit_card"] = fit_card

    #   8. Return the session.

    # ─────────────────────────────────────────────────────────────────────
    # IN UNIT 4 you come back and add two things:
    #
    #   • Trace calls. One per step. `trace.step("search_listings",
    #     inputs=..., returned=...)` — see trace.py. Your README needs the
    #     output.
    #
    #   • A handler for ModelUnavailable, so a bad key produces a message
    #     rather than a stack trace. The import is already at the top of
    #     this file.

    return session


# ── running it directly ───────────────────────────────────────────────────────


def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(
        f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}"
    )
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(
        run_agent(
            query="looking for a vintage graphic tee under $30",
            wardrobe=get_example_wardrobe(),
        )
    )

    print("\n=== A query it can't ===")
    _show(
        run_agent(
            query="designer ballgown size XXS under $5",
            wardrobe=get_example_wardrobe(),
        )
    )

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )

"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    max_listings = config.SEARCH_RESULT_LIMIT

    listings = load_listings()
    filtered_price = [
        listing
        for listing in listings
        if max_price is None or listing["price"] <= max_price
    ]
    filtered_size = [
        listing
        for listing in filtered_price
        if size is None or (listing["size"] and size.lower() in listing["size"].lower())
    ]

    description_keywords = set(description.lower().split())

    def score_listing(listing) -> int:
        listing_keywords = set()
        keys = ["title", "description", "style_tags", "colors", "brand"]
        for key in keys:
            value = listing.get(key)
            if isinstance(value, str):
                listing_keywords.update(value.lower().split())
            elif isinstance(value, list):
                for item in value:
                    listing_keywords.update(item.lower().split())
            score = len(description_keywords.intersection(listing_keywords))
        return score

    scored_listings = [(listing, score_listing(listing)) for listing in filtered_size]
    scored_listings.sort(key=lambda x: x[1], reverse=True)
    top_listings = [
        listing for listing, score in scored_listings[:max_listings] if score > 0
    ]
    return top_listings


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """

    EMPTY_WARDROBE_PROMPT = (
        "You are a fashion stylist. A user has just thrifted the following item:\n"
        f"{new_item}\n"
        "They have no other items in their wardrobe. Give them general styling advice "
        "for using this item in a single outfit."
    )

    if not wardrobe.get("items"):
        return generate(EMPTY_WARDROBE_PROMPT)

    NON_EMPTY_WARDROBE_PROMPT = (
        "You are a fashion stylist. A user has just thrifted the following item:\n"
        f"{new_item}\n"
        "They have the following items in their wardrobe:\n"
        f"{wardrobe['items']}\n"
        "Suggest a single outfit that combines the new item with pieces from their wardrobe."
    )

    return generate(NON_EMPTY_WARDROBE_PROMPT)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """

    EMPTY_OUTFIT_PROMPT = (
        "You are a fashion stylist. A user has just thrifted the following item:\n"
        f"{new_item}\n"
        "They have no outfit suggestions. Write a two-to-four sentence caption "
        "that describes the item and its price and platform, that could be used "
        "as a social media post with a picture of the item."
    )

    OUTFIT_PROMPT = (
        "You are a fashion stylist. A user has just thrifted the following item:\n"
        f"{new_item}\n"
        "They have the following outfit suggestion:\n"
        f"{outfit}\n"
        "Write a two-to-four sentence caption that describes the item and its price "
        "and platform, that could be used as a social media post with a picture of the user "
        "wearing it."
    )

    if not outfit:
        return generate(EMPTY_OUTFIT_PROMPT)

    return generate(OUTFIT_PROMPT)


# ── Tool 4: Stretch Feature - compare_price ───────────────────────────────────────────────────


def compare_price(new_item: dict) -> dict:
    """
    Compare the price of the new item with similar items in the listings.

    Args:
        new_item: a listing dict — the item the user is considering.

    Returns:
        A dict containing the comparison results, including:
        "item_id":          str,
        "price":            float,
        "comparable_count": int,
        "median_price":     float | None,   # None when comparables are too thin
        "delta":            float | None,   # price - median, negative = cheaper
        "delta_pct":        float | None,
        "verdict":          "good_deal" | "fair" | "overpriced" | "unknown",
        "comparables":      [ {"id","title","price","platform"}, ... ]  # ≤5, cheapest first

    If comparable_count < 3, returns verdict "unknown", median_price /
    delta / delta_pct all None, comparables []

    """
    listings = load_listings()

    # Filter listings to find comparables based on category and style_tags
    comparable_listings = [
        listing
        for listing in listings
        if listing["category"] == new_item["category"]
        and listing["size"] == new_item["size"]
        and any(tag in new_item["style_tags"] for tag in listing["style_tags"])
    ]

    comparable_count = len(comparable_listings)

    if comparable_count < 3:
        return {
            "item_id": new_item["id"],
            "price": new_item["price"],
            "comparable_count": comparable_count,
            "median_price": None,
            "delta": None,
            "delta_pct": None,
            "verdict": "unknown",
            "comparables": [],
        }

    # Sort comparables by price and calculate median
    comparable_listings.sort(key=lambda x: x["price"])
    median_price = (
        (
            comparable_listings[comparable_count // 2]["price"]
            + comparable_listings[(comparable_count - 1) // 2]["price"]
        )
        / 2
        if comparable_count % 2 == 0
        else comparable_listings[comparable_count // 2]["price"]
    )

    delta = new_item["price"] - median_price
    delta_pct = (delta / max(median_price, 0.01)) * 100  # Avoid division by zero

    # Determine verdict based on delta percentage
    if delta_pct < -10:
        verdict = "good_deal"
    elif -10 <= delta_pct <= 10:
        verdict = "fair"
    else:
        verdict = "overpriced"

    # Prepare comparables list with limited fields and sorted by price
    comparables = [
        {
            "id": listing["id"],
            "title": listing["title"],
            "price": listing["price"],
            "platform": listing.get("platform"),
        }
        for listing in comparable_listings[:5]
    ]

    return {
        "item_id": new_item["id"],
        "price": new_item["price"],
        "comparable_count": comparable_count,
        "median_price": median_price,
        "delta": delta,
        "delta_pct": delta_pct,
        "verdict": verdict,
        "comparables": comparables,
    }

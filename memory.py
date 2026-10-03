"""
Style memory — the agent remembers a wardrobe between runs.

Everything else in this repo forgets everything when the process exits. The
session dict is the record of one run and it dies with the run, so a second
`python app.py ask` starts with exactly the wardrobe it started with the first
time. This file is the part that survives: a JSON file on disk that a run can
read at the start and add its purchase to at the end.

Three rules hold it together:

  • **The file is never trusted.** A half-written or hand-edited file must read
    as an empty wardrobe, not raise. Same reason `generate._cache_read` swallows
    a bad cache entry: losing one answer is cheap, crashing the run is not.
  • **Writes are atomic.** `_write` writes a temp file and renames it. A rename
    is the one filesystem operation that can't land half-finished, so Ctrl-C
    during a save leaves either the old wardrobe or the new one.
  • **One item, one entry.** Purchases are keyed on the listing id, so running
    the same query twice doesn't fill the wardrobe with the same baby tee.

The storage format is the wardrobe format from data/wardrobe_schema.json —
{id, name, category, colors, style_tags, notes} — so a remembered item goes
into `suggest_outfit()` with no translating. A listing maps onto it cleanly: the
two share the same five `category` values and the same `colors` / `style_tags`
shape, and nothing else in a listing is worth carrying except where it came from
and what it cost, which go in `notes`.

What gets stored is the purchases, not the whole closet: `merge_wardrobes()`
joins them to the wardrobe a run was handed, so shopping adds to what the agent
knows about you instead of standing in for it.

    python memory.py        show what's remembered, and from where
"""

import json
import os
from datetime import datetime, timezone

import config

MEMORY_PATH = config.DATA_DIR / config.MEMORY_FILENAME


# ── reading ─────────────────────────────────────────────────────────────────────


def load_memory() -> dict:
    """
    The remembered wardrobe, in the shape `suggest_outfit()` expects.

    Returns:
        A dict with an "items" key holding the remembered wardrobe items, in the
        order they were bought.

        **Returns {"items": []} when there is nothing to remember** — the file
        is missing (a first run), unreadable, not JSON, or has no usable items.
        It never raises, because an empty wardrobe is a state the agent already
        knows how to handle and a crash is one it doesn't.
    """
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"items": []}

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return {"items": []}

    return {"items": [item for item in items if isinstance(item, dict)]}


def count() -> int:
    """How many items are remembered. For the one-line status in the CLI."""
    return len(load_memory()["items"])


def merge_wardrobes(wardrobe: dict, remembered: list) -> dict:
    """
    What the user owns now: the wardrobe this run was handed, plus what memory
    kept from the runs before it.

    Memory holds *purchases*, not the whole closet — the starter wardrobe in
    data/wardrobe.json still arrives as an argument. The obvious thing, swapping
    the handed wardrobe out for the remembered items, would make the second run
    forget nine pieces the first run knew about; every later suggestion gets
    worse the more you shop. So the two are joined, handed items first, deduped
    by id, and an id already in the wardrobe wins — `clear_memory()` is the way
    to take something out.

    Args:
        wardrobe:   the wardrobe dict this run was handed.
        remembered: the "items" list from load_memory().

    Returns:
        A new dict shaped like a wardrobe ({"items": [...]}) even when both
        sides are empty, so `suggest_outfit()` takes it without checking. The
        wardrobe passed in is not modified.
    """
    items = list(wardrobe.get("items") or [])
    known = {item.get("id") for item in items}

    for item in remembered:
        if item.get("id") in known:
            continue
        items.append(item)
        known.add(item.get("id"))

    return {"items": items}


# ── writing ─────────────────────────────────────────────────────────────────────


def _wardrobe_item(listing: dict) -> dict:
    """
    Turn a listing dict into a wardrobe item.

    `notes` is where the provenance goes. `suggest_outfit()` formats the whole
    item into its prompt, so a line like "Remembered from depop at $18" is what
    lets the stylist tell a thrifted find from a piece owned for years instead
    of treating everything in the closet as equally old.
    """
    price = listing.get("price")
    price_note = f" at ${price:g}" if isinstance(price, (int, float)) else ""

    return {
        "id": listing.get("id"),
        "name": listing.get("title"),
        "category": listing.get("category"),
        "colors": listing.get("colors") or [],
        "style_tags": listing.get("style_tags") or [],
        "notes": (
            f"Remembered from {listing.get('platform', 'the listings')}"
            f"{price_note}, {listing.get('condition', 'unknown')} condition"
        ),
    }


def _write(memory: dict) -> None:
    """Save the wardrobe. Temp file then rename, so a crash can't halve it."""
    memory["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    tmp = MEMORY_PATH.with_name(MEMORY_PATH.name + ".tmp")
    tmp.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, MEMORY_PATH)


def remember_item(listing: dict) -> dict | None:
    """
    Add the item the agent just picked out to the remembered wardrobe.

    Args:
        listing: a listing dict — the one in session["selected_item"].

    Returns:
        The wardrobe item that was added, so the caller can print it.

        **Returns None when the item is already remembered** (same listing id).
        That is the normal outcome the second time you run a query, not an
        error. Nothing is written in that case — the file keeps the `updated_at`
        from when the item actually arrived.
    """
    memory = load_memory()
    listing_id = listing.get("id")

    if listing_id is not None and any(
        item.get("id") == listing_id for item in memory["items"]
    ):
        return None

    item = _wardrobe_item(listing)
    memory["items"].append(item)
    _write(memory)
    return item


def clear_memory() -> int:
    """
    Forget everything — delete the saved wardrobe.

    Returns:
        How many items were dropped, so the CLI can say a number rather than
        "done". 0 when there was nothing saved.
    """
    dropped = count()
    try:
        MEMORY_PATH.unlink()
    except FileNotFoundError:
        pass
    return dropped


# ── running it directly ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    saved = load_memory()

    print(f"Style memory: {MEMORY_PATH}")
    if not saved["items"]:
        print("  (nothing remembered yet)")

    for item in saved["items"]:
        tags = ", ".join(item.get("style_tags") or []) or "—"
        print(f"  {str(item.get('id')):<9} {str(item.get('name'))[:44]:<46} {tags}")

    print(f"\n{len(saved['items'])} item(s).")


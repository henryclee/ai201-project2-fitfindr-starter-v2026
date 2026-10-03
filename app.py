#!/usr/bin/env python3
"""
FitFindr — command line.

    python app.py ask 'vintage graphic tee under $30, size M'
    python app.py ask                     keep asking until you quit
    python app.py ask --empty-wardrobe    run as a user with nothing saved
    python app.py ask '...' --memory      start from the saved wardrobe, and keep
                                          what this run finds in it
    python app.py wardrobe                what style memory remembers
    python app.py forget                  clear the saved wardrobe
    python app.py listings                browse the data  (Milestone 1)
    python app.py fields                  what fields a listing has
    python app.py examples                queries worth trying, including a dud

Add --trace to any `ask` to print the loop step by step.

⚠️ Quote your query with SINGLE quotes. In PowerShell, "under $30" in double
quotes silently becomes "under " — PowerShell reads $30 as a variable and
substitutes nothing, so you search with no price ceiling and get no error
telling you why. Single quotes are literal in PowerShell, bash and zsh alike.
"""

import argparse
import sys

import config

# Every query here except the last one has something real to find in
# data/listings.json. If you add your own, check it against the data first — a
# query that finds nothing because the item doesn't exist looks exactly like a
# search tool that's broken.
EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "silk slip dress in midi length under $40",
    "platform sneakers size 8",
    "denim jacket under $50",
    "designer ballgown size XXS under $5",   # matches nothing, on purpose
]


def cmd_fields(args):
    """Milestone 1 — you can't filter on a field that isn't there."""
    from utils.data_loader import load_listings, get_example_wardrobe

    listing = load_listings()[0]
    print("A listing has these fields:\n")
    for key, value in listing.items():
        shown = str(value)
        if len(shown) > 58:
            shown = shown[:58] + "…"
        print(f"  {key:<14} {type(value).__name__:<6} {shown}")

    item = get_example_wardrobe()["items"][0]
    print("\nA wardrobe item has these fields:\n")
    for key, value in item.items():
        shown = str(value)
        if len(shown) > 58:
            shown = shown[:58] + "…"
        print(f"  {key:<14} {type(value).__name__:<6} {shown}")

    print(
        "\nThese are what search_listings can filter on. Read a few whole "
        "listings\nwith `python app.py listings` before you write it."
    )


def cmd_listings(args):
    """Milestone 1 — read the data before you write tools against it."""
    from utils.data_loader import load_listings

    listings = load_listings()

    if args.full:
        import json
        for listing in listings[: args.n]:
            print(json.dumps(listing, indent=2))
            print()
        return

    print(f"{len(listings)} listings.\n")
    print(f"{'id':<6}{'price':>8}  {'size':<22}{'platform':<11}title")
    print("-" * 92)
    for listing in listings[: args.n]:
        print(
            f"{str(listing['id']):<6}"
            f"{listing['price']:>8.2f}  "
            f"{str(listing['size']):<22}"
            f"{listing['platform']:<11}"
            f"{listing['title'][:38]}"
        )
    if len(listings) > args.n:
        print(f"\n… {len(listings) - args.n} more. Use -n {len(listings)} to see them all.")
    print("\nRead five or six all the way through: python app.py listings --full -n 6")


def cmd_examples(args):
    print("Queries worth trying:\n")
    for query in EXAMPLE_QUERIES[:-1]:
        print(f"  python app.py ask '{query}'")
    print(f"\nAnd one the data cannot match — this is the empty-search branch:\n")
    print(f"  python app.py ask '{EXAMPLE_QUERIES[-1]}'")
    print(
        "\nSingle quotes on purpose. In PowerShell a query in \"double quotes\"\n"
        "loses the $30 — it gets read as a variable — and you search with no\n"
        "price ceiling, with nothing to tell you it happened."
    )


def _ask_one(query, wardrobe, use_trace, remember=False):
    from agent import run_agent
    import trace as trace_module

    if use_trace:
        trace_module.start_trace()

    session = run_agent(query, wardrobe, remember=remember)

    print()
    if session["error"]:
        print(f"  {session['error']}")
    else:
        item = session["selected_item"] or {}
        print(f"  Found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
        print()
        print(f"  Outfit:   {session['outfit_suggestion']}")
        print()
        print(f"  Fit card: {session['fit_card']}")

    # Style memory, said out loud — this is the only place the CLI can show that
    # the state survived, and "already remembered" is a result worth printing:
    # it means the dedupe by listing id worked rather than that nothing happened.
    if remember:
        added = (session.get("memory") or {}).get("added")
        if added:
            print(f"  + remembered: {added.get('name')} ({added.get('id')})")
        elif session["error"]:
            print("  (nothing remembered — the run stopped early)")
        else:
            print("  (already remembered — nothing new added)")
    print()

    if use_trace:
        text = trace_module.get_trace()
        if not text:
            print(
                "  (--trace printed nothing. You haven't added trace.step() calls to\n"
                "   run_agent() yet — that's unit 4, Milestone 2.)\n"
            )
    return session


def cmd_ask(args):
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
    import generate

    wardrobe = get_empty_wardrobe() if args.empty_wardrobe else get_example_wardrobe()
    if args.empty_wardrobe:
        print("(running with an empty wardrobe)")

    # --empty-wardrobe is unit 4's failure-mode switch, and a switch that also
    # loaded a saved closet would not be one. It wins over --memory, and says so
    # out loud rather than quietly ignoring a flag somebody typed.
    remember = args.memory and not args.empty_wardrobe
    if args.memory and args.empty_wardrobe:
        print("(--empty-wardrobe wins over --memory: this run reads and writes nothing)")
    if remember:
        import memory

        print(
            f"(style memory on — {memory.count()} remembered purchase(s) in "
            f"data/{config.MEMORY_FILENAME})"
        )

    try:
        if args.query:
            _ask_one(args.query, wardrobe, args.trace, remember)
        else:
            print("Ask for something, or press Enter on an empty line to quit.\n")
            while True:
                try:
                    query = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if not query:
                    break
                _ask_one(query, wardrobe, args.trace, remember)
    finally:
        print(generate.usage())


def cmd_wardrobe(args):
    """
    Show what style memory is holding. No model call, no run — the file is the
    proof, so this is the command you point at in the README.
    """
    import memory

    saved = memory.load_memory()

    print(f"Remembered purchases: {memory.MEMORY_PATH}\n")

    if not saved["items"]:
        print("  (nothing remembered yet)")
        print("  Try:  python app.py ask '90s band tee under $25' --memory")
        return

    print(f"{'id':<9}{'category':<13}name")
    print("-" * 78)
    for item in saved["items"]:
        print(
            f"{str(item.get('id')):<9}"
            f"{str(item.get('category')):<13}"
            f"{str(item.get('name'))[:44]}"
        )
        if item.get("notes"):
            print(f"{'':<22}{item['notes']}")

    print(f"\n{len(saved['items'])} item(s). Clear them with: python app.py forget")


def cmd_forget(args):
    """Drop the saved wardrobe and start from an empty closet again."""
    import memory

    dropped = memory.clear_memory()
    if dropped:
        print(f"Forgot {dropped} item(s) — {memory.MEMORY_PATH} is gone.")
    else:
        print("Nothing was remembered, so there was nothing to forget.")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="FitFindr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_fields = sub.add_parser("fields", help="what fields the data has")
    p_fields.set_defaults(func=cmd_fields)

    p_list = sub.add_parser("listings", help="browse the listings data")
    p_list.add_argument("-n", type=int, default=15, help="how many to show")
    p_list.add_argument("--full", action="store_true", help="print whole records")
    p_list.set_defaults(func=cmd_listings)

    p_ex = sub.add_parser("examples", help="queries worth trying")
    p_ex.set_defaults(func=cmd_examples)

    p_ask = sub.add_parser("ask", help="run the agent")
    p_ask.add_argument("query", nargs="?")
    p_ask.add_argument("--trace", action="store_true", help="print the loop step by step")
    p_ask.add_argument(
        "--empty-wardrobe",
        action="store_true",
        help="run as a user with nothing saved — one of unit 4's failure modes",
    )
    p_ask.add_argument(
        "--memory",
        action="store_true",
        help=f"start from data/{config.MEMORY_FILENAME} and add this run's find to it",
    )
    p_ask.set_defaults(func=cmd_ask)

    p_wardrobe = sub.add_parser(
        "wardrobe", help="show the wardrobe style memory kept between runs"
    )
    p_wardrobe.set_defaults(func=cmd_wardrobe)

    p_forget = sub.add_parser("forget", help="clear the remembered wardrobe")
    p_forget.set_defaults(func=cmd_forget)

    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 — students read this, not a traceback
        print(f"\n{type(exc).__name__}: {exc}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

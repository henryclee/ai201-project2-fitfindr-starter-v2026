# Stretch Feature 2 — Retry with looser constraints

**Status:** not implemented. This document is the complete implementation plan.
**Audience:** an agent or person implementing it who has not read the discussion that produced it.
**Repo:** `ai201-project2-fitfindr-starter-v2026` (same fork submitted for units 3 and 4).

**What has been verified vs. assumed.** Everything in §1.5 (listing counts, prices,
sizes, platforms) was measured against `data/listings.json`; every code block in §3 was
parsed; `relax.py`'s code was executed, so the strings in §3.3 are what it prints; and
§5's suite — all 21 tests — was run against the repo with only §3.1's alias and §3.2's
flag shimmed in, and passes. Still unverified, and to be checked during implementation:
the model's parse of the query §6 runs (`size: XXS`, `max_price: 30`), the trace step
numbering (§6), and the before/after output itself, which does not exist until §6 is run.

> ⚠️ **Before starting §6:** a recent `run_eval.py` run in this workspace ended in
> `429 RESOURCE_EXHAUSTED` on the Gemini free tier (`limit: 500`, `model:
> gemini-3.5-flash-lite`), with the API asking to retry in ~3 hours. That is exactly why
> §6 measures with two CLI runs instead of the two full five-try logs `run_eval.py`
> would produce — ~3 model calls rather than ~160, and no risk of dying halfway through
> and leaving half a pair. Confirm the key works with one cheap run —
> `python app.py ask 'vintage graphic tee under $30'` — before starting, and do not run
> the `--no-relax` side if you cannot also finish the default side: half a before/after
> pair is worth less than none.


---

## 0. The requirement, verbatim

From the unit brief, under **Stretch Features**:

> Retry with looser constraints — an empty search retries once without the size
> filter, and says what it dropped.

Two obligations, and the second is the graded one:

1. **Retry once**, without the size filter, when the search comes back empty.
2. **Say what it dropped.** A completed run with no disclosure is a silent lie — the
   agent would hand the user an item in a size they did not ask for. The disclosure
   is the feature; the completion is a side effect.

Stretch features must be **declared in README.md before you start**, and **measured
the same way as the unit-4 improvement** (five criteria, five tries, before/after).

**How this plan meets that, and where it deliberately departs.** *Declared first* is
kept: §7.1 writes the README section and criterion 6 before any of §3's code exists.
*Before/after* is kept: one run with `--no-relax`, one without, same query, both saved
and pasted into the README as the artifact (§6). *Five tries* is the half given up on
purpose — criterion 6 is decided by code, not generation (§2.2), so five tries would
exercise the same branch five times and cost ~160 model calls on a free tier that has
already returned `429 RESOURCE_EXHAUSTED` in this workspace. The deviation is stated in
the README and in `criteria.md` rather than glossed over, and §4.1 keeps a criterion-6
scenario row so anyone can still produce the five-try version later. Unit 4's five-try
logs for criteria 1–5 stay exactly as submitted, untouched.

---

## 1. Current behaviour (read this before touching anything)

### 1.1 The branch that exists today

`agent.py::run_agent`, lines 229–249. This is the only place the loop can end early
on a search miss, and it is the seam this feature is built into:

```python
    if len(session["search_results"]) == 0:
        diagnosis = no_results.diagnose(
            description=description,
            size=size,
            max_price=max_price,
        )

        trace.step(
            "no_results",
            inputs=str(
                {
                    "description": description,
                    "size": size,
                    "max_price": max_price,
                }
            ),
            returned=diagnosis["message"],
        )

        session["error"] = diagnosis["message"]
        return session
```

Today the empty result is terminal: message, `return`, `suggest_outfit` never runs.

### 1.2 What `no_results.diagnose()` already gives you

`no_results.py::diagnose(description, size=None, max_price=None) -> dict`. **No model
call** — it re-runs `search_listings` directly three times, one constraint lifted at a
time (lines 83–95). Returns:

```text
{
    "cause":         "no_match" | "size" | "price" | "size_and_price" | "unknown",
    "message":       the sentence for session["error"],
    "tried":         "'tee' in size M under $30",
    "probes":        {"size": int, "price": int, "description": int},   # listing counts
    "closest":       cheapest description-only match, or None,
    "sizes_on_file": every size that description comes in,
}
```

Module-private helpers worth reusing rather than duplicating: `_sizes(items)` (line 52)
and `_cheapest(items)` (line 57). Constant `SIZE_HINT_LIMIT = 6` (line 36) caps how many
sizes a message names.

**Key insight:** `price_probe` is literally `search_listings(description, max_price=…)`
with **no size** — i.e. it is already the relaxed search. The diagnosis knows whether
dropping the size would help, for free.

### 1.3 The MCP seam (do not disturb it)

`agent.py` calls the tool over MCP, which is unit 4's Milestone 1 deliverable:

```python
    search_results = mcp_client.call_tool(
        "search_listings",
        {
            "description": session["parsed"]["description"],
            "size": session["parsed"]["size"],
            "max_price": session["parsed"]["max_price"],
        },
    )
```

`mcp_client.call_tool(name, arguments)` spawns `mcp_server.py` as a subprocess per call
(~0.3–1 s), unwraps the MCP content blocks back to native Python, and raises
`MCPError` on failure. `mcp_server.py` currently offers two tools: `search_listings`
(unit 4) and `suggest_outfit` (Stretch Feature 1). **The retry must go through
`mcp_client.call_tool`, not a direct `tools.search_listings(...)` call**, so the retry
is visible in the trace as an MCP call — that is required evidence for the Loop Trace
section. (`no_results.py` deliberately calls `tools.search_listings` directly for its
probes; that reasoning is documented in its module docstring and stays as it is.)

### 1.4 Everything on the path after selection

Once `session["search_results"]` is non-empty, the existing code (lines 251–309) runs
unchanged: a `compare_price` loop picks the first item whose verdict is not
`"overpriced"` (falling back to `search_results[0]`), then `suggest_outfit` over MCP,
then `create_fit_card`. **The feature must not touch any of that** — relaxed results
re-enter the path at `session["search_results"]` and are then handled identically.

### 1.5 Verified facts about `data/listings.json` (40 listings)

Measured with `PYTHONDONTWRITEBYTECODE=1 python3` against the real data — no model
calls. Re-run them before writing README examples; the example sentences in this
document use these numbers.

| query | strict | relaxed (size dropped) | `diagnose()["cause"]` | `probes` |
|---|---|---|---|---|
| `vintage graphic tee` XXS ≤ $30 | 0 | **10** | `size` | `{size:0, price:10, description:10}` |
| `vintage graphic tee` XXS ≤ $1 | 0 | **0** (cheapest listing matching the words is $12 — a belt; cheapest tee is $15) | `size` | `{size:0, price:0, description:10}` |
| `denim jacket` XXS ≤ $50 | 0 | **6** | `size` | `{size:0, price:6, description:6}` |
| `designer ballgown` XXS ≤ $5 (criterion 2's scenario) | 0 | **0** | `no_match` | `{size:0, price:0, description:0}` |

The relaxed list for `vintage graphic tee` / no size / ≤ $30, in order, with the
`compare_price` verdict the existing selection loop will read:

```
lst_002  tops        S/M                      $18.0  Y2K Baby Tee — Butterfly Print     fair
lst_033  tops        L                        $19.0  Vintage Band Tee — Faded Grey      good_deal
lst_006  tops        L                        $24.0  Graphic Tee — 2003 Tour Bootleg    fair
lst_017  tops        S/M                      $15.0  Mesh Long-Sleeve Top — Black       unknown
lst_015  tops        L                        $26.0  Vintage Graphic Hoodie — Faded B…  fair
lst_014  accessories One Size (adjustable)    $12.0  Leather Belt — Brown, Braided      unknown
lst_034  accessories One Size                 $14.0  Bucket Hat — Reversible, Brown…    unknown
lst_020  tops        M                        $16.0  Henley Long Sleeve — Washed Bu…    good_deal
lst_024  tops        M                        $18.0  Vintage Polo Shirt — Forest Green  good_deal
lst_012  tops        XL (fits oversized)      $20.0  Oversized Crewneck Sweatshirt…     unknown
```

Consequences that matter:

- The item the loop selects is **`lst_002`, size S/M, $18** — verdict `fair`, so it is
  the first non-overpriced candidate. The scenario's outcome is a top, not an accessory.
- **Category drift is real but does not bite here:** the belt and bucket hat sit at
  ranks 6–7. `score_listing` in `tools.py` needs only one shared token, so relaxing the
  size also surfaces accessories that mention "vintage". Tracked in §8.1.
- Every relaxed item fails `size_matches("XXS", item["size"])` — verified. That is the
  invariant the disclosure sentence rests on, and §5 pins it with a test.

Baseline at the time of writing: `python -m unittest test_size_matching` → **24 tests,
OK**. A green re-run after the change is part of acceptance (§9).

---

## 2. Design decisions

### 2.1 The retry lives in the loop, not in the tool

`tools.py::search_listings` keeps its published contract: it filters on size when a
size is given, and returns `[]` when nothing matches — never relaxed results, never
`None`, never an exception. Relaxing is **policy**, not tool behaviour:

- A tool that quietly widens its own filter makes the empty case ambiguous for the next
  agent that calls it, and `README.md`'s Tool Inventory promises the strict contract.
- `mcp_server.py`'s registered signature is already submitted work (unit 4 + Stretch
  Feature 1). Changing it re-opens a graded artefact.
- The unit rule says the MCP move and one improvement are the only changes; keeping the
  diff inside `agent.py` plus one new module honours that.

### 2.2 Always attempt once when a size was applied (**chosen**)

Two options were weighed. The chosen one is the second.

| | Probe-gated | **Always attempt once (chosen)** |
|---|---|---|
| Gate | retry only if `probes` show lifting the size returns something | retry whenever a size was applied and the switch is on |
| Code | reads `diagnosis["probes"]`, needs a `max_price is None` special case | one boolean |
| Dead ends | no extra MCP spawn, but the message only *infers* the price is the wall | one extra spawn (~0.3–1 s), and the message has *proved* it |
| Trace | retry sometimes absent, so the trace varies between runs | retry always present on a size-blocked miss |

Chosen: **always attempt once when `size` is truthy**, and when the retry still comes
back empty say so explicitly — `"(I searched again without the size filter and still
found nothing, so the size is not what is blocking this — everything above still
stands.)"` That sentence adds only the fact the retry owns. It does not re-name the
constraint that blocked, because `diagnose()` has already named it, in the message this
gets appended to, down to a suggested `max_price` (§3.3). Simpler code, and a dead-end
attempt is evidence rather than waste.

**The one guard that must exist:** `should_attempt(None)` is `False`. Without it, every
empty search with no size re-runs the identical query and wastes a process spawn for a
result that cannot differ.

### 2.3 Exactly once, never recursive

One second MCP call inside the existing branch. No `while`, no re-entry into the
branch, no second relaxation of any kind. The price ceiling is **never** dropped — the
brief says "without the size filter", and dropping two constraints at once makes the
disclosure sentence impossible to write honestly.

### 2.4 The disclosure is structured, not just prose

`session["relaxed"]` records what happened so a recorded run can be scored without
reading a trace, the same way `session["memory"]` documents the style-memory feature:

```python
session["relaxed"] = {
    "attempted":      bool,          # a retry was made at all (call issued)
    "dropped":        "size" | None, # only set when a relaxed result came back
    "requested_size": str | None,    # what the user asked for
    "found":          int,           # how many listings the relaxed search returned
    "sizes":          [str],         # sizes actually on offer, deduped + sorted
    "error":          str | None,    # set when the retry call itself failed (§3.4e)
    "note":           str | None,    # the sentence for the user; None unless found > 0
}
```

`attempted` distinguishes `[]` ("searched without the size, still nothing") from
`None` ("never relaxed — no size was applied"), so the message can never claim a retry
that did not happen. `error` exists for the same reason: a retry whose subprocess died
must not be reported as a retry that found nothing.

### 2.5 Toggleable, so it can be measured

- `config.RETRY_WITHOUT_SIZE = os.getenv("AI201_RELAX", "1") != "0"` — default on.
- `app.py ask --no-relax` sets it off for one CLI run, mirroring the `--empty-wardrobe`
  convention.

Two switches for one behaviour, because they get used at different moments: `--no-relax`
is the flag on the single run that becomes the README's BEFORE half (§6), and
`AI201_RELAX=0` turns it off for a whole shell session, so a sweep of commands can be run
without repeating the flag. They must be one switch and not two similar ones — §6 checks
that by reproducing the BEFORE file through the env var. Neither switch needs anything
edited or re-run, which is what makes the pair honest: same code, same query, one flag
between them.

> ⚠️ **Implementation trap:** read the flag as `config.RETRY_WITHOUT_SIZE` at call
> time. `from config import RETRY_WITHOUT_SIZE` binds the value at import and the flag
> silently stops working — which is exactly how a measured feature ends up measuring
> nothing. `run_eval.py` uses the same dynamic pattern for `config.CACHE_ENABLED`,
> which is where the habit comes from.

### 2.6 Alternatives rejected

1. **`allow_size_relax: bool = False` parameter on the MCP tool.** Saves one process
   spawn, but rewrites a published contract, hides the policy from other callers, and
   makes `[]` mean two different things. Rejected.
2. **Ask the model to rewrite the query** (loosen price, re-word description). More
   general, but costs a model call and converts a deterministic criterion into a
   probabilistic one. Rejected for this unit; worth noting in *What's Still Broken*.
3. **Probe-gated retry.** See §2.2 — not chosen, but the probes stay in place because
   `diagnose()` is still needed for the failure sentence.

---

## 3. The code

Four files change; one is new (`relax.py`). Order matters only in that §3.1 must land
before §3.3. `criteria.md` changes too and `scenarios.py` optionally — those are §4, not
part of the code path.

### 3.1 `no_results.py` — promote one helper (additive, no behaviour change)

`relax.py` needs the size-spread reading `diagnose()` already builds. Duplicating it
lets the two messages drift apart, so add a public alias directly below `_cheapest`
(around line 60):

```python
# Public alias. relax.py writes a user-facing sentence out of the same reading
# diagnose() uses; one definition keeps the two honest about the same numbers.
sizes_on_file = _sizes
```

That is the whole edit — one line, nothing re-wired. `_cheapest` does **not** need an
alias: `tried_anyway()` reads the cheapest match straight out of
`diagnosis["closest"]`, which is already public.

Do **not** change `_sizes`, `_cheapest`, `SIZE_HINT_LIMIT`, `diagnose()`, or the
`_CAUSE_*` builders. Criterion 2 of unit 4 is graded on their output and
`test_size_matching.py` covers them.

### 3.2 `config.py` — the switch

Add next to the other behaviour switches (`CACHE_ENABLED`, `MEMORY_FILENAME`):

```python
# Stretch Feature 2: when a size-filtered search comes back empty, retry it once with
# the size dropped and tell the user that's what happened. On by default;
# AI201_RELAX=0 (or app.py ask --no-relax) turns it off, which is how the feature
# gets measured against the behaviour it replaced.
RETRY_WITHOUT_SIZE = os.getenv("AI201_RELAX", "1") != "0"
```

`config.py` already imports `os`, so no new import.

### 3.3 `relax.py` (new file, ~80 lines with comments)

Pure helpers only — no MCP, no model, no printing. Every branch is unit-testable
without the agent loop.

```python
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
```

`relax.py`, continued:

```python
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
    the session as evidence (§3.4); it just does not go in this sentence.
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
```

**Actual outputs**, produced by running this document's own `relax.py` code against the
repo (that is how these strings were verified — re-run them, don't paste them):

- `note("XXS", lst_002, 10)` →
  `Nothing on FitFindr comes in size XXS, so I dropped the size filter and found 10 matches. The pick below is size S/M — Y2K Baby Tee — Butterfly Print, $18 on depop. It is not the size you asked for.`
- `tried_anyway()` →
  `(I searched again without the size filter and still found nothing, so the size is not what is blocking this — everything above still stands.)`
- `call_failed_note()` →
  `(I tried searching again without the size filter and that call failed, so nothing here was loosened — the size you asked for is still the one in effect.)`
- `sizes_found(relaxed)` → `['L', 'M', 'One Size', 'One Size (adjustable)', 'S/M', 'XL (fits oversized)']`

And the three `diagnose()["message"]` strings these sentences get appended to, measured
rather than imagined:

| query | `cause` | what `diagnose()` already says |
|---|---|---|
| tee, XXS, $30 | `size` | *"Nothing comes in size XXS — 'vintage graphic tee' does exist in L, M, One Size, One Size (adjustable), S/M, XL (fits oversized), so try one of those **or leave the size out**."* |
| tee, XXS, $1 | `size` | the above, plus *"nothing is under $1 — the cheapest match is Leather Belt — Brown, Braided at $12 on thredUp, so raise max_price to about $12."* |
| ballgown, XXS, $5 | `no_match` | *"Nothing in the listings matches 'designer ballgown' at all, whatever the size or price — loosen the wording…"* |

Three things that exercise taught, all of which the wording above already accounts for:

- **The first message tells the user to do the thing this feature does.** "…or leave the
  size out" is the brief's retry, written in prose and handed to the user to perform.
  That sentence is the best justification for the feature, and belongs in the README.
- **`diagnose()` already names the price wall**, down to a suggested `max_price`. That is
  why `tried_anyway()` carries no arguments and re-states nothing: an earlier draft of
  this plan had it append *"the cheapest listing matching those words is $12"*, which
  would have printed the same fact twice in one reply. If you find yourself passing
  `diagnosis` into a sentence-builder here, stop and read the message it is being glued
  to.
- **`platform` values are `depop`, `poshmark`, `thredUp`** — capitalised as written, and
  there is no "thegoodwill". Anything pasted into the README must come from the data.

### 3.4 `agent.py` — the branch, and one field

**(a) Import** (line 23, next to `import no_results`):

```python
import relax
```

**(b) `new_session()`** — add one field after `"memory": None,` (line 56):

```python
        # Stretch Feature 2: did this run drop the size filter to get a result?
        # Filled in by run_agent() only when a size-filtered search came back empty —
        # see the branch in run_agent() and relax.py.
        "relaxed": None,
```

**(c) Replace lines 217–249** (the existing comment block plus the whole
`if len(session["search_results"]) == 0:` body) with:

```python
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
    #
    #      Stretch Feature 2 changes what "empty" means, in one direction only: when
    #      the search had a size in it, we ask for the same thing once without the
    #      size and say out loud that we did. The price ceiling is never dropped —
    #      loosening two constraints at once leaves you with nothing honest to say
    #      about what came back. The retry is one call, never a loop: a second
    #      relaxation would be a different feature, and an unbounded one.

    if len(session["search_results"]) == 0:
        diagnosis = no_results.diagnose(
            description=description,
            size=size,
            max_price=max_price,
        )

        trace.step(
            "no_results",
            inputs=str(
                {
                    "description": description,
                    "size": size,
                    "max_price": max_price,
                }
            ),
            returned=diagnosis["message"],
        )

        # Stretch Feature 2 — one retry, size dropped, over the same MCP seam the
        # first call used, so the trace shows a real second tool call rather than a
        # branch nobody can see. Three states have to stay distinguishable: None means
        # "never attempted" (no size applied, or the feature is off), [] means
        # "attempted, still nothing", and a set `error` means "attempted, the call
        # itself failed". Collapse them and the message can claim a search that never
        # happened.

        relaxed = None
        retry_error = None
        if relax.should_attempt(size):
            try:
                relaxed = mcp_client.call_tool(
                    "search_listings",
                    {
                        "description": description,
                        "size": None,
                        "max_price": max_price,
                    },
                )

                trace.step(
                    "MCP tool call search_listings (retry: size filter dropped)",
                    inputs=str(
                        {
                            "description": description,
                            "size": None,
                            "max_price": max_price,
                        }
                    ),
                    returned=relaxed,
                    note=f"dropped size={size} after 0 results",
                )
            except mcp_client.MCPError as exc:
                # The retry is a bonus on top of an answer we already have — the
                # diagnosis. A dead subprocess must not turn a clean "here is what
                # blocked you" into a stack trace, and it must not be reported as "I
                # retried and found nothing" either: it retried and got an error.
                retry_error = str(exc)

                trace.step(
                    "MCP tool call search_listings (retry failed)",
                    inputs=str(
                        {
                            "description": description,
                            "size": None,
                            "max_price": max_price,
                        }
                    ),
                    returned=retry_error,
                    note="retry never completed; falling back to the diagnosis",
                )

        session["relaxed"] = {
            "attempted": relaxed is not None or retry_error is not None,
            "dropped": "size" if relaxed else None,
            "requested_size": size,
            "found": len(relaxed or []),
            "sizes": relax.sizes_found(relaxed or []),
            "error": retry_error,
            "note": None,  # written below, once an item has actually been selected
        }

        if relaxed:
            # Back into the normal path. Everything from here on — selection,
            # compare_price, suggest_outfit, create_fit_card — is unchanged and does
            # not know or care that the results arrived without a size filter; the
            # disclosure is what makes that safe to say out loud.
            session["search_results"] = relaxed
        else:
            session["error"] = diagnosis["message"]
            if retry_error is not None:
                session["error"] += " " + relax.call_failed_note()
            elif relaxed is not None:
                # The retry proved the size was not the only thing stopping it, which
                # is worth more than the guess it replaced. diagnose() has already
                # named the wall; this only records that we climbed it.
                session["error"] += " " + relax.tried_anyway()
            return session
```

**(e) Why the `try` is around the retry and nowhere else**

`agent.py` catches no `MCPError` anywhere — a failed first `search_listings` call is
allowed to propagate, and that is correct: there is no answer to fall back to. Inside
this branch there *is* one, already sitting in `diagnosis["message"]`. So the retry is
the only MCP call in the file that is wrapped, and it degrades to the pre-feature
message instead of a traceback. `MCPError` is defined in `mcp_client.py` (line 37) and
`agent.py` already imports the module, so `mcp_client.MCPError` needs no new import.

**(d) After the selection block** — insert between line 271
(`session["selected_item"] = search_results[0]`) and the step-6 comment:

```python
    # Stretch Feature 2 — now that there is a pick, the disclosure can name its size.
    # Written here rather than in the branch above because the relaxed list contains
    # whatever matched the words, accessories included; the honest sentence is about
    # the item this run is actually recommending.
    if session["relaxed"] and session["relaxed"]["found"]:
        session["relaxed"]["note"] = relax.note(
            session["relaxed"]["requested_size"],
            session["selected_item"],
            session["relaxed"]["found"],
        )

        trace.step(
            "relax disclosure",
            inputs=f"requested size={session['relaxed']['requested_size']}",
            returned=session["relaxed"]["note"],
        )
```

**`trace.step` already accepts `note=`** (verified: `def step(name, inputs=None,
returned=None, note="")`, `trace.py` line 41) and renders it as a `→` line, so the
retry's note prints without touching `trace.py`. Note also that `out:` is only printed
when `returned is not None`, so a relaxed search that returns `[]` still shows up as
`out: []` — the attempt is visible even when it fails, which is the point.


**Why the branch order is what it is:** `diagnose()` runs *before* the retry even though
the retry no longer consults it, because the failure sentence needs `cause` and
`closest`. If you move the retry above it to save a function call, the dead-end message
loses the price evidence — which is the half of the message the user acts on.

### 3.5 `app.py` — say it out loud, and add the switch

**(a) Module docstring** (after line 9) — the usage block is what a marker reads first:

```
    python app.py ask '...' --no-relax    stop at the empty search instead of
                                          retrying it without the size
```

**(b) `cmd_ask`** (line 154) — set the flag before the agent runs, next to the
`--empty-wardrobe` handling:

```python
    # --no-relax is Stretch Feature 2's switch, and it has to be set before
    # run_agent() reads it. Off means the run stops at the empty search and says
    # what blocked it — which is the behaviour this feature gets measured against.
    if args.no_relax:
        config.RETRY_WITHOUT_SIZE = False
        print("(retry-without-size off — this run stops at the empty search)")
```

**(c) argparse** (in the `p_ask` block, lines 255–268, after `--memory`):

```python
    p_ask.add_argument(
        "--no-relax",
        action="store_true",
        help="don't retry an empty size-filtered search without the size filter",
    )
```

argparse turns `--no-relax` into `args.no_relax`. `_ask_one` is called from two places
(the one-shot path and the `ask` loop) — both go through `cmd_ask`, so setting the flag
once there covers both.

**(d) `_ask_one`** (line 121) — the disclosure prints **before** the result:

```python
    print()
    if session["error"]:
        print(f"  {session['error']}")
    else:
        # Stretch Feature 2 — before the result, not after. Once somebody has read a
        # title they like, they stop paying attention, and an item in the wrong size
        # is exactly the thing that must not arrive unlabelled.
        note = (session.get("relaxed") or {}).get("note")
        if note:
            print(f"  {note}")
            print()

        item = session["selected_item"] or {}
        print(f"  Found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
```

`session["error"]` already carries the retry sentence on a failed run (§3.4c), so the
failure path needs no new code here.

**`serve.py` needs no change.** It serialises the session dict, so `relaxed` reaches any
API consumer automatically — worth one README line rather than an edit. Do not add a
`--no-relax` equivalent to the HTTP layer in this unit; that is scope creep, and note it
in *What's Still Broken*.

---

## 4. Scenario and criterion

### 4.1 `scenarios.py` — optional, and not on the measurement path

§6's artifact is one query run twice from the CLI, so nothing in this unit *depends* on
`scenarios.py`. Adding the two rows is cheap — two dicts, no model calls to write them —
and buys one thing worth having: anyone can later run
`python run_eval.py --tries 5 --label relax_on` and get the five-try version of
criterion 6 that this plan deliberately skips (§0). If you skip §4.1, say so in the note
under criterion 6 rather than leaving a criterion that points at a scenario nobody added.

When you do add them, append to `SCENARIOS`, following the existing dict shape exactly:

```python
    {
        # A size the data does not carry. Criterion 6 — Stretch Feature 2: the run
        # should retry once without the size, finish, and say that it did.
        "name": "size-blocked search retries without the size",
        "query": "vintage graphic tee size XXS under $30",
        "wardrobe": "example",
        "criterion": 6,
    },
    {
        # Diagnostic, not one of the six: the retry has to fail politely when the size
        # was not the only thing blocking. $1 is under the cheapest listing matching
        # those words ($12 — a belt; the cheapest tee is $15).
        "name": "retry onto a dead end still stops early",
        "query": "vintage graphic tee size XXS under $1",
        "wardrobe": "empty",
        "criterion": None,
    },
```

Delete the stale `# TODO: add what your criteria 3, 4 and 5 need.` comment block — those
criteria already have scenarios; leaving it reads as unfinished work.

**Validate the parse, don't assume it.** The parser is a model call, and with one
before/after pair there is no second sample to catch a bad parse in. Read trace step `[1]`
of §6's AFTER run and confirm it produced `size: XXS` and `max_price: 30`: a parse that
drops the size means no retry was ever owed, and the pair would then show the old
behaviour on both sides and prove nothing at all. Unit 4's logs already show
`"designer ballgown size XXS under $5"` parsing to `XXS`, so this shape works. If it does
drop the size, re-word (e.g. `"vintage graphic tee in size XXS under $30"`), and record
the phrasing you landed on next to the artifact in the README.

### 4.2 `criteria.md` — criterion 6, added without touching 1–5

Originals are graded work; append only. Shape to match the file's existing entries:

```markdown
## Criterion 6 — Retry with looser constraints (stretch)

**Type:** decision + state
**Target:** the before/after pair — FAILs with `--no-relax`, PASSes without it (1 try each side)

Given a query whose size filter cannot be satisfied (`vintage graphic tee size XXS
under $30`), the agent retries the search exactly once with the size dropped, keeps
the price ceiling, completes the run, and states in its own words that it dropped the
size filter and what size the result actually is.

**Passes when:** the trace shows a second `search_listings` call with `size: None`
after an empty first one, the run reaches `suggest_outfit`, and the reply names both
the size asked for and the size returned.

**Fails when:** it stops at the empty result, silently returns a wrong-size item,
drops the price ceiling too, or retries more than once.

**Why one try each side and not five of five:** the retry is code, not a model decision —
unlike criteria 3–5, nothing after `parse_query` depends on generation, so five tries
would exercise the same branch five times and print the same cell five times. The one step
that *is* model-driven, the parse, is checked inside the run instead of sampled: trace
step `[1]` must show `size: XXS`, or the criterion was never exercised. This departs from
the five-tries convention the other criteria use, and says so here rather than leaving the
difference unexplained. A miss on either side is a bug, not variance, and gets written up
as one; if a five-try row is ever wanted, `run_eval.py --tries 5 --label relax_on` still
produces it.

**Not covered:** whether dropping the size was the *right* thing to drop. The agent
knows the price ceiling is what a $1 search is really up against; it drops the size
because that is the constraint it was told to drop.
```

Also fix the sentence at the top of `criteria.md` that says "Five criteria" if it now
carries six — say plainly that 6 is the stretch criterion added in unit 5, and that it is
measured as a before/after pair rather than five tries, with §4.2's reason in one line.

---

## 5. Tests — `test_relaxed_retry.py` (new file)

Same conventions as `test_size_matching.py`: plain `unittest`, no model calls, real
`data/listings.json`, a module docstring that explains the split. Run with
`python -m unittest test_relaxed_retry -v`.

**This suite has been run.** All 21 tests pass against the current repo, with `relax.py`
built from §3.3's blocks and only the two additive edits (§3.1's alias, §3.2's flag)
shimmed in. One test failed while this document was being written and the *test* was
wrong, not the code — see `test_it_repeats_nothing_diagnose_already_said`. Fixing it
there is recorded in the comment rather than quietly edited out.

```python
"""
Retry-without-the-size tests — criterion 6 in criteria.md (Stretch Feature 2).

    python -m unittest test_relaxed_retry -v

Three kinds of test, and the split matters:

    policy     should_attempt() — when the retry happens, including the two cases
               where it must not: no size was applied, and the feature is off.
    honesty    the disclosure sentence. The retry is the easy half; a run that
               hands back a size the user never asked for without saying so is
               worse than the empty result it replaced, and that failure is
               silent — nothing crashes, the user just buys an L. Includes the
               two note() branches ordinary data never reaches.
    dead ends  the retry failing. It has to stay a message about what blocked,
               not become a second empty result.

No model call anywhere in this file: search_listings() reads JSON and diagnose()
re-runs search_listings(). Same reason no_results.py is testable at all.
"""

import unittest

import config
import relax
from no_results import diagnose
from tools import search_listings
from utils.sizes import size_matches

# The query criterion 6 runs, as data — the same words §4.1's optional scenario row
# uses, so a recorded run and this test cannot drift apart. A size the file does not
# carry and a ceiling the file can meet: verified against data/listings.json, 0 strict
# matches and 10 relaxed.
BLOCKED = ("vintage graphic tee", "XXS", 30.0)

# Same words, ceiling under the cheapest tee on file ($18): dropping the size cannot
# help, and the message has to say so rather than just repeat "nothing found".
DEAD_END = ("vintage graphic tee", "XXS", 1.0)

# Criterion 2's scenario from unit 4. Nothing matches the words at all, so this is the
# regression guard: the new branch must not turn a clean stop into a wrong answer.
NO_MATCH = ("designer ballgown", "XXS", 5.0)


class ShouldAttempt(unittest.TestCase):
    def test_a_size_that_was_applied_gets_one_retry(self):
        self.assertTrue(relax.should_attempt("XXS"))

    def test_no_size_means_no_retry(self):
        # The guard that keeps an empty search from re-running itself.
        self.assertFalse(relax.should_attempt(None))
        self.assertFalse(relax.should_attempt(""))

    def test_the_switch_turns_it_off(self):
        original = config.RETRY_WITHOUT_SIZE
        self.addCleanup(setattr, config, "RETRY_WITHOUT_SIZE", original)
        config.RETRY_WITHOUT_SIZE = False
        self.assertFalse(relax.should_attempt("XXS"))

    def test_the_flag_is_read_at_call_time(self):
        # If agent.py ever does `from config import RETRY_WITHOUT_SIZE`, the
        # before/after pair measures nothing. This is that bug's only tripwire.
        original = config.RETRY_WITHOUT_SIZE
        self.addCleanup(setattr, config, "RETRY_WITHOUT_SIZE", original)
        size = BLOCKED[1]
        config.RETRY_WITHOUT_SIZE = False
        self.assertFalse(relax.should_attempt(size))
        config.RETRY_WITHOUT_SIZE = True
        self.assertTrue(relax.should_attempt(size))


class TheRetryFindsWhatTheSizeHid(unittest.TestCase):
    def setUp(self):
        description, size, max_price = BLOCKED
        self.size = size
        self.relaxed = search_listings(description, None, max_price)

    def test_dropping_the_size_is_what_unblocks_it(self):
        description, size, max_price = BLOCKED
        self.assertEqual(search_listings(description, size, max_price), [])
        self.assertEqual(len(self.relaxed), 10)

    def test_the_price_ceiling_survives_the_retry(self):
        # Only the size may be dropped. If this fails, the disclosure sentence is a lie.
        self.assertTrue(all(item["price"] <= BLOCKED[2] for item in self.relaxed))

    def test_none_of_it_is_the_size_that_was_asked_for(self):
        # The invariant the note rests on: every relaxed listing fails the size check,
        # which is why the sentence has to name a different size rather than imply a
        # match. If this ever starts returning items, the disclosure is still true but
        # the wording needs revisiting.
        self.assertTrue(
            all(size_matches(self.size, item["size"]) is None for item in self.relaxed)
        )
```

`test_relaxed_retry.py`, continued:

```python
class Disclosure(unittest.TestCase):
    def setUp(self):
        description, size, max_price = BLOCKED
        self.item = search_listings(description, None, max_price)[0]
        self.note = relax.note(size, self.item, 10)

    def test_it_names_the_dropped_size_and_the_one_you_get(self):
        self.assertIn("XXS", self.note)
        self.assertIn(str(self.item["size"]), self.note)

    def test_it_does_not_let_the_result_read_as_a_match(self):
        self.assertIn("dropped", self.note.lower())
        self.assertIn("not the size you asked for", self.note)

    def test_it_quotes_the_price_back(self):
        # A reader deciding whether to click needs the number in the same breath as
        # the size that changed.
        self.assertIn(f"${self.item['price']:g}", self.note)

    def test_nothing_is_claimed_when_there_is_no_item(self):
        self.assertEqual(relax.note("XXS", None, 0), "")
        self.assertEqual(relax.note(None, self.item, 10), "")

    def test_the_size_spread_is_deduped_and_sorted(self):
        sizes = relax.sizes_found(search_listings(BLOCKED[0], None, BLOCKED[2]))
        self.assertEqual(sizes, sorted(set(sizes)))
        # Documents why note() names the pick rather than this list: a relaxed search
        # for a tee also returns a belt and a bucket hat.
        self.assertIn("One Size", sizes)


class RetryOntoADeadEnd(unittest.TestCase):
    def test_the_size_was_never_the_only_thing_stopping_it(self):
        description, size, max_price = DEAD_END
        self.assertEqual(search_listings(description, None, max_price), [])
        self.assertEqual(diagnose(description, size, max_price)["cause"], "size")

    def test_the_retry_sentence_reports_only_the_retry(self):
        # diagnose() already named the wall. This sentence owns one fact: the size was
        # tried, and it did not help.
        message = relax.tried_anyway()
        self.assertIn("searched again without the size filter", message)
        self.assertIn("still found nothing", message)

    def test_it_repeats_nothing_diagnose_already_said(self):
        # The trap this test exists for: an earlier draft of relax.py re-stated the
        # price here, so the reply printed the same fact twice in one breath. Our half
        # carries no money, no size, no listing name — those belong to the sentence
        # above it.
        message = relax.tried_anyway()
        self.assertNotIn("$", message)
        self.assertNotIn("XXS", message)

        # Appending it must not raise the number of prices in the reply. Written as a
        # comparison rather than a literal because diagnose() already says "$12" twice
        # on this query ("… at $12 … so raise max_price to about $12") — a hard-coded
        # count is a test of the data's phrasing, not of this sentence.
        diagnosis = diagnose(*DEAD_END)["message"]
        self.assertEqual((diagnosis + message).count("$"), diagnosis.count("$"))

    def test_a_dead_end_reads_as_one_account_of_one_search(self):
        # diagnose() is category-blind — on this query "closest" is a $12 belt — but
        # that is its business. Our appended half must not add a second claim about
        # what the cheapest thing is, or the reply starts arguing with itself.
        diagnosis = diagnose(*DEAD_END)
        self.assertEqual(diagnosis["closest"]["category"], "accessories")
        combined = diagnosis["message"] + " " + relax.tried_anyway()
        self.assertIn("leave the size out", combined)      # diagnose()'s own advice
        self.assertEqual(combined.count("cheapest"), 1)

    def test_a_broken_call_is_not_reported_as_an_empty_one(self):
        # "Found nothing" is a fact about the data; "the call failed" is a fact about
        # our plumbing. Conflating them tells the user their size does not exist.
        message = relax.call_failed_note()
        self.assertIn("call failed", message)
        self.assertNotIn("found nothing", message)
        self.assertIn("still the one in effect", message)

    def test_a_query_that_matches_nothing_still_gets_its_diagnosis(self):
        # The regression that matters most: criterion 2's scenario must keep stopping
        # early with the same advice. Our sentence is tagged on the end, not swapped in.
        description, size, max_price = NO_MATCH
        diagnosis = diagnose(description, size, max_price)
        self.assertEqual(diagnosis["cause"], "no_match")
        self.assertEqual(search_listings(description, None, max_price), [])
        combined = diagnosis["message"] + " " + relax.tried_anyway()
        self.assertIn("wording", combined)
        self.assertIn("designer ballgown", combined)


class TheTwoNoteEdges(unittest.TestCase):
    """
    `note()`'s two branches that ordinary data never reaches, both of which print a
    number straight at the user. The happy path is covered above; these are the ones
    that would put a wrong claim in a reply while every test stayed green.
    """

    ITEM = {"size": "M", "title": "Plain Tee", "price": 12.0, "platform": "depop"}

    def test_one_match_is_not_called_matches(self):
        singular = relax.note("XXS", self.ITEM, 1)
        self.assertIn("found 1 match.", singular)
        self.assertNotIn("matches", singular)
        self.assertIn("found 10 matches", relax.note("XXS", self.ITEM, 10))

    def test_a_listing_without_a_price_does_not_break_the_sentence(self):
        # `tools.search_listings` skips listings with no usable price, so this should be
        # unreachable — which is exactly why it gets a test. The alternative is an f-
        # string raising TypeError on the way to telling someone they got a result, or
        # printing "$None" at them.
        item = {"size": "M", "title": "Plain Tee", "platform": "depop"}
        sentence = relax.note("XXS", item, 3)
        self.assertIn(", ? on depop", sentence)   # note()'s placeholder is a bare "?"
        self.assertNotIn("None", sentence)

    def test_the_platform_is_written_the_way_the_data_writes_it(self):
        # `thredUp`, not `thredup`. There is no "thegoodwill" either — the README quotes
        # these sentences, and a mangled platform name is what makes a pasted run look
        # invented rather than measured.
        item = {"size": "M", "title": "Plain Tee", "price": 12.0, "platform": "thredUp"}
        self.assertIn("on thredUp", relax.note("XXS", item, 2))


if __name__ == "__main__":
    unittest.main()
```

Two notes on the tests themselves:

- `size_matches()` returning `None` is the confirmed no-match signal (verified against
  all ten relaxed listings), so the `is None` assertion is right — but re-read
  `utils/sizes.py` before trusting it across a tier change.
- Nothing here exercises `run_agent()`, because that costs a model call. The loop-level
  proof is the before/after trace pair in §6; say so in the README rather than implying
  the unit tests cover the loop.

What running them caught: `test_it_repeats_nothing_diagnose_already_said` originally
asserted the combined dead-end reply mentioned `$12` once. It appears twice — in
`diagnose()`'s own sentence, *"the cheapest match is Leather Belt … at $12 … so raise
max_price to about $12"*. The assertion was rewritten to compare price counts before and
after appending, which is the property actually being protected. Keep that shape: an
assertion about how the sample data happens to be worded will break for reasons that have
nothing to do with this feature.

---

## 6. Measurement — the before/after pair

**The artifact is two CLI runs of one query**: `--no-relax` (the behaviour being
replaced) and the default (the feature), each with `--trace`, each saved to a file under
`results/` and pasted into the README under Stretch Feature 2. Nothing else is run for
the measurement, and `run_eval.py` is not touched — in either direction.

**Why not `run_eval.py`.** It has no scenario filter, so a before/after pair through it
means every scenario × five tries: ~160 model calls and 10–20 minutes, all of it spent
sampling variance in generation — and criterion 6 has none past `parse_query` (§2.2,
§4.2). This workspace's key has already returned `429 RESOURCE_EXHAUSTED` on the free
tier, so the expensive version of this measurement carries a real risk of dying halfway
and leaving half a pair, which is worth less than none. Two runs cost ~3 model calls,
take under a minute, and cannot be misread about what they compared. The trade — one try
per side instead of five — is stated in `criteria.md` and the README rather than left for
a marker to notice.

```bash
# BEFORE — the behaviour being replaced: stops at the empty search
python app.py ask 'vintage graphic tee size XXS under $30' --trace --no-relax \
    2>&1 | tee results/relax_before.txt

# AFTER — same query, default settings: retries once without the size
python app.py ask 'vintage graphic tee size XXS under $30' --trace \
    2>&1 | tee results/relax_after.txt
```

Run them back to back, and put the command that produced each block above it in the README
so a reader can reproduce it. `results/` is committed on purpose (`config.py`, *Paths*),
so the two files survive as evidence the runs happened. `--trace` prints every step as it
happens and `app.py::cmd_ask` ends with `generate.usage()`, so each file already carries
the step list *and* an "N model calls this session, M served from cache" line — quote
that line instead of estimating the cost. (PowerShell: `| Tee-Object -FilePath
results\relax_before.txt`.)

**Leave the cache on** — do not set `AI201_CACHE=0` for this. The thing under test is a
branch, not the wording of a fit card; `parse_query` hitting the cache on the second run
is what keeps the pair to ~3 calls, and it cannot flatter the feature because both sides
read the same parse. Say so in one README line: a reader who spots "served from cache"
should not have to work out whether the comparison was rigged.

**What to check in each file**, and what should differ:

| Check | BEFORE (`--no-relax`) | AFTER (default) |
|---|---|---|
| `parse_query` step | `size='XXS'`, `max_price=30.0` — **must match, or the pair proves nothing** | identical to BEFORE |
| `search_listings` steps | 1, ending `out: [] (empty)` | 2 — the second with `size=None` and `→ dropped size=XXS after 0 results` |
| `no_results` step | present | present, same sentence |
| `compare_price` / `suggest_outfit` / `create_fit_card` | absent — the run stopped early | present, in that order |
| CLI reply | diagnosis only | disclosure line **above** `Found:`, naming XXS and the returned size |
| `generate.usage()` line | 1 model call (the parse), or 0 with a warm cache | 3 cold, 2 with the parse cached |
| wall clock (`time`) | one MCP spawn | two — measure both, quote the delta |

**Verdict, written by hand under the pair.** One line for criterion 6, naming the steps
that decided it — e.g. *"criterion 6 — MET (1/1 with the feature on, 0/1 with it off;
steps [4]–[7] of `results/relax_after.txt`)"*. Dropping the harness does not drop that
judgment; `run_eval.py`'s docstring is blunt about it being the point.

**The near-free second pair — do it.** The dead-end query stops early on both sides, so
each run is one model call and the pair costs almost nothing while proving the half of
the feature that is easiest to fake:

```bash
python app.py ask 'vintage graphic tee size XXS under $1' --trace --no-relax \
    2>&1 | tee results/dead_end_before.txt
python app.py ask 'vintage graphic tee size XXS under $1' --trace \
    2>&1 | tee results/dead_end_after.txt
```

BEFORE ends with `diagnose()`'s sentence. AFTER must end with the *same* sentence plus
`tried_anyway()`, and still stop early — no `suggest_outfit` step. Paste both: a pair
that only shows the success case is the one a marker trusts least.

**The two regressions, one run each** (no flag needed; neither should produce a
disclosure):

```bash
python app.py ask 'designer ballgown size XXS under $5' --trace   # criterion 2 unchanged
python app.py ask 'vintage graphic tee under $30' --trace         # no size → no retry
```

The first is the regression that would cost the most marks: it must still stop early,
still name what to change, and show **one** `search_listings` call. The second proves the
`should_attempt(None)` guard (§2.2) — one call, not two.

*Optional, only if quota is spare afterwards:* `python run_eval.py --tries 1 --label
relax_check` puts every scenario on the page in one pass (~7 runs) and is the cheap way
to show criteria 1–5 did not move. It is a bonus, not this plan's artifact — do not let
it become the reason the pair gets skipped.

**Sweep, in order** (each catches something the runs above don't):

```bash
python -m unittest test_relaxed_retry test_size_matching       # new + regression
python mcp_client.py                                           # server still lists both tools
time python app.py ask 'vintage graphic tee size XXS under $30' --trace
time python app.py ask 'vintage graphic tee size XXS under $30' --trace --no-relax
AI201_RELAX=0 python app.py ask 'vintage graphic tee size XXS under $30' --trace
python app.py ask 'denim jacket under $50' --trace                 # drift watch (§8.1)
```

The `time` pair is the latency evidence §7.2 asks for: a relaxed run that succeeds makes
the same number of model calls as a normal run, because the retry adds one MCP subprocess
spawn (~0.3–1 s) and no model call; a dead-end run stays at one model call but pays two
spawns — `diagnose()`'s probes plus the retry. Quote the measured delta, not these
estimates. The `AI201_RELAX=0` run must reproduce `results/relax_before.txt` exactly —
that is what proves the flag and the env var are one switch rather than two that look
alike.

**Expected trace shape for the AFTER run**, which is what goes in the README. The BEFORE
file stops after step [3] — that absence *is* the comparison, so paste both traces rather
than describing the missing one:

```
[1] parse_query            …  size='XXS', max_price=30.0
[2] MCP tool call search_listings     in: size='XXS' …   out: [] (empty)
[3] no_results             →  "Nothing comes in size XXS — 'vintage graphic tee' does
      exist in L, M, One Size, … so try one of those or leave the size out."
[4] MCP tool call search_listings (retry: size filter dropped)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    dropped size=XXS after 0 results
[5] compare_price          …  verdict=fair
[6] MCP tool call suggest_outfit      …
[7] create_fit_card        …
```

The `out:` line is `trace._short()`'s rendering, not a raw list: ten items come out as
`10 items: <first three titles> … +7 more`, and an empty list as `[] (empty)` — which is
why the failed first search stays visible in both files. Step numbering will differ if
`create_fit_card` traces differently — copy the real output, never this sketch.

**What `session["relaxed"]` adds to the artifact:** nothing the pair doesn't already
show. The CLI never prints it and no check above depends on it; `serve.py` carries it for
API consumers (§8.2), and the disclosure line above `Found:` is its readable half. Don't
invent a third command just to display it.

---

## 7. Documentation

### 7.1 Declare it **before** implementing

The brief requires stretch features to be declared in `README.md` first. Under
`## Stretch Features` (line 295, which currently holds `compare_price`, the
unparseable-query branch and style memory), add a short section — declared, not yet
delivered:

```markdown
### Stretch Feature 2 — retry with looser constraints (declared, in progress)

**The problem it aims at:** criterion 2's scenario ends the run at an empty search. For
`designer ballgown size XXS under $5` stopping is right — nothing matches the words. For
`vintage graphic tee size XXS under $30` stopping is wrong: ten tees fit the words and
the price, and none of them come in XXS. The run had an answer and threw it away because
one filter could not be satisfied.

**What I'll build:** when a search that had a size in it returns nothing, ask for the
same thing once more without the size — one retry, price ceiling kept — and say out loud
that the size filter was dropped and what size came back. If that still finds nothing,
say it found nothing *after* retrying and name the constraint that actually blocked.

**How I'll measure it:** a sixth criterion (`criteria.md`), then the same query run twice
from the CLI — once with `--no-relax`, once without — and both traces pasted side by side.
Five tries would sample variance in generation, and criterion 6 has none past the query
parse; two runs cost about three model calls against a free tier that is already rate
limited here, so that is a deliberate trade and not a shortcut, and it's why this
criterion is written as a pair instead of out of five. The comparison stays fair because
the flag is one line of config, not a rewrite.

**What I'll count as failure:** a result that arrives without the disclosure. That is
worse than the empty message it replaced, and I'll write it up if it happens.
```

Alongside it: add criterion 6 to `criteria.md` (§4.2), and the two rows to `scenarios.py`
if you want the five-try route kept open (§4.1 — optional, nothing in §6 uses it).
Nothing else changes yet. Declaring first is the point: at this moment the README
describes a feature the code does not have, and running the query still stops at the
empty search. Commits are yours to sequence by hand — this plan does not script them — so
the evidence that the order was real is the "(declared, in progress)" heading and the fact
that §3's files do not exist yet when you write this section. Keep those two honest;
without a commit trail they are the whole proof.

### 7.2 After the measurement

Keep the section where §7.1 put it — under `## Stretch Features` — and just drop
"(declared, in progress)" from the heading. (`## Stretch Feature 1 - A second tool moved
to MCP` sits at the end of the file instead; two stretch sections in two places is
already this README's inconsistency. Don't add a third convention — leave Stretch
Feature 1 where it is and make sure the `## Stretch Features` list reads in order.)
The section must contain:

1. **The decision, in prose** — §2.1/§2.2, including that the retry is deliberately not
   inside `search_listings`, and that always-attempting was chosen over gating on the
   probes with the reason (§2.2's table).
2. **The traces** — both real outputs from §6, labelled BEFORE (`--no-relax`) and AFTER,
   each under the command that produced it. The AFTER one must show the second
   `search_listings` step with `size: None` and its
   `→ dropped size=XXS after 0 results` note.
3. **The disclosure, verbatim** — the sentence `app.py` printed, plus the failed-retry
   sentence. Quote both; they are the graded artefacts.
4. **The before/after pair** — `results/relax_before.txt` and `results/relax_after.txt`
   as two fenced blocks, plus §6's check table and the hand-written verdict line. Put the
   dead-end pair (`results/dead_end_{before,after}.txt`) next to them: the retry that
   finds nothing and says so is the half that reads as evidence rather than a demo.
5. **Whether it helped** — plain answer, with the numbers from the pair: BEFORE stopped at
   the empty search, AFTER completed with a size S/M top at $18, and the measured
   wall-clock delta between them. Say plainly which of criteria 1–5 were *not* re-run: the
   evidence for them here is `test_size_matching`'s 24 tests plus §6's two regression
   runs, not a fresh five-try log — claim exactly that much and no more.
6. **What it cost** — one extra MCP spawn per size-blocked miss, no extra model call on
   a successful retry; the dead-end case pays two spawns to buy one honest sentence.
7. **The measurement's own limits** — one sentence saying this is a 1-try pair and not
   five, with §4.2's reason. A stretch feature measured more lightly than the unit-4
   improvement has to say so out loud, or the difference looks hidden.

Then update, in place:

| Section | Change |
|---|---|
| `## Planning Loop` (line 127) | Its **Branch rule** currently reads *"If search_listings returns an empty list, put a message in session["error"] and stop."* That sentence becomes false. Replace it with the two-path rule below, and add `relaxed` to the **"What moves through the session"** list (it currently ends at `error`). A grader checks code against this section, so the file and function names must stay real. |
| `## Tool Inventory` / `### search_listings` (line 63) | One line: the contract is unchanged — a size filter still filters, empty still means empty. The retry is loop policy in `agent.py`, and say why (§2.1). |
| `## Loop Trace` (line 775) | Either extend the existing trace with a labelled second example, or point at the new one under Stretch Feature 2. Don't paste the same trace twice. |
| `## How I Used AI` (line 237) | Add the real exchange that shaped this: the probe-gated design was proposed, and the choice to always attempt came from *you* — with the tradeoff that decided it (a dead-end retry proves the price is the wall instead of inferring it). |
| `## What's Still Broken` (line 1230) | Add §8.1, §8.2, §8.3 below. This section is graded for honesty; a stretch feature with no listed downside reads as unexamined. |
| `Sample Run` (line 168) | Leave alone — it documents a normal run. Add one line pointing at the stretch section for a size-blocked run. |

The branch rule to paste in, replacing the one-sentence version (keep the existing note
about `compare_price` choosing the item — it is still true):

```markdown
**Branch rule:**
If search_listings returns an empty list, ask `no_results.diagnose` what blocked it.
If no size was applied (or the retry is switched off), put that diagnosis in
session["error"] and stop. If a size *was* applied, call search_listings once more over
MCP with `size=None` and the same price ceiling: results found go back into
session["search_results"] and the run continues, with session["relaxed"]["note"] saying
out loud which size was dropped and what size the pick actually is; nothing found stops
with the diagnosis plus a sentence saying the retry was tried and what is really left
blocking. Otherwise take the highest-scoring item that is not "overpriced" and go to
suggest_outfit.

**Where it lives:** `agent.py::run_agent`, the `if len(session["search_results"]) == 0:`
branch. The diagnosis sentence comes from `no_results.py::diagnose`; the drop-the-size
decision and its sentences live in `relax.py`. The retry is one call, never a loop, and
it never drops the price ceiling.
```

### 7.3 `RUNNING.md`

- **`## Every command`** (line 71): add
  `python app.py ask 'vintage graphic tee size XXS under $30' --no-relax` with the
  one-line explanation, next to the existing `--memory` / `--empty-wardrobe` rows.
- **`## The two settings people go looking for`** (line 184): it becomes three — add
  `RETRY_WITHOUT_SIZE` (`AI201_RELAX=0`) with the same shape as the existing entries:
  what it does, default, how to turn it off for one run vs. every run. Rename the
  heading rather than leaving it lying.
- **`## When something goes wrong`** (line 220): add the row a user will actually hit —
  *"It sent me something in the wrong size"* → it never changes your request silently;
  the line above `Found:` names the size that was dropped, and `--no-relax` restores the
  old stop-at-nothing behaviour. Plus: *"`--no-relax` did nothing"* → check you're on a
  build that has the flag (`python app.py ask --help`).

---

## 8. Limits to state honestly (goes in *What's Still Broken*)

### 8.1 Relaxing the size also relaxes what counts as a match

`score_listing()` in `tools.py` ranks on shared tokens, not category, so dropping the
size filter surfaces whatever else mentions the words. Verified against the data:

```
'denim jacket'      no size, ≤ $50 → 1 Denim Jacket S · 2 Denim Shorts W27 · 3 Denim Vest M
'90s track jacket'  no size        → 1 90s Track Jacket M · 2 Bucket Hat One Size
```

In criterion 6's scenario the pick is a top (`lst_002`, S/M), so drift does not bite —
but that is luck about this query, not a property of the feature. The same blindness is
already in `diagnose()`: for this query `closest` is the **$12 belt**, which is why the
dead-end sentence says "the cheapest listing matching those words" rather than naming a
garment (§3.3). Two mitigations already in the design: the disclosure names the item and
its size, so a wrong-category result is at least visible; and `compare_price` still runs
on whatever comes back. What is *not* done: no category guard, because `search_listings`
has no category parameter and adding one is a tool-contract change this unit should not
make. If a future unit wants it, the clean shape is `category=None` on the tool plus a
`session["relaxed"]["drift"]` flag — not a filter bolted onto the retry.

### 8.2 Only the web layer has to trust the field

`app.py` prints the disclosure before `Found:`. `serve.py` serialises
`session["relaxed"]` but renders nothing, so a future front end can show the item and
silently omit the sentence that makes it honest. Recorded rather than fixed: adding a
render path here is scope creep, and the JSON does carry `note`.

### 8.3 The retry never questions the *other* constraint

`vintage graphic tee size XXS under $1` drops the size, finds nothing, and reports that
the $1 ceiling is the wall — correctly. But it does not offer to lift the price, because
the brief named one constraint and loosening two at once makes the disclosure impossible
to write. The next step is a `--relax price` or a model-suggested rewording (§2.6.2);
neither is in this unit, and the README should say so rather than implying the agent can
negotiate.

### 8.4 Small, real costs

- One extra MCP subprocess spawn (~0.3–1 s) on every size-blocked miss, including ones
  that were always going to fail — the price of choosing always-attempt (§2.2).
- `sizes_found()` on a relaxed list mixes in accessory sizes (`One Size` from a belt),
  which is why the disclosure names the pick rather than the spread.
- The disclosure sentence is fixed prose, not model-generated — deliberate (a model that
  re-writes the caveat can drop the part that matters), but it means the sentence will
  not adapt to a query phrased unusually.

---

## 9. Acceptance checklist

Commits are handled by hand, so this is a checklist and not a commit plan. The one rule
that survives the loss of a scripted history: write §7.1's README section and criterion 6
**before** any of §3 exists, so the declared-but-failing state is real when you describe
it. Without commit boundaries, that ordering and the "(declared, in progress)" heading are
the evidence.

**The order to work in:**

1. **Declaration** — `README.md` §7.1 block, `criteria.md` criterion 6, and optionally
   `scenarios.py`'s two rows (§4.1). Expected state: the query still stops at the empty
   search, and nothing else has changed.
2. **Implementation + tests** — `config.py` (the flag), `no_results.py` (one alias line),
   `relax.py`, `agent.py`, `app.py`, `test_relaxed_retry.py`.
3. **Measurement + docs** — the §6 pairs under `results/`, the README Stretch Feature 2
   write-up and its six in-place section updates, `RUNNING.md`'s three updates.

**Done means all of these:**

- [ ] `python -m unittest test_relaxed_retry test_size_matching` green — 21 new tests
      (§5) plus the original 24, unchanged and still passing
- [ ] `results/relax_before.txt` and `results/relax_after.txt` exist, each with the
      command that produced it recorded above its README block
- [ ] The AFTER trace contains a `search_listings` step with `size: None` **and** a
      `suggest_outfit` step after it; the BEFORE trace contains exactly one
      `search_listings` step and no `suggest_outfit` — the old behaviour, on the record
- [ ] The AFTER run **without** `--trace` prints the disclosure line above `Found:`,
      naming `XXS` and the returned size
- [ ] `AI201_RELAX=0 python app.py ask 'vintage graphic tee size XXS under $30' --trace`
      reproduces `results/relax_before.txt` — the flag and the env var are one switch
      (PowerShell: `$env:AI201_RELAX='0'` first, `Remove-Item Env:AI201_RELAX` after)
- [ ] `results/dead_end_before.txt` and `results/dead_end_after.txt` exist; the AFTER one
      appends the retry sentence to the same diagnosis and still stops early, with no
      `suggest_outfit` step
- [ ] A sizeless empty search (`python app.py ask 'designer ballgown under $5'`) makes
      **one** `search_listings` call, not two — the no-size guard works
- [ ] Criterion 2's scenario still stops early and still names what to change, with the
      retry sentence appended rather than replacing it
- [ ] The README carries a hand-written criterion 6 verdict naming the steps that decided
      it, and one sentence saying this is a 1-try pair and why (§4.2)
- [ ] `## Planning Loop` in the README matches what the code now does, line for line
- [ ] `git diff` touches only: `config.py`, `no_results.py` (one alias line),
      `agent.py`, `app.py`, `relax.py`, `test_relaxed_retry.py`, `criteria.md`,
      `README.md`, `RUNNING.md`, `results/` — plus `scenarios.py` if you took §4.1's
      optional rows. **`tools.py`, `mcp_server.py`, `mcp_client.py`, `run_eval.py`,
      `trace.py`, `utils/sizes.py` and `test_size_matching.py` are untouched.**

---

## 10. One-paragraph summary for the README

> When a search that had a size in it comes back empty, FitFindr now asks for the same
> thing once more without the size and says that it did: *"Nothing on FitFindr comes in
> size XXS, so I dropped the size filter and found 10 matches. The pick below is size
> S/M — Y2K Baby Tee, $18. It is not the size you asked for."* One retry, never two; the
> price ceiling stays put; if it still finds nothing the message says a retry happened
> and names the constraint that actually blocked. `--no-relax` turns it off, which is how
> the README's before/after pair was produced.












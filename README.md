# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->
Fitfindr agent allows a user to query the agent for a clothing item with a given
description, size and max price. It then searches the listings for the item that
most closely matches this query. It returns the selected item, a suggested outfit
that incorporates this item into the user's existing wardrobe, and a caption that
the user could use to caption a photo wearing all of these items.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:**
Search the listings data for items matching a description, size (optional), and
max price (optional), and returns a list of items from the listing that match the
parameters, best match first.
- **Inputs:** <!-- name and type each: `max_price` (float), not "a price" -->
description: str - keywords describing what the user wants
size: str | None - the size asked for, as a seller's label or as spoken English
  ("S", "small", "medium", "M/L", "w30", "W30 L30", "US 8", "size 8",
  "one size", "oversized"), or None to skip size filtering.
  A listing matches when it is in the same size *family* as the request and
  shares a label with it. Families: alpha (S/M/L/XL, including ranges like
  "S/M" and fit-qualified labels like "XL (oversized)"), one size, waist
  ("W30 L30") and shoe ("US 8.5"). Families never cross, so "s" does not
  return the US 7 shoes and "l" does not return the W30 L30 jeans. The ladder
  never slides: "XS" does not match an S and "8" does not match a US 8.5.
  "One Size" answers an S/M/L request only (it fits *most*, not the tails of
  the ladder) and is ranked last. A size that can't be read ("free spirit")
  is treated as no size filter at all, not as a false empty.
  The rules live in utils/sizes.py; the pairs are pinned by test_size_matching.py.
max_price: float | None - maximum price in whole dollars, inclusive
- **Returns:**
A list of matching items (dict) from listings, best match first, or an empty list 
if no matches are found. An item dict contains keys for description, category, style_tags, 
size, etc...
- **Ordering:**
Size match tier first — exact label, then a range that covers the request
("S/M" for "small"), then a one-size listing — then keyword overlap, then
price ascending. The price tie-break is there so the order doesn't depend on
the order of rows in listings.json.
- **When it has nothing:**
Empty list (never None, never an exception). An empty result means "nothing in
that size or under that price", which is what no_results.py probes to name the
wall — so the size filter stays strict instead of widening to near-misses.

### `suggest_outfit`

- **What it does:**
Given an item, and the user's wardrobe, suggests an outfit
- **Inputs:**
new_item: dict - an item from listings
warddrobe: dict - a dict with an item key holding a list of items
- **Returns:**
A string suggestion of one or two outfits incorporating the item and items from
the users warddrobe
- **When it has nothing:**
If warddrobe is empty, returns general styling advice

### `create_fit_card`

- **What it does:**
Writes a short caption that a user might use to caption of picture of themselves
wearing an outfit with an item from listings
- **Inputs:**
outfit: str - The outfit string from suggest outfit
new_item: dict - an item from listings
- **Returns:**
A caption string of two to four sentences describing the outfit and the item
- **When it has nothing:**
If outfit is empty, return a descriptive message of the item

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:**
If search_listings returns an empty list, put a message in session["error"] and stop.
Otherwise, take the first item from the list, and place it in session["selected_item],
and use it for suggest_outfit

Note, that with the stretch feature fourth tool, the selected item is the highest scoring
item that is not "overpriced." If no such item exists, then it defaults to the first
item in the list.

**Where it lives:** the branch itself — `if len(search_results) == 0:` ... `return session` —
is in `agent.py::run_agent`. The sentence it puts in `session["error"]` is built by
`no_results.py::diagnose`, which `run_agent` calls from inside that branch.

**How the query is parsed:** <!-- regex, string splitting, or asking the model — say which -->
The query is sent to generate with a prompt asking for a JSON object including keys for 
description, size, and max_price

**What moves through the session:** <!-- which fields, in what order -->
query — set at session creation
parsed (description, size, max_price) — filled from the model-parsing step
search_results — filled from search_listings()
selected_item — the first search result (or loop stops here if empty, setting error instead)
outfit_suggestion — filled from suggest_outfit()
fit_card — filled from create_fit_card()
error - filled in case of an error (e.g. if search items fails to find a matched item)

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
python app.py ask 'vintage graphic tee under $30' 

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey babe! Oh, you scored *so* hard with this Y2K butterfly baby tee—it is giving major early 2000s pop princess vibes, and at $18? Absolute steal. 

Since the baby tee is fitted and cropped with those sweet pink and purple butterfly tones, the key to nailing the silhouette is playing with proportions. Let's lean into that effortless, off-duty model streetwear aesthetic.

Here is your styled look:

### **The Fit: 2000s Streetwear Contrast**

*   **Top:** Y2K Butterfly Baby Tee *(Your new thrift find!)*
*   **Bottoms:** Baggy straight-leg jeans, dark wash (`w_001`) — *The high waist and baggy fit create that classic tight-top/baggy-bottom Y2K silhouette that looks so effortlessly cool.*
*   **Outerwear:** Vintage black denim jacket (`w_006`) — *Throw this slightly cropped jacket over your shoulders if it gets chilly, keeping the black accents sharp.*
*   **Shoes:** Chunky white sneakers (`w_007`) — *To keep the legs looking long and tie in the white base of the tee.*
*   **Accessories:** Black crossbody bag (`w_010`) — *Sleek, minimal, and practical for carrying your lip gloss and flip phone (or, you know, your actual phone).*

**Why it works:** 
The dark wash of the baggy jeans grounds the playful, pastel butterfly graphic so it doesn't look too costume-y, while the chunky sneakers and crossbody bag tie the whole streetwear look together. You're ready for coffee runs, thrift shopping, or hanging out with the girls! 🦋✨

  Fit card: Scored this ultimate Y2K butterfly baby tee for just $18 on Depop, and honestly, I’m never taking it off! 🦋✨ Paired it with some baggy denim for that effortless 2000s off-duty model look. Absolute thrift win!

3 model calls this session, 1371 prompt + 463 output tokens

```

**The three tools, tested one at a time**

```
 % python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

```
% python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Hey! Amazing find on those vintage Levi’s 501s—classic medium-wash denim at $38 is an absolute steal, and that slight knee fading gives them instant character. 

Since 501s have that timeless, straight-leg vintage silhouette, let’s lean into an effortless, cool-girl streetwear look using pieces you already own.

### **The Outfit: Off-Duty Vintage Streetwear**

*   **Top:** **White ribbed tank top** (`w_003`) — Tucked into the jeans to define your waist and balance the straight-leg fit.
*   **Outerwear:** **Oversized grey crewneck sweatshirt** (`w_004`) — Layered right over the tank. Since it drops below the hip, let it slouch off one shoulder for that relaxed, effortlessly thrown-together vibe.
*   **Shoes:** **Chunky white sneakers** (`w_007`) — To tie in the white from the tank and give the outfit a fresh, modern streetwear edge as they pool slightly over the hems of the 501s.
*   **Accessories:** 
    *   **Brown leather belt** (`w_009`) — Add this to cinch the waist if you want to let the crewneck peek out slightly over the waistband, adding a nice touch of warmth against the blue denim.
    *   **Black crossbody bag** (`w_010`) — For a sleek, everyday finishing touch.

**Why it works:** It’s comfortable, high-contrast (grey, white, and medium indigo wash), and plays with proportions by pairing a fitted base with an oversized cozy layer. You're ready to run errands, grab coffee, or hit the thrift stores again!
```

```
% python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these classic vintage Levi's 501s in the ultimate medium wash on Depop for just $38! I styled them with crisp white sneakers for that effortless, timeless everyday look. Nothing beats the fit and character of a true vintage pair of denim. ✨👖
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I used AI to help me write the search_listings tool, especially for the syntax for the score_listing sub function.

**Moment 1**

- *What I asked for:*
I used AI to check my criteria to make sure they were testable.
"Here are five acceptance criteria for a multi-tool agent. For each one, tell me exactly how you would test it using only what the sentence says. Don't suggest improvements — just tell me what you'd do."
- *What came back:*
It made suggestions for some criteria that were not objectively testable.
- *What I changed:*
I changed the criteria so they could be tested by an objective reviewer.

**Moment 2**

- *What I asked for:*
I used AI to help me write the search_listings tool, especially for the syntax for the score_listing sub function. I had the idea of creating a set of keywords from the description, and counting the keywords from multiple sections from the item listing (desription, style_tags, colors, brand)
- *What came back:*
The syntax for collecting all of the item's keywords into a set
- *What I changed:*
The code for the search_listings tool, primarily in score_listing

**Moment 3**
- *What I asked for:*
Assistance with the first branch logic -- when a search fails, giving a response that makes
suggestions of what to change requires some logic, and multiple queries (ablating the price,
size)
- *What came back:*
AI wrote the code after I approved the plan.
- *What I changed:*
The code for the logic was written and tested by the AI.

**Moment 4**
- *What I asked for:*
Assistance with planning and implementing stretch feature 3 - Style memory.
- *What came back:*
Iterated over planning the feature implementation with AI, then allowed AI to act on this plan.
- *What I changed:*
The code and comments for style memory are AI generated.

**Moment 5**
- *What I asked for:*
Assistance with planning and implementing a refactor for search_listings.
- *What came back:*
Iterated over planning the feature implementation with AI, then allowed AI to act on this plan.
- *What I changed:*
The code and comments for search_listings, as well as the unit tests, are AI generated.

---

## Stretch Features

### A fourth tool - compare_price

`compare_price`

**What it does:**
Compare's one listing's price against comparable listings in the dataset and 
returns a price verdict. In this case, comparable means matching on the same
category, size, and at least one shared style_tag. The verdict is considered
a "good_deal" if it is more than 10% less than the median price among comparables, 
and "overpriced" if it is more than 10% more expensive than the median. If there
are not enough comparables, it is "unknown", otherwise it is "fair."

**Inputs:**
new_item: dict - an item from listings

**Returns:**
A dict:
{
     "item_id":          str,
     "price":            float,
     "comparable_count": int,
     "median_price":     float | None,   # None when comparables are too thin
     "delta":            float | None,   # price - median, negative = cheaper
     "delta_pct":        float | None,
     "verdict":          "good_deal" | "fair" | "overpriced" | "unknown",
     "comparables":      [ {"id","title","price","platform"}, ... ]  # ≤5, cheapest first
}

**When it has nothing:**
If comparable_count < 3, returns verdict "unknown", median_price /
delta / delta_pct all None, comparables []

**Sample Trace**
Sample run showing the agent calling the compare_price tool

```
% python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query
      in:  dict with keys: query
      out: dict with keys: raw_result, cleaned_result
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: dict with keys: search_results
[3] compare_price
      in:  dict with keys: new_item
      out: dict with keys: price_comparison
[4] suggest_outfit
      in:  dict with keys: new_item, wardrobe
      out: dict with keys: outfit_suggestion
[5] create_fit_card
      in:  dict with keys: outfit, new_item
      out: dict with keys: fit_card

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey babe, what an absolute score! That Y2K butterfly baby tee is so nostalgic and effortlessly cute for $18. Since it has that fitted, cropped silhouette, the golden rule of styling is to play with proportions—balancing that snug top with something a bit more relaxed on the bottom. 

Here is your go-to outfit formula using pieces straight from your wardrobe:

*   **Top:** Y2K Baby Tee — Butterfly Print *(Your new thrift find!)*
*   **Bottoms:** Baggy straight-leg jeans, dark wash (`w_001`)
*   **Outerwear:** Vintage black denim jacket (`w_006`) — *throw this over your shoulders for that effortless model-off-duty vibe*
*   **Shoes:** Chunky white sneakers (`w_007`)
*   **Accessories:** Black crossbody bag (`w_010`)

### Why this works:
The high-waisted, dark wash baggy jeans create that classic 2000s contrast against the fitted baby tee, hugging your waist while keeping the lower half super relaxed. Tying it together with chunky white sneakers keeps the Y2K streetwear energy alive, and the cropped black denim jacket adds a little edge without hiding the butterfly graphic. 

Go stunt in this! ✨🦋

  Fit card: Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop, and I am officially never taking it off! 🦋✨ Embracing the ultimate 2000s proportions by pairing it with my favorite baggy denim.

3 model calls this session, 1280 prompt + 365 output tokens
```

### A second branch - reject unparseable query

**Branch rule:** If the model's parse step returns no description, stop before
calling `search_listings` and put a message in `session["error"]`. Otherwise —
with or without a size or max_price — proceed along the happy path to the search.

**Where it lives:** `agent.py::run_agent`, the `if not description:` guard
between the parse loop and the `search_listings()` call.

**Why it exists:** `search_listings` opens with `description.lower().split()`, so
a `None` description raises `AttributeError` out of the tool rather than
returning an empty list. My parse prompt explicitly allows the model to answer
`null`, so this is an expected outcome, not an exotic one.

Distinct from the empty-search branch: that one fires when the search ran and
found nothing. This one fires when the search never ran.

**Sample Run**
This run shows the agent takes this branch when the query is nonsensical.

```
% python app.py ask 'a'

  I couldn't read a description out of that query, so there was nothing to search for. Name the item, e.g. 'vintage graphic tee under $30'.

1 model calls this session, 55 prompt + 30 output tokens
```

### Style memory

In the initial implementation, every session with the agent starts with the same
wardrobe, and thus has no memory of things that have previously been selected. This
feature adds the ability for agent to remember a wardrobe between runs -- 
specifically, if memory is on (using the python app.py ask '...' --memory), items 
that are selected in one round are added to the wardrobe in the next round so they 
can be included in suggested outfits.

This involves another branch rule -- If `remember` is on **and** 
`data/style_memory.json` holds at least one remembered purchase, plan against the 
wardrobe it was handed *plus* those purchases; and after `create_fit_card` returns 
with `session["error"]` still `None`, append `session["selected_item"]` to that file 
— unless its `id` is already in it. Otherwise (flag off, nothing remembered yet, 
or the run stopped early) the run reads no file and writes no file, which is every 
run that came before this feature.

**Where it lives:** `memory.py` (new), plus two short branches in
`agent.py::run_agent` — the read at the top of the loop (step 1b) and the write
after the fit card (step 7b). `app.py` is the front door: `ask --memory`,
`wardrobe`, `forget`.

**The API** (`memory.py`):

| function | takes | returns |
|---|---|---|
| `load_memory()` | — | `{"items": [...]}` in `wardrobe_schema.json` shape. **`{"items": []}` when the file is missing, is not JSON, or has no dict items** — it never raises. |
| `remember_item(listing)` | one listing dict | the wardrobe item written, or **`None` when that listing `id` is already remembered**, in which case nothing is written |
| `merge_wardrobes(wardrobe, remembered)` | the run's wardrobe + the remembered items | a new `{"items": [...]}`, handed items first, deduped by `id`; the dict passed in is not mutated |
| `clear_memory()` | — | how many items were dropped (0 if there was no file) |
| `count()` | — | int |

A listing maps onto a wardrobe item without translation — the two share the same
five `category` values and the same `colors` / `style_tags` list shape — so what
the file gives back goes straight into `suggest_outfit()`. Where it came from and
what it cost ride along in `notes` (`Remembered from depop at $18, excellent
condition`), which is the only thing that lets the stylist tell a thrifted find
from a piece you have owned for years.

**Robustness:** writes go to a `.tmp` file and then `os.replace`, so Ctrl-C
mid-save leaves either the old wardrobe or the new one, never half of each.
`data/style_memory.json` is gitignored — it is one user's closet, not evidence.
`python memory.py` prints the file and where it lives.

**Evidence** — full transcript in `results/style_memory_demo.txt`:

    $ python app.py ask 'vintage graphic tee under $30, size M' --memory
    (style memory on — 0 remembered purchase(s) in data/style_memory.json)
      Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop
      + remembered: Y2K Baby Tee — Butterfly Print (lst_002)

    $ python app.py ask 'baggy jeans under $40' --memory
    (style memory on — 1 remembered purchase(s) in data/style_memory.json)
      Found:    Baggy Carpenter Jeans — Dark Wash — $36.0 on depop
      Outfit:   ... White ribbed tank top (w_003) ... Chunky white sneakers (w_007) ...
      + remembered: Baggy Carpenter Jeans — Dark Wash (lst_031)

    $ python app.py ask 'vintage graphic tee under $30, size M' --memory
    (style memory on — 2 remembered purchase(s) in data/style_memory.json)
      Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop
      (already remembered — nothing new added)

    $ python app.py wardrobe
    Remembered purchases: .../data/style_memory.json

    id       category     name
    ------------------------------------------------------------------------------
    lst_002  tops         Y2K Baby Tee — Butterfly Print
                          Remembered from depop at $18, excellent condition
    lst_031  bottoms      Baggy Carpenter Jeans — Dark Wash
                          Remembered from depop at $36, good condition

    2 item(s). Clear them with: python app.py forget

Same two calls looked at from inside the session (`session["memory"]`, `path`
left out; the file already held `lst_002` and `lst_031` when this started):

    flagless run -> {"requested": false, "items_before": 0, "items_owned": 10,
                     "used_memory": false, "added": null}      # file: 2 items → 2
    memory run   -> {"requested": true,  "items_before": 2, "items_owned": 12,
                     "used_memory": true,  "added": {"id": "lst_006", ...}}   # 2 → 3

`items_owned` 10 → 12 is the read branch firing; `added: null` on the first row
while the file still holds 2 items is the guarantee that a flagless run — an
eval, a `serve.py` request — leaves the state alone.

**Reproduce:** `python app.py forget`, then the four commands above.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. matching query completes | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. impossible query stops early | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. selected item is correctly passed to suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. fit card contains the item's price | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. query with a size successfully matches | 5 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

Source: `results/run_2026-10-08_1114_before.md` 
Produced by `run_eval.py::main`

### matching query completes

- Query: `vintage graphic tee under $30`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 0

Outfit suggestion:

```
Omg, what an absolute score! That Y2K butterfly baby tee is so nostalgic and effortlessly cute. Since it has a fitted, cropped silhouette with those lovely pink and purple tones, we want to play with proportions and lean right into that early 2000s model-off-duty vibe.

Here is your styled look using pieces straight from your wardrobe:

### **The Fit: 2000s Streetwear Contrast**

*   **Top:** Y2K Butterfly Baby Tee (Your new thrift find!)
*   **Bottoms:** Baggy straight-leg jeans, dark wash (`w_001`) — *The tight top + baggy bottom silhouette is peak Y2K.*
*   **Outerwear:** Vintage black denim jacket (`w_006`) — *Throw this on over your shoulders or wear it open to add a little structure and edge.*
*   **Shoes:** Chunky white sneakers (`w_007`) — *Keeps the fit grounded, sporty, and super comfortable for walking around.*
*   **Accessories:** Black crossbody bag (`w_010`) — *Sleek, minimal, and keeps your hands free while tying the black accents of the jacket together.*

**Why it works:** 
The fitted crop of the baby tee balances out the high-waisted, relaxed fit of the dark wash jeans. Tossing on the slightly cropped vintage black denim jacket adds a cool denim-on-denim texture moment without hiding the butterfly graphic, and the chunky sneakers pull the whole streetwear aesthetic together. You're ready for iced coffee runs or a vintage market crawl! 🦋✨
```

Fit card:

```
Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop, and I’m officially obsessed! Paired it with some baggy denim and chunky sneakers for the ultimate 2000s streetwear vibe. 🦋✨
```

Trace:

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {   "description": "vintage graphic tee",   "size": null,   "max_price": 30.0 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] compare_price
      in:  {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee w…
      out: fair
[4] suggest_outfit
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Omg, what an absolute score! That Y2K butterfly baby tee is so nostalgic and effortlessly cute. Since it has a…
[5] create_fit_card
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop, and I’m officially obsessed! Pai…
```

### impossible query stops early

- Query: `designer ballgown size XXS under $5`
- Wardrobe: example

**Try 1**

- stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches 'designer ballgown' at all, whatever the size or price — loosen the wording (try 'tee' or 'top' on its own) and keep the rest as it is.
- selected_item: (none)
- search_results: 0

Trace:

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {   "description": "designer ballgown",   "size": "XXS",   "max_price": 5 }
[2] MCP tool call search_listings
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
[3] no_results
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches 'designer ballgo…
```

### selected item is correctly passed to suggest_outfit

- Query: `vintage blue jeans under $40`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
- search_results: 0

Outfit suggestion:

```
Hey! First of all, incredible score on those vintage Levi's 501s—$38 for a classic medium wash in that condition is an absolute steal. 

Since 501s are the ultimate versatile baseline, I’ve put together an effortless, streetwear-leaning look using pieces you already own. Here is your recipe for the perfect casual-cool outfit:

### **The Outfit Formula: 90s Off-Duty Streetwear**

*   **Top:** **White ribbed tank top (`w_003`)** tucked in to define your waist against the straight-leg cut of the 501s.
*   **Outerwear:** Layer the **Oversized grey crewneck sweatshirt (`w_004`)** right over the tank. Since it drops below the hip, let it slouch loosely for that lived-in, effortless drape. 
*   **Footwear:** **Chunky white sneakers (`w_007`)** to tie in the crisp white of the tank and give the hems of the jeans that ideal slight break/pooling effect.
*   **Accessories:** **Black crossbody bag (`w_010`)** for a sleek, everyday finish.

### **Why it works:**
This look plays on high-low proportions. The fitted white tank contrasts beautifully with the slouchy, oversized grey crewneck, while the vintage medium-wash denim bridges the gap between classic Americana and modern streetwear. It’s comfortable, timeless, and lets those newly thrifted 501s take center stage!
```

Fit card:

```
Scored these vintage Levi's 501s in the perfect medium wash for just $38 over on Depop, and they are officially my new daily uniform! Nothing beats classic denim with that lived-in vintage fade. 👖✨
```

Trace:

```
[1] parse_query
      in:  vintage blue jeans under $40
      out: {   "description": "vintage blue jeans",   "size": null,   "max_price": 40 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage blue jeans', 'size': None, 'max_price': 40.0}
      out: 10 items: Vintage Levi's 501 Jeans — Medium Wash, Baggy Carpenter Jeans — Dark Wash, High-Waisted Denim Shorts — Cutoff … +7 more
[3] compare_price
      in:  {'id': 'lst_001', 'title': "Vintage Levi's 501 Jeans — Medium Wash", 'description': 'Classic 501s in a perfect…
      out: unknown
[4] suggest_outfit
      in:  new_item: {'id': 'lst_001', 'title': "Vintage Levi's 501 Jeans — Medium Wash", 'description': 'Classic 501s in…
      out: Hey! First of all, incredible score on those vintage Levi's 501s—$38 for a classic medium wash in that conditi…
[5] create_fit_card
      in:  new_item: {'id': 'lst_001', 'title': "Vintage Levi's 501 Jeans — Medium Wash", 'description': 'Classic 501s in…
      out: Scored these vintage Levi's 501s in the perfect medium wash for just $38 over on Depop, and they are officiall…
```

### fit card contains the item's price

- Query: `oversized sweatshirt under $25`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Oversized Crewneck Sweatshirt — Vintage Navy ($20.0, thredUp)
- search_results: 0

Outfit suggestion:

```
Hey! Oh, what a find—you can *never* have too many perfectly faded vintage crewnecks, and that navy wash is timeless. At $20, that’s an absolute steal for something with that genuine, lived-in character. 

Since the sweatshirt is an XL and fits intentionally oversized, the trick is to balance out that volume so you look effortlessly cool, not swallowed whole. 

Here is your go-to look using pieces straight from your wardrobe:

### **The Outfit: Casual Streetwear Contrast**

*   **Top:** Your new **Oversized Crewneck Sweatshirt (Vintage Navy)** layered loosely over the **White ribbed tank top** (let just a tiny peek of the white hem or collar show if you want some dimension).
*   **Bottoms:** **Wide-leg khaki trousers** (`w_002`)
*   **Shoes:** **Chunky white sneakers** (`w_007`)
*   **Accessories:** **Black crossbody bag** (`w_010`)

### **Why This Works:**
Pairing the faded navy with the tan/khaki of the wide-leg trousers gives you an incredible, effortless earth-tone and vintage color palette. Because the sweatshirt and the trousers both have a relaxed, roomy fit, it leans into that cool, laid-back skater/minimalist streetwear aesthetic. Tossing on the chunky white sneakers ties the whole fit together and echoes the crispness of the white tank underneath, while the black crossbody bag keeps it functional for everyday wear. 

How are we feeling about this vibe? Ready to wear it out?
```

Fit card:

```
Scored the ultimate vintage faded navy crewneck for just $20 on thredUp, and honestly, I might never take it off. There’s nothing quite like that genuine, lived-in wash and oversized fit. ⚓️✨
```

Trace:

```
[1] parse_query
      in:  oversized sweatshirt under $25
      out: {   "description": "sweatshirt",   "size": "oversized",   "max_price": 25.0 }
[2] MCP tool call search_listings
      in:  {'description': 'sweatshirt', 'size': 'oversized', 'max_price': 25.0}
      out: 1 items: Oversized Crewneck Sweatshirt — Vintage Navy
[3] compare_price
      in:  {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded nav…
      out: unknown
[4] suggest_outfit
      in:  new_item: {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly…
      out: Hey! Oh, what a find—you can *never* have too many perfectly faded vintage crewnecks, and that navy wash is ti…
[5] create_fit_card
      in:  new_item: {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly…
      out: Scored the ultimate vintage faded navy crewneck for just $20 on thredUp, and honestly, I might never take it o…
```

### query with a size successfully matches

- Query: `small denim jacket under $50`
- Wardrobe: example

**Try 1**

- stopped early: yes — No listings matched 'denim jacket' in size small under $50. Nothing comes in size small — 'denim jacket' does exist in M, S, W27, W28, W30 L30, so try one of those or leave the size out.
- selected_item: (none)
- search_results: 0

Trace:

```
[1] parse_query
      in:  small denim jacket under $50
      out: {   "description": "denim jacket",   "size": "small",   "max_price": 50 }
[2] MCP tool call search_listings
      in:  {'description': 'denim jacket', 'size': 'small', 'max_price': 50.0}
      out: [] (empty)
[3] no_results
      in:  {'description': 'denim jacket', 'size': 'small', 'max_price': 50.0}
      out: No listings matched 'denim jacket' in size small under $50. Nothing comes in size small — 'denim jacket' does …
```
---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | matching query completes | 4 of 5 | MET (5/5) | 5/5 clears the at least 4 of 5 gate |
| 2 | impossible query stops early | 5 of 5 | MET (5/5) | 5/5 clears the at least 5 of 5 gate |
| 3 | selected item is correctly passed to suggest_outfit | 5 of 5 | MET (5/5) | 5/5 clears the at least 5 of 5 gate |
| 4 | fit card contains the item's price | 4 of 5 | MET (5/5) | 5/5 clears the at least 4 of 5 gate |
| 5 | query with a size successfully matches | 5 of 5 | MISSED (0/5) | Did not pass on any of the runs |

**Diagnoses**

Criterion 5 failed 5/5 times. This is because the search_listing tool call failed to return any listings despite
there being a valid listing. The tool call worked, but the search_listing function did not correctly find the listing
with size "S" when looking for size "small" from parse listing.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```
% python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: {   "description": "vintage graphic tee",   "size": null,   "max_price": 30 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] compare_price
      in:  {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee w…
      out: fair
[4] suggest_outfit
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Hey bestie! ✨ Oh, you *scored* with this Y2K butterfly baby tee—$18 is an absolute steal for such a classic ea…
[5] create_fit_card
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop! 🦋✨ Paired it with baggy denim an…

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey bestie! ✨ Oh, you *scored* with this Y2K butterfly baby tee—$18 is an absolute steal for such a classic early 2000s piece, and the pink and purple graphic is just so dreamy. 

Since the baby tee is fitted and cropped, the golden rule of styling is to play with proportions by pairing it with something looser on the bottom. Luckily, your wardrobe has the *perfect* match!

Here is your complete styled look:

### 🦋 The "Y2K Streetwear" Look

*   **Top:** Your new **Y2K Butterfly Baby Tee** (`lst_002`)
*   **Bottoms:** **Baggy straight-leg jeans, dark wash** (`w_001`) 
    * *Why it works:* The tight-fitted baby tee paired with these high-waisted, dark wash baggy jeans creates that ultimate authentic 2000s model-off-duty silhouette. Plus, the indigo contrast makes the pink and purple in the butterfly graphic really pop!
*   **Outerwear:** **Vintage black denim jacket** (`w_006`)
    * *Why it works:* Throw this slightly cropped black denim jacket over your shoulders if it gets chilly. It keeps the vintage aesthetic cohesive without hiding the cute baby tee underneath.
*   **Shoes:** **Chunky white sneakers** (`w_007`)
    * *Why it works:* These lean right into the streetwear vibe and tie in the white base of the tee. 
*   **Accessories:** **Black crossbody bag** (`w_010`)
    * *Why it works:* Keeps your essentials handy while keeping that effortless, everyday city-girl aesthetic locked down.

You are officially ready to turn some heads. Go rock it! 🛍️✨

  Fit card: Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop! 🦋✨ Paired it with baggy denim and chunky sneakers for the ultimate 2000s model-off-duty vibe. Thrift magic is real, besties! 🛍️💖

3 model calls this session, 1388 prompt + 483 output tokens
```

**Empty search**

```
% python app.py ask 'vintage graphic tee under $1' --trace
[1] parse_query
      in:  vintage graphic tee under $1
      out: {   "description": "vintage graphic tee",   "size": null,   "max_price": 1.00 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 1.0}
      out: [] (empty)
[3] no_results
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 1.0}
      out: No listings matched 'vintage graphic tee' under $1. Nothing is under $1 — the cheapest match is Mesh Long-Slee…

  No listings matched 'vintage graphic tee' under $1. Nothing is under $1 — the cheapest match is Mesh Long-Sleeve Top — Black at $15 on depop, so raise max_price to about $15.

1 model calls this session, 60 prompt + 37 output tokens
```

**Empty wardrobe**

```
% python app.py ask 'vintage graphic tee under $30' --empty-wardrobe --trace 
(running with an empty wardrobe)
[1] parse_query
      in:  vintage graphic tee under $30
      out: {   "description": "vintage graphic tee",   "size": null,   "max_price": 30 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] compare_price
      in:  {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee w…
      out: fair
[4] suggest_outfit
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Hey babe, congratulations on the score! That Y2K butterfly baby tee is an absolute Depop holy grail. Since it …
[5] create_fit_card
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Living out my 2001 pop star dreams in this vintage butterfly baby tee, scored on Depop for just $18! Paired it…

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey babe, congratulations on the score! That Y2K butterfly baby tee is an absolute Depop holy grail. Since it has that fitted, cropped silhouette and the dreamy pink, purple, and white colorway, we are leaning *fully* into the early 2000s nostalgic aesthetic. 

Since this is the only piece in your wardrobe right now, let’s build a complete, head-turning outfit around it from the ground up. Here is your stylist blueprint:

### 👖 The Bottoms: Low-Rise is Key
To keep that authentic Y2K proportion going, pair this baby tee with **low-rise, wide-leg cargo pants or baggy denim**. 
* **The Look:** A light-wash denim jean with some slight whiskering or distressing will play up the vintage vibe. Alternatively, khaki or olive green parachute cargos will create a cool, contrasting "sweet meets street" look. 
* **Why it works:** The tightness of the baby tee balances the volume of the baggy bottoms—it's the ultimate 2000s silhouette.

### 👟 The Shoes: Chunky & Nostalgic
Don't ruin the vibe with dainty flats! You need some footwear with weight.
* **The Look:** Platform sneakers (think vintage chunky Pumas, retro Adidas Sambas, or even a pair of platform Converse) will ground the outfit. If you want to lean a little more retro-femme, a pair of pink or white kitten heel mules would also be majorly chic.

### 👜 The Bag: The Shoulder Bag
Keep your hands free and your armpit cozy with the quintessential Y2K accessory.
* **The Look:** A small baguette bag in white patent leather, pink nylon, or even a subtle metallic silver. 

### 💍 The Extras: Y2K Details
Since the tee already has a lot of personality with the butterfly graphic, keep the accessories fun but simple:
* **Jewelry:** Chunky pastel butterfly hair clips (bring those pinks and purples up to your hair!), a chunky resin or beaded choker necklace, and maybe some hoop earrings.
* **Layering (Optional):** If it gets chilly, throw an unzipped oversized zip-up hoodie over your shoulders or a little cropped faux-leather jacket.

**Your Style Summary:** You’re wearing a fitted pink-and-purple butterfly baby tee, baggy low-rise cargo jeans, chunky platform sneakers, and a pastel baguette bag. You look like you just stepped out of a 2001 music video, and honestly? Iconic. 🦋✨

  Fit card: Living out my 2001 pop star dreams in this vintage butterfly baby tee, scored on Depop for just $18! Paired it with low-rise cargos and platform kicks for the ultimate Y2K moment. 🦋✨

3 model calls this session, 970 prompt + 627 output tokens
```

**Model unavailable**

```
% python app.py ask 'vintage graphic tee under $30' --trace                 
1 model calls this session

ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

**On the MCP move:** 

<!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

I put the search_listings function into the MCP server, so when agent.py gets search_results
from mcp_client.call_tool() instead of calling the search_listings function directly.

The behavior is unchanged.

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

I refactored `tools.py::search_listings` so that it handles size search more robustly.

**Which failure it was meant to fix:**

Criterion 5 failed because it could not find a listing item with size "S" given
a size constraint "small"

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. matching query completes | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. impossible query stops early | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. selected item is correctly passed to suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. fit card contains the item's price | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. query with a size successfully matches | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

Source: `results/run_2026-10-08_1535_after.md` 
Produced by `run_eval.py::main`

### matching query completes

- Query: `vintage graphic tee under $30`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Outfit suggestion:

```
Omg, major Y2K score! That butterfly baby tee is so nostalgic and the pink and purple tones are going to look amazing on you. Since the tee is super fitted and cropped, the best styling rule here is to play with proportions. 

Here is your go-to look straight out of the early 2000s with a modern streetwear twist:

**The Outfit:**
* **Top:** Y2K Butterfly Baby Tee (*new item!*)
* **Bottoms:** Baggy straight-leg jeans, dark wash (`w_001`)
* **Shoes:** Chunky white sneakers (`w_007`)
* **Accessories:** Black crossbody bag (`w_010`)
* **Outerwear Layer (Optional):** Vintage black denim jacket (`w_006`) thrown over your shoulders if it gets chilly.

**Why it works:**
The contrast is everything! Pairing the ultra-feminine, fitted crop top with your high-waisted, dark wash baggy jeans creates that effortless, quintessential 90s/Y2K model-off-duty silhouette. The chunky white sneakers tie into the white base of the tee, and the black crossbody bag keeps it practical and sleek. 

You're ready to serve looks. 🦋✨
```

Fit card:

```
Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop! 🦋✨ The pink and purple graphic gives major nostalgic vibes, and I'm obsessed with how it fits.
```

Trace:

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {   "description": "vintage graphic tee",   "size": null,   "max_price": 30 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
[3] compare_price
      in:  {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee w…
      out: fair
[4] suggest_outfit
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Omg, major Y2K score! That butterfly baby tee is so nostalgic and the pink and purple tones are going to look …
[5] create_fit_card
      in:  new_item: {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s …
      out: Scored this absolute dream of a Y2K butterfly baby tee for just $18 on Depop! 🦋✨ The pink and purple graphic g…
```

### impossible query stops early

- Query: `designer ballgown size XXS under $5`
- Wardrobe: example

**Try 1**

- stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches 'designer ballgown' at all, whatever the size or price — loosen the wording (try 'tee' or 'top' on its own) and keep the rest as it is.
- selected_item: (none)
- search_results: 0

Trace:

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {   "description": "designer ballgown",   "size": "XXS",   "max_price": 5 }
[2] MCP tool call search_listings
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
[3] no_results
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches 'designer ballgo…
```

### selected item is correctly passed to suggest_outfit

- Query: `vintage blue jeans under $40`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Baggy Carpenter Jeans — Dark Wash ($36.0, depop)
- search_results: 10

Outfit suggestion:

```
Hey! Amazing find on Depop—those 90s baggy carpenter jeans are such a staple, and at $36 with that hammer loop detail? Absolute steal. 

Since the jeans have that heavy, relaxed workwear energy, the trick is to balance out the proportions up top while leaning into that effortless streetwear aesthetic. 

Here is your go-to look using pieces straight from your wardrobe:

### **The Fit: 90s Off-Duty Streetwear**

* **Top:** **White ribbed tank top** (`w_003`)
  * *Why it works:* The fitted silhouette of the ribbed tank creates a sharp, intentional contrast against the super-baggy, low-slung fit of the carpenter jeans. It’s that classic 90s model-off-duty proportion play.
* **Outerwear:** **Oversized grey crewneck sweatshirt** (`w_004`)
  * *Why it works:* Since it drops below the hip, you can wear this draped over your shoulders or throw it on top if there's a chill. It doubles down on the cozy, oversized streetwear vibe without losing the shape of the outfit.
* **Shoes:** **Chunky white sneakers** (`w_007`)
  * *Why it works:* These will stack perfectly over the hems of the wide carpenter legs, keeping the silhouette grounded and effortlessly cool.
* **Accessories:** **Black crossbody bag** (`w_010`)
  * *Why it works:* Keeps it functional, hands-free, and adds a sleek, modern touch to finish off the street style look.

**Styling Pro-Tip:** Since the jeans sit at the waist and have that utilitarian edge, let the white tank tuck in slightly or wear it solo on warmer days with a chunky silver chain if you have one. If you need an extra layer for the evening, toss on that **Vintage black denim jacket** (`w_006`) for a cool denim-on-denim moment (indigo and black go *so* well together). 

How are we feeling about this look? Ready to take those carpenter jeans for a spin?
```

Fit card:

```
Scored these vintage 90s baggy carpenter jeans on Depop for just $36, and the workwear fit is unmatched. Paired them with a classic ribbed tank and chunky sneakers for the ultimate off-duty streetwear look. 🛠️✨ #ThriftFinds #StreetwearStyle #90sFashion
```

Trace:

```
[1] parse_query
      in:  vintage blue jeans under $40
      out: {   "description": "vintage blue jeans",   "size": null,   "max_price": 40 }
[2] MCP tool call search_listings
      in:  {'description': 'vintage blue jeans', 'size': None, 'max_price': 40.0}
      out: 10 items: Baggy Carpenter Jeans — Dark Wash, Vintage Levi's 501 Jeans — Medium Wash, High-Waisted Denim Shorts — Cutoff … +7 more
[3] compare_price
      in:  {'id': 'lst_031', 'title': 'Baggy Carpenter Jeans — Dark Wash', 'description': 'Baggy carpenter jeans with ham…
      out: unknown
[4] suggest_outfit
      in:  new_item: {'id': 'lst_031', 'title': 'Baggy Carpenter Jeans — Dark Wash', 'description': 'Baggy carpenter jean…
      out: Hey! Amazing find on Depop—those 90s baggy carpenter jeans are such a staple, and at $36 with that hammer loop…
[5] create_fit_card
      in:  new_item: {'id': 'lst_031', 'title': 'Baggy Carpenter Jeans — Dark Wash', 'description': 'Baggy carpenter jean…
      out: Scored these vintage 90s baggy carpenter jeans on Depop for just $36, and the workwear fit is unmatched. Paire…
```

### fit card contains the item's price

- Query: `oversized sweatshirt under $25`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Oversized Crewneck Sweatshirt — Vintage Navy ($20.0, thredUp)
- search_results: 1

Outfit suggestion:

```
Hey! Incredible find on that vintage navy crewneck—a genuinely faded, unbranded sweatshirt is the holy grail of thrift shopping, and at $20, you totally won. 

Since it’s an XL and has that great slouchy, lived-in feel, let's lean into an effortless, cool-girl streetwear look using pieces you already own. Here is the outfit formula:

### **The Look: High-Low Casual Prep**

*   **Top:** Your new **Oversized Crewneck Sweatshirt (Vintage Navy)** layered loosely over the **White ribbed tank top** (let the white hem peek out just a tiny bit at the bottom for dimension).
*   **Bottoms:** Your **Wide-leg khaki trousers** (`w_002`). Navy and khaki are a timeless, effortless color combination that feels a bit more elevated than standard denim-on-denim. 
*   **Footwear:** The **Chunky white sneakers** (`w_007`) to keep the vibe fresh, sporty, and balanced against the relaxed fit of the trousers and sweatshirt.
*   **Accessories:** Pull it together with the **Black crossbody bag** (`w_010`) for a touch of everyday structure.

**Why it works:** 
The slouchy volume of the vintage navy sweatshirt paired with the relaxed drape of the wide-leg khaki trousers gives off that perfect relaxed, borrowed-from-the-boys silhouette. Letting the white tank peek out breaks up the navy-and-khaki palette, while the chunky sneakers anchor the whole look with a modern streetwear edge. 

Throw it on, push up the sleeves, and you're out the door!
```

Fit card:

```
Scored the ultimate holy grail thrift find: a genuinely faded vintage navy crewneck with the best slouchy fit for just $20 on thredUp! ✨ Styled it with wide-leg trousers and fresh sneakers for the easiest high-low streetwear fit. Nothing beats the feel of the real vintage deal. 🤍
```

Trace:

```
[1] parse_query
      in:  oversized sweatshirt under $25
      out: {   "description": "sweatshirt",   "size": "oversized",   "max_price": 25 }
[2] MCP tool call search_listings
      in:  {'description': 'sweatshirt', 'size': 'oversized', 'max_price': 25.0}
      out: 1 items: Oversized Crewneck Sweatshirt — Vintage Navy
[3] compare_price
      in:  {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded nav…
      out: unknown
[4] suggest_outfit
      in:  new_item: {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly…
      out: Hey! Incredible find on that vintage navy crewneck—a genuinely faded, unbranded sweatshirt is the holy grail o…
[5] create_fit_card
      in:  new_item: {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly…
      out: Scored the ultimate holy grail thrift find: a genuinely faded vintage navy crewneck with the best slouchy fit …
```

### query with a size successfully matches

- Query: `small denim jacket under $50`
- Wardrobe: example

**Try 1**

- stopped early: no
- selected_item: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
- search_results: 1

Outfit suggestion:

```
Hey! Amazing find on that Wrangler cropped light wash jacket—structured shoulders *and* a blank canvas make it such a versatile piece to add to your rotation. 

Since the jacket is cropped with a great vintage shape, let's play with proportions and lean into a classic 90s streetwear vibe by pairing different shades of denim. 

Here is your styled look:

### **The Outfit: "Double Denim Streetwear"**

*   **Outerwear:** Denim Jacket — Light Wash, Cropped (*Your new thrift find!*)
*   **Top:** White ribbed tank top (`w_003`)
*   **Bottoms:** Baggy straight-leg jeans, dark wash (`w_001`)
*   **Shoes:** Chunky white sneakers (`w_007`)
*   **Accessories:** Black crossbody bag (`w_010`)

### **Why this works:**
*   **The Proportion Play:** Because your new jacket is cropped and has structured shoulders, it pairs *dreamily* with high-waisted, baggy bottoms (`w_001`). The contrast between the fitted crop top and the relaxed, slouchy denim creates that effortless, perfectly balanced silhouette.
*   **The Denim-on-Denim Contrast:** Pairing the light wash jacket with the dark indigo baggy jeans gives you a high-contrast double-denim look that feels very intentional and modern rather than costume-y. 
*   **The Finishing Touches:** The white ribbed tank keeps things clean and minimal underneath, echoing the chunky white sneakers to tie the whole color story together. Throw on your black crossbody bag, and you’re ready to run errands or meet friends looking effortlessly cool.
```

Fit card:

```
Thrifted this structured Wrangler light wash cropped denim jacket for just $42 on Poshmark, and it’s officially my new wardrobe MVP. 🤌✨ Such a classic vintage find with endless styling potential—can't wait to live in this double-denim fit all season long!
```

Trace:

```
[1] parse_query
      in:  small denim jacket under $50
      out: {   "description": "denim jacket",   "size": "small",   "max_price": 50 }
[2] MCP tool call search_listings
      in:  {'description': 'denim jacket', 'size': 'small', 'max_price': 50.0}
      out: 1 items: Denim Jacket — Light Wash, Cropped
[3] compare_price
      in:  {'id': 'lst_007', 'title': 'Denim Jacket — Light Wash, Cropped', 'description': 'Cropped denim jacket in a lig…
      out: unknown
[4] suggest_outfit
      in:  new_item: {'id': 'lst_007', 'title': 'Denim Jacket — Light Wash, Cropped', 'description': 'Cropped denim jacke…
      out: Hey! Amazing find on that Wrangler cropped light wash jacket—structured shoulders *and* a blank canvas make it…
[5] create_fit_card
      in:  new_item: {'id': 'lst_007', 'title': 'Denim Jacket — Light Wash, Cropped', 'description': 'Cropped denim jacke…
      out: Thrifted this structured Wrangler light wash cropped denim jacket for just $42 on Poshmark, and it’s officiall…
```

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->
Refactoring tools.py::search_listings resolved the issue that caused criterion 5 to fail.
By making search_listings more robust (instead of just a string search) to different sizes, 5/5 queries which included a size now passed.

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->
After the fix in Milestone 5, all 5 criteria now pass.

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**

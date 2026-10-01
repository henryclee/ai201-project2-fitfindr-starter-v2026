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
size: str | None - size string
max_price: float | None - maximum price, inclusive
- **Returns:**
A list of matching items (dict) from listings, best match first, or an empty list 
if no matches are found. An item dict contains keys for description, category, style_tags, 
size, etc...
- **When it has nothing:**
Empty list

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

**Where it lives:** `agent.py::run_agent`

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
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
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

I used AI to check my criteria to make sure they were testable.

I used AI to help me write the search_listings tool, especially for the syntax for the score_listing sub function.

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

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
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

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
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



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

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



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

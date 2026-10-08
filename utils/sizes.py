"""
Size normalisation and matching — no model, no dependencies beyond the stdlib.

`data/listings.json` stores size the way a seller types it into a listing form:
"S/M", "XL (oversized)", "W30 L30", "US 8.5", "One Size". The agent's query
parser hands back the way a person says it: "small", "medium", "size 8". A
substring test cannot bridge those two because it has no idea what a size *is*:
"s" is inside "US 7", "l" is inside "W30 L30", and "small" never reaches "S".

So both sides get normalised into a comparable shape first:

    tokens    the alpha labels carried (S / M / XL …), plus OVERSIZE as a fit
              qualifier — a fit word, not a rung on the ladder
    numbers   tagged measurements: ("W", 30.0) waist, ("L", 30.0) inseam,
              ("N", 8.0) an untagged number
    region    "us" / "uk" / "eu" when the string named a shoe scale
    onesize   True for "One Size", "OS", "OSFM", "Free size"

Matching is deliberately strict. An empty result has to keep meaning "the size
really is the wall", because no_results.py probes exactly that to work out which
constraint to blame.

    from utils.sizes import size_matches

    size_matches("small", "S")        → 3   the same size, said differently
    size_matches("S", "S/M")         → 2   a range that covers it
    size_matches("M", "One Size")    → 1   fits-most, so ranked last
    size_matches("XXS", "One Size")  → None  "most" is not the tails of the ladder
    size_matches("s", "US 7")        → None  shoes are not a small top
"""

from __future__ import annotations

import difflib
import re
from typing import NamedTuple

# ── match tiers ───────────────────────────────────────────────────────────────
# Higher sorts first. search_listings() filters on "not None" and orders on the
# number, so a true S outranks an S/M which outranks a One Size that fits.
TIER_ANY = 0       # the request carried no usable size — nothing to filter on
TIER_ONE_SIZE = 1  # satisfied only by a "one size fits most" listing
TIER_RANGE = 2     # shares a label, or agrees on every dimension it states
TIER_EXACT = 3     # both sides normalise to the same size

OVERSIZE = "OVERSIZE"  # a fit qualifier, not a rung on the S–XL ladder

# What "One Size fits most" is actually claiming: the middle of the ladder. The
# tails are outside it — a size XXS body and a size XXL body are exactly the two
# the label is not making a promise to. A one-size garment that genuinely runs
# big says so on the label ("One Size / Oversized"), and that fit qualifier is
# what carries it, rather than widening this set.
ONE_SIZE_COVERS = frozenset({"S", "M", "L"})

# ── vocabulary ────────────────────────────────────────────────────────────────
# Word forms → the canonical label. Single letters are here so "s" and "S" land
# in the same bucket; they are only ever reached by an exact word match, never by
# a substring test, which is what keeps "s" out of "US 7".
_ALPHA_WORDS = {
    "xxxl": "XXXL",
    "xxl": "XXL",
    "2xl": "XXL",
    "xs": "XS",
    "xsmall": "XS",
    "xxs": "XXS",
    "2xs": "XXS",
    "s": "S",
    "small": "S",
    "sm": "S",
    "sml": "S",
    "m": "M",
    "medium": "M",
    "med": "M",
    "md": "M",
    "mid": "M",
    "l": "L",
    "large": "L",
    "lg": "L",
    "xl": "XL",
    "xlarge": "XL",
}

_ALPHA_VOCAB = list(_ALPHA_WORDS)

# Words that turn up in a size field and mean nothing. "one" survives only when
# the "one size" phrase pass missed, so treating it as noise is safe.
_NOISE = frozenset(
    {
        "size", "sizes", "sized", "fit", "fits", "like", "a", "an", "the", "to",
        "of", "in", "or", "and", "is", "it", "run", "runs", "wear", "wears",
        "true", "most", "all", "about", "around", "approx", "approximately",
        "same", "as", "but", "tag", "tags", "say", "says", "said", "one",
        "single", "ladies", "women", "womens", "woman", "men", "mens", "man",
        "missy", "petite", "tall", "regular", "unisex", "junior", "juniors",
        "youth", "boys", "girls", "kid", "kids",
    }
)

_REGIONS = {"us": "us", "usa": "us", "uk": "uk", "eu": "eu", "eur": "eu"}

# Slashes, brackets and every kind of dash become spaces. Dots stay: "8.5" is a
# half size, and 8.5 is not 8.
_SEPARATORS = re.compile(r"[/,()\[\]{}|]|[\u2010\u2011\u2012\u2013\u2014\-]+")

# Multi-word forms collapse to one token before the split, so "extra large" and
# "x-large" arrive as "xl" the same way "xlarge" already does.
_PHRASES = [
    (re.compile(r"\b(?:extra|ex)[\s-]*x?[\s-]*(?:large|lg)\b"), " xl "),
    (re.compile(r"\bx[\s-]+(?:large|lg)\b"), " xl "),
    (re.compile(r"\b(?:extra|ex)[\s-]*x?[\s-]*(?:small|sm)\b"), " xs "),
    (re.compile(r"\bx[\s-]+(?:small|sm)\b"), " xs "),
    (re.compile(r"\b(?:double|treble)[\s-]*x?[\s-]*(?:large|lg)\b"), " xxl "),
    (re.compile(r"\bone[\s-]*size(\s+fits\s*(?:most|all))?\b"), " os "),
    (re.compile(r"\bosfm\b|\bos\b|\bfree[\s-]*size\b"), " os "),
    (re.compile(r"\bover[\s-]*si?zed\b|\bover[\s-]*size\b"), " oversize "),
]

# Order matters: waist and inseam are read out first and cut out of the string,
# so the bare-number pass afterwards cannot mistake "W30 L30" for two shoe sizes.
_WAIST = re.compile(r"\bw(?:aist)?[\s-]*(\d{2,3})\b")
_LENGTH = re.compile(r"\bl(?:ength)?[\s-]*(\d{2,3})\b")
_REGION_NUM = re.compile(r"\b(us|usa|uk|eu|eur)[\s.-]*(\d{1,2}(?:\.\d)?)\b")
_BARE_NUM = re.compile(r"\b(\d{1,2}(?:\.\d)?)\b")


class ParsedSize(NamedTuple):
    """What a size string actually claims, in comparable form."""

    tokens: frozenset[str]                  # {"S"} · {"S", "M"} · {"XL", OVERSIZE}
    numbers: tuple[tuple[str, float], ...]  # (("W", 30.0), ("L", 30.0))
    region: str | None                      # "us" / "uk" / "eu" on a shoe scale
    has_onesize: bool
    raw: str

    @property
    def core(self) -> set[str]:
        """The alpha labels, without fit qualifiers."""
        return set(self.tokens) - {OVERSIZE}

    @property
    def family(self) -> str:
        """A readable label for what kind of size this is — for traces and tests."""
        kinds = {kind for kind, _ in self.numbers}
        parts = []
        if self.has_onesize:
            parts.append("onesize")
        if self.core:
            parts.append("alpha")
        if "W" in kinds:
            parts.append("waist")
        elif "N" in kinds:
            values = [value for kind, value in self.numbers if kind == "N"]
            shoeish = bool(self.region) or any(value != int(value) for value in values)
            parts.append("shoe" if shoeish else "numeric")
        return "+".join(parts) or "unknown"


def _blank_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """Cut matched spans out so a later pass can't re-read them."""
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + " " + text[end:]
    return text


def parse_size(raw: object) -> ParsedSize | None:
    """
    Normalise one size string — seller-typed or user-spoken — into a ParsedSize.

    Args:
        raw: anything. Sizes arrive as str from the data, but a model can hand
             back an int (8) or a bool, and this gets called over MCP where the
             caller's own normalisation never ran. It is never allowed to raise.

    Returns:
        A ParsedSize, or None when the string carries no size at all — "",
        None, "see description". A None on the listing side means "unlabelled";
        a None on the request side means "nothing to filter on". Not the same
        situation, and size_matches() treats them differently.
    """
    if raw is None:
        return None

    text = _SEPARATORS.sub(" ", str(raw).strip().lower())
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    for pattern, replacement in _PHRASES:
        text = pattern.sub(replacement, text)

    numbers: list[tuple[str, float]] = []
    for pattern, kind in ((_WAIST, "W"), (_LENGTH, "L")):
        found = [(m.group(1), m.span()) for m in pattern.finditer(text)]
        if not found:
            continue
        numbers.extend((kind, float(value)) for value, _ in found)
        text = _blank_spans(text, [span for _, span in found])

    region = None
    match = _REGION_NUM.search(text)
    if match:
        region = _REGIONS[match.group(1)]
        numbers.append(("N", float(match.group(2))))
        text = _blank_spans(text, [match.span()])

    for match in _BARE_NUM.finditer(text):
        numbers.append(("N", float(match.group(1))))
    text = _BARE_NUM.sub(" ", text)

    tokens: set[str] = set()
    has_onesize = False
    for word in text.split():
        if word in _NOISE:
            continue
        if word == "os":
            has_onesize = True
            continue
        if word in ("oversize", "oversized"):
            tokens.add(OVERSIZE)
            continue
        token = _ALPHA_WORDS.get(word)
        if token is None and len(word) >= 4:
            # Typo recovery, gated on length so "xs" can never be "corrected"
            # into "s". Only a word already in the vocabulary can win.
            near = difflib.get_close_matches(word, _ALPHA_VOCAB, n=1, cutoff=0.8)
            token = _ALPHA_WORDS.get(near[0]) if near else None
        if token:
            tokens.add(token)

    if not tokens and not numbers and not has_onesize:
        return None

    return ParsedSize(frozenset(tokens), tuple(numbers), region, has_onesize, str(raw))


def _alpha_tier(requested: ParsedSize, listed: ParsedSize) -> int | None:
    """
    S/M/L/XL against S/M/L/XL.

    A shared label is enough — "S" answers a listing of "S/M", and "S/M" answers
    a listing of "S"; both are the same garment labelled from two ends. What is
    *not* here is any sliding along the ladder: "XS" shares nothing with "S", so
    it comes back None rather than "close enough".

    An "oversized" request has to be honoured by an oversized listing. A plain L
    is not what someone asked for when they asked for oversized.
    """
    if OVERSIZE in requested.tokens and OVERSIZE not in listed.tokens:
        return None

    wanted, on_file = requested.core, listed.core
    if not wanted & on_file:
        return None
    return TIER_EXACT if wanted == on_file else TIER_RANGE


def _numeric_tier(requested: ParsedSize, listed: ParsedSize) -> int | None:
    """
    Waist, inseam and shoe numbers against each other.

    Every dimension the request names has to be either matched exactly or absent
    from the listing (a listing that never states an inseam is not contradicting
    one). A dimension the listing does state and disagrees on is a refusal —
    W30 asked, W32 listed, no.

    An untagged number ("30") is allowed to land on a tagged one ("W30"), which
    is how "size 8" reaches "US 8"; it is ranked below a tagged-for-tagged hit,
    and half sizes never slide into each other.
    """
    if not listed.numbers:
        return None
    if requested.region and listed.region and requested.region != listed.region:
        return None

    wanted = dict(requested.numbers)
    on_file = dict(listed.numbers)
    exact = bool(requested.region) == bool(listed.region)

    for kind, value in wanted.items():
        if kind in on_file:
            if on_file[kind] != value:
                return None
        elif kind == "N" and any(known == value for known in on_file.values()):
            exact = False
        else:
            return None

    if set(on_file) - set(wanted):
        exact = False

    return TIER_EXACT if exact else TIER_RANGE


def size_matches(requested: object, listing_size: object) -> int | None:
    """
    Decide whether a listing's size satisfies a requested size.

    Args:
        requested:     the size that was asked for, in any of the shapes a query
                       parser produces — "small", "M", "size 8", "w30", None.
        listing_size:  the size on the listing, in whatever the seller typed.

    Returns:
        A tier int when it matches — 3 exact, 2 a range or an untagged number
        that covers it, 1 a "One Size" answering a request for S, M or L — or
        None when it does not. TIER_ANY (0) means the request carried nothing
        readable, so there is nothing to filter on; that is not a match claim,
        it is an absence of one, and callers rank those last.

        Families never cross: an alpha request cannot be satisfied by a shoe or a
        waist number, which is the whole reason "s" used to return the US 7
        Mary Janes. A listing with no size on the label is excluded when a size
        was asked for — an absent label cannot prove it fits.
    """
    req = parse_size(requested)
    if req is None:
        return TIER_ANY

    listed = parse_size(listing_size)
    if listed is None:
        return None

    if req.core:
        if listed.core:
            return _alpha_tier(req, listed)
        if listed.has_onesize and OVERSIZE not in req.tokens:
            # "One size fits most", and *most* is the middle of the ladder. A
            # request from either tail stays a refusal: without this gate a
            # search for a graphic tee in XXS survives on one-size belts and
            # hats, and no_results.py loses the "nothing comes in size XXS"
            # diagnosis that only an empty probe can prove.
            return TIER_ONE_SIZE if req.core <= ONE_SIZE_COVERS else None
        return None

    if req.has_onesize:
        # "One size" asked for means one size on the label, not "whatever fits".
        return TIER_EXACT if listed.has_onesize else None

    if req.numbers:
        return _numeric_tier(req, listed)

    if OVERSIZE in req.tokens:
        # The request was only a fit word, so the listing has to carry it too.
        return TIER_RANGE if OVERSIZE in listed.tokens else None

    return TIER_ANY


# ── running it directly ───────────────────────────────────────────────────────
# No model call, so this is the cheap way to see how the matcher reads the real
# data after changing a vocabulary entry.
#
#     python -m utils.sizes

if __name__ == "__main__":
    from utils.data_loader import load_listings

    on_file = sorted({str(item.get("size")) for item in load_listings()})
    print(f"the {len(on_file)} sizes on file, as the matcher reads them\n")
    for size in on_file:
        parsed = parse_size(size)
        if parsed is None:
            print(f"  {size!r:26} → unreadable")
            continue
        print(
            f"  {size!r:26} → {parsed.family:14} "
            f"tokens={sorted(parsed.tokens) or '—'} numbers={parsed.numbers or '—'}"
            f"{f' region={parsed.region}' if parsed.region else ''}"
        )

    REQUESTED = [
        "small", "medium", "large", "extra large", "xs", "xxs", "oversized",
        "one size", "size 8", "w30", "W30 L32", "meium", "free spirit",
    ]
    print("\nrequested size → which sizes on file answer it\n")
    for requested in REQUESTED:
        if parse_size(requested) is None:
            print(f"  {requested!r:15} → unreadable, so no size filter is applied")
            continue
        answers = []
        for size in on_file:
            tier = size_matches(requested, size)
            if tier:
                answers.append(f"{size}({tier})")
        print(f"  {requested!r:15} → {', '.join(answers) or 'nothing'}")



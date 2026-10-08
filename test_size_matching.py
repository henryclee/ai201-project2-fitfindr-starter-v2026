"""
Size-matching tests — criterion 5 in criteria.md ("a query with a size
successfully matches"), and the reason utils/sizes.py exists.

    python -m unittest test_size_matching -v

Two kinds of test here, and the split matters:

    tables        size_matches() against hand-picked pairs — the spec written as
                  data, including the pairs that must NOT match. The old
                  substring filter failed mostly by matching too much, so a suite
                  that only checked positives would have passed it.

    integration   search_listings() against the real data/listings.json, because
                  a matcher that is right in isolation is still wrong if the
                  ordering buries the true match.

No model call anywhere in this file, so it runs offline and costs nothing:
search_listings() reads JSON, and diagnose() re-runs search_listings(). That is
the whole point of the split no_results.py made.
"""

import unittest

import config
from no_results import diagnose
from tools import search_listings
from utils.sizes import (
    TIER_ANY,
    TIER_EXACT,
    TIER_ONE_SIZE,
    TIER_RANGE,
    parse_size,
    size_matches,
)

# ── the spec, as data ─────────────────────────────────────────────────────────
# (requested, size on the listing, expected tier)
#
# The tiers are part of the contract, not an implementation detail: search_listings
# orders results by them, so "S/M answers a small request" and "…but behind the
# listing actually labelled S" are two separate promises.
MATCHES = [
    # same size, said differently — the case that started this
    ("small", "S", TIER_EXACT),
    ("S", "S", TIER_EXACT),
    ("medium", "M", TIER_EXACT),
    ("med", "M", TIER_EXACT),
    ("large", "L", TIER_EXACT),
    ("extra large", "XL", TIER_EXACT),
    ("x-large", "XL", TIER_EXACT),
    ("xl", "XL (oversized)", TIER_EXACT),  # a fit qualifier doesn't move the label
    ("S/M", "S/M", TIER_EXACT),
    # a range answers a single label, and a single label answers a range
    ("S", "S/M", TIER_RANGE),
    ("medium", "S/M", TIER_RANGE),
    ("large", "M/L", TIER_RANGE),
    ("S/M", "S", TIER_RANGE),
    # one size claims to fit most, so it answers an alpha request — last
    ("M", "One Size", TIER_ONE_SIZE),
    ("small", "One Size (adjustable)", TIER_ONE_SIZE),
    ("large", "One Size / Oversized", TIER_ONE_SIZE),
    # one size asked for, one size on the label
    ("one size", "One Size / Oversized", TIER_EXACT),
    ("OSFM", "One Size", TIER_EXACT),
    # a fit word has to be carried by the listing
    ("oversized", "XL (fits oversized)", TIER_RANGE),
    ("oversized", "One Size / Oversized", TIER_RANGE),
    # waist and inseam
    ("w30", "W30", TIER_EXACT),
    ("W30 L30", "W30 L30", TIER_EXACT),
    ("w30", "W30 L30", TIER_RANGE),  # inseam unstated, nothing contradicted
    ("30", "W30", TIER_RANGE),  # untagged number, so a weaker claim
    # shoes
    ("us 8", "US 8", TIER_EXACT),
    ("US 8.5", "US 8.5", TIER_EXACT),
    ("size 8", "US 8", TIER_RANGE),
    ("8", "US 8", TIER_RANGE),
]

# (requested, size on the listing) — every pair here used to match under the
# substring filter. That is what "s returns the Mary Janes" meant in practice.
NO_MATCHES = [
    ("s", "US 7"),  # a shoe is not a small top
    ("small", "US 7"),
    ("l", "W30 L30"),  # an inseam is not a large
    ("large", "W30 L30"),
    ("9", "W29"),  # a bare 9 must not read the 9 out of a waist
    ("xs", "S"),  # no sliding up the ladder
    ("s", "M/L"),  # nor down into a range that excludes it
    ("m", "L/XL"),
    ("8", "US 8.5"),  # half sizes are not close enough
    ("w30", "W32"),
    ("W30 L32", "W30 L30"),  # inseam stated, and it disagrees
    ("us 8", "UK 8"),  # different scales, same number
    ("oversized", "L"),  # the listing doesn't carry the fit that was asked for
    ("m", "oversized"),
    ("one size", "M"),  # a one-size request wants a one-size label
    ("xxs", "One Size"),  # "fits most" is not the tails of the ladder
    ("xs", "One Size (adjustable)"),
    ("xl", "One Size / Oversized"),
    ("XL/XXL", "One Size"),
    ("small", None),  # an unlabelled listing can't prove it fits
    ("large", ""),
]

class TestParseSize(unittest.TestCase):
    """Both sides of the search arrive speaking different vocabularies."""

    def test_every_family_in_the_data_parses(self):
        families = {
            "S": "alpha",
            "small": "alpha",
            "S/M": "alpha",
            "XL (oversized)": "alpha",
            "One Size": "onesize",
            "OSFM": "onesize",
            "Free size": "onesize",
            "W30 L30": "waist",
            "US 8.5": "shoe",
        }
        for raw, family in families.items():
            with self.subTest(size=raw):
                parsed = parse_size(raw)
                self.assertIsNotNone(parsed, f"{raw!r} parsed as nothing")
                self.assertEqual(parsed.family, family)

    def test_numbers_keep_their_tags(self):
        # The tags are what stop "W30 L30" from being read as two shoe sizes.
        self.assertEqual(parse_size("W30 L30").numbers, (("W", 30.0), ("L", 30.0)))
        self.assertEqual(parse_size("US 8").numbers, (("N", 8.0),))
        self.assertEqual(parse_size("US 8").region, "us")

    def test_an_untagged_number_stays_untagged(self):
        # "8" from a query parser must not be dressed up as a US 8. It earns the
        # match in size_matches(), and ranks below one that names its scale.
        parsed = parse_size("8")
        self.assertEqual(parsed.numbers, (("N", 8.0),))
        self.assertIsNone(parsed.region)

    def test_a_fit_qualifier_is_not_a_label(self):
        parsed = parse_size("XL (oversized)")
        self.assertEqual(parsed.core, {"XL"})
        self.assertIn("OVERSIZE", parsed.tokens)

    def test_a_typo_that_could_only_mean_one_size_is_read(self):
        self.assertEqual(parse_size("meium").core, {"M"})

    def test_a_short_token_is_never_corrected_into_another_size(self):
        # "xs" is two letters, so the length gate keeps it out of correction
        # entirely — recovery may fix a mangled word, never move a label.
        self.assertEqual(parse_size("xs").core, {"XS"})

    def test_there_is_nothing_to_parse(self):
        for raw in [None, "", "   ", "see description", "as-is", "vintage"]:
            with self.subTest(size=raw):
                self.assertIsNone(parse_size(raw))

    def test_it_survives_the_wrong_type(self):
        # The MCP path hands over whatever the caller parsed. A size arriving as
        # an int, a bool or None is a normal Tuesday, not a traceback.
        self.assertEqual(parse_size(8).numbers, (("N", 8.0),))
        self.assertIsNone(parse_size(None))
        self.assertIsNone(parse_size(True))


class TestSizeMatches(unittest.TestCase):
    """The pairs that match, and the tiers they match at."""

    def test_matching_pairs(self):
        for requested, listed, expected in MATCHES:
            with self.subTest(requested=requested, listed=listed):
                self.assertEqual(size_matches(requested, listed), expected)

    def test_pairs_that_must_not_match(self):
        for requested, listed in NO_MATCHES:
            with self.subTest(requested=requested, listed=listed):
                self.assertIsNone(size_matches(requested, listed))

    def test_an_unreadable_request_is_no_filter_rather_than_a_false_empty(self):
        # Better to hand back results the user can reject than to claim the
        # catalog is empty. TIER_ANY means "nothing was actually asked".
        for junk in ["free spirit", "???", "whatever you have"]:
            with self.subTest(requested=junk):
                self.assertEqual(size_matches(junk, "US 7"), TIER_ANY)
                self.assertEqual(size_matches(junk, "S"), TIER_ANY)


class TestSearchListingsSizeFilter(unittest.TestCase):
    """The filter wired into the real data, in the real order."""

    def test_small_denim_jacket_returns_the_listing_labelled_s(self):
        # The criterion-5 scenario in README: it came back [] before, because
        # "small" is not a substring of "S".
        results = search_listings("denim jacket", size="small", max_price=50)
        self.assertTrue(results, "no results for a listing that exists")
        self.assertEqual(results[0]["id"], "lst_007")
        self.assertEqual(results[0]["size"], "S")

    def test_s_no_longer_finds_the_mary_janes(self):
        self.assertTrue(search_listings("mary janes"), "the shoes should still exist")
        self.assertEqual(search_listings("mary janes", size="s"), [])

    def test_l_no_longer_finds_the_jeans(self):
        self.assertTrue(search_listings("straight leg jeans"))
        self.assertEqual(search_listings("straight leg jeans", size="l"), [])
        self.assertTrue(search_listings("straight leg jeans", size="w30"))

    def test_the_true_label_outranks_the_range_that_covers_it(self):
        results = search_listings("straight leg", size="w30")
        self.assertTrue(results)
        self.assertEqual(results[0]["size"], "W30")
        self.assertNotIn("US 8", [item["size"] for item in results])

    def test_one_size_accessories_survive_an_alpha_request(self):
        # Strict on families, not strict to the point of losing the item the user
        # can actually buy: a belt and a hat only ever come in one size.
        for query in ("belt", "bucket hat"):
            with self.subTest(query=query):
                results = search_listings(query, size="m")
                self.assertTrue(results, f"{query} vanished against a one-size catalog")
                self.assertTrue(results[0]["size"].startswith("One Size"))

    def test_half_sizes_do_not_slide_into_each_other(self):
        self.assertEqual(search_listings("boots", size="8"), [])
        self.assertEqual([item["id"] for item in search_listings("boots", size="8.5")],
                         ["lst_028"])

    def test_a_named_scale_finds_that_number_only(self):
        sneakers = search_listings("sneakers", size="us 8")
        ids = [item["id"] for item in sneakers]
        self.assertIn("lst_019", ids)
        self.assertNotIn("lst_035", ids)

    def test_xs_does_not_borrow_an_s(self):
        self.assertTrue(search_listings("denim jacket", size="small"))
        self.assertEqual(search_listings("denim jacket", size="xs"), [])

    def test_a_fit_word_still_finds_the_fit(self):
        results = search_listings("crewneck sweatshirt", size="oversized")
        self.assertEqual(results[0]["id"], "lst_012")

    def test_an_unreadable_size_is_not_applied_as_a_filter(self):
        self.assertEqual(
            search_listings("graphic tee", size="free spirit"),
            search_listings("graphic tee"),
        )

    def test_the_other_constraints_still_hold(self):
        results = search_listings("graphic tee", size="l", max_price=30)
        for item in results:
            with self.subTest(item=item["id"]):
                self.assertLessEqual(item["price"], 30)
                self.assertIsNotNone(size_matches("l", item["size"]))
        self.assertLessEqual(len(results), config.SEARCH_RESULT_LIMIT)


class TestEmptyResultsStillDiagnose(unittest.TestCase):
    """
    Why the filter is strict instead of helpful-but-vague.

    no_results.py works out which constraint to blame by lifting one at a time and
    watching whether the search stays empty. If size matching quietly widened to
    "close enough", every probe would return something, the diagnosis would come
    back "size_and_price" or "unknown", and the message would get vaguer than the
    one this whole exercise started from.
    """

    def test_a_size_that_really_is_absent_still_blames_the_size(self):
        self.assertEqual(search_listings("denim jacket", size="xxs", max_price=50), [])
        report = diagnose("denim jacket", size="xxs", max_price=50)
        self.assertEqual(report["cause"], "size")
        self.assertIn("xxs", report["message"])
        self.assertIn("S", report["sizes_on_file"])

    def test_the_wall_is_gone_for_a_size_that_exists(self):
        # The same query in a size the catalog carries. The loop never reaches
        # diagnose now; seen from the probe side, a size probe that finds
        # something is exactly what stops no_results blaming the size.
        report = diagnose("denim jacket", size="small", max_price=50)
        self.assertGreater(report["probes"]["size"], 0)
        self.assertNotEqual(report["cause"], "size")


if __name__ == "__main__":
    unittest.main(verbosity=2)



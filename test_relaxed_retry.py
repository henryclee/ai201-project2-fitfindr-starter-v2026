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

Nothing here exercises run_agent(), because that costs a model call. The loop-level
proof is the before/after trace pair in results/relax_{before,after}.txt.
"""

import unittest

import config
import relax
from no_results import diagnose
from tools import search_listings
from utils.sizes import size_matches

# The query criterion 6 runs, as data — the same words scenarios.py's criterion-6 row
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


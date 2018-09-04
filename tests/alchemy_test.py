import sys
sys.path.insert(0,'..')
import unittest
import copy

from alchemy import (
    Review
)

class ReviewTest(unittest.TestCase):
    def test_is_valid(self):
        good_review = Review()
        good_review.comment = "Lorem ipsum dolor sit amet."
        good_review.ref_knowledge = 2
        good_review.score = 1.7
        self.assertTrue(good_review.is_valid())

        blank = Review()
        self.assertFalse(blank.is_valid())

        short = copy.copy(good_review)
        short.comment = "Lorem ipsum dolor s" # 19
        self.assertFalse(short.is_valid())

        too_dumb = copy.copy(good_review)
        too_dumb.ref_knowledge = 88
        self.assertFalse(too_dumb.is_valid())

        too_smart = copy.copy(good_review)
        too_smart.ref_knowledge = 0
        self.assertFalse(too_smart.is_valid())

        too_nice = copy.copy(good_review)
        too_nice.score = 0.9
        self.assertFalse(too_nice.is_valid())

        too_mean = copy.copy(good_review)
        too_mean.score = 13.2
        self.assertFalse(too_mean.is_valid())

        # todo: a True for either of the conflicts is_valid() regardless of other properties


if __name__ == '__main__':
    unittest.main()
import sys
sys.path.insert(0,'..')
import unittest
import copy
from datetime import datetime

from alchemy import (
    Review
)

class ReviewTest(unittest.TestCase):
    def test_is_valid(self):
        good_review = Review()
        good_review.comment = "Lorem ipsum dolor sit amet."
        good_review.ref_knowledge = 2
        good_review.score = 1.7
        good_review.conflicted = 0
        self.assertTrue(good_review.is_valid())

    	# a blank review is valid, but incomplete:
        blank = Review()
        self.assertTrue(blank.is_valid())

        short = copy.copy(good_review)
        short.comment = "Lorem ipsum dolor s" # 19
        self.assertTrue(short.is_valid())

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

        # being conflicted overrides other constraints:
        too_mean.conflicted = 1
        self.assertTrue(too_mean.is_valid())
        too_dumb.conflicted = 2
        self.assertTrue(too_dumb.is_valid())
    

    def test_is_complete(self):
        good_review = Review()
        good_review.comment = "Lorem ipsum dolor sit amet."
        good_review.ref_knowledge = 2
        good_review.score = 1.7
        good_review.conflicted = 0
        self.assertTrue(good_review.is_complete())

        # blank review is valid, but incomplete:
        blank = Review()
        self.assertFalse(blank.is_complete())

        short = copy.copy(good_review)
        short.comment = "Lorem ipsum dolor s" # 19
        self.assertFalse(short.is_complete())

        missing_score = copy.copy(good_review)
        missing_score.score = None
        self.assertFalse(missing_score.is_complete())

        missing_ref_knowledge = copy.copy(good_review)
        missing_ref_knowledge.ref_knowledge = None
        self.assertFalse(missing_ref_knowledge.is_complete())

        # a conflicted review is already complete:
        blank.conflicted = 1
        self.assertTrue(blank.is_complete())
        missing_score.conflicted = 2
        self.assertTrue(missing_score.is_complete())
        
    
    def test_update_from_json(self):
        review = Review()
        review.id = 7
        review.referee_id = 55
        review.proposal_id = 99
        review.comment = "Lorem ipsum dolor sit amet."
        review.ref_knowledge = 2
        review.score = 1.7
        review.conflicted = 0
        review.last_updated = '2018-09-01 12:00:00.000'

        # assume JSON has quoted values, which need to be cast:
        json = {'id': '7', 'referee_id': '55', 'proposal_id': '99', 'comment': 'PI is clearly an astrologer', 'ref_knowledge': '1', 'score': '5.0', 'conflicted': '1', 'last_updated': '2018-09-01 15:00:00.000'}
        
        review.update_from_json(json)
        
        self.assertEqual(7, review.id)
        self.assertEqual(55, review.referee_id)
        self.assertEqual(99, review.proposal_id)
        self.assertEqual('PI is clearly an astrologer', review.comment)
        self.assertEqual(1, review.ref_knowledge)
        self.assertEqual(5.0, review.score)
        self.assertEqual('2018-09-01 12:00:00.000', review.last_updated) # does not change--handled by sqlalchemy
        self.assertEqual(1, review.conflicted)
        self.assertTrue(review.is_complete())

        # incomplete review should have None fields where appropriate: 
        json = {'id': 7, 'referee_id': 55, 'proposal_id': 99, 'comment': '', 'ref_knowledge': 1, 'score': '', 'conflicted': 0, 'last_updated': '2018-09-01 15:00:00.000'}
        review.update_from_json(json)
        self.assertEqual(None, review.comment)
        self.assertEqual(1, review.ref_knowledge)
        self.assertEqual(None, review.score)
        self.assertEqual(0, review.conflicted)
        self.assertFalse(review.is_complete())

        # JSON missing a field, e.g. referee_id:
        json = {'id': 13, 'proposal_id': 537, 'comment': '', 'ref_knowledge': 1, 'score': '', 'last_updated': '2018-09-01 15:00:00.000'}
        with self.assertRaises(TypeError):
            review.update_from_json(json)
        
        # JSON has a mismatched referee_id or proposal_id:
        json = {'id': '7', 'referee_id': '88', 'proposal_id': '99', 'comment': 'PI is clearly an astrologer', 'ref_knowledge': '1', 'score': '5.0', 'conflicted': '1', 'last_updated': '2018-09-01 15:00:00.000'}
        with self.assertRaises(ValueError):
            review.update_from_json(json)
        json['referee_id'] = 55
        json['proposal_id'] = 100000
        with self.assertRaises(ValueError):
            review.update_from_json(json)

    def test_to_json(self):
        review = Review()
        review.id = 7
        review.referee_id = 55
        review.proposal_id = 99
        review.comment = "Lorem ipsum dolor sit amet."
        review.ref_knowledge = 2
        review.score = 1.7
        review.conflicted = 0
        review.last_updated = datetime(2018, 9, 1, 12, 0, 0, 0)

        expected = {'id': 7, 'referee_id': 55, 'proposal_id': 99, 'comment': 'Lorem ipsum dolor sit amet.', 'ref_knowledge': 2, 'score': 1.7, 'conflicted': 0, 'last_updated': '2018-09-01 12:00:00'}
        self.assertEqual(expected, review.to_json())


if __name__ == '__main__':
    unittest.main()
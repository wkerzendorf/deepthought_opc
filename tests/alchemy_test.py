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

        # todo: a True for either of the conflicts is_valid() regardless of other properties
    

    def test_is_complete(self):
        good_review = Review()
        good_review.comment = "Lorem ipsum dolor sit amet."
        good_review.ref_knowledge = 2
        good_review.score = 1.7
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
    
    def test_from_json(self):
        # assume JSON has quoted values, which need to be cast:
        json = {'id': '13', 'referee_id': '44', 'proposal_id': '537', 'comment': 'PI is clearly an astrologer', 'ref_knowledge': '1', 'score': '5.0', 'last_updated': '2018-09-01 15:00:00.000'}
        received = Review.from_json(json)
        
        self.assertEqual(13, received.id)
        self.assertEqual(44, received.referee_id)
        self.assertEqual(537, received.proposal_id)
        self.assertEqual('PI is clearly an astrologer', received.comment)
        self.assertEqual(1, received.ref_knowledge)
        self.assertEqual(5.0, received.score)
        self.assertEqual('2018-09-01 15:00:00.000', received.last_updated)
        self.assertTrue(received.is_complete())

        # incomplete review should have None fields where appropriate: 
        json = {'id': 13, 'referee_id': 44, 'proposal_id': 537, 'comment': '', 'ref_knowledge': 1, 'score': '', 'last_updated': '2018-09-01 15:00:00.000'}
        received = Review.from_json(json)
        self.assertEqual(13, received.id)
        self.assertEqual(44, received.referee_id)
        self.assertEqual(537, received.proposal_id)
        self.assertEqual(None, received.comment)
        self.assertEqual(1, received.ref_knowledge)
        self.assertEqual(None, received.score)
        self.assertEqual('2018-09-01 15:00:00.000', received.last_updated)
        self.assertFalse(received.is_complete())

        # JSON missing a field, e.g. referee_id:
        json = {'id': 13, 'proposal_id': 537, 'comment': '', 'ref_knowledge': 1, 'score': '', 'last_updated': '2018-09-01 15:00:00.000'}
        with self.assertRaises(TypeError):
            Review.from_json(json)
    
    def test_to_json(self):
        review = Review()
        review.id = 7
        review.referee_id = 55
        review.proposal_id = 99
        review.comment = "Lorem ipsum dolor sit amet."
        review.ref_knowledge = 2
        review.score = 1.7
        review.last_updated = '2018-09-01 12:00:00.000'

        expected = {'id': 7, 'referee_id': 55, 'proposal_id': 99, 'comment': 'Lorem ipsum dolor sit amet.', 'ref_knowledge': 2, 'score': 1.7, 'last_updated': '2018-09-01 12:00:00.000'}
        self.assertEqual(expected, review.to_json())






if __name__ == '__main__':
    unittest.main()
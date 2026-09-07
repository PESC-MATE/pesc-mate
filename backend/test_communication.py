import unittest
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError
from app.api.router import SentenceRequest
from app.services.communication import save_session, statistics


class Cursor(list):
    def sort(self, *_):
        return Cursor(sorted(self, key=lambda row: row['created_at'], reverse=True))


class Collection:
    def __init__(self): self.documents = {}
    def find_one(self, query): return deepcopy(self.documents.get(query['_id']))
    def insert_one(self, document): self.documents[document['_id']] = deepcopy(document)
    def find(self, _query): return Cursor(deepcopy(list(self.documents.values())))


class CommunicationTests(unittest.TestCase):
    def setUp(self):
        self.collection = Collection()
        self.mock = patch('app.services.communication._collection', return_value=self.collection)
        self.mock.start()
    def tearDown(self): self.mock.stop()

    def test_sentence_persistence_and_retry(self):
        request = SentenceRequest(cards=['me', 'water', 'drink'], request_id=uuid4())
        self.assertEqual(save_session(request)['sentence'], '저는 물을 마시고 싶어요.')
        save_session(request)
        self.assertEqual(statistics()['sessions'], 1)
        self.assertEqual(statistics()['selections'], 3)
        request.cards = ['rice', 'eat']
        with self.assertRaises(HTTPException) as caught: save_session(request)
        self.assertEqual(caught.exception.status_code, 409)

    def test_unknown_empty_and_large_inputs(self):
        for cards in ([], ['water'] * 13):
            with self.assertRaises(ValidationError): SentenceRequest(cards=cards, request_id=uuid4())
        with self.assertRaises(HTTPException): save_session(SentenceRequest(cards=['invalid'], request_id=uuid4()))
        self.assertEqual(statistics()['sessions'], 0)

    def test_fallback_preserves_negation_and_duplicates(self):
        result = save_session(SentenceRequest(cards=['water', 'no', 'water'], request_id=uuid4()))
        self.assertEqual(result['sentence'], '물 · 싫어요 · 물')
        self.assertEqual(statistics()['top_cards'][0]['count'], 2)


if __name__ == '__main__': unittest.main()

import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError
from app.api.router import SentenceRequest
from app.services.communication import ensure_demo_history, save_session, statistics


class Cursor(list):
    def sort(self, *_):
        return Cursor(sorted(self, key=lambda row: row['created_at'], reverse=True))


class Collection:
    def __init__(self): self.documents = {}
    def find_one(self, query):
        document = self.documents.get(query['_id'])
        if not document or not all(document.get(key) == value for key, value in query.items()):
            return None
        return deepcopy(document)
    def insert_one(self, document):
        if document['_id'] in self.documents:
            raise DuplicateKeyError('duplicate')
        self.documents[document['_id']] = deepcopy(document)
    def find(self, query):
        def matches(document):
            for key, value in query.items():
                if isinstance(value, dict) and '$gte' in value:
                    if document.get(key) < value['$gte']: return False
                elif document.get(key) != value: return False
            return True
        return Cursor(deepcopy([document for document in self.documents.values() if matches(document)]))
    def count_documents(self, query, limit=0):
        count = len(self.find(query))
        return min(count, limit) if limit else count
    def update_one(self, query, update, upsert=False):
        if query['_id'] not in self.documents and upsert:
            self.documents[query['_id']] = deepcopy(query | update.get('$setOnInsert', {}))


class CommunicationTests(unittest.TestCase):
    def setUp(self):
        self.collection = Collection()
        self.mock = patch('app.services.communication._collection', return_value=self.collection)
        self.mock.start()
    def tearDown(self): self.mock.stop()

    def test_sentence_persistence_and_retry(self):
        request = SentenceRequest(cards=['me', 'water', 'drink'], request_id=uuid4())
        self.assertEqual(save_session(request, 'demo')['sentence'], '저는 물을 마시고 싶어요.')
        save_session(request, 'demo')
        self.assertEqual(statistics('demo')['sessions'], 1)
        self.assertEqual(statistics('demo')['selections'], 3)
        self.assertEqual(statistics('another-user')['sessions'], 0)
        request.cards = ['rice', 'eat']
        with self.assertRaises(HTTPException) as caught: save_session(request, 'demo')
        self.assertEqual(caught.exception.status_code, 409)

    def test_request_id_cannot_expose_another_users_session(self):
        request = SentenceRequest(cards=['water'], request_id=uuid4())
        save_session(request, 'first-user')
        with self.assertRaises(HTTPException) as caught:
            save_session(request, 'second-user')
        self.assertEqual(caught.exception.status_code, 409)

    def test_unknown_empty_and_large_inputs(self):
        for cards in ([], ['water'] * 13):
            with self.assertRaises(ValidationError): SentenceRequest(cards=cards, request_id=uuid4())
        with self.assertRaises(HTTPException): save_session(SentenceRequest(cards=['invalid'], request_id=uuid4()), 'demo')
        self.assertEqual(statistics('demo')['sessions'], 0)

    def test_fallback_preserves_negation_and_duplicates(self):
        result = save_session(SentenceRequest(cards=['water', 'no', 'water'], request_id=uuid4()), 'demo')
        self.assertEqual(result['sentence'], '물 · 싫어요 · 물')
        self.assertEqual(statistics('demo')['top_cards'][0]['count'], 2)

    def test_statistics_can_filter_recent_period(self):
        now = datetime(2026, 9, 8, tzinfo=timezone.utc)
        self.collection.documents = {
            'recent': {'_id': 'recent', 'user_id': 'demo', 'cards': ['water'],
                       'sentence': '물을 주세요.', 'created_at': now - timedelta(days=2)},
            'old': {'_id': 'old', 'user_id': 'demo', 'cards': ['rice'],
                    'sentence': '밥을 주세요.', 'created_at': now - timedelta(days=40)},
        }
        self.assertEqual(statistics('demo', days=7, now=now)['sessions'], 1)
        self.assertEqual(statistics('demo', days=30, now=now)['sessions'], 1)
        self.assertEqual(statistics('demo', now=now)['sessions'], 2)

    def test_guardian_summary_contains_daily_and_attention_data(self):
        now = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
        self.collection.documents = {
            'today': {'_id': 'today', 'user_id': 'demo', 'cards': ['hurt', 'help'],
                      'sentence': '아파요 · 도와주세요', 'created_at': now - timedelta(hours=1)},
            'yesterday': {'_id': 'yesterday', 'user_id': 'demo', 'cards': ['happy'],
                          'sentence': '좋아요', 'created_at': now - timedelta(days=1)},
        }
        result = statistics('demo', now=now)
        self.assertEqual(result['today_sessions'], 1)
        self.assertEqual(result['today_selections'], 2)
        self.assertEqual(len(result['daily_activity']), 7)
        self.assertEqual({item['id'] for item in result['attention']}, {'hurt', 'help'})
        self.assertEqual(result['primary_emotion']['id'], 'hurt')

    def test_demo_history_is_seeded_once(self):
        ensure_demo_history('demo')
        self.assertEqual(statistics('demo')['sessions'], 4)
        ensure_demo_history('demo')
        self.assertEqual(statistics('demo')['sessions'], 4)


if __name__ == '__main__': unittest.main()

import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError
from app.api.router import SentenceRequest
from app.services.communication import CARDS, attach_particle, ensure_demo_history, save_session, sentence, statistics
from app.services.sentence_validation import validate_safety, validate_semantics


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

    def test_default_cards_have_sentence_metadata(self):
        required = {'meaning', 'part_of_speech', 'has_batchim', 'sentence_role'}
        self.assertTrue(all(required <= card.keys() for card in CARDS))
        cards = {card['id']: card for card in CARDS}
        self.assertTrue(cards['water']['has_batchim'])
        self.assertFalse(cards['apple']['has_batchim'])
        self.assertEqual(cards['me']['sentence_role'], 'subject')
        self.assertEqual(cards['go']['part_of_speech'], 'verb')

    def test_particles_follow_batchim_and_sentence_role(self):
        cards = {card['id']: card for card in CARDS}
        self.assertEqual(attach_particle(cards['water'], 'topic'), '물은')
        self.assertEqual(attach_particle(cards['apple'], 'topic'), '사과는')
        self.assertEqual(attach_particle(cards['water'], 'subject'), '물이')
        self.assertEqual(attach_particle(cards['apple'], 'subject'), '사과가')
        self.assertEqual(attach_particle(cards['water'], 'object'), '물을')
        self.assertEqual(attach_particle(cards['apple'], 'object'), '사과를')
        self.assertEqual(attach_particle(cards['water'], 'with'), '물과')
        self.assertEqual(attach_particle(cards['apple'], 'with'), '사과와')

    def test_rule_sentence_uses_roles_and_particles(self):
        self.assertEqual(sentence(['mom', 'happy']), '엄마가 좋아요.')
        self.assertEqual(sentence(['water', 'apple', 'eat']), '물과 사과를 먹고 싶어요.')
        self.assertEqual(sentence(['me', 'home', 'go']), '저는 집에 가고 싶어요.')
        self.assertEqual(sentence(['water', 'no']), '물이 싫어요.')

    def test_semantic_validation_accepts_inflections_and_synonyms(self):
        cards = {card['id']: card for card in CARDS}
        result = validate_semantics(
            [cards['me'], cards['water'], cards['drink']],
            '저는 물을 마시고 싶어요.',
        )
        self.assertTrue(result['passed'])
        negative = validate_semantics([cards['water'], cards['no']], '물을 원하지 않아요.')
        self.assertTrue(negative['passed'])
        missing_subject = validate_semantics([cards['me'], cards['water']], '물을 원하나요?')
        self.assertEqual(missing_subject['missing_card_ids'], ['me'])

    @patch('app.services.communication.generate_sentence')
    def test_generated_sentence_missing_card_meaning_uses_rule(self, mocked_generate):
        mocked_generate.return_value = ('저는 밥을 먹고 싶어요.', 'ollama')
        result = save_session(
            SentenceRequest(cards=['me', 'water', 'drink'], request_id=uuid4()), 'demo',
        )
        self.assertEqual(result['sentence'], '저는 물을 마시고 싶어요.')
        self.assertEqual(result['generation_source'], 'rule')

    @patch('app.services.communication.generate_sentence')
    def test_generated_sentence_preserving_card_meaning_is_kept(self, mocked_generate):
        mocked_generate.return_value = ('저는 물을 마시고 싶어요.', 'ollama')
        result = save_session(
            SentenceRequest(cards=['me', 'water', 'drink'], request_id=uuid4()), 'demo',
        )
        self.assertEqual(result['sentence'], '저는 물을 마시고 싶어요.')
        self.assertEqual(result['generation_source'], 'ollama')

    @patch('app.services.communication.generate_sentence')
    def test_generated_sentence_cannot_drop_negation(self, mocked_generate):
        mocked_generate.return_value = ('물을 원해요.', 'ollama')
        result = save_session(
            SentenceRequest(cards=['water', 'no'], request_id=uuid4()), 'demo',
        )
        self.assertEqual(result['sentence'], '물이 싫어요.')
        self.assertEqual(result['generation_source'], 'rule')

    def test_sentence_safety_flags_harmful_and_personal_content(self):
        self.assertEqual(validate_safety('시 발이라고 욕했어요.')['flags'], ['prohibited_language'])
        self.assertEqual(validate_safety('전화번호는 010-1234-5678이에요.')['flags'],
                         ['personal_data', 'personal_inference'])
        self.assertEqual(validate_safety('장애가 있어서 물을 마셔요.')['flags'], ['personal_inference'])
        self.assertTrue(validate_safety('저는 물을 마시고 싶어요.')['passed'])

    @patch('app.services.communication.generate_sentence')
    def test_unsafe_generated_sentence_uses_safe_rule(self, mocked_generate):
        mocked_generate.return_value = ('저는 물을 마시고 싶어요. 전화번호는 010-1234-5678이에요.', 'ollama')
        result = save_session(
            SentenceRequest(cards=['me', 'water', 'drink'], request_id=uuid4()), 'demo',
        )
        self.assertEqual(result['sentence'], '저는 물을 마시고 싶어요.')
        self.assertEqual(result['generation_source'], 'rule')

    @patch('app.services.communication.generate_sentence')
    def test_unsafe_rule_sentence_is_not_exposed(self, mocked_generate):
        custom = {'id': 'custom:unsafe', 'label': '전화번호는', 'symbol': '🖼️', 'category': '사용자'}
        mocked_generate.return_value = ('전화번호는', 'rule')
        with self.assertRaises(HTTPException) as caught:
            save_session(
                SentenceRequest(cards=['custom:unsafe'], request_id=uuid4()), 'demo', [custom],
            )
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(statistics('demo')['sessions'], 0)

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

    def test_approved_custom_card_can_generate_and_be_counted(self):
        custom = {'id': 'custom:pencil', 'label': '연필', 'symbol': '🖼️', 'category': '학습'}
        result = save_session(
            SentenceRequest(cards=['custom:pencil'], request_id=uuid4()),
            'demo', [custom],
        )
        self.assertEqual(result['sentence'], '연필')
        stats = statistics('demo')
        self.assertEqual(stats['top_cards'][0]['label'], '연필')
        self.assertEqual(stats['categories']['학습'], 1)
        metadata = next(iter(self.collection.documents.values()))['card_metadata']['custom:pencil']
        self.assertEqual(metadata['part_of_speech'], 'noun')
        self.assertTrue(metadata['has_batchim'])
        self.assertEqual(metadata['sentence_role'], 'object')


if __name__ == '__main__': unittest.main()

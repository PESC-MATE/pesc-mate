import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi import HTTPException

from app.services.card_submissions import (
    approved_cards_for, create_submission, image_for, review_submission,
    submissions_for,
)


class Cursor(list):
    def sort(self, key, direction):
        return Cursor(sorted(self, key=lambda row: row[key], reverse=direction < 0))


class Collection:
    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        self.documents.append(deepcopy(document))

    def find_one(self, query):
        return next((deepcopy(document) for document in self.documents
                     if all(document.get(key) == value for key, value in query.items())), None)

    def update_one(self, query, update):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                document.update(deepcopy(update['$set']))
                return

    def find(self, query):
        return Cursor(deepcopy([
            document for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]))


class CardSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.collection = Collection()
        self.audit_collection = Collection()
        self.mock = patch('app.services.card_submissions._collection', return_value=self.collection)
        self.audit_mock = patch('app.services.card_submissions._audit_collection', return_value=self.audit_collection)
        self.mock.start()
        self.audit_mock.start()

    def tearDown(self):
        self.mock.stop()
        self.audit_mock.stop()

    def test_submission_is_pending_and_scoped_to_owner(self):
        saved = create_submission(
            'demo', '연필', '글을 쓰는 도구', '학습', 'private',
            'pencil.png', 'image/png', b'png data',
        )
        self.assertEqual(saved['status'], 'pending')
        self.assertEqual(saved['owner_id'], 'demo')
        self.assertEqual(len(submissions_for('demo')), 1)
        self.assertEqual(submissions_for('another-user'), [])

    def test_submission_rejects_invalid_image_and_visibility(self):
        with self.assertRaises(HTTPException) as image_error:
            create_submission('demo', '연필', '뜻', '학습', 'private', 'x.svg', 'image/svg+xml', b'x')
        self.assertEqual(image_error.exception.status_code, 422)
        with self.assertRaises(HTTPException) as visibility_error:
            create_submission('demo', '연필', '뜻', '학습', 'public', 'x.png', 'image/png', b'x')
        self.assertEqual(visibility_error.exception.status_code, 422)

    def test_admin_approval_exposes_card_without_removing_defaults(self):
        saved = create_submission('demo', '연필', '글을 쓰는 도구', '학습', 'private',
                                  'pencil.png', 'image/png', b'png data')
        approved = review_submission(saved['id'], 'admin', 'approved', '')
        self.assertEqual(approved['status'], 'approved')
        cards = approved_cards_for('demo')
        self.assertEqual(cards[0]['label'], '연필')
        self.assertEqual(approved_cards_for('another-user'), [])
        image, content_type = image_for(saved['id'], {'id': 'demo', 'role': 'user'})
        self.assertEqual((image, content_type), (b'png data', 'image/png'))
        self.assertEqual(len(self.audit_collection.documents), 1)

    def test_rejection_requires_reason_and_prevents_second_review(self):
        saved = create_submission('demo', '연필', '뜻', '학습', 'shared',
                                  'pencil.png', 'image/png', b'png data')
        with self.assertRaises(HTTPException):
            review_submission(saved['id'], 'admin', 'rejected', '')
        review_submission(saved['id'], 'admin', 'rejected', '이미지를 확인해 주세요.')
        with self.assertRaises(HTTPException) as caught:
            review_submission(saved['id'], 'admin', 'approved', '')
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == '__main__':
    unittest.main()

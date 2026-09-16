import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi import HTTPException

from app.services.card_submissions import create_submission, submissions_for


class Cursor(list):
    def sort(self, key, direction):
        return Cursor(sorted(self, key=lambda row: row[key], reverse=direction < 0))


class Collection:
    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        self.documents.append(deepcopy(document))

    def find(self, query):
        return Cursor(deepcopy([
            document for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]))


class CardSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.collection = Collection()
        self.mock = patch('app.services.card_submissions._collection', return_value=self.collection)
        self.mock.start()

    def tearDown(self):
        self.mock.stop()

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


if __name__ == '__main__':
    unittest.main()

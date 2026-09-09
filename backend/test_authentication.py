import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.services.authentication import dashboard_user


class AuthorizationTests(unittest.TestCase):
    def test_user_can_only_read_own_dashboard(self):
        user = {'id': 'demo', 'role': 'user'}
        self.assertEqual(dashboard_user(user), 'demo')
        with self.assertRaises(HTTPException) as caught:
            dashboard_user(user, 'another')
        self.assertEqual(caught.exception.status_code, 403)

    @patch('app.services.authentication.linked_users')
    def test_caregiver_can_only_read_linked_user(self, mocked):
        mocked.return_value = [{'id': 'demo'}]
        caregiver = {'id': 'caregiver', 'role': 'caregiver'}
        self.assertEqual(dashboard_user(caregiver), 'demo')
        with self.assertRaises(HTTPException) as caught:
            dashboard_user(caregiver, 'another')
        self.assertEqual(caught.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()

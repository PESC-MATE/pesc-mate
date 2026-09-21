import unittest
from unittest.mock import patch

from app.services.database import log_crud


class DatabaseLoggingTests(unittest.TestCase):
    @patch('app.services.database.logger')
    def test_read_is_logged_at_debug_level(self, mocked_logger):
        log_crud('READ', 'users', '인증 사용자 조회')

        mocked_logger.debug.assert_called_once_with(
            'DB CRUD | %s | %s%s', 'READ', 'users', ' | 인증 사용자 조회',
        )
        mocked_logger.info.assert_not_called()

    @patch('app.services.database.logger')
    def test_write_is_logged_at_info_level(self, mocked_logger):
        log_crud('CREATE', 'users', '사용자 생성')

        mocked_logger.info.assert_called_once_with(
            'DB CRUD | %s | %s%s', 'CREATE', 'users', ' | 사용자 생성',
        )
        mocked_logger.debug.assert_not_called()


if __name__ == '__main__':
    unittest.main()

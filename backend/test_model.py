import io
import json
import os
import unittest
from unittest.mock import patch

from app.services.model import generate_sentence


class ModelTests(unittest.TestCase):
    def test_disabled_model_uses_rule(self):
        with patch.dict(os.environ, {'OLLAMA_ENABLED': 'false'}):
            self.assertEqual(generate_sentence(['나'], '나'), ('나', 'rule'))

    @patch('app.services.model.urlopen')
    def test_ollama_response_is_used(self, mocked_urlopen):
        response = io.BytesIO(json.dumps({'response': '저는 물을 마시고 싶어요.'}).encode())
        mocked_urlopen.return_value = response
        with patch.dict(os.environ, {'OLLAMA_ENABLED': 'true'}):
            self.assertEqual(generate_sentence(['나', '물', '마시다'], '기본 문장'),
                             ('저는 물을 마시고 싶어요.', 'ollama'))

    @patch('app.services.model.urlopen', side_effect=TimeoutError)
    def test_model_failure_uses_rule(self, _mocked_urlopen):
        with patch.dict(os.environ, {'OLLAMA_ENABLED': 'true'}):
            self.assertEqual(generate_sentence(['나'], '나'), ('나', 'rule'))


if __name__ == '__main__':
    unittest.main()

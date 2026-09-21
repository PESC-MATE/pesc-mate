import io
import json
import os
import unittest
from unittest.mock import patch

from app.services.model import generate_sentence, status
from app.services.sentence_policy import policy_versions, system_prompt


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
        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload['system'], system_prompt())
        self.assertIn('카드에 없는 사람', payload['system'])

    def test_status_exposes_generation_policy_versions(self):
        model_status = status()
        self.assertEqual(model_status['policy_versions'], policy_versions())
        self.assertEqual(set(model_status['policy_versions']),
                         {'persona', 'output_rules', 'rule_engine', 'safety'})

    @patch('app.services.model.urlopen', side_effect=TimeoutError)
    def test_model_failure_uses_rule(self, _mocked_urlopen):
        with patch.dict(os.environ, {'OLLAMA_ENABLED': 'true'}):
            self.assertEqual(generate_sentence(['나'], '나'), ('나', 'rule'))


if __name__ == '__main__':
    unittest.main()

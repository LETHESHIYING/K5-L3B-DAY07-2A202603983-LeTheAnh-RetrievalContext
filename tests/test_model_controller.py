"""Offline contract tests; these do not replace a real provider evaluation."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from local_agent import LocalController


class FakeResponse:
    def __init__(self, content):
        self.content = json.dumps({'choices': [{'message': {'content': content}}],
                                   'usage': {'total_tokens': 10}}).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return self.content


class ModelControllerTests(unittest.TestCase):
    def test_json_mode_and_valid_action(self):
        response = FakeResponse('{"action":"search","query":"history"}')
        with patch('urllib.request.urlopen', return_value=response) as call:
            controller = LocalController('http://localhost:1234/v1', 'model')
            action = controller.decide('question', [])
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(action['query'], 'history')
        self.assertEqual(controller.usage[0]['total_tokens'], 10)

    def test_invalid_or_nonobject_json_is_not_silently_accepted(self):
        for content in ('', '[]', 'not json'):
            with self.subTest(content=content), patch('urllib.request.urlopen', return_value=FakeResponse(content)):
                with self.assertRaises(ValueError):
                    LocalController('http://localhost:1234/v1', 'model').decide('question', [])


if __name__ == '__main__':
    unittest.main()

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer_v13.proposals import OllamaModels
from lab4.scripts.run_v13_part import recover_delivered_responses


class ResponseRecoveryTests(unittest.TestCase):
    def fixture(self, directory):
        payload = dict(model='pinned', prompt='saved prompt', seed=42)
        attempt = dict(http_request=dict(url='http://127.0.0.1:11435/api/generate', payload=payload),
                       response=dict(raw=dict(response='delivered result', done=True)))
        (directory / 'checkpoint.json').write_text(json.dumps(dict(evaluations=[])))
        (directory / 'metadata.json').write_text('{}')
        (directory / 'evaluations.jsonl').write_text(json.dumps(dict(attempts=[attempt])) + '\n')
        (directory / 'interruptions.jsonl').write_text(json.dumps(dict(attempts=[])) + '\n')
        return payload

    def test_recorded_response_does_not_call_model(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            payload = self.fixture(directory)
            with patch.object(OllamaModels, '_post', return_value={'new': True}) as transport:
                state = recover_delivered_responses(directory)
                model = OllamaModels('pinned', 'e5', 'http://127.0.0.1:11435')
                self.assertEqual(model._post('/api/generate', payload)['response'], 'delivered result')
                transport.assert_not_called()
                self.assertEqual(state['reused_responses'], 1)
                self.assertEqual(model._post('/api/generate', payload), {'new': True})
                transport.assert_called_once()

    def test_changed_seed_refuses_to_resample(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            payload = self.fixture(directory)
            with patch.object(OllamaModels, '_post') as transport:
                recover_delivered_responses(directory)
                model = OllamaModels('pinned', 'e5', 'http://127.0.0.1:11435')
                with self.assertRaisesRegex(ValueError, 'refusing to resample'):
                    model._post('/api/generate', dict(payload, seed=43))
                transport.assert_not_called()


if __name__ == '__main__':
    unittest.main()

"""Audit guarantees for preliminary first-response probes without live services."""
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer import benchmark as probes
from lab4.optimizer.metrics import BASELINE_COUNTS
from lab4.optimizer.proposals import Proposal, ProposalError


class BenchmarkTests(unittest.TestCase):
    def fixture(self, root):
        models = root / 'models'
        payload = b'small offline weight fixture'
        digest = hashlib.sha256(payload).hexdigest()
        blob = models / 'blobs' / ('sha256-' + digest)
        blob.parent.mkdir(parents=True)
        blob.write_bytes(payload)
        raw = json.dumps(dict(schemaVersion=2, layers=[dict(
            mediaType='application/vnd.ollama.image.model',
            digest='sha256:' + digest, size=len(payload))])).encode()
        manifest = models / 'manifests/registry.ollama.ai/library/probe/test'
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(raw)
        tags = dict(models=[dict(name='probe:test', digest=hashlib.sha256(raw).hexdigest())])
        baseline = dict(manchester='Class: VideoCardModel\n    Annotations: полный контекст',
                        counts=dict(BASELINE_COUNTS),violations=[dict(code='P13',key='https://example.org/ontologies/videocard#hasMemory')])
        api = lambda endpoint, path: tags if path == '/api/tags' else dict(version='offline-fixture')
        return models, blob, digest, baseline, api

    def test_first_response_failures_are_not_retried_and_audit_matches_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            models, _, digest, baseline, api = self.fixture(root)
            output = root / 'probe'
            raw = [dict(response=text, model='probe:test', done=True,
                        eval_count=11 + index, custom=dict(tokens=[index], text='сырой ответ'))
                   for index, text in enumerate(('bad first', 'valid first', 'bad third'))]
            diagnostic = dict(detail='full parser diagnostic', axiom='broken')
            parse_results = [ProposalError('compact error', diagnostic),
                             Proposal('учебный пример', ['SubClassOf(:A :B)'], []),
                             ProposalError('third response error')]
            with patch.object(probes, 'evaluate', return_value=baseline), patch.object(
                    probes, 'read_api', side_effect=api), patch.object(
                    probes.OllamaModels, '_post', side_effect=raw) as post, patch.object(
                    probes, 'parse_proposal', side_effect=parse_results) as parse, redirect_stdout(StringIO()):
                summary = probes.benchmark(['probe:test'], 'http://offline.invalid/', models, output, count=3)
            self.assertEqual(post.call_count, 3)
            self.assertEqual([call.args[0] for call in parse.call_args_list], [row['response'] for row in raw])
            result = summary['models'][0]
            self.assertEqual((result['count'], result['first_response_correct']), (3, 1))
            self.assertEqual(result['first_response_fraction'], 1 / 3)
            self.assertEqual(result['weights']['sha256'], digest)
            self.assertIn('not T04', summary['kind'])
            self.assertNotIn('acceptance_approved', summary)
            for index, seed in enumerate((1000, 1001, 1002)):
                row = json.loads((output / 'probe-test' / f'{seed}.json').read_text())
                self.assertEqual(row['seed'], seed)
                self.assertEqual(row['response']['raw'], raw[index])
                self.assertEqual(row['request']['payload'], post.call_args_list[index].args[1])
                self.assertEqual(row['request']['url'], 'http://offline.invalid/api/generate')
                self.assertEqual(row['request']['payload']['options'], dict(
                    temperature=.7, top_p=.95, num_predict=2000, num_ctx=32768, seed=seed))
                self.assertIn(baseline['manchester'], row['request']['payload']['prompt'])
                self.assertEqual(row['syntax_valid'], index == 1)
                self.assertGreaterEqual(row['elapsed_seconds'], 0)
            first = json.loads((output / 'probe-test' / '1000.json').read_text())
            self.assertEqual(first['parse_diagnostic'], diagnostic)
            self.assertEqual(json.loads((output / 'summary.json').read_text()), summary)

    def test_service_failure_is_saved_and_aborts_without_success_summary(self):
        failures = [RuntimeError('service offline'),
                    dict(response='partially delivered', model='probe:test', done=False,
                         custom=dict(retain='entire raw response'))]
        for failure in failures:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                models, _, digest, baseline, api = self.fixture(root)
                output = root / 'probe'
                first = dict(response='valid', model='probe:test', done=True)
                with patch.object(probes, 'evaluate', return_value=baseline), patch.object(
                        probes, 'read_api', side_effect=api), patch.object(
                        probes.OllamaModels, '_post', side_effect=[first, failure]) as post, patch.object(
                        probes, 'parse_proposal', return_value=Proposal('why', ['SubClassOf(:A :B)'], [])) as parse, redirect_stdout(StringIO()):
                    with self.assertRaises(RuntimeError):
                        probes.benchmark(['probe:test'], 'http://offline.invalid', models, output, count=3)
                self.assertEqual(post.call_count, 2)
                self.assertEqual(parse.call_count, 1)
                directory = output / 'probe-test'
                row = json.loads((directory / '1001.json').read_text())
                self.assertEqual(row['seed'], 1001)
                self.assertIn('service_error', row)
                self.assertNotIn('syntax_valid', row)
                self.assertGreaterEqual(row['elapsed_seconds'], 0)
                if isinstance(failure, dict):
                    self.assertEqual(row['response']['raw'], failure)
                else:
                    self.assertNotIn('response', row)
                self.assertTrue((directory / '1000.json').exists())
                self.assertFalse((directory / '1002.json').exists())
                self.assertFalse((directory / 'summary.json').exists())
                self.assertFalse((output / 'summary.json').exists())
                weights=json.loads((directory / 'weights.json').read_text())
                self.assertEqual(weights['sha256'],digest)
                self.assertEqual(weights['model'],'probe:test')
                protocol = json.loads((output / 'protocol.json').read_text())
                self.assertNotIn('completed_utc', protocol)

    def test_changed_weight_file_prevents_any_generation_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            models, blob, _, baseline, api = self.fixture(root)
            blob.write_bytes(b'tampered model bytes')
            output = root / 'probe'
            with patch.object(probes, 'evaluate', return_value=baseline), patch.object(
                    probes, 'read_api', side_effect=api), patch.object(probes.OllamaModels, '_post') as post:
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    probes.benchmark(['probe:test'], 'http://offline.invalid', models, output, count=1)
            post.assert_not_called()
            self.assertFalse(list(output.glob('*/1000.json')))
            self.assertFalse((output / 'summary.json').exists())

    def test_existing_output_is_preserved_before_any_service_or_parser_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'existing'
            output.mkdir()
            sentinel = output / '1000.json'
            original = b'{"existing":"audit must remain untouched"}\n'
            sentinel.write_bytes(original)
            with patch.object(probes, 'evaluate') as evaluate, patch.object(
                    probes, 'read_api') as api, patch.object(probes.OllamaModels, '_post') as post:
                with self.assertRaises(FileExistsError):
                    probes.benchmark(['probe:test'], 'http://offline.invalid', Path(temporary), output)
            evaluate.assert_not_called()
            api.assert_not_called()
            post.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), original)
            self.assertEqual(list(output.iterdir()), [sentinel])


if __name__ == '__main__':
    unittest.main()

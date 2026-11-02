"""Debug phase persists across interruptions without changing the main budget."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lab4.optimizer import journal, search
from lab4.optimizer.validator import ValidationResult


class DebugJournalTests(unittest.TestCase):
    def runtime(self, fail_at=None):
        calls = []

        def check(delta):
            calls.append(delta)
            if len(calls) == fail_at:
                raise RuntimeError('debug interruption')
            score = 1.0 + sum(int(axiom) for axiom in delta['add']) / 1000000
            return ValidationResult('valid', F=score)

        return dict(
            validate=check,
            model_generator=lambda delta, rng: dict(
                add=delta['add'] + [str(rng.randrange(100000))], remove=[]),
            inspect=lambda delta: dict(axioms=sorted(delta['add']))), calls

    def test_debug_resume_matches_uninterrupted_and_preserves_phase(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'search.json'
            config.write_text(json.dumps(search.DEFAULTS) + '\n')
            run = root / 'interrupted'
            reference = root / 'reference'
            # These tests isolate journal/search state from actual Java services
            # and concurrent local dependency downloads.
            with patch.object(journal.platform, 'platform', return_value='test platform'), patch.object(journal, 'LIB', root / 'isolated-lib'), patch.object(
                    journal.subprocess, 'run', return_value=SimpleNamespace(stderr='Java test double')):
                runtime, calls = self.runtime(fail_at=14)
                with self.assertRaisesRegex(RuntimeError, 'debug interruption'):
                    journal.start(config, 'model', 100, run, runtime, phase='debug')
                self.assertEqual(len(calls), 14)
                self.assertEqual(json.loads((run / 'checkpoint.json').read_text())['generation'], 0)

                runtime, calls = self.runtime()
                resumed = journal.resume(run, runtime)
                self.assertEqual(len(calls), 24)
                expected = journal.start(config, 'model', 100, reference,
                                         self.runtime()[0], phase='debug')
                self.assertEqual(resumed, expected)
                self.assertEqual(len(resumed.evaluations), 34)
                self.assertEqual(len(resumed.generations), 4)
                self.assertEqual(json.loads((run / 'metadata.json').read_text())['phase'], 'debug')
                self.assertEqual(json.loads((run / 'config.yaml').read_text())['generations'], 20)
                rows = [json.loads(line) for line in (run / 'evaluations.jsonl').read_text().splitlines()]
                self.assertEqual([row['id'] for row in rows], list(range(34)))
                self.assertEqual({row['phase'] for row in rows}, {'debug'})
                archives = list(run.glob('audit-*.jsonl'))
                self.assertEqual(len(archives), 1)
                self.assertEqual(len(archives[0].read_text().splitlines()), 3)

                def forbidden(*args):
                    raise AssertionError('completed debug resumed an evaluation')

                saved_timing = (run / 'timing.json').read_bytes()
                self.assertEqual(journal.resume(run, dict(validate=forbidden, model_generator=forbidden)), resumed)
                self.assertEqual((run / 'timing.json').read_bytes(), saved_timing)

    def test_runtime_builder_receives_phase_from_metadata_on_start_and_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = dict(marker='manifest used by builder test')
            config = root / 'search.json'
            config.write_text(json.dumps(dict(services=manifest)) + '\n')
            run = root / 'debug'
            with patch.object(journal.platform, 'platform', return_value='test platform'), patch.object(journal, 'LIB', root / 'isolated-lib'), patch.object(
                    journal.subprocess, 'run', return_value=SimpleNamespace(stderr='Java test double')), patch(
                    'lab4.optimizer.runtime.build_runtime', return_value=self.runtime()[0]) as builder:
                result = journal.start(config, 'model', 100, run, phase='debug')
                builder.assert_called_once_with(manifest, 100, phase='debug')
                builder.reset_mock()
                self.assertEqual(journal.resume(run), result)
                builder.assert_called_once_with(manifest, 100, phase='debug')


if __name__ == '__main__':
    unittest.main()

"""Factual report checks over synthetic, fully journaled completed runs."""
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote
import re

from lab4.optimizer import analysis, journal
from lab4.optimizer.validator import ValidationResult
from lab4.scripts import report


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.runs = cls.root / 'relocated-runs'
        cls.graphics = cls.root / 'analysis-output'
        cls.graphics.mkdir()
        cls.library_patch = patch.object(journal, 'LIB', cls.root / 'isolated-libraries')
        cls.library_patch.start()
        config = cls.root / 'config.json'
        config.write_text('{}\n')
        results = []
        with patch.object(journal.platform, 'platform', return_value='synthetic-test-platform'), patch.object(
                journal.subprocess, 'run', return_value=SimpleNamespace(stderr='synthetic Java metadata')):
            for mode, first_seed in (('model', 101), ('control', 201)):
                for index in range(5):
                    seed = first_seed + index
                    score = (1.30 if mode == 'model' else 1.01) + index / 100
                    directory = cls.runs / f'{mode}-{seed}'
                    counter = [0]
                    code = 'CONSISTENCY' if mode == 'model' else 'DUPLICATE'
                    def check(delta):
                        counter[0] += 1
                        return ValidationResult('invalid', code, 0.) if counter[0] % 17 == 0 else ValidationResult('valid', F=score)
                    def generate(delta, rng):
                        return dict(add=delta['add'] + [str(rng.getrandbits(32))], remove=[])
                    runtime = dict(validate=check, inspect=lambda delta: dict(axioms=sorted(delta['add'])),
                                   **{mode + '_generator': generate})
                    journal.start(config, mode, seed, directory, runtime)
                    result = analysis.analyze_run(directory, replay=False)
                    result['replay'] = journal.replay(directory, result['best_id'],
                                                     inspect=lambda delta: dict(axioms=sorted(delta['add'])),
                                                     score=lambda delta: score)
                    # Saved source paths deliberately refer to another layout.
                    # Explicit --runs-root must select the relocated journals.
                    result['path'] = 'original-project/runs/' + directory.name
                    results.append(result)
                    stem = f'{mode}-{seed}'
                    (cls.graphics / (stem + '.csv')).write_text('generation,best_F\n0,' + str(score) + '\n')
                    (cls.graphics / (stem + '.png')).write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-graph-fixture')
        cls.data = dict(runs=results, series=analysis.summarize(results))
        cls.source = cls.graphics / 'analysis.json'
        cls.source.write_text(json.dumps(cls.data, allow_nan=False) + '\n')

    @classmethod
    def tearDownClass(cls):
        cls.library_patch.stop()
        cls.temporary.cleanup()

    def output(self):
        directory = Path(tempfile.mkdtemp(prefix='report-output-', dir=self.root))
        return directory / 'EXPERIMENTS.md'

    def altered(self, change):
        data = json.loads(json.dumps(self.data))
        change(data)
        source = self.graphics / ('altered-' + str(random.getrandbits(64)) + '.json')
        source.write_text(json.dumps(data, allow_nan=False))
        return source

    def test_report_uses_actual_counts_and_relative_artifact_links_without_mutating_sources(self):
        def snapshot():
            return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for start in (self.runs, self.graphics) for path in start.rglob('*') if path.is_file()}
        before = snapshot()
        output = self.output()
        with patch('lab4.optimizer.proposals.OllamaModels.propose', side_effect=AssertionError('model called')), patch(
                'lab4.optimizer.proposals.OllamaModels.embed', side_effect=AssertionError('embedding called')):
            report.build_report(self.source, output, self.root, self.runs)
        self.assertEqual(snapshot(), before)
        text = output.read_text()
        self.assertIn('| CONSISTENCY | 50 | 0 | 50 |', text)
        self.assertIn('| DUPLICATE | 0 | 50 | 50 |', text)
        self.assertIn('| Всего | 50 | 50 | 100 |', text)
        self.assertIn('252 разбиения', text)
        self.assertIn(hashlib.sha256(self.source.read_bytes()).hexdigest(), text)
        self.assertIn('не подтверждают автоматически', text)
        self.assertIn('Protégé/OOPS!', text)
        self.assertEqual(text.count('совпадает |'), 10)
        targets = [unquote(target) for target in re.findall(r'\]\(([^)]+)\)', text)]
        self.assertEqual(sum(target.endswith('.png') for target in targets), 10)
        self.assertEqual(sum(target.endswith('.csv') for target in targets), 10)
        for target in targets:
            self.assertFalse(Path(target).is_absolute())
            self.assertTrue((output.parent / target).is_file(), target)

    def test_refuses_stale_summary_or_run_metrics_and_missing_replay(self):
        changes = [lambda data: data['runs'][0].update(best_F=9.),
                   lambda data: data['series'].update(model_median=9.),
                   lambda data: data['runs'][0].update(replay=None),
                   lambda data: data['runs'][0]['replay'].update(F=9.),
                   lambda data: data['runs'].pop()]
        for change in changes:
            with self.subTest(change=change):
                output = self.output()
                with self.assertRaises(report.ReportError):
                    report.build_report(self.altered(change), output, self.root, self.runs)
                self.assertFalse(output.exists())

    def test_missing_graph_is_reported_without_writing_a_fake_report(self):
        graph = self.graphics / 'model-101.png'
        stored = graph.read_bytes()
        graph.unlink()
        output = self.output()
        try:
            with self.assertRaisesRegex(report.ReportError, 'CSV/PNG'):
                report.build_report(self.source, output, self.root, self.runs)
            self.assertFalse(output.exists())
        finally:
            graph.write_bytes(stored)

    def test_existing_output_is_never_overwritten(self):
        output = self.output()
        original = b'previous report must be preserved\n'
        output.write_bytes(original)
        with self.assertRaises(FileExistsError):
            report.build_report(self.source, output, self.root, self.runs)
        self.assertEqual(output.read_bytes(), original)

    def test_unsorted_complete_analysis_keeps_its_original_series_order(self):
        def shuffled(data):
            data['runs'].reverse()
            data['series'] = analysis.summarize(data['runs'])
        output = self.output()
        with redirect_stdout(StringIO()):
            code = report.main(['--analysis', str(self.altered(shuffled)), '--output', str(output),
                                '--project-root', str(self.root), '--runs-root', str(self.runs)])
        self.assertEqual(code, 0)
        self.assertIn('model-105', output.read_text())


if __name__ == '__main__':
    unittest.main()

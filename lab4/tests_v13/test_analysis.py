"""Read-only schema-2 analysis checks using explicitly synthetic fixtures."""
from copy import deepcopy
from dataclasses import asdict
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer_v13 import analysis, journal
from lab4.optimizer_v13.metrics import BASELINE, BASELINE_COUNTS, compute_metrics, fitness
from lab4.tests_v13.test_journal import fake_inspect


def seal(root, checkpoint, rows=None):
    if rows is not None:
        raw = b''.join(journal.encoded(row) + b'\n' for row in rows)
        (root / 'evaluations.jsonl').write_bytes(raw)
        checkpoint['log_sha256'] = journal.digest(raw)
    checkpoint.pop('payload_sha256', None)
    checkpoint['payload_sha256'] = journal.digest(journal.encoded(checkpoint))
    (root / 'checkpoint.json').write_bytes(journal.encoded(checkpoint))


def synthetic_fixture(root, last_generation=20):
    rows = []
    evaluations = []
    history = []
    for generation in range(last_generation + 1):
        new = []
        for _ in range(10 if generation == 0 else 8):
            index = len(rows)
            delta = dict(add=[f'explicitly-synthetic-{i}' for i in range(index + 1)], remove=[])
            reconstruction = fake_inspect(delta)
            metrics = compute_metrics(reconstruction['counts'], graph=reconstruction['graph'])
            score = fitness(metrics, BASELINE)
            candidate = dict(id=index, generation=generation, parents=[],
                             operator='initial' if generation == 0 else 'mutation',
                             delta=delta, status='valid', F=score.F, code=None)
            row = dict(**candidate, schema=journal.SCHEMA, methodology=journal.METHODOLOGY,
                       counts=reconstruction['counts'], graph=reconstruction['graph'],
                       axioms=reconstruction['axioms'], metrics=asdict(metrics),
                       B=score.B, S=score.S, coefficients=score.coefficients,
                       formula_F=score.F, ri=list(score.relative),
                       mode='model', seed=999, elapsed_seconds=.01,
                       attempts=[dict(response='explicitly synthetic response')])
            rows.append(row)
            evaluations.append(candidate)
            new.append(candidate)
        history.append(sorted((history[-1][:2] if generation else []) + new,
                              key=lambda item: (-item['F'], item['id'])))
    (root / 'metadata.json').write_bytes(b'{}')
    checkpoint = dict(schema=journal.SCHEMA, generation=last_generation,
                      evaluations=evaluations, history=history,
                      best=history[-1][0], metadata_sha256=journal.digest(b'{}'))
    seal(root, checkpoint, rows)
    metadata = dict(schema=journal.SCHEMA, methodology=journal.METHODOLOGY,
                    mode='model', seed=999, config_sha256='explicitly-synthetic',
                    phase='debug' if last_generation == 3 else 'main',
                    baseline_metrics=asdict(BASELINE), baseline_counts=BASELINE_COUNTS)
    return checkpoint, rows, metadata


class AnalysisTests(unittest.TestCase):
    def test_full_metrics_and_three_scores_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, rows, metadata = synthetic_fixture(root)
            with patch.object(journal, '_metadata', return_value=metadata):
                result = analysis.analyze_run(root)
            self.assertEqual(len(result['generations']), 21)
            self.assertEqual(result['best_counts'], rows[-1]['counts'])
            self.assertEqual(result['best_metrics'], rows[-1]['metrics'])
            self.assertEqual(result['best_B'], rows[-1]['B'])
            self.assertEqual(result['best_S'], 1)
            self.assertEqual(result['methodology'], journal.METHODOLOGY)
            for generation in result['generations']:
                self.assertEqual(generation['best_F'], generation['best_B'])
                self.assertEqual(generation['median_S'], 1)
            self.assertIsNone(result['replay'])

    def test_incomplete_runs_and_legacy_schemas_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, rows, metadata = synthetic_fixture(root, 3)
            with patch.object(journal, '_metadata', return_value={**metadata, 'phase': 'main'}):
                with self.assertRaisesRegex(ValueError, 'Incomplete main run'):
                    analysis.analyze_run(root)
            with patch.object(journal, '_metadata', return_value={**metadata, 'schema': 1}):
                with self.assertRaisesRegex(ValueError, 'schema'):
                    analysis.analyze_run(root)
            rows[0]['schema'] = 1
            seal(root, checkpoint, rows)
            with patch.object(journal, '_metadata', return_value=metadata):
                with self.assertRaisesRegex(ValueError, 'Row schema'):
                    analysis.analyze_run(root)

    def test_checksum_and_metric_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, rows, metadata = synthetic_fixture(root, 3)
            with patch.object(journal, '_metadata', return_value=metadata):
                with (root / 'evaluations.jsonl').open('ab') as output:
                    output.write(b'{}\n')
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    analysis.analyze_run(root)
                seal(root, checkpoint, rows)
                rows[0]['metrics']['structural']['D1'] += 1
                seal(root, checkpoint, rows)
                with self.assertRaisesRegex(ValueError, 'metrics/components'):
                    analysis.analyze_run(root)

    def test_population_ranking_and_monotonicity_still_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, rows, metadata = synthetic_fixture(root, 3)
            checkpoint['history'][1][0], checkpoint['history'][1][1] = checkpoint['history'][1][1], checkpoint['history'][1][0]
            seal(root, checkpoint)
            with patch.object(journal, '_metadata', return_value=metadata):
                with self.assertRaisesRegex(ValueError, 'rank'):
                    analysis.analyze_run(root)

    def test_debug_budget_projection_and_main_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, metadata = synthetic_fixture(root, 3)
            with patch.object(journal, '_metadata', return_value=metadata), \
                 patch.object(analysis, 'timing_summary', return_value=dict(wall_clock_seconds=680)):
                result = analysis.analyze_run(root)
            self.assertEqual(len(result['generations']), 4)
            self.assertEqual(result['t04']['model_requests'], 34)
            self.assertEqual(result['t04']['projected_850_evaluation_seconds'], 17000)
            with self.assertRaisesRegex(ValueError, 'Debug runs'):
                analysis.summarize([result])

    def test_csv_png_and_best_json_include_full_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, metadata = synthetic_fixture(root, 3)
            with patch.object(journal, '_metadata', return_value=metadata):
                result = analysis.analyze_run(root)
            analysis.export_run(result, root / 'output')
            with (root / 'output/model-999.csv').open() as source:
                reader = csv.DictReader(source)
                self.assertTrue({'best_F', 'best_B', 'best_S', 'median_F', 'median_B', 'median_S'} <= set(reader.fieldnames))
                self.assertEqual(len(list(reader)), 4)
            self.assertTrue((root / 'output/model-999.png').read_bytes().startswith(b'\x89PNG'))
            best = json.loads((root / 'output/model-999-best.json').read_text())
            self.assertIn('CY2', best['best_metrics']['structural'])
            self.assertEqual(best['best_S'], 1)

    def test_exact_mann_whitney_with_ties_and_nonsignificance(self):
        self.assertAlmostEqual(analysis.mann_whitney([2.] * 5, [1.] * 5)['p'], 1 / 252)
        equal = analysis.mann_whitney([1.] * 5, [1.] * 5)
        self.assertEqual(equal['p'], 1)
        self.assertFalse(equal['significant'])

    def test_series_timing_preserves_gaps_and_active_time(self):
        result = analysis.series_timing([
            dict(wall_clock_seconds=1, active_seconds=1, started_at=0, completed_at=1),
            dict(wall_clock_seconds=1, active_seconds=1, started_at=30000, completed_at=30001),
        ])
        self.assertEqual(result['seconds'], 30001)
        self.assertEqual(result['active_seconds'], 2)
        self.assertFalse(result['within_eight_hours'])
        self.assertIsNone(analysis.series_timing([{}])['within_eight_hours'])


if __name__ == '__main__':
    unittest.main()

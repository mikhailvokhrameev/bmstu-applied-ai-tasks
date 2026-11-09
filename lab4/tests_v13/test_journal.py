"""Journal integration uses deterministic synthetic proposals, never a model."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer_v13 import journal
from lab4.optimizer_v13.metrics import BASELINE, BASELINE_COUNTS, BASELINE_GRAPH, compute_metrics, fitness
from lab4.optimizer_v13.validator import ValidationResult


def fake_inspect(delta, graph=None):
    graph = deepcopy(BASELINE_GRAPH if graph is None else graph)
    counts = dict(BASELINE_COUNTS, Individuals=41)
    counts['H'] = len({tuple(edge) for edge in graph['edges']})
    counts['A'] += len(delta['add'])
    counts['Al'] += len(delta['add'])
    return dict(axioms=sorted(delta['add']), counts=counts, graph=graph)


def fake_runtime(fail=None, graph=None, invalid=False):
    calls = [0]
    def check(delta):
        calls[0] += 1
        if calls[0] == fail:
            raise RuntimeError('synthetic interruption')
        result = fake_inspect(delta, graph)
        metrics = compute_metrics(result['counts'], graph=result['graph'])
        score = fitness(metrics, BASELINE)
        return ValidationResult('invalid' if invalid else 'valid',
                                code='SYNTHETIC' if invalid else None,
                                F=0. if invalid else score.F,
                                metrics=metrics, relative=score.relative)
    generator = lambda delta, rng: dict(add=delta['add'] + ['synthetic-' + str(rng.randrange(10**8))], remove=[])
    return dict(validate=check, control_generator=generator, model_generator=generator,
                inspect=lambda delta: fake_inspect(delta, graph))


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.json'
        self.config.write_text('{}')
        self.pin = patch.object(journal, 'source_inventory', return_value={'synthetic.py': 'fixed'})
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def start_debug(self, runtime=None):
        run = self.root / 'run'
        journal.start(self.config, 'control', 100, run, runtime or fake_runtime(), phase='debug')
        return run

    def rows(self, run):
        return [json.loads(line) for line in (run / 'evaluations.jsonl').read_text().splitlines()]

    def write_rows(self, run, rows):
        (run / 'evaluations.jsonl').write_bytes(b''.join(journal.encoded(row) + b'\n' for row in rows))

    def test_full_metadata_and_all_metrics_are_saved(self):
        run = self.start_debug()
        metadata = journal._metadata(run)
        self.assertEqual(metadata['schema'], 2)
        self.assertEqual(metadata['methodology'], 'videocard-lr4-v1.3')
        self.assertEqual(metadata['baseline_metrics'], asdict(BASELINE))
        rows = self.rows(run)
        self.assertEqual(len(rows), 34)
        for row in rows:
            self.assertEqual(row['schema'], 2)
            self.assertEqual(row['metrics']['structural']['CY1'], 0)
            self.assertEqual(row['S'], 1)
            self.assertAlmostEqual(row['F'], row['B'])
            self.assertTrue(row['counts'])
            self.assertTrue(row['graph'])
            self.assertEqual(set(row['coefficients']), {'KD', 'KW', 'KT', 'KI'})

    def test_resume_preserves_rng_and_all_170_evaluations(self):
        run = self.root / 'interrupted'
        with self.assertRaisesRegex(RuntimeError, 'synthetic interruption'):
            journal.start(self.config, 'control', 201, run, fake_runtime(fail=14))
        actual = journal.resume(run, fake_runtime())
        expected = journal.start(self.config, 'control', 201, self.root / 'complete', fake_runtime())
        self.assertEqual(actual, expected)
        self.assertEqual([row['id'] for row in self.rows(run)], list(range(170)))
        audits = list(run.glob('audit-*.jsonl'))
        self.assertEqual(len(audits), 1)
        self.assertEqual(len(audits[0].read_text().splitlines()), 3)
        replay = journal.replay(run, audits[0].stem + ':12', inspect=fake_inspect)
        self.assertTrue(replay['matches'])

    def test_completed_resume_does_not_evaluate_again(self):
        run = self.start_debug()
        before = (run / 'timing.json').read_bytes()
        def forbidden(*args):
            raise AssertionError('completed run was evaluated again')
        with (run / 'evaluations.jsonl').open('ab') as output:
            output.write(b'{torn')
        result = journal.resume(run, dict(validate=forbidden, control_generator=forbidden))
        self.assertEqual(len(result.evaluations), 34)
        self.assertEqual((run / 'timing.json').read_bytes(), before)
        self.assertEqual(len(list(run.glob('audit-*.jsonl'))), 1)

    def test_replay_never_calls_models_and_detects_tampering(self):
        run = self.start_debug()
        with patch('lab4.optimizer_v13.proposals.OllamaModels.propose', side_effect=AssertionError('LLM called')), \
             patch('lab4.optimizer_v13.proposals.OllamaModels.embed', side_effect=AssertionError('E5 called')):
            result = journal.replay(run, 3, inspect=fake_inspect)
        self.assertTrue(result['matches'])
        self.assertTrue(result['counts_match'])
        self.assertTrue(result['metrics_match'])
        self.assertTrue(result['components_match'])
        self.assertFalse(result['semantic_validation_repeated'])
        rows = self.rows(run)
        rows[3]['counts']['A'] += 1
        self.write_rows(run, rows)
        result = journal.replay(run, 3, inspect=fake_inspect)
        self.assertFalse(result['counts_match'])
        self.assertFalse(result['matches'])

    def test_replay_float_tolerance_and_exact_integer_metrics(self):
        run = self.start_debug()
        original = self.rows(run)
        rows = deepcopy(original)
        rows[0]['metrics']['M1'] += .0009
        rows[0]['B'] += .0009
        rows[0]['F'] += .0009
        self.write_rows(run, rows)
        self.assertTrue(journal.replay(run, 0, inspect=fake_inspect)['matches'])
        rows[0]['metrics']['M1'] += .0002
        self.write_rows(run, rows)
        self.assertFalse(journal.replay(run, 0, inspect=fake_inspect)['matches'])
        rows = deepcopy(original)
        rows[0]['metrics']['structural']['D1'] += 1
        self.write_rows(run, rows)
        self.assertFalse(journal.replay(run, 0, inspect=fake_inspect)['matches'])

    def test_cyclic_candidates_keep_undefined_metrics_and_zero_fitness(self):
        graph = deepcopy(BASELINE_GRAPH)
        vertex = graph['vertices'][0]
        graph['edges'].append([vertex, vertex])
        run = self.start_debug(fake_runtime(graph=graph, invalid=True))
        row = self.rows(run)[0]
        self.assertEqual(row['F'], 0)
        self.assertGreater(row['B'], 0)
        self.assertIsNone(row['S'])
        self.assertIsNone(row['metrics']['structural']['D1'])
        self.assertGreater(row['metrics']['structural']['CY1'], 0)
        result = journal.replay(run, 0, inspect=lambda delta: fake_inspect(delta, graph))
        self.assertTrue(result['matches'])
        self.assertFalse(result['structure_valid'])
        rows = self.rows(run)
        rows[0]['status'] = 'valid'
        self.write_rows(run, rows)
        self.assertFalse(journal.replay(run, 0, inspect=lambda delta: fake_inspect(delta, graph))['matches'])

    def test_real_baseline_graph_roundtrips_through_journal_and_replay(self):
        from lab4.optimizer_v13.bridge import CORE, evaluate
        from lab4.optimizer_v13.validator import validate
        from lab4.optimizer_v13.search import Candidate
        delta = dict(add=[], remove=[])
        reconstruction = evaluate(CORE, [], [])
        validation = validate(delta, duplicate_checker=lambda entities: False)
        self.assertEqual(validation.status, 'valid', validation.detail)
        def one_test_record(config, mode, seed, **kwargs):
            candidate = Candidate(0, 0, (), 'initial', delta, 'valid', validation.F)
            config['runtime']['on_evaluation'](candidate, validation, .01, None)
            return candidate
        run = self.root / 'ONE-RECORD-ENGINE-INTEGRATION-TEST'
        with patch.object(journal.search, 'run', side_effect=one_test_record):
            journal.start(self.config, 'control', 100, run,
                          dict(control_generator=lambda parent, rng: delta,
                               inspect=lambda value: evaluate(CORE, value['add'], value['remove'])),
                          phase='debug')
        result = journal.replay(run, 0)
        self.assertTrue(result['matches'], result)
        self.assertEqual(result['F'], 1)
        self.assertEqual(result['S'], 1)
        self.assertEqual(self.rows(run)[0]['counts'], reconstruction['counts'])

    def test_source_change_and_legacy_schema_are_rejected(self):
        run = self.start_debug()
        with patch.object(journal, 'source_inventory', return_value={'synthetic.py': 'changed'}):
            with self.assertRaisesRegex(journal.JournalError, 'implementation or prompt changed'):
                journal.resume(run, fake_runtime())
        metadata = json.loads((run / 'metadata.json').read_text())
        metadata['schema'] = 1
        raw = journal.encoded(metadata)
        (run / 'metadata.json').write_bytes(raw)
        (run / 'metadata.sha256').write_text(journal.digest(raw))
        with self.assertRaisesRegex(journal.JournalError, 'schema'):
            journal.resume(run, fake_runtime())

    def test_checkpoint_corruption_is_rejected(self):
        run = self.start_debug()
        (run / 'checkpoint.json').write_text('{')
        with self.assertRaisesRegex(journal.JournalError, 'checkpoint'):
            journal.resume(run, fake_runtime())


if __name__ == '__main__':
    unittest.main()

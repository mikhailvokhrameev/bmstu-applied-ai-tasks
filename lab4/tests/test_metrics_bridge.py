import hashlib
import json
from pathlib import Path
import unittest
from collections import Counter
import tempfile
from unittest.mock import patch
from lab4.optimizer.metrics import compute_metrics, fitness, BASELINE_COUNTS, BASELINE, MetricError
from lab4.optimizer.bridge import evaluate, BridgeError

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / 'lab2/ontology/videocard.owl'

class MetricsTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual([round(v, 3) for v in BASELINE.values[:5]], [.333,.667,.467,.133,.536])
        self.assertAlmostEqual(fitness(BASELINE, BASELINE).F, 1)
    def test_reference_fixtures(self):
        expected = json.loads((ROOT/'lab4/assessment/fixtures/expected.json').read_text())
        for case in expected['cases']:
            with self.subTest(case=case['fixture']):
                result = evaluate(ROOT/f"lab4/assessment/fixtures/{case['fixture']}.ofn", [], [])
                for key in ('C','H','Po','Pd','E','Al','A','Q'):
                    self.assertEqual(result['counts'][key], case[key])
                self.assertEqual(Counter(v['code'] for v in result['violations']),
                                 Counter({k:case[k] for k in ('P04','P08','P10','P11','P13','P22') if case[k]}))
                metrics = compute_metrics(result['counts'], 10)
                self.assertAlmostEqual(fitness(metrics, BASELINE).F, case['F'], places=9)
    def test_zero_denominators(self):
        for updates in ({'C':0}, {'H':0,'Po':0}, {'A':0}):
            with self.assertRaises(MetricError):
                compute_metrics(dict(BASELINE_COUNTS, **updates), 10)
    def test_nonfinite_and_invalid_counts(self):
        for value in (float('nan'), float('inf'), -1, True, 1.5):
            with self.assertRaises(MetricError):
                compute_metrics(dict(BASELINE_COUNTS, C=value), 10)

class BridgeTests(unittest.TestCase):
    def test_core_counts(self):
        result = evaluate(CORE, [], [])
        self.assertEqual(result['counts'], dict(BASELINE_COUNTS, Individuals=41, SubClassOf=16, EquivalentClasses=2, DisjointClasses=3))
        self.assertTrue(result['core_preserved'])
        self.assertEqual(len(result['violations']), 10)
    def test_add_remove_and_repeat_without_mutation(self):
        before = hashlib.sha256(CORE.read_bytes()).hexdigest()
        ax = 'SubClassOf(:GraphicsCard :NewCategory)'
        added = evaluate(CORE, [ax], [])
        self.assertEqual(added['counts']['A'], 473)
        self.assertEqual(added, evaluate(CORE, [ax, ax], []))
        removed = evaluate(CORE, [ax], [ax])
        self.assertEqual(removed, evaluate(CORE, [], []))
        self.assertEqual(hashlib.sha256(CORE.read_bytes()).hexdigest(), before)
    def test_core_preservation_uses_axioms_not_serialization(self):
        with tempfile.TemporaryDirectory() as directory:
            alternate = Path(directory)/'core.owl'
            alternate.write_bytes(CORE.read_bytes()+b'\n')
            result = evaluate(alternate, [], [])
            self.assertTrue(result['core_preserved'])
            self.assertEqual(result['counts']['A'],472)
            with self.assertRaisesRegex(BridgeError, 'CORE_REMOVAL'):
                evaluate(alternate, [], ['Declaration(Class(<https://example.org/ontologies/videocard#VideoCardModel>))'])

    def test_core_removal_rejected(self):
        with self.assertRaisesRegex(BridgeError, 'CORE_REMOVAL'):
            evaluate(CORE, [], ['Declaration(Class(:VideoCardModel))'])
    def test_bad_syntax_and_missing_file_are_errors(self):
        for path, add in ((CORE, ['garbage']), (ROOT/'missing.owl', [])):
            with self.assertRaises(BridgeError):
                evaluate(path, add, [])
    def test_transport_failures_rejected(self):
        for output in ('{}', 'not-json', '{"core_preserved":true,"counts":{}}', json.dumps(dict(core_preserved=True, counts=BASELINE_COUNTS, axioms=[42], violations=[{}]*10))):
            with patch('lab4.optimizer.bridge._run', return_value=output):
                with self.assertRaises(BridgeError):
                    evaluate(CORE, [], [])

    def test_empty_or_multiple_axiom_item_rejected(self):
        for ax in ('', 'Declaration(Class(:A)) Declaration(Class(:B))'):
            with self.assertRaises(BridgeError):
                evaluate(CORE, [ax], [])

if __name__ == '__main__':
    unittest.main()

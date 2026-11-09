import unittest
from unittest.mock import patch

from lab4.optimizer_v13 import bridge
from lab4.optimizer_v13.metrics import BASELINE, compute_metrics, fitness


class EngineTests(unittest.TestCase):
    def setUp(self):
        bridge.clear_caches()

    def tearDown(self):
        bridge.clear_caches()

    def test_baseline_and_final_graph_are_exactly_equal(self):
        baseline = bridge.evaluate(bridge.CORE, [], [])
        final = bridge.evaluate(bridge.ROOT / 'lab4/ontology/videocard.owl', [], [])
        self.assertEqual(baseline['graph'], final['graph'])
        self.assertEqual((len(final['graph']['vertices']), len(final['graph']['edges'])), (15, 5))
        measured = fitness(compute_metrics(final['counts'], graph=final['graph']), BASELINE)
        self.assertEqual(measured.S, 1)
        self.assertAlmostEqual(measured.F, 1.3207143079447086)

    def test_exact_delta_cache_preserves_response_against_caller_mutation(self):
        first = bridge.evaluate(bridge.CORE, [], [])
        first['graph']['vertices'].append('not-an-ontology-class')
        second = bridge.evaluate(bridge.CORE, [], [])
        self.assertEqual(len(second['graph']['vertices']), 15)
        self.assertEqual(bridge.cache_info()['worker_requests'], 1)
        self.assertEqual(bridge.cache_info()['evaluate_hits'], 1)

    def test_duplicate_annotated_named_edges_are_counted_once(self):
        added = ['SubClassOf(Annotation(rdfs:comment "same edge") :ActiveCooling :CoolingSystem)']
        result = bridge.evaluate(bridge.CORE, added, [])
        self.assertEqual(result['counts']['H'], 5)
        self.assertEqual(len(result['graph']['edges']), 5)
        self.assertEqual(result['counts']['SubClassOf'], 17)

    def test_one_worker_handles_isolated_requests_without_axiom_leaks(self):
        before = bridge.evaluate(bridge.CORE, [], [])
        added = bridge.evaluate(bridge.CORE, ['FunctionalObjectProperty(:usesGPU)'], [])
        after = bridge.evaluate(bridge.CORE, [], [])
        # usesGPU is already functional in this immutable core; use a new class
        # to test a fresh request that really changes the ontology.
        changed = bridge.evaluate(bridge.CORE, ['Declaration(Class(:TemporaryClass))'], [])
        self.assertEqual(after, before)
        self.assertEqual(changed['counts']['C'], before['counts']['C'] + 1)
        self.assertEqual(bridge.java_request('syntax', {'add': [], 'remove': []})['status'], 'ok')
        self.assertTrue(added['core_preserved'])
        self.assertEqual(bridge.evaluate(bridge.CORE, [], [])['counts']['C'], 15)

    def test_bad_request_does_not_poison_following_requests(self):
        with self.assertRaises(bridge.BridgeError):
            bridge.evaluate(bridge.CORE, ['not OWL syntax'], [])
        self.assertEqual(bridge.cache_info()['evaluations'], 0)
        self.assertEqual(bridge.evaluate(bridge.CORE, [], [])['counts']['C'], 15)

    def test_core_identity_is_checked_before_cache_hit(self):
        bridge.evaluate(bridge.CORE, [], [])
        with patch.object(bridge, 'CORE_SHA256', '0' * 64):
            with self.assertRaisesRegex(bridge.BridgeError, 'CORE_CHECKSUM'):
                bridge.evaluate(bridge.CORE, [], [])


if __name__ == '__main__':
    unittest.main()

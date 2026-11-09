from dataclasses import asdict, replace
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

from lab4.optimizer_v13.metrics import (
    BASELINE, BASELINE_COUNTS, BASELINE_GRAPH, MetricError,
    compute_metrics, fitness,
)


def counts_for(graph, **changes):
    return dict(BASELINE_COUNTS, C=len(set(graph['vertices'])),
                H=len({tuple(edge) for edge in graph['edges']}), **changes)


class MetricsV13Tests(unittest.TestCase):
    def test_baseline_full_structural_values_and_fitness(self):
        result = BASELINE.structural
        self.assertEqual((result.N, result.H, result.U), (15, 5, 0))
        self.assertEqual((result.D1, result.D2, result.D3), (2, 6 / 13, 6))
        self.assertEqual((result.W1, result.W2, result.W3), (10, 5.0, 15))
        self.assertEqual((result.T1, result.T2, result.T3), (0, 1 / 3, 0.0))
        self.assertEqual((result.I1, result.I2, result.I3), (1.0, 2 / 3, 0.0))
        self.assertAlmostEqual(result.I4, 1.0465362369445672)
        score = fitness(BASELINE, BASELINE)
        self.assertEqual((score.B, score.S, score.F), (1.0, 1.0, 1.0))
        self.assertEqual(score.coefficients, dict(KD=1, KW=1, KT=1, KI=1))
        self.assertEqual(score.relative, (1, 1, 1, 1, 1, 1))

    def test_baseline_graph_matches_actual_frozen_rdf_xml(self):
        source = Path(__file__).resolve().parents[2] / 'lab2/ontology/videocard.owl'
        root = ET.parse(source).getroot()
        ns = dict(owl='http://www.w3.org/2002/07/owl#',
                  rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                  rdfs='http://www.w3.org/2000/01/rdf-schema#')
        user = 'https://example.org/ontologies/videocard#'
        about = '{' + ns['rdf'] + '}about'
        resource = '{' + ns['rdf'] + '}resource'
        vertices = {node.get(about) for node in root.findall('owl:Class', ns)
                    if node.get(about, '').startswith(user)}
        edges = {(parent.get(resource), node.get(about))
                 for node in root.findall('owl:Class', ns)
                 for parent in node.findall('rdfs:subClassOf', ns)
                 if parent.get(resource) in vertices and node.get(about) in vertices}
        self.assertEqual(set(BASELINE_GRAPH['vertices']), vertices)
        self.assertEqual({tuple(edge) for edge in BASELINE_GRAPH['edges']}, edges)

    def test_final_inverse_properties_keep_structural_factor_one(self):
        counts = dict(BASELINE_COUNTS, Po=16, Al=271, A=508, Q=4)
        metrics = compute_metrics(counts, graph=BASELINE_GRAPH)
        result = fitness(metrics, BASELINE)
        self.assertEqual(metrics.structural, BASELINE.structural)
        self.assertEqual(result.S, 1.0)
        self.assertAlmostEqual(result.B, 1.3207143079447086, places=14)
        self.assertEqual(result.F, result.B)

    def test_missing_real_graph_is_not_inferred_from_counts(self):
        with self.assertRaisesRegex(MetricError, 'Explicit graph'):
            compute_metrics(BASELINE_COUNTS)

    def test_graph_schema_count_mismatch_is_rejected(self):
        for counts in (dict(BASELINE_COUNTS, C=16), dict(BASELINE_COUNTS, H=6)):
            with self.subTest(counts=counts), self.assertRaisesRegex(MetricError, 'N/H'):
                compute_metrics(counts, graph=BASELINE_GRAPH)

    def test_invalid_counts_and_zero_denominators(self):
        for changes in ({'C': 0}, {'H': 0, 'Po': 0}, {'A': 0}, {'Al': -1},
                        {'C': True}, {'Po': float('nan')}, {'Pd': float('inf')}, {'Q': 1.5}):
            with self.subTest(changes=changes), self.assertRaises(MetricError):
                compute_metrics(dict(BASELINE_COUNTS, **changes), graph=BASELINE_GRAPH)

    def test_all_schema_and_structural_metrics_are_serialized(self):
        result = asdict(BASELINE)
        self.assertEqual(set(result), {'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'structural'})
        self.assertEqual(result['structural']['D2'], 6 / 13)
        self.assertEqual(len(BASELINE.values), 6)
        self.assertEqual(set(asdict(fitness(BASELINE, BASELINE))),
                         {'relative', 'F', 'B', 'S', 'coefficients'})

    def test_four_structural_coefficients_use_absolute_overload_and_multiple_counts(self):
        structural = replace(BASELINE.structural, D1=5, W1=21, T1=1, U=1)
        candidate = replace(BASELINE, structural=structural)
        result = fitness(candidate, BASELINE)
        self.assertEqual(result.coefficients, dict(KD=.5, KW=.5, KT=.5, KI=.5))
        self.assertEqual((result.B, result.S, result.F), (1.0, .5, .5))

    def test_structural_improvement_does_not_boost_score(self):
        structural = replace(BASELINE.structural, D1=1, W1=9)
        score = fitness(replace(BASELINE, structural=structural), BASELINE)
        self.assertEqual(score.S, 1.0)
        self.assertEqual(score.F, score.B)

    def test_one_additional_multiple_parent_vertex_falls_below_structural_limit(self):
        candidate = replace(BASELINE, structural=replace(BASELINE.structural, T1=1))
        score = fitness(candidate, BASELINE)
        self.assertAlmostEqual(score.S, .5 ** .25)
        self.assertLess(score.S, .85)

    def test_cycle_has_fitness_zero_and_undefined_depth_width_factor(self):
        graph = {'vertices': ['A', 'B'], 'edges': [['A', 'B'], ['B', 'A']]}
        candidate = compute_metrics(counts_for(graph), graph=graph)
        score = fitness(candidate, BASELINE)
        self.assertEqual(score.F, 0.0)
        self.assertIsNone(score.S)
        self.assertIsNone(score.coefficients['KD'])
        self.assertIsNone(score.coefficients['KW'])
        self.assertIsInstance(score.B, float)
        self.assertGreater(score.B, 0)
        self.assertIsNone(asdict(candidate)['structural']['D1'])

    def test_nonfinite_schema_metric_is_rejected(self):
        for bad in (float('nan'), float('inf'), -1, True):
            with self.subTest(value=bad), self.assertRaises(MetricError):
                fitness(replace(BASELINE, M1=bad), BASELINE)

    def test_cyclic_baseline_is_rejected(self):
        baseline = replace(BASELINE, structural=replace(BASELINE.structural, CY1=1, CY2=.1))
        with self.assertRaisesRegex(MetricError, 'Baseline class graph'):
            fitness(BASELINE, baseline)

    def test_relative_ratios_are_capped_at_two(self):
        candidate = replace(BASELINE, M1=BASELINE.M1 * 3, M6=0)
        score = fitness(candidate, BASELINE)
        self.assertEqual(score.relative[0], 2)
        self.assertEqual(score.relative[5], 2)
        self.assertEqual(score.S, 1)

    def test_structural_penalty_can_reverse_schema_ranking(self):
        high_b = replace(BASELINE, M6=4,
                         structural=replace(BASELINE.structural, T1=1))
        low_b = replace(BASELINE, M6=5)
        a, b = fitness(high_b, BASELINE), fitness(low_b, BASELINE)
        self.assertGreater(a.B, b.B)
        self.assertLess(a.F, b.F)


if __name__ == '__main__':
    unittest.main()

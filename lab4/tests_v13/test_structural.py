from dataclasses import asdict
from itertools import permutations
import math
import random
import unittest

from lab4.optimizer_v13.structural import (
    StructuralError, compute_structural_metrics, graph_has_cycle,
)


def graph(vertices, edges=()):
    return dict(vertices=list(vertices), edges=[list(edge) for edge in edges])


class StructuralMetricsTests(unittest.TestCase):
    def test_chain(self):
        result = compute_structural_metrics(graph('ABCD', [('A', 'B'), ('B', 'C'), ('C', 'D')]))
        self.assertEqual((result.D1, result.D2, result.D3), (3, 3.0, 3))
        self.assertEqual((result.W1, result.W2, result.W3), (1, 1.0, 4))
        self.assertEqual((result.T1, result.T2, result.T3), (0, .75, 0.0))
        self.assertEqual((result.I1, result.I2, result.I3), (1.0, 1.5, 1.5))
        self.assertAlmostEqual(result.I4, math.sqrt(1 / 3))
        self.assertEqual((result.CY1, result.CY2), (0, 0.0))

    def test_branch_depth_uses_every_root_leaf_path_and_isolated_vertex(self):
        result = compute_structural_metrics(graph('ABCDE', [('A', 'B'), ('A', 'C'), ('C', 'D')]))
        # A-B, A-C-D and isolated E have lengths 1, 2, 0.
        self.assertEqual((result.D1, result.D2, result.D3), (2, 1.0, 3))
        self.assertEqual((result.W1, result.W2, result.W3), (2, 5 / 3, 5))

    def test_diamond_and_direct_shortcut(self):
        result = compute_structural_metrics(graph('ABCD', [
            ('A', 'B'), ('A', 'C'), ('B', 'D'), ('C', 'D'), ('A', 'D'),
        ]))
        self.assertEqual((result.D1, result.D2, result.D3), (2, 5 / 3, 5))
        self.assertEqual((result.W1, result.W2, result.W3), (2, 4 / 3, 4))
        self.assertEqual((result.T1, result.T2, result.T3), (1, 1.25, .25))

    def test_vertex_uses_longest_level_only(self):
        result = compute_structural_metrics(graph('ABCD', [
            ('A', 'B'), ('B', 'C'), ('A', 'C'), ('C', 'D'),
        ]))
        self.assertEqual((result.D1, result.D2, result.D3), (3, 2.5, 5))
        self.assertEqual((result.W1, result.W2), (1, 1.0))

    def test_all_isolated_vertices_are_zero_length_paths(self):
        result = compute_structural_metrics(graph('ABC'))
        self.assertEqual((result.D1, result.D2, result.D3), (0, 0.0, 0))
        self.assertEqual((result.W1, result.W2, result.W3), (3, 3.0, 3))
        self.assertEqual((result.I2, result.I3, result.I4), (0.0, 0.0, 0.0))

    def test_single_vertex_sample_deviation_is_zero(self):
        result = compute_structural_metrics(graph('A'))
        self.assertEqual((result.N, result.H, result.I4), (1, 0, 0.0))
        self.assertEqual((result.W1, result.W2, result.W3), (1, 1.0, 1))

    def test_duplicate_vertices_and_arcs_do_not_change_result(self):
        expected = compute_structural_metrics(graph('AB', [('A', 'B')]))
        actual = compute_structural_metrics(graph('AAB', [('A', 'B'), ('A', 'B')]))
        self.assertEqual(actual, expected)

    def test_overloaded_vertex_uses_absolute_count(self):
        vertices = ['root'] + [str(i) for i in range(10)]
        result = compute_structural_metrics(graph(vertices, [('root', v) for v in vertices[1:]]))
        self.assertEqual(result.U, 1)
        self.assertEqual(result.I1, 10 / 11)
        self.assertEqual(result.I2, 20 / 11)
        self.assertEqual(result.I3, 1.0)
        self.assertAlmostEqual(result.I4, math.sqrt(81 / 11))

    def test_degree_nine_is_not_overloaded(self):
        vertices = ['root'] + [str(i) for i in range(9)]
        result = compute_structural_metrics(graph(vertices, [('root', v) for v in vertices[1:]]))
        self.assertEqual((result.U, result.I1), (0, 1.0))

    def test_self_loop_is_one_cycle_and_degree_two(self):
        value = graph('A', [('A', 'A')])
        self.assertTrue(graph_has_cycle(value))
        result = compute_structural_metrics(value)
        self.assertEqual((result.CY1, result.CY2), (1, 1.0))
        self.assertEqual((result.I2, result.I3, result.I4), (2.0, 2.0, 0.0))
        for name in ('D1', 'D2', 'D3', 'W1', 'W2', 'W3'):
            self.assertIsNone(getattr(result, name))

    def test_simple_cycles_count_rotations_once(self):
        result = compute_structural_metrics(graph('ABCD', [
            ('A', 'B'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('D', 'D'),
        ]))
        self.assertEqual((result.CY1, result.CY2), (3, 1.0))

    def test_opposite_directed_triangles_are_distinct(self):
        edges = [(a, b) for a in 'ABC' for b in 'ABC' if a != b]
        result = compute_structural_metrics(graph('ABCD', edges))
        self.assertEqual((result.CY1, result.CY2), (5, .75))

    def test_cycle_in_one_component_makes_all_depth_width_undefined(self):
        result = compute_structural_metrics(graph('ABCDE', [
            ('A', 'B'), ('B', 'A'), ('C', 'D'),
        ]))
        self.assertEqual((result.CY1, result.CY2), (1, .4))
        self.assertIsNone(result.D1)
        self.assertIsNone(result.W3)

    def test_every_named_metric_is_serialized(self):
        values = asdict(compute_structural_metrics(graph('A')))
        self.assertEqual(set(values), {
            'N', 'H', 'U', 'D1', 'D2', 'D3', 'W1', 'W2', 'W3',
            'T1', 'T2', 'T3', 'I1', 'I2', 'I3', 'I4', 'CY1', 'CY2',
        })

    def test_invalid_graphs_are_explicit_errors(self):
        for value in (None, {}, graph(''), graph('A', [('A', 'B')]),
                      dict(vertices=['A'], edges=['AA']),
                      dict(vertices=['A'], edges=[['A']]),
                      dict(vertices=[7], edges=[])):
            with self.subTest(graph=value), self.assertRaises(StructuralError):
                compute_structural_metrics(value)

    def test_cycle_counts_match_independent_permutation_enumerator(self):
        rng = random.Random(13)
        vertices = list('ABCDE')
        for _ in range(25):
            edges = {(a, b) for a in vertices for b in vertices if rng.random() < .22}
            expected_cycles = []
            for length in range(1, len(vertices) + 1):
                for cycle in permutations(vertices, length):
                    if cycle[0] != min(cycle):
                        continue
                    if all((cycle[i], cycle[(i + 1) % length]) in edges for i in range(length)):
                        expected_cycles.append(cycle)
            result = compute_structural_metrics(graph(vertices, edges))
            self.assertEqual(result.CY1, len(expected_cycles))
            members = {v for cycle in expected_cycles for v in cycle}
            self.assertEqual(result.CY2, len(members) / len(vertices))
            self.assertEqual(graph_has_cycle(graph(vertices, edges)), bool(expected_cycles))

    def test_dag_aggregates_match_independent_path_enumeration(self):
        rng = random.Random(31)
        vertices = list('ABCDEF')
        for _ in range(30):
            edges = {(a, b) for i, a in enumerate(vertices) for b in vertices[i + 1:]
                     if rng.random() < .4}
            children = {a: [b for x, b in edges if x == a] for a in vertices}
            roots = [a for a in vertices if not any(b == a for _, b in edges)]
            paths = []

            def enumerate_paths(path):
                if not children[path[-1]]:
                    paths.append(path)
                for child in children[path[-1]]:
                    enumerate_paths(path + [child])

            for root in roots:
                enumerate_paths([root])
            lengths = [len(path) - 1 for path in paths]
            levels = {v: max(path.index(v) for path in paths if v in path) for v in vertices}
            widths = [sum(level == k for level in levels.values()) for k in range(max(levels.values()) + 1)]
            result = compute_structural_metrics(graph(vertices, edges))
            self.assertEqual((result.D1, result.D2, result.D3),
                             (max(lengths), sum(lengths) / len(lengths), sum(lengths)))
            self.assertEqual((result.W1, result.W2, result.W3),
                             (max(widths), len(vertices) / len(widths), len(vertices)))


if __name__ == '__main__':
    unittest.main()

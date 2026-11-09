import json
from dataclasses import asdict
from pathlib import Path
import unittest
from unittest.mock import patch

from lab4.optimizer_v13.metrics import BASELINE, fitness
from lab4.optimizer_v13.proposals import parse_proposal, render_prompt
from lab4.optimizer_v13.runtime import build_runtime


class RuntimeTests(unittest.TestCase):
    def test_full_metrics_and_actual_objective_are_in_prompt(self):
        score = fitness(BASELINE, BASELINE)
        context = dict(metrics=asdict(BASELINE), relative=score.relative,
                       fitness=dict(B=score.B, S=score.S, F=score.F,
                                    coefficients=score.coefficients),
                       ontology_manchester='Ontology: <https://example.org/test>')
        text = render_prompt(context)
        self.assertIn('F=B*S', text)
        self.assertIn('"D1": 2', text)
        self.assertIn('"CY1": 0', text)
        self.assertIn('"S":1.0', text)
        self.assertNotIn('$ontology_manchester', text)
        del context['fitness']
        with self.assertRaises(ValueError):
            render_prompt(context)

    def test_json_example_is_accepted_by_real_functional_syntax_parser(self):
        path = Path('lab4/optimizer_v13/prompts/proposal.txt')
        text = path.read_text().split('Пример формы: ', 1)[1].split('. Пример применим', 1)[0]
        proposal = parse_proposal(text)
        self.assertEqual(len(proposal.add), 6)
        self.assertEqual(proposal.remove, [])

    def test_runtime_assigns_pinned_semantic_cache_provenance(self):
        manifest = json.loads(Path('lab4/optimizer/series-v1.yaml').read_text())['services']
        runtime = build_runtime(manifest, 100, phase='debug')
        checker = runtime['duplicate_checker']
        self.assertEqual(checker.cache_identity['embedding_sha256'], manifest['embedding_sha256'])
        self.assertEqual(checker.cache_identity['duplicate_threshold'], manifest['duplicate_threshold'])

    def test_main_requires_real_debug_qualification(self):
        manifest = json.loads(Path('lab4/optimizer/series-v1.yaml').read_text())['services']
        manifest['qualification_path'] = '/definitely-missing-v13-qualification.json'
        with self.assertRaises(FileNotFoundError):
            build_runtime(manifest, 101, phase='main')


if __name__ == '__main__':
    unittest.main()

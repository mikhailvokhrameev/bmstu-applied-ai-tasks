from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer_v13 import bridge, validator


class Checker:
    def __init__(self, duplicate=False):
        self.cache_identity = {'revision': 'test-revision', 'threshold': .9, 'duplicate': duplicate}
        self.calls = 0
        self.duplicate = duplicate

    def __call__(self, entities):
        self.calls += 1
        return self.duplicate


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        bridge.clear_caches()
        validator.clear_cache()

    def tearDown(self):
        bridge.clear_caches()
        validator.clear_cache()

    def test_baseline_has_all_metrics_and_unit_score(self):
        result = validator.validate({'add': [], 'remove': []}, duplicate_checker=Checker())
        self.assertEqual((result.status, result.F, result.B, result.S), ('valid', 1, 1, 1), result.detail)
        self.assertEqual(result.metrics.structural.D1, 2)
        self.assertEqual(result.metrics.structural.W1, 10)
        self.assertEqual(result.metrics.structural.CY1, 0)

    def test_final_ontology_is_valid_with_new_fitness(self):
        result = validator.validate(bridge.ROOT / 'lab4/ontology/videocard.owl', duplicate_checker=Checker())
        self.assertEqual(result.status, 'valid', result.detail)
        self.assertEqual(result.S, 1)
        self.assertAlmostEqual(result.F, 1.3207143079447086)

    def test_cycles_rejected_before_reasoner_with_undefined_depth_width(self):
        delta = {'add': ['SubClassOf(:ModelComponent :CoolingSystem)'], 'remove': []}
        with patch.object(validator, '_inspect', side_effect=AssertionError('reasoner must not execute')):
            result = validator.validate(delta, duplicate_checker=Checker())
        self.assertEqual((result.status, result.code, result.F), ('invalid', 'CYCLE', 0), result.detail)
        self.assertGreater(result.metrics.structural.CY1, 0)
        self.assertIsNone(result.metrics.structural.D1)
        self.assertIsNone(result.metrics.structural.W1)
        self.assertIsNone(result.S)
        self.assertIsNotNone(result.B)

    def test_structure_penalty_rejected_before_reasoner(self):
        delta = {'add': ['SubClassOf(:Extra1 :ActiveCooling)', 'SubClassOf(:Extra2 :Extra1)',
                         'SubClassOf(:Extra3 :Extra2)'], 'remove': []}
        with patch.object(validator, '_inspect', side_effect=AssertionError('reasoner must not execute')):
            result = validator.validate(delta, duplicate_checker=Checker())
        self.assertEqual((result.status, result.code, result.F), ('invalid', 'STRUCTURE', 0), result.detail)
        self.assertLess(result.S, .85)

    def test_duplicate_candidates_reuse_completed_validation(self):
        checker = Checker()
        first = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        second = validator.validate({'remove': [], 'add': []}, duplicate_checker=checker)
        self.assertEqual(checker.calls, 1)
        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        self.assertEqual(first.cache_key, second.cache_key)
        self.assertEqual(first.metrics, second.metrics)

    def test_checker_identity_change_invalidates_full_validation(self):
        checker = Checker()
        first = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        checker.cache_identity['threshold'] = .8
        second = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        self.assertEqual(first.status, 'valid')
        self.assertEqual(second.status, 'valid')
        self.assertFalse(second.cache_hit)
        self.assertEqual(checker.calls, 2)

    def test_checker_without_provenance_is_never_assumed_stable(self):
        calls = []
        def checker(entities):
            calls.append(entities)
            return len(calls) > 1
        first = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        second = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        self.assertEqual((first.status, second.code), ('valid', 'DUPLICATE'))
        self.assertFalse(second.cache_hit)

    def test_infrastructure_errors_are_not_cached(self):
        checker = Checker()
        with patch.object(validator, '_inspect', side_effect=TimeoutError('test timeout')):
            first = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        self.assertEqual((first.status, first.code, first.F), ('error', 'TIMEOUT', None))
        second = validator.validate({'add': [], 'remove': []}, duplicate_checker=checker)
        self.assertEqual(second.status, 'valid', second.detail)
        self.assertFalse(second.cache_hit)

    def test_structural_failures_can_be_reused_without_claiming_reasoner_success(self):
        checker = Checker()
        delta = {'add': ['SubClassOf(:ModelComponent :ModelComponent)'], 'remove': []}
        first = validator.validate(delta, duplicate_checker=checker)
        second = validator.validate(delta, duplicate_checker=checker)
        self.assertEqual((first.code, second.code), ('CYCLE', 'CYCLE'))
        self.assertEqual(checker.calls, 0)
        self.assertTrue(second.cache_hit)

    def test_external_import_is_rejected_without_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'import.owl'
            text = bridge.CORE.read_text().replace('</owl:Ontology>',
                '<owl:imports rdf:resource="https://invalid.example/never-fetch.owl"/></owl:Ontology>', 1)
            path.write_text(text)
            result = validator.validate(path, duplicate_checker=Checker())
        self.assertEqual((result.status, result.code), ('invalid', 'FORBIDDEN'), result.detail)

    def test_unsatisfiable_isolated_class_is_rejected_by_reasoner(self):
        delta = {'add': [
            'Declaration(Class(:Impossible))',
            'EquivalentClasses(:Impossible owl:Nothing)',
            'AnnotationAssertion(rdfs:label :Impossible "Невыполнимый класс"@ru)',
            'AnnotationAssertion(rdfs:comment :Impossible "Контроль выполнимости класса"@ru)',
        ], 'remove': []}
        result = validator.validate(delta, duplicate_checker=Checker())
        self.assertEqual((result.status, result.code), ('invalid', 'CONSISTENCY'), result.detail)

    def test_queries_and_negative_controls_are_still_executed(self):
        import xml.etree.ElementTree as ET
        ns = {'owl': 'http://www.w3.org/2002/07/owl#',
              'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
              'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
        prefix = 'https://example.org/ontologies/videocard#'
        resource = '{' + ns['rdf'] + '}resource'
        about = '{' + ns['rdf'] + '}about'
        with tempfile.TemporaryDirectory() as folder:
            for kind, expected in [('query', 'QUERIES'), ('negative', 'NEGATIVE_TESTS')]:
                with self.subTest(kind=kind):
                    root = ET.parse(bridge.CORE)
                    if kind == 'query':
                        card = next(e for e in root.getroot().findall('owl:NamedIndividual', ns)
                                    if e.get(about) == prefix + 'U01')
                        card.find('{' + prefix + '}producedByManufacturer').set(resource, prefix + 'P2')
                    else:
                        prop = next(e for e in root.getroot().findall('owl:DatatypeProperty', ns)
                                    if e.get(about) == prefix + 'volumeGiB')
                        prop.remove(prop.find('rdfs:range', ns))
                    path = Path(folder) / (kind + '.owl')
                    root.write(path, encoding='utf-8', xml_declaration=True)
                    result = validator.validate(path, duplicate_checker=Checker())
                    self.assertEqual((result.status, result.code), ('invalid', expected), result.detail)

    def test_missing_annotation_is_rejected_when_metrics_are_eligible(self):
        delta = {'add': [
            'Declaration(ObjectProperty(:inverseGPU))',
            'AnnotationAssertion(rdfs:comment :inverseGPU "От модели GPU к использующим её видеокартам"@ru)',
            'InverseObjectProperties(:inverseGPU :usesGPU)',
            'ObjectPropertyDomain(:inverseGPU :GPUModel)',
            'ObjectPropertyRange(:inverseGPU :VideoCardModel)',
        ], 'remove': []}
        result = validator.validate(delta, duplicate_checker=Checker())
        self.assertEqual((result.status, result.code), ('invalid', 'ANNOTATIONS'), result.detail)

    def test_all_original_negative_fixtures_remain_invalid(self):
        import json
        for path in sorted((bridge.ROOT / 'lab4/tests/validator_fixtures').glob('*.json')):
            fixture = json.loads(path.read_text())
            with self.subTest(name=path.name):
                result = validator.validate(fixture['candidate'], duplicate_checker=Checker(fixture['duplicate']))
                self.assertEqual((result.status, result.F), ('invalid', 0), result.detail)


if __name__ == '__main__':
    unittest.main()

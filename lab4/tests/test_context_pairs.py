import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.assessment.build_context_pairs import build, contextualize
from lab4.optimizer.paths import ASSESSMENT
from lab4.optimizer.prepare import load_pairs, ontology_inventory


class ContextPairTests(unittest.TestCase):
    def test_frozen_dataset_preserves_labels_phrases_and_ontology_definitions(self):
        directory = ASSESSMENT
        original = load_pairs(directory / 'concept_pairs.csv')
        contextual = load_pairs(directory / 'concept_pairs_context.csv')
        _, entities = ontology_inventory()
        definitions = {entity['iri']: entity for entity in entities}
        for old, new in zip(original, contextual):
            self.assertEqual((old['id'], old['synonym']), (new['id'], new['synonym']))
            for side in ('left', 'right'):
                self.assertEqual(old[side], new[side + '_label'])
                definition = definitions[new[side + '_iri']]
                self.assertEqual(new[side + '_comment'], definition['comment'])
                self.assertEqual(new[side + '_category'], definition['category'])
                self.assertEqual(new[side], new[side + '_label'] + '. ' + definition['comment'])
            self.assertEqual(new['left_iri'] == new['right_iri'], new['synonym'] == '1')
        self.assertEqual([row['id'] for row in contextual if row['same_category'] == 'false'],
                         ['PAIR17', 'PAIR20'])

    def test_embedding_text_does_not_depend_on_pair_id_or_expected_label(self):
        _, entities = ontology_inventory()
        pair = dict(id='anything', left='Графический процессор', right='GPU',
                    synonym='1', review_status='approved')
        original = contextualize([pair], entities)[0]
        changed = contextualize([{**pair, 'id': 'different', 'synonym': '0'}], entities)[0]
        self.assertEqual((original['left'], original['right']), (changed['left'], changed['right']))

    def test_holdout_is_balanced_and_concept_disjoint_without_skipping_categories(self):
        directory = ASSESSMENT
        calibration = load_pairs(directory / 'concept_pairs_context.csv')
        holdout = load_pairs(directory / 'concept_pairs_holdout.csv')
        self.assertEqual(len(holdout), 20)
        self.assertEqual(sum(row['synonym'] == '1' for row in holdout), 10)
        calibration_iris = {row[side + '_iri'] for row in calibration for side in ('left', 'right')}
        holdout_iris = {row[side + '_iri'] for row in holdout for side in ('left', 'right')}
        self.assertFalse(calibration_iris & holdout_iris)
        self.assertTrue(all(row['same_category'] == 'true' for row in holdout))
        self.assertTrue(all((row['left_iri'] == row['right_iri']) == (row['synonym'] == '1')
                            for row in holdout))

    def test_builder_reproduces_frozen_bytes_without_api_and_refuses_overwrite(self):
        directory = ASSESSMENT
        registration = json.loads((directory / 'CONTEXT_PREREGISTRATION.json').read_text())
        with tempfile.TemporaryDirectory() as tmp, \
                patch('lab4.optimizer.prepare.read_api') as api, \
                patch('lab4.optimizer.prepare.OllamaModels.embed') as embed:
            rebuilt = build(tmp)
            api.assert_not_called()
            embed.assert_not_called()
            for name, info in registration['datasets'].items():
                raw = (directory / name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), info['sha256'])
                self.assertEqual((Path(tmp) / name).read_bytes(), raw)
                self.assertEqual(rebuilt['datasets'][name], info)
            with self.assertRaises(FileExistsError):
                build(tmp)


if __name__ == '__main__':
    unittest.main()

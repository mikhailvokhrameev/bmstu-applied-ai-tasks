import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from contextlib import redirect_stdout, redirect_stderr
import xml.etree.ElementTree as ET

from lab4.optimizer.bridge import CORE, ROOT
from lab4.optimizer.paths import ASSESSMENT
from lab4.optimizer.prepare import (calibrate_pairs, context_metadata, main,
                                    ontology_inventory, prepare, verify_weights)


class PrepareTests(unittest.TestCase):
    def weight_tree(self, directory, name, payload):
        digest = hashlib.sha256(payload).hexdigest()
        manifest = dict(schemaVersion=2, layers=[dict(
            mediaType='application/vnd.ollama.image.model',
            digest='sha256:' + digest, size=len(payload))])
        raw = json.dumps(manifest).encode()
        path = directory / 'manifests/registry.ollama.ai/library' / name / 'test'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        blob = directory / 'blobs' / ('sha256-' + digest)
        blob.parent.mkdir(exist_ok=True)
        blob.write_bytes(payload)
        return dict(name=name + ':test', digest=hashlib.sha256(raw).hexdigest()), blob

    def pairs(self):
        return [dict(id=str(i), left='base', right='positive' if i < 10 else 'negative',
                     synonym='1' if i < 10 else '0', review_status='approved')
                for i in range(20)]

    def embeddings(self, positive, negative):
        def embed(texts):
            scores = {'base': 1., 'positive': positive, 'negative': negative}
            return [[scores[text], (1 - scores[text] ** 2) ** .5] for text in texts]
        return embed

    def test_inventory_uses_actual_ontology_entities_and_russian_annotations(self):
        inventory, entities = ontology_inventory()
        groups = ('classes', 'object_properties', 'data_properties')
        self.assertEqual({key: len(inventory[key]) for key in groups},
                         dict(classes=15, object_properties=10, data_properties=7))
        self.assertEqual(len(entities), 32)
        self.assertEqual({row['category'] for row in entities},
                         {'Class', 'ObjectProperty', 'DataProperty'})
        self.assertTrue(all(value.startswith('<https://example.org/ontologies/videocard#')
                            and value.endswith('>') for key in groups for value in inventory[key]))
        active = next(row for row in entities if row['iri'].endswith('#ActiveCooling'))
        self.assertEqual(active['label'], 'Активное охлаждение')
        self.assertIn('вентилятором', active['comment'])

    def test_control_inventory_contains_named_domains_ranges_and_only_teaching_cards(self):
        inventory, entities = ontology_inventory()
        iri = lambda name: '<https://example.org/ontologies/videocard#' + name + '>'
        self.assertEqual(inventory['object_property_domains'][iri('usesGPU')], [iri('VideoCardModel')])
        self.assertEqual(inventory['object_property_ranges'][iri('usesGPU')], [iri('GPUModel')])
        self.assertEqual(inventory['object_property_domains'][iri('hasArchitecture')], [iri('GPUModel')])
        self.assertEqual(inventory['object_property_ranges'][iri('hasArchitecture')], [iri('GPUArchitecture')])
        for key in ('object_property_domains', 'object_property_ranges'):
            self.assertEqual(set(inventory[key]), set(inventory['object_properties']))
            self.assertTrue(all(values for values in inventory[key].values()))
        self.assertEqual(inventory['teaching_class'], iri('VideoCardModel'))
        self.assertEqual(inventory['individuals'], [iri('U0' + str(i)) for i in range(1, 9)])
        self.assertFalse(set(inventory['individuals']) & {'<' + entity['iri'] + '>' for entity in entities})

    def test_control_inventory_excludes_anonymous_domains_and_out_of_scope_individuals(self):
        tree = ET.parse(CORE)
        root = tree.getroot()
        ns = dict(owl='http://www.w3.org/2002/07/owl#',
                  rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                  rdfs='http://www.w3.org/2000/01/rdf-schema#')
        resource = '{' + ns['rdf'] + '}resource'
        about = '{' + ns['rdf'] + '}about'
        prefix = 'https://example.org/ontologies/videocard#'
        prop = next(element for element in root.findall('owl:ObjectProperty', ns)
                    if element.get(about) == prefix + 'usesGPU')
        prop.remove(prop.find('rdfs:domain', ns))
        anonymous = ET.SubElement(prop, '{' + ns['rdfs'] + '}domain')
        ET.SubElement(anonymous, '{' + ns['owl'] + '}Class')
        # A same-category external class and a datatype are not class operands.
        ET.SubElement(prop, '{' + ns['rdfs'] + '}domain', {resource: 'https://external.org/Other'})
        ET.SubElement(prop, '{' + ns['rdfs'] + '}domain', {resource: 'http://www.w3.org/2001/XMLSchema#string'})
        for name in ('U09', 'GPU_G6'):
            individual = ET.SubElement(root, '{' + ns['owl'] + '}NamedIndividual', {about: prefix + name})
            ET.SubElement(individual, '{' + ns['rdf'] + '}type', {resource: prefix + 'VideoCardModel'})
        u08 = next(element for element in root.findall('owl:NamedIndividual', ns)
                   if element.get(about) == prefix + 'U08')
        u08.remove(u08.find('rdf:type', ns))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'copy.owl'
            tree.write(path, encoding='utf-8')
            inventory, _ = ontology_inventory(path)
        self.assertEqual(inventory['object_property_domains']['<' + prefix + 'usesGPU>'], [])
        self.assertEqual(inventory['object_property_ranges']['<' + prefix + 'usesGPU>'], ['<' + prefix + 'GPUModel>'])
        self.assertEqual(len(inventory['individuals']), 7)
        self.assertTrue(all(name.endswith(tuple('U0' + str(i) + '>' for i in range(1, 8)))
                            for name in inventory['individuals']))

    def test_weights_reject_server_mismatch_and_same_size_blob_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry, blob = self.weight_tree(Path(tmp), 'model', b'weights')
            report = verify_weights('model:test', tmp, dict(models=[entry]))
            self.assertEqual(report['sha256'], hashlib.sha256(b'weights').hexdigest())
            with self.assertRaisesRegex(ValueError, 'Server/local'):
                verify_weights('model:test', tmp, dict(models=[{**entry, 'digest': '0' * 64}]))
            blob.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum/size'):
                verify_weights('model:test', tmp, dict(models=[entry]))

    def test_registry_wrapper_matches_original_manifest_and_rejects_changed_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            entry, weights = self.weight_tree(directory, 'model', b'weights')
            path = directory / 'manifests/registry.ollama.ai/library/model/test'
            original = json.loads(path.read_bytes())
            original.update(mediaType='application/vnd.docker.distribution.manifest.v2+json',
                            config=dict(digest='sha256:' + 'a' * 64, size=17))
            original_raw = json.dumps(original).encode()
            digest = hashlib.sha256(original_raw).hexdigest()
            registry_blob = directory / 'blobs' / ('sha256-' + digest)
            registry_blob.write_bytes(original_raw)
            entry['digest'] = digest
            wrapper = {**original, 'layers': original['layers'] + [dict(
                mediaType='application/vnd.docker.distribution.manifest.v2+json',
                digest='sha256:' + digest, size=len(original_raw))]}
            path.write_text(json.dumps(wrapper))
            tags = dict(models=[entry])
            result = verify_weights('model:test', tmp, tags)
            self.assertNotEqual(result['manifest_sha256'], digest)
            self.assertEqual(result['api_manifest_sha256'], digest)
            self.assertEqual(result['registry_manifest'], original)
            weights.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'Weight checksum'):
                verify_weights('model:test', tmp, tags)
            weights.write_bytes(b'weights')
            registry_blob.write_bytes(original_raw.replace(b'17', b'18'))
            with self.assertRaisesRegex(ValueError, 'Registry manifest checksum'):
                verify_weights('model:test', tmp, tags)
            registry_blob.write_bytes(original_raw)
            for field in ('config', 'layers'):
                modified = {**wrapper}
                modified[field] = dict(digest='different') if field == 'config' else [
                    {**wrapper['layers'][0], 'size': 99}, wrapper['layers'][-1]]
                path.write_text(json.dumps(modified))
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'content mismatch'):
                    verify_weights('model:test', tmp, tags)

    def test_threshold_changes_only_from_measured_scores_and_rechecks_decisions(self):
        result = calibrate_pairs(self.pairs(), self.embeddings(.8, .7))
        self.assertEqual(result['initial_errors'], 10)
        self.assertAlmostEqual(result['chosen_threshold'], .75)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['main_blockers'], [])
        self.assertTrue(all(row['duplicate'] == row['expected'] for row in result['rows']))
        untouched = calibrate_pairs(self.pairs(), self.embeddings(.95, .8))
        self.assertEqual(untouched['chosen_threshold'], .90)

    def test_threshold_cannot_separate_equal_or_overlapping_scores(self):
        for positive, negative in ((.7, .8), (.8, .8)):
            with self.subTest(positive=positive, negative=negative):
                result = calibrate_pairs(self.pairs(), self.embeddings(positive, negative))
                self.assertEqual(result['chosen_threshold'], .90)
                self.assertGreater(result['errors'], 0)
                self.assertTrue(result['main_blockers'])

    def test_zero_boundary_is_a_valid_threshold_when_negatives_are_below_zero(self):
        result = calibrate_pairs(self.pairs(), self.embeddings(0., -.5))
        self.assertEqual(result['chosen_threshold'], 0.)
        self.assertEqual(result['errors'], 0)

    def test_advertised_context_does_not_certify_real_inference(self):
        for info, supported in (({'general.architecture': 'qwen2', 'qwen2.context_length': 32768}, True),
                                ({'general.architecture': 'qwen2', 'qwen2.context_length': 8192}, False),
                                ({'other.context_length': 32768}, False)):
            result = context_metadata(dict(model_info=info))
            self.assertEqual(result['advertised_at_least_32000'], supported)
            self.assertFalse(result['actual_context_verified'])

    def test_live_preparation_contract_with_mock_services_keeps_main_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            model, _ = self.weight_tree(directory, 'model', b'model weights')
            embedding, _ = self.weight_tree(directory, 'embed', b'embed weights')
            show = dict(model_info={'general.architecture': 'qwen2', 'qwen2.context_length': 32768})
            def api(endpoint, path, payload=None):
                return {'/api/version': {'version': 'test-server'},
                        '/api/tags': dict(models=[model, embedding]), '/api/show': show}[path]
            with patch('lab4.optimizer.prepare.read_api', side_effect=api), \
                    patch('lab4.optimizer.prepare.OllamaModels.embed', side_effect=lambda texts: [[1., 0.]] * len(texts)):
                config, evidence = prepare('http://localhost:11435', 'model:test', 'embed:test', directory)
            services = config['services']
            self.assertFalse(services['acceptance_approved'])
            self.assertEqual(services['server_version'], 'test-server')
            self.assertTrue(services['main_blockers'])
            self.assertEqual(evidence['calibration']['errors'], 10)
            self.assertEqual(evidence['weights']['model']['sha256'], services['model_sha256'])
            self.assertEqual(evidence['api']['model_show'], show)

    def test_cli_transport_failure_writes_evidence_without_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            output = directory / 'config.json'
            arguments = ['--model', 'model:test', '--embedding-model', 'embed:test',
                         '--models-dir', tmp, '--output', str(output),
                         '--evidence-dir', str(directory / 'evidence')]
            with patch('lab4.optimizer.prepare.read_api', side_effect=URLError('unreachable')), \
                    redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 2)
            self.assertFalse(output.exists())
            failure = json.loads((directory / 'evidence/failure.json').read_text())
            self.assertFalse(failure['acceptance_approved'])
            output.write_text('user configuration')
            with patch('lab4.optimizer.prepare.read_api') as api, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 2)
                api.assert_not_called()
            self.assertEqual(output.read_text(), 'user configuration')

    def test_cli_passes_frozen_calibration_and_holdout_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            pairs, holdout = directory / 'pairs.csv', directory / 'holdout.csv'
            arguments = ['--model', 'model:test', '--embedding-model', 'embed:test',
                         '--models-dir', tmp, '--output', str(directory / 'config.json'),
                         '--evidence-dir', str(directory / 'evidence'),
                         '--pairs', str(pairs), '--holdout-pairs', str(holdout)]
            with patch('lab4.optimizer.prepare.prepare', return_value=(
                    dict(services=dict(duplicate_threshold=.8)), dict(status='mock'))) as prepared, \
                    redirect_stdout(StringIO()):
                self.assertEqual(main(arguments), 0)
            self.assertEqual(prepared.call_args.kwargs, dict(
                pairs_path=pairs, holdout_path=holdout, embedding_backend='ollama',
                embedding_endpoint=None, embedding_revision=None, embedding_instruction=''))

    def test_cli_forwards_explicit_sentence_transformer_backend_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            arguments = ['--model', 'model:test', '--embedding-model', 'sentence-transformers/LaBSE',
                         '--models-dir', tmp, '--output', str(directory / 'config.json'),
                         '--evidence-dir', str(directory / 'evidence'),
                         '--embedding-backend', 'sentence-transformers',
                         '--embedding-endpoint', 'http://127.0.0.1:11436',
                         '--embedding-revision', 'a' * 40,
                         '--embedding-instruction', 'Represent the complete meaning of this ontology entity.']
            with patch('lab4.optimizer.prepare.prepare', return_value=(
                    dict(services=dict(duplicate_threshold=.8)), dict(status='mock'))) as prepared, \
                    redirect_stdout(StringIO()):
                self.assertEqual(main(arguments), 0)
            self.assertEqual(prepared.call_args.kwargs, dict(
                pairs_path=None, holdout_path=None, embedding_backend='sentence-transformers',
                embedding_endpoint='http://127.0.0.1:11436', embedding_revision='a' * 40,
                embedding_instruction='Represent the complete meaning of this ontology entity.'))

    def test_holdout_is_scored_at_fixed_calibration_threshold_without_retuning(self):
        directory = ASSESSMENT
        def api(endpoint, path, payload=None):
            return dict(version='test') if path == '/api/version' else {}
        with patch('lab4.optimizer.prepare.read_api', side_effect=api), \
                patch('lab4.optimizer.prepare.verify_weights', return_value=dict(sha256='a' * 64)), \
                patch('lab4.optimizer.prepare.calibrate_pairs', return_value=dict(
                    chosen_threshold=.73, main_blockers=[])) as calibrate, \
                patch('lab4.optimizer.prepare.OllamaModels.embed', side_effect=lambda texts: [[1., 0.]] * len(texts)) as embed:
            config, evidence = prepare('http://localhost', 'model:test', 'embed:test', directory,
                                       pairs_path=directory / 'concept_pairs_context.csv',
                                       holdout_path=directory / 'concept_pairs_holdout.csv')
        calibrate.assert_called_once()
        self.assertEqual(embed.call_count, 20)
        self.assertEqual(config['services']['duplicate_threshold'], .73)
        self.assertEqual(evidence['holdout']['assessment']['threshold'], .73)
        self.assertEqual(evidence['holdout']['assessment']['errors'], 10)
        self.assertFalse(config['services']['acceptance_approved'])


if __name__ == '__main__':
    unittest.main()

"""Temporary capability tests; no real experimental result is released."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from lab4.optimizer import release
from lab4.optimizer.bridge import CORE, CORE_SHA256


class ReleaseTests(unittest.TestCase):
    delta = dict(add=[
        'Declaration(Class(:ReleaseTestClass))',
        'AnnotationAssertion(rdfs:label :ReleaseTestClass "Проверочный учебный подкласс"@ru)',
        'AnnotationAssertion(rdfs:comment :ReleaseTestClass "Проверка временного экспорта: подкласс модели видеокарты"@ru)',
        'SubClassOf(:ReleaseTestClass :VideoCardModel)'], remove=[])

    def test_export_roundtrip_identity_and_isolated_shared_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root/'candidate.owl'
            # This explicit test stub does not claim real semantic qualification.
            result = release.export_candidate(self.delta, output, duplicate_checker=lambda _: False)
            self.assertFalse(result['accepted'])
            self.assertFalse(result['gui_verified'])
            self.assertEqual(result['status'],'exported-unaccepted')
            self.assertTrue(result['roundtrip_verified'])
            self.assertTrue(result['core_preserved'])
            self.assertEqual(result['counts']['A'],476)
            self.assertEqual(result['counts']['C'],16)
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),result['sha256'])
            ns = dict(owl='http://www.w3.org/2002/07/owl#',rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#')
            identity = ET.parse(output).getroot().find('owl:Ontology',ns)
            self.assertEqual(identity.get('{'+ns['rdf']+'}about'),'https://example.org/ontologies/videocard')
            self.assertEqual(identity.find('owl:versionIRI',ns).get('{'+ns['rdf']+'}resource'),
                             'https://example.org/ontologies/videocard/2.0.0')
            self.assertEqual(identity.find('owl:versionInfo',ns).text,'2.0.0')
            evidence = root/'engine-check'
            checked = release.run_acceptance(output,evidence)
            self.assertTrue(checked['all_passed'],checked)
            self.assertEqual(set(checked['groups']),{f'T{i:02d}' for i in range(4,11)})
            self.assertFalse(checked['gui_verified'])
            self.assertFalse(checked['accepted'])
            self.assertEqual(json.loads((evidence/'acceptance.json').read_text()),checked)
            for name in checked['groups']:
                self.assertTrue((evidence/checked['groups'][name]['log']).read_text().rstrip().endswith(name+': PASS'))
            for mutant in (evidence/'tests/negative').glob('*.owl'):
                # Each defect copy retains the candidate's non-core addition.
                self.assertIn('ReleaseTestClass',mutant.read_text())
                self.assertIn('videocard/2.0.0',mutant.read_text())
                self.assertNotEqual(mutant.read_bytes(),output.read_bytes())
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                release.export_candidate(self.delta,output,duplicate_checker=lambda _: False)
            self.assertEqual(output.read_bytes(),before)
            with self.assertRaises(FileExistsError):release.run_acceptance(output,evidence)
            self.assertEqual(hashlib.sha256(CORE.read_bytes()).hexdigest(),CORE_SHA256)

    def test_missing_checker_invalid_candidate_and_failed_integrity_create_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'candidate.owl'
            with self.assertRaisesRegex(ValueError,'duplicate_checker'):
                release.export_candidate(self.delta,output)
            with self.assertRaisesRegex(release.ReleaseError,'invalid'):
                release.export_candidate(dict(add=[],remove=['Declaration(Class(:VideoCardModel))']),
                                         output,duplicate_checker=lambda _:False)
            with self.assertRaisesRegex(release.ReleaseError,'DUPLICATE'):
                release.export_candidate(self.delta,output,duplicate_checker=lambda _:True)
            with self.assertRaisesRegex(ValueError,'2.0.0'):
                release.export_candidate(self.delta,output,version='3.0.0',duplicate_checker=lambda _:False)
            fake = dict(document_base64='eA==',roundtrip_verified=True,core_preserved=True,sha256='0'*64)
            with patch.object(release,'_java',return_value=fake):
                with self.assertRaisesRegex(release.ReleaseError,'verification'):
                    release.export_candidate(self.delta,output,duplicate_checker=lambda _:False)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

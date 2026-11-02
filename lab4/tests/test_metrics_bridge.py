import hashlib
import json
from pathlib import Path
import unittest
from collections import Counter
import tempfile
import subprocess
from unittest.mock import patch
from lab4.optimizer.metrics import compute_metrics, fitness, BASELINE_COUNTS, BASELINE, MetricError
from lab4.optimizer.bridge import evaluate, BridgeError
from lab4.optimizer.paths import ROOT, CORE, LIB, ASSESSMENT

class MetricsTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual([round(v, 3) for v in BASELINE.values[:5]], [.333,.667,.467,.133,.536])
        self.assertAlmostEqual(fitness(BASELINE, BASELINE).F, 1)
    def test_reference_fixtures(self):
        expected = json.loads((ASSESSMENT/'fixtures/expected.json').read_text())
        for case in expected['cases']:
            with self.subTest(case=case['fixture']):
                result = evaluate(ASSESSMENT/f"fixtures/{case['fixture']}.ofn", [], [])
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
    def test_complete_manchester_roundtrip_preserves_axioms_identity_annotations(self):
        source = r'''
import java.io.File;
import java.util.*;
import com.fasterxml.jackson.databind.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.io.StringDocumentSource;
import org.semanticweb.owlapi.model.*;
public class ManchesterRoundtripCheck {
    static Set<OWLAxiom> parse(JsonNode values) throws Exception {
        StringBuilder text = new StringBuilder("Prefix(:=<https://example.org/ontologies/videocard#>) Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>) Ontology(");
        for (JsonNode value : values) text.append(value.asText()).append('\n');
        text.append(')');
        return OWLManager.createOWLOntologyManager().loadOntologyFromOntologyDocument(new StringDocumentSource(text.toString())).getAxioms();
    }
    public static void main(String[] args) throws Exception {
        OWLOntology expected = OWLManager.createOWLOntologyManager().loadOntologyFromOntologyDocument(new File(args[0]));
        JsonNode delta = new ObjectMapper().readTree(args[2]);
        expected.getOWLOntologyManager().addAxioms(expected, parse(delta.get("add")));
        expected.getOWLOntologyManager().removeAxioms(expected, parse(delta.get("remove")));
        OWLOntology restored = OWLManager.createOWLOntologyManager().loadOntologyFromOntologyDocument(new File(args[1]));
        if (!expected.getAxioms().equals(restored.getAxioms())) {
            Set<OWLAxiom> lost = new HashSet<>(expected.getAxioms()); lost.removeAll(restored.getAxioms());
            Set<OWLAxiom> gained = new HashSet<>(restored.getAxioms()); gained.removeAll(expected.getAxioms());
            throw new AssertionError("Axiom set changed during Manchester roundtrip; lost="+lost+"; gained="+gained);
        }
        if (!expected.getOntologyID().equals(restored.getOntologyID())) throw new AssertionError("Ontology/version IRI changed during Manchester roundtrip");
        if (!expected.getAnnotations().equals(restored.getAnnotations())) throw new AssertionError("Ontology annotations changed during Manchester roundtrip");
    }
}
'''
        delta = dict(add=['Declaration(Class(:RoundtripClass))',
                          'AnnotationAssertion(rdfs:label :RoundtripClass "Проверочный класс"@ru)',
                          'AnnotationAssertion(rdfs:comment :RoundtripClass "Учебный подкласс модели GPU"@ru)',
                          'SubClassOf(:RoundtripClass :GPUModel)',
                          'DataPropertyAssertion(:powerW :U01 "040.0"^^xsd:decimal)',
                          'FunctionalObjectProperty(:usesGPU)'],
                     remove=['FunctionalObjectProperty(:usesGPU)'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            java = root/'ManchesterRoundtripCheck.java'
            java.write_text(source, encoding='utf-8')
            libs = str(LIB/'*')
            compiled = subprocess.run(['javac','-encoding','UTF-8','-cp',libs,'-d',str(root),str(java)],
                                      capture_output=True,text=True,timeout=120)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            for change in (dict(add=[],remove=[]),delta):
                with self.subTest(delta=change):
                    before = hashlib.sha256(CORE.read_bytes()).hexdigest()
                    result = evaluate(CORE,change['add'],change['remove'])
                    text = result['manchester']
                    self.assertIn('Prefix: : <https://example.org/ontologies/videocard#>',text)
                    self.assertIn('Prefix: xsd:',text)
                    self.assertIn('Ontology: <https://example.org/ontologies/videocard>',text)
                    self.assertIn('<https://example.org/ontologies/videocard/1.0.0>',text)
                    self.assertIn('Онтология дискретных видеокарт',text)
                    document = root/'candidate.omn'
                    document.write_text(text,encoding='utf-8')
                    check = subprocess.run(['java','-cp',str(root)+':'+libs,'ManchesterRoundtripCheck',
                                            str(CORE),str(document),json.dumps(change,ensure_ascii=False)],
                                           capture_output=True,text=True,timeout=120)
                    self.assertEqual(check.returncode,0,check.stderr)
                    restored = evaluate(document,[],[])
                    self.assertEqual(restored['axioms'],result['axioms'])
                    self.assertEqual(restored['counts'],result['counts'])
                    self.assertEqual(hashlib.sha256(CORE.read_bytes()).hexdigest(),before)

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

"""Synthetic layout checks only; mocks do not establish experiment acceptance."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from lab4.optimizer.paths import ROOT, OPTIMIZER, ASSESSMENT, TESTS, SPEC, SCRIPTS, CORE, HARNESS, EXPECTED, REQUIREMENTS
from lab4.scripts import delivery
from lab4.optimizer.metrics import BASELINE_COUNTS


class DeliveryTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)/'SYNTHETIC-SOURCE'
        shutil.copytree(OPTIMIZER,root/'lab4/optimizer',ignore=shutil.ignore_patterns('__pycache__','*.md'))
        (root/'lab4/optimizer/README.md').write_text('[Operator](../docs/OPERATOR.md)\n')
        def copy(source,name):
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        copy(CORE,'lab2/ontology/videocard.owl')
        copy(EXPECTED,'lab2/tests/expected.json')
        copy(HARNESS/'src/Main.java','lab2/tests/harness/src/Main.java')
        copy(HARNESS/'fetch_libs.sh','lab2/tests/harness/fetch_libs.sh')
        copy(SPEC,'lab4/tz_videokarta_lr4_nn_v1.0.docx')
        copy(REQUIREMENTS,'lab4/requirements.txt')
        copy(SCRIPTS/'delivery.py','lab4/scripts/delivery.py')
        copy(SCRIPTS/'report.py','lab4/scripts/report.py')
        (root/'lab4/scripts/package.py').write_text('REPO_ONLY = True\n')
        copy(TESTS/'run_tests.sh','lab4/tests/run_tests.sh')
        (root/'lab4/tests/test_dummy.py').write_text('SYNTHETIC = True\n')
        (root/'lab4/tests/test_package.py').write_text('REPO_ONLY = True\n')
        copy(ASSESSMENT/'fixtures/expected.json','lab4/assessment/fixtures/expected.json')
        copy(ASSESSMENT/'concept_pairs.csv','lab4/assessment/concept_pairs.csv')
        documentation={}
        for name in delivery.DOCS:
            relative='lab4/docs/'+name
            path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('Synthetic layout fixture; not real acceptance.\n')
            # Methodology is already under assessment in the canonical tree.
            if name=='assessment/METHODOLOGY.md':
                relative='lab4/assessment/METHODOLOGY.md'
                (root/relative).write_text(path.read_text())
            documentation[name]=relative
        (root/'README.md').write_text('Synthetic delivery fixture.\n')
        (root/'lab4/docs/OPERATOR.md').write_text('''[Methodology](../assessment/METHODOLOGY.md#formula)
[Expected](../assessment/fixtures/expected.json "fixture title")
[Data directory](../assessment/)
[Specification](../tz_videokarta_lr4_nn_v1.0.docx)
[External](https://example.org/guide) and [anchor](#local).
[`Model docs`](../optimizer/README.md)
[reference]: ../assessment/concept_pairs.csv "pairs"
Inline example: `[not a link](missing-inline.md)`.
```text
[not a link](missing-code.md)
```
''')
        final=root/'lab4/final.owl'
        final.write_text('''<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#"><owl:Ontology rdf:about="https://example.org/ontologies/videocard"><owl:versionIRI rdf:resource="https://example.org/ontologies/videocard/2.0.0"/><owl:versionInfo>2.0.0</owl:versionInfo></owl:Ontology></rdf:RDF>''')
        digest=hashlib.sha256(final.read_bytes()).hexdigest()
        (root/'expert.json').write_text(json.dumps(dict(approved=True,final_sha256=digest,validation=dict(status='valid',F=1.3))))
        runs=[]
        for mode,seeds in [('model',range(101,106)),('control',range(201,206)),('debug',[100])]:
            for seed in seeds:
                relative=f'lab4/runs/{mode}-{seed}'
                path=root/relative;path.mkdir(parents=True)
                (path/'metadata.json').write_text(json.dumps(dict(mode='model' if mode=='debug' else mode,
                    phase='debug' if mode=='debug' else 'main',seed=seed)))
                (path/'evaluations.jsonl').write_text('Synthetic placeholder; analysis is mocked in this layout test.\n')
                if mode!='debug':runs.append(relative)
        manifest=dict(schema=1,accepted=True,checks={f'T{i:02d}':'passed' for i in range(1,12)},
                      final_ontology='lab4/final.owl',final_sha256=digest,expert_review='expert.json',
                      debug_run='lab4/runs/debug-100',runs=runs,readme='README.md',docs=documentation)
        path=root/'accepted.json';path.write_text(json.dumps(manifest))
        return root,path,manifest

    def synthetic_analysis(self,path,replay):
        self.assertTrue(replay)
        meta=json.loads((path/'metadata.json').read_text())
        return dict(**meta,t04=dict(meets_70_percent=True))

    def summary(self):
        return dict(targets=dict(maximum=True,median=True,each_above_one=True,median_above_control=True),
                    series_timing={mode:dict(within_eight_hours=True) for mode in ('model','control')})

    def synthetic_evaluate(self,path,add,remove):
        return dict(counts={**BASELINE_COUNTS,'Individuals':41,'Q':4 if path.name=='final.owl' else 10},
                    axioms=['synthetic core'])

    def test_canonical_layout_preserves_code_bytes_and_imports_after_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root,path,manifest=self.fixture(directory)
            original_operator=(root/'lab4/docs/OPERATOR.md').read_bytes()
            archive=Path(directory)/'SYNTHETIC.zip'
            with patch.object(delivery.analysis,'analyze_run',side_effect=self.synthetic_analysis), \
                    patch.object(delivery.analysis,'summarize',return_value=self.summary()), \
                    patch.object(delivery,'evaluate',side_effect=self.synthetic_evaluate):
                result=delivery.build_delivery(root,path,archive)
            unpacked=Path(directory)/'unpacked'
            with zipfile.ZipFile(archive) as zipped:
                names=zipped.namelist()
                self.assertNotIn('tests/test_package.py',names)
                self.assertNotIn('scripts/package.py',names)
                self.assertFalse(any(name.startswith(('lab2/','lab4/optimizer/')) for name in names))
                self.assertEqual(zipped.read('optimizer/paths.py'),(OPTIMIZER/'paths.py').read_bytes())
                self.assertEqual(zipped.read('optimizer/bridge.py'),(OPTIMIZER/'bridge.py').read_bytes())
                self.assertEqual(zipped.read('ontology/1.0.0/videocard.owl'),(root/'lab2/ontology/videocard.owl').read_bytes())
                self.assertIn('test_package.py',result['excluded_repo_tests'][0])
                operator=zipped.read('docs/OPERATOR.md').decode()
                self.assertIn('[Methodology](assessment/METHODOLOGY.md#formula)',operator)
                self.assertIn('[Expected](assessment/fixtures/expected.json "fixture title")',operator)
                self.assertIn('[Data directory](assessment/)',operator)
                self.assertIn('[Specification](tz_videokarta_lr4_nn_v1.0.docx)',operator)
                self.assertIn('[External](https://example.org/guide)',operator)
                self.assertIn('[`Model docs`](../optimizer/README.md)',operator)
                self.assertIn('[reference]: assessment/concept_pairs.csv "pairs"',operator)
                self.assertIn('`[not a link](missing-inline.md)`',operator)
                self.assertIn('```text\n[not a link](missing-code.md)\n```',operator)
                self.assertTrue(result['documentation_link_adaptations'])
                for destination,original in delivery.collect_sources(root,manifest).items():
                    if original.suffix.lower()!='.md':
                        self.assertEqual(hashlib.sha256(zipped.read(destination)).hexdigest(),
                                         hashlib.sha256(original.read_bytes()).hexdigest(),destination)
                zipped.extractall(unpacked)
            self.assertEqual((root/'lab4/docs/OPERATOR.md').read_bytes(),original_operator)
            canonical={**manifest, 'final_ontology':'ontology/2.0.0/videocard.owl',
                       'expert_review':'docs/expert-review.json', 'readme':'README.md',
                       'debug_run':'runs/debug-100',
                       'runs':['runs/'+Path(name).name for name in manifest['runs']],
                       'docs':{name:'docs/'+name for name in manifest['docs']}}
            canonical_files=delivery.collect_sources(unpacked,canonical)
            self.assertEqual(canonical_files['scripts/delivery.py'],(unpacked/'scripts/delivery.py').resolve())
            self.assertEqual(canonical_files['docs/assessment/fixtures/expected.json'],
                             (unpacked/'docs/assessment/fixtures/expected.json').resolve())
            updated,changes,missing=delivery.adapt_documentation(
                (unpacked/'docs/OPERATOR.md').read_bytes(),unpacked/'docs/OPERATOR.md',
                'docs/OPERATOR.md',canonical_files)
            self.assertFalse(changes)
            self.assertFalse(missing)
            self.assertEqual(updated,(unpacked/'docs/OPERATOR.md').read_bytes())
            probe='''import json
from lab4.optimizer import bridge, validator, release
from lab4.optimizer.paths import *
assert IS_DELIVERY
assert CORE == ROOT/'ontology/1.0.0/videocard.owl' and CORE.is_file()
assert HARNESS == ROOT/'tests/harness' and (HARNESS/'src/Main.java').is_file()
assert EXPECTED == ROOT/'tests/expected.json' and EXPECTED.is_file()
assert ASSESSMENT == ROOT/'docs/assessment'
assert json.loads((ASSESSMENT/'fixtures/expected.json').read_text())
assert (ASSESSMENT/'concept_pairs.csv').is_file()
from lab4.scripts import delivery, report
print('SYNTHETIC layout import check passed')
'''
            checked=subprocess.run([sys.executable,'-I','-c','import sys;sys.path.insert(0,sys.argv[1]);exec(sys.argv[2])',str(unpacked),probe],
                                   cwd=unpacked,text=True,capture_output=True)
            self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertIn('SYNTHETIC layout',checked.stdout)

    def test_broken_documentation_link_blocks_archive_without_rewriting_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root,path,manifest=self.fixture(directory)
            source=root/'lab4/docs/OPERATOR.md'
            source.write_text('[Missing](../assessment/absent.csv)\n')
            original=source.read_bytes()
            output=Path(directory)/'must-not-exist.zip'
            with patch.object(delivery.analysis,'analyze_run',side_effect=self.synthetic_analysis), \
                    patch.object(delivery.analysis,'summarize',return_value=self.summary()), \
                    patch.object(delivery,'evaluate',side_effect=self.synthetic_evaluate):
                with self.assertRaisesRegex(ValueError,'Unresolved local documentation'):
                    delivery.build_delivery(root,path,output)
            self.assertEqual(source.read_bytes(),original)
            self.assertFalse(output.exists())

    def test_refuses_missing_approval_or_series_and_does_not_create_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root,path,manifest=self.fixture(directory)
            output=Path(directory)/'refused.zip'
            for change in ({'accepted':False},{'runs':manifest['runs'][:9]},
                           {'checks':{}},{'final_sha256':'0'*64}):
                path.write_text(json.dumps({**manifest,**change}))
                with self.subTest(change=change), self.assertRaises(ValueError):
                    delivery.build_delivery(root,path,output)
                self.assertFalse(output.exists())
            path.write_text(json.dumps(manifest))
            summary=self.summary();summary['series_timing']['model']['within_eight_hours']=False
            with patch.object(delivery.analysis,'analyze_run',side_effect=self.synthetic_analysis), \
                    patch.object(delivery.analysis,'summarize',return_value=summary):
                with self.assertRaisesRegex(ValueError,'eight hours'):delivery.build_delivery(root,path,output)
            self.assertFalse(output.exists())

    def test_historical_run_link_cannot_silently_point_to_selected_debug(self):
        with tempfile.TemporaryDirectory() as directory:
            root,path,manifest=self.fixture(directory)
            old=root/'lab4/runs/debug-100'
            old.rename(root/'lab4/runs/debug-100-v4')
            old.mkdir()
            (old/'historical.txt').write_text('Earlier, unselected experiment.\n')
            manifest['debug_run']='lab4/runs/debug-100-v4'
            path.write_text(json.dumps(manifest))
            (root/'lab4/docs/OPERATOR.md').write_text('[Historical](../runs/debug-100/)\n')
            output=Path(directory)/'must-not-exist.zip'
            with patch.object(delivery.analysis,'analyze_run',side_effect=self.synthetic_analysis), \
                    patch.object(delivery.analysis,'summarize',return_value=self.summary()), \
                    patch.object(delivery,'evaluate',side_effect=self.synthetic_evaluate):
                with self.assertRaisesRegex(ValueError,'Unresolved local documentation'):
                    delivery.build_delivery(root,path,output)
            self.assertFalse(output.exists())

    def test_explicit_active_clock_preserves_calendar_failure_and_requires_complete_timings(self):
        with tempfile.TemporaryDirectory() as directory:
            root,path,manifest=self.fixture(directory)
            manifest['performance_clock']='active_sessions'
            path.write_text(json.dumps(manifest))
            summary=self.summary()
            summary['series_timing']['model']['within_eight_hours']=False
            def measured(run,replay):
                return {**self.synthetic_analysis(run,replay),'active_seconds':100.0}
            with patch.object(delivery.analysis,'analyze_run',side_effect=measured), \
                    patch.object(delivery.analysis,'summarize',return_value=summary), \
                    patch.object(delivery,'evaluate',side_effect=self.synthetic_evaluate):
                result=delivery.build_delivery(root,path,Path(directory)/'synthetic-active.zip')
            self.assertFalse(result['series']['series_timing']['model']['within_eight_hours'])
            self.assertEqual(result['active_series_seconds'],dict(model=500.0,control=500.0))
            for invalid in (None,True,-1,float('inf'),6000):
                def bad(run,replay):
                    return {**self.synthetic_analysis(run,replay),'active_seconds':invalid}
                with self.subTest(invalid=invalid), \
                        patch.object(delivery.analysis,'analyze_run',side_effect=bad), \
                        patch.object(delivery.analysis,'summarize',return_value=summary):
                    with self.assertRaisesRegex(ValueError,'active timing'):
                        delivery.qualify(root,manifest)

    def test_selected_evidence_preserves_history_in_source_and_rejects_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root,_,manifest=self.fixture(directory)
            evidence=root/'lab4/assessment/evidence'
            (evidence/'accepted').mkdir(parents=True)
            (evidence/'accepted/result.json').write_text('{"synthetic":true}\n')
            (evidence/'accepted/results').mkdir()
            (evidence/'accepted/results/T11.log').write_text('Synthetic acceptance log.\n')
            (evidence/'old-trial.txt').write_text('Historical evidence stays in the repository.\n')
            manifest['assessment_evidence']=['accepted']
            files=delivery.collect_sources(root,manifest)
            self.assertIn('docs/assessment/evidence/accepted/result.json',files)
            self.assertIn('docs/assessment/evidence/accepted/results/T11.log',files)
            self.assertNotIn('docs/assessment/evidence/old-trial.txt',files)
            self.assertIn('docs/assessment/fixtures/expected.json',files)
            self.assertTrue((evidence/'old-trial.txt').is_file())
            for invalid in ([],['../outside'],['accepted','accepted'],'accepted'):
                with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                    delivery.collect_sources(root,{**manifest,'assessment_evidence':invalid})

    def test_rejects_external_and_symlink_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root,path,manifest=self.fixture(directory)
            with self.assertRaisesRegex(ValueError,'safe relative'):
                delivery.source(root,'../outside')
            (root/'symlink').symlink_to(path)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                delivery.source(root,'symlink')


if __name__ == '__main__':
    unittest.main()

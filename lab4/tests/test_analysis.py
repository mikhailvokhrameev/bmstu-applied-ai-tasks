"""Synthetic fixtures only: no experimental measurements or real series."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lab4.optimizer import analysis, journal


def synthetic_fixture(root, last_generation=20):
    rows=[];history=[]
    for g in range(last_generation + 1):
        new=[]
        for _ in range(10 if g==0 else 8):
            i=len(rows)
            row=dict(id=i,generation=g,parents=[],operator='initial' if not g else 'mutation',delta={'add':[],'remove':[]},status='valid',F=1+i/1000,code=None,seed=999,mode='model',elapsed_seconds=.01,attempts=[dict(response='synthetic parsed response')])
            rows.append(row);new.append(copy.deepcopy(row))
        pop=sorted((history[-1][:2] if g else [])+new,key=lambda c:(-c['F'],c['id']))
        history.append(pop)
    raw=b''.join(journal.encoded(r)+b'\n' for r in rows)
    (root/'metadata.json').write_bytes(b'{}');(root/'evaluations.jsonl').write_bytes(raw)
    cp=dict(generation=last_generation,evaluations=copy.deepcopy(rows),history=history,best=history[-1][0],log_sha256=journal.digest(raw),metadata_sha256=journal.digest(b'{}'))
    seal_checkpoint(root,cp)
    return cp


def seal_checkpoint(root,cp):
    cp.pop('payload_sha256',None);cp['payload_sha256']=journal.digest(journal.encoded(cp));(root/'checkpoint.json').write_bytes(journal.encoded(cp))


class AnalysisTests(unittest.TestCase):
    def test_debug_budget_and_projection_are_separate_from_main_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);synthetic_fixture(root,last_generation=3)
            meta=dict(seed=999,mode='model',phase='debug',config_sha256='test-only')
            with patch.object(journal,'_metadata',return_value=meta), patch.object(analysis,'timing_summary',return_value=dict(wall_clock_seconds=680)):
                result=analysis.analyze_run(root)
            self.assertEqual(result['phase'],'debug')
            self.assertEqual(len(result['generations']),4)
            self.assertEqual(result['t04']['model_requests'],34)
            self.assertTrue(result['t04']['meets_70_percent'])
            self.assertEqual(result['t04']['projected_170_evaluation_seconds'],3400)
            self.assertTrue(result['t04']['projected_within_eight_hours'])
            self.assertEqual(result['t04']['projected_850_evaluation_seconds'],17000)
            self.assertTrue(result['t04']['projected_series_within_eight_hours'])
            self.assertIsNone(result['t04']['duration_acceptance'])
            with patch.object(journal,'_metadata',return_value={**meta,'phase':'main'}):
                with self.assertRaisesRegex(ValueError,'170 evaluations'):analysis.analyze_run(root)
            with self.assertRaisesRegex(ValueError,'Debug runs'):analysis.summarize([result])

    def test_one_run_projection_does_not_pass_the_five_run_series_budget(self):
        rows=[dict(operator='mutation',status='invalid',elapsed_seconds=1766.48/34,
                   attempts=[dict(response='synthetic')]) for _ in range(34)]
        result=analysis.debug_assessment(rows,'model',dict(wall_clock_seconds=2461.24))
        self.assertAlmostEqual(result['projected_170_evaluation_seconds'],12306.2)
        self.assertTrue(result['projected_within_eight_hours'])
        self.assertAlmostEqual(result['projected_850_evaluation_seconds'],61531.)
        self.assertFalse(result['projected_series_within_eight_hours'])
        self.assertAlmostEqual(result['steady_projection_series_seconds'],44162.)
        self.assertIsNone(result['duration_acceptance'])
        self.assertIn('850 evaluations',result['projection_status'])
        self.assertIn('not acceptance',result['steady_projection_status'])
        no_wall=analysis.debug_assessment(rows,'model',{})
        self.assertIsNone(no_wall['projected_850_evaluation_seconds'])
        self.assertIsNone(no_wall['projected_series_within_eight_hours'])
        self.assertAlmostEqual(no_wall['steady_projection_series_seconds'],44162.)
        rows[0].pop('elapsed_seconds')
        self.assertIsNone(analysis.debug_assessment(rows,'model',{})['steady_projection_series_seconds'])

    def test_first_parsed_response_is_not_ontology_validity_or_retry_success(self):
        # Ten model requests: seven parse on their first response, despite all
        # failing ontology validation. Crossover must not inflate the denominator.
        rows=[dict(operator='mutation',status='invalid',attempts=[dict(response='parsed')]) for _ in range(7)]
        rows += [dict(operator='mutation',status='valid',attempts=[dict(response='bad',parse_error='bad OWL'),dict(response='parsed')]) for _ in range(3)]
        rows += [dict(operator='crossover',status='valid',attempts=[]) for _ in range(2)]
        result=analysis.debug_assessment(rows,'model',{})
        self.assertEqual(result['model_requests'],10)
        self.assertEqual(result['first_response_success_count'],7)
        self.assertEqual(result['first_response_fraction'],.7)
        self.assertTrue(result['meets_70_percent'])
        self.assertAlmostEqual(result['valid_ontology_fraction'],5/12)
        self.assertIsNone(result['projected_170_evaluation_seconds'])
        rows[0]['attempts'][0]['parse_error']='not parsed'
        self.assertFalse(analysis.debug_assessment(rows,'model',{})['meets_70_percent'])

    def test_missing_first_attempt_evidence_does_not_qualify_t04(self):
        for attempts in ([],[{}],[dict(response=None)],[dict(response='partial',service_error='incomplete')]):
            rows=[dict(operator='initial',status='valid',attempts=attempts)]
            result=analysis.debug_assessment(rows,'model',{})
            self.assertEqual(result['first_response_success_count'],0)
            self.assertIsNot(result['meets_70_percent'],True)
        rows=[dict(operator='initial',status='valid',attempts=[dict(response='parsed')])]
        control=analysis.debug_assessment(rows,'control',{})
        self.assertEqual(control['model_requests'],0)
        self.assertIsNone(control['first_response_fraction'])
        self.assertIsNone(control['meets_70_percent'])

    def test_unknown_metadata_phase_is_rejected(self):
        with patch.object(journal,'_metadata',return_value=dict(phase='other')):
            with self.assertRaisesRegex(ValueError,'phase'):analysis.analyze_run('unused')

    def test_real_journal_callbacks_and_resumed_timing(self):
        from lab4.tests.test_journal import JournalTests
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=root/'config';config.write_text('{}');run=root/'TEST-ONLY'
            runtime=JournalTests().runtime
            with self.assertRaisesRegex(RuntimeError,'interrupted'):
                journal.start(config,'control',999,run,runtime(14))
            first=journal.read_timing(run)
            self.assertEqual(first['sessions'][0]['outcome'],'interrupted')
            journal.resume(run,runtime())
            result=analysis.analyze_run(run)
            self.assertGreaterEqual(result['wall_clock_seconds'],0)
            self.assertEqual(len(journal.read_timing(run)['sessions']),2)
            rows=[json.loads(line) for line in (run/'evaluations.jsonl').read_text().splitlines()]
            checkpoint=json.loads((run/'checkpoint.json').read_text())
            self.assertGreater(set(rows[0]),set(checkpoint['evaluations'][0]))
            self.assertEqual(result['best_id'],checkpoint['best']['id'])
            timing=(run/'timing.json').read_bytes()
            journal.resume(run,runtime())
            self.assertEqual((run/'timing.json').read_bytes(),timing)
            summary=analysis.series_timing([result])
            self.assertTrue(summary['within_eight_hours'])
            (run/'timing.json').unlink()
            self.assertIsNone(analysis.analyze_run(run)['wall_clock_seconds'])

    def test_timing_rejects_empty_and_inconsistent_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            base=dict(schema=1,complete_origin=True,started_at=100,completed_at=101)
            cases=[[],[dict(started_at=100,ended_at=200,outcome='completed')],
                   [dict(started_at=100,outcome='completed')],
                   [dict(started_at=100,ended_at=101,outcome='interrupted')],
                   [dict(started_at=100,ended_at=100.5,outcome='completed')]]
            for sessions in cases:
                with self.subTest(sessions=sessions):
                    journal._timing_write(root,dict(base,sessions=sessions))
                    self.assertIsNone(analysis.timing_summary(root)['wall_clock_seconds'])
            journal._timing_write(root,dict(base,sessions=[dict(started_at=100,ended_at=101,outcome='completed')]))
            self.assertEqual(analysis.timing_summary(root)['wall_clock_seconds'],1)

    def test_legacy_resume_before_first_evaluation_has_unknown_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(journal,'_run_search',return_value=None):
                journal._run(root,{}, {}, {},None)
            self.assertFalse(journal.read_timing(root)['complete_origin'])
            self.assertIsNone(analysis.timing_summary(root)['wall_clock_seconds'])

    def test_series_wall_clock_includes_gaps(self):
        result=analysis.series_timing([dict(wall_clock_seconds=1,started_at=0,completed_at=1),dict(wall_clock_seconds=1,started_at=30000,completed_at=30001)])
        self.assertEqual(result['seconds'],30001)
        self.assertFalse(result['within_eight_hours'])
        self.assertIsNone(analysis.series_timing([{}])['within_eight_hours'])

    def test_exact_and_ties(self):
        self.assertAlmostEqual(analysis.mann_whitney([2]*5,[1]*5)['p'],1/252)
        self.assertEqual(analysis.mann_whitney([1]*5,[1]*5)['p'],1)
        self.assertEqual(analysis.mann_whitney([1]*5,[2]*5)['U'],0)

    def test_synthetic_run_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cp=synthetic_fixture(root)
            with patch.object(journal,'_metadata',return_value=dict(seed=999,mode='model',config_sha256='test-only')):
                r=analysis.analyze_run(root)
                self.assertEqual(r['phase'],'main')
                self.assertIsNone(r['t04'])
                self.assertEqual(r['best_generation'],20)
                self.assertEqual(len(r['generations']),21)
                self.assertIsNone(r['wall_clock_seconds'])
                self.assertIsNone(r['replay'])
                cp['history'][1][0],cp['history'][1][1]=cp['history'][1][1],cp['history'][1][0]
                seal_checkpoint(root,cp)
                with self.assertRaisesRegex(ValueError,'rank'):analysis.analyze_run(root)

    def test_rejects_incomplete_and_debug_series(self):
        with self.assertRaisesRegex(ValueError,'seeds'):analysis.summarize([])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cp=synthetic_fixture(root);cp['generation']=19;seal_checkpoint(root,cp)
            with patch.object(journal,'_metadata',return_value=dict(seed=999,mode='model')):
                with self.assertRaisesRegex(ValueError,'Incomplete'):analysis.analyze_run(root)

    def test_csv_and_png_from_explicit_synthetic_fixture(self):
        try:import matplotlib
        except ImportError:self.skipTest('Optional matplotlib is unavailable')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);synthetic_fixture(root)
            with patch.object(journal,'_metadata',return_value=dict(seed=999,mode='model',config_sha256='test-only')):result=analysis.analyze_run(root)
            analysis.export_run(result,root/'TEST-ONLY')
            self.assertTrue((root/'TEST-ONLY/model-999.png').read_bytes().startswith(b'\x89PNG'))
            self.assertEqual(len((root/'TEST-ONLY/model-999.csv').read_text().splitlines()),22)

if __name__=='__main__':unittest.main()

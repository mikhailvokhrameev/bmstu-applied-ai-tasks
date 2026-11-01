"""Synthetic fixtures only: no experimental measurements or real series."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lab4.optimizer import analysis, journal


def synthetic_fixture(root):
    rows=[];history=[]
    for g in range(21):
        new=[]
        for _ in range(10 if g==0 else 8):
            i=len(rows)
            row=dict(id=i,generation=g,parents=[],operator='initial' if not g else 'mutation',delta={'add':[],'remove':[]},status='valid',F=1+i/1000,code=None,seed=999,mode='model',elapsed_seconds=.01)
            rows.append(row);new.append(copy.deepcopy(row))
        pop=sorted((history[-1][:2] if g else [])+new,key=lambda c:(-c['F'],c['id']))
        history.append(pop)
    raw=b''.join(journal.encoded(r)+b'\n' for r in rows)
    (root/'metadata.json').write_bytes(b'{}');(root/'evaluations.jsonl').write_bytes(raw)
    cp=dict(generation=20,evaluations=copy.deepcopy(rows),history=history,best=history[-1][0],log_sha256=journal.digest(raw),metadata_sha256=journal.digest(b'{}'))
    seal_checkpoint(root,cp)
    return cp


def seal_checkpoint(root,cp):
    cp.pop('payload_sha256',None);cp['payload_sha256']=journal.digest(journal.encoded(cp));(root/'checkpoint.json').write_bytes(journal.encoded(cp))


class AnalysisTests(unittest.TestCase):
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

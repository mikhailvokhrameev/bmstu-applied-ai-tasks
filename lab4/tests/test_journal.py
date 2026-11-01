import json
import tempfile
import unittest
from pathlib import Path
from lab4.optimizer import journal
from lab4.optimizer.validator import ValidationResult

class JournalTests(unittest.TestCase):
    def runtime(self, fail=None):
        n=[0]
        def check(d):
            n[0]+=1
            if n[0]==fail: raise RuntimeError('interrupted')
            return ValidationResult('valid',F=1+len(d['add'])/100)
        return dict(validate=check, control_generator=lambda d,r:dict(add=d['add']+[str(r.randrange(100000))],remove=[]),
                    inspect=lambda d:dict(axioms=sorted(d['add'])))
    def test_resume_discards_partial_to_audit_and_matches_uninterrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config=root/'search.yaml';config.write_text('{}')
            a=root/'a'; b=root/'b'
            with self.assertRaisesRegex(RuntimeError,'interrupted'):
                journal.start(config,'control',5,a,self.runtime(14))
            result=journal.resume(a,self.runtime())
            expected=journal.start(config,'control',5,b,self.runtime())
            self.assertEqual(result,expected)
            rows=[json.loads(s) for s in (a/'evaluations.jsonl').read_text().splitlines()]
            self.assertEqual([r['id'] for r in rows],list(range(170)))
            self.assertEqual(len(list(a.glob('audit-*.jsonl'))),1)
            self.assertEqual(len(next(a.glob('audit-*.jsonl')).read_text().splitlines()),3)
    def test_metadata_and_checkpoint_corruption_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            journal.start(config,'control',5,run,self.runtime())
            (run/'checkpoint.json').write_text('{')
            with self.assertRaisesRegex(journal.JournalError,'checkpoint'):
                journal.resume(run,self.runtime())
    def test_incompatible_checkpoint_and_changed_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            journal.start(config,'control',5,run,self.runtime())
            cp=json.loads((run/'checkpoint.json').read_text());cp['schema']=999
            (run/'checkpoint.json').write_text(json.dumps(cp))
            with self.assertRaisesRegex(journal.JournalError,'incompatible'):
                journal.resume(run,self.runtime())
            (run/'config.yaml').write_text('{"generations":1}')
            with self.assertRaisesRegex(journal.JournalError,'configuration changed'):
                journal.resume(run,self.runtime())
    def test_interruption_before_first_checkpoint_and_finished_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            with self.assertRaises(RuntimeError):journal.start(config,'control',5,run,self.runtime(3))
            result=journal.resume(run,self.runtime())
            def forbidden(d):raise AssertionError('completed resume evaluated again')
            with (run/'evaluations.jsonl').open('ab') as file:file.write(b'{torn')
            again=journal.resume(run,dict(validate=forbidden,control_generator=forbidden))
            self.assertEqual(result,again)
            self.assertEqual(sorted(len(p.read_text().splitlines()) for p in run.glob('audit-*.jsonl')),[1,2])

    def test_real_core_replay_never_calls_models(self):
        from unittest.mock import patch
        from lab4.optimizer.bridge import evaluate, CORE
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            journal.start(config,'control',5,run,self.runtime())
            rows=[json.loads(s) for s in (run/'evaluations.jsonl').read_text().splitlines()]
            rows[0].update(delta=dict(add=[],remove=[]),F=1.,axioms=evaluate(CORE,[],[])['axioms'])
            (run/'evaluations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with patch('lab4.optimizer.proposals.OllamaModels.propose',side_effect=AssertionError('model called')) as model, patch('lab4.optimizer.proposals.OllamaModels.embed',side_effect=AssertionError('embedding called')) as embed:
                self.assertTrue(journal.replay(run,0)['matches'])
                model.assert_not_called();embed.assert_not_called()

    def test_replay_uses_saved_delta_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            journal.start(config,'control',5,run,self.runtime())
            replay=journal.replay(run,3,inspect=lambda d:dict(axioms=sorted(d['add'])),score=lambda d:1+len(d['add'])/100)
            self.assertTrue(replay['matches'])
            replay=journal.replay(run,3,inspect=lambda d:dict(axioms=[]),score=lambda d:0)
            self.assertFalse(replay['matches'])

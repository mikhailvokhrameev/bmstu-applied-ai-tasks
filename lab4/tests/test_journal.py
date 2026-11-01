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

    def test_resume_rejects_changed_added_or_removed_jars(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);lib=root/'lib';lib.mkdir();jar=lib/'owl.jar';jar.write_bytes(b'original')
            config=root/'c';config.write_text('{}');run=root/'run'
            with patch.object(journal,'LIB',lib):
                journal.start(config,'control',5,run,self.runtime())
                for change in ('changed','removed','added'):
                    jar.write_bytes(b'original')
                    extra=lib/'hermit.jar'
                    if extra.exists():extra.unlink()
                    if change=='changed':jar.write_bytes(b'new version')
                    elif change=='removed':jar.unlink()
                    else:extra.write_bytes(b'extra')
                    with self.assertRaisesRegex(journal.JournalError,'incompatible libraries'):
                        journal.resume(run,self.runtime())

    def test_audit_replay_has_unambiguous_address_with_reused_active_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            with self.assertRaises(RuntimeError):journal.start(config,'control',5,run,self.runtime(14))
            partial=[json.loads(s) for s in (run/'evaluations.jsonl').read_text().splitlines()][-1]
            resumed=self.runtime()
            resumed['control_generator']=lambda d,r:dict(add=d['add']+['resumed-'+str(r.randrange(100000))],remove=[])
            journal.resume(run,resumed)
            active=[json.loads(s) for s in (run/'evaluations.jsonl').read_text().splitlines()][partial['id']]
            self.assertNotEqual(active['delta'],partial['delta'])
            audit=next(run.glob('audit-*.jsonl'))
            # Simulate a torn final append; full preceding audit records stay readable.
            with audit.open('ab') as file:file.write(b'{torn')
            address=audit.stem+':'+str(partial['id'])
            seen=[]
            result=journal.replay(run,address,inspect=lambda d:(seen.append(d) or dict(axioms=sorted(d['add']))),score=lambda d:1+len(d['add'])/100)
            self.assertTrue(result['matches']);self.assertEqual(seen,[partial['delta']])
            self.assertTrue(journal.replay(run,str(partial['id']),inspect=lambda d:dict(axioms=sorted(d['add'])),score=lambda d:1+len(d['add'])/100)['matches'])
            with self.assertRaises(journal.JournalError):journal.replay(run,'../audit:12')

    def test_incomplete_http_response_retained_in_interruption_log(self):
        from unittest.mock import patch
        from lab4.optimizer.proposals import OllamaModels
        from lab4.optimizer.runtime import ModelGenerator
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'c';config.write_text('{}');run=root/'run'
            raw=dict(done=False,response='partial',model='pinned',extra='full raw')
            client=OllamaModels('pinned','embed')
            context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
            runtime=self.runtime();runtime['model_generator']=ModelGenerator(client.propose,context)
            with patch.object(client,'_post',return_value=raw):
                with self.assertRaises(RuntimeError):journal.start(config,'model',5,run,runtime)
            interruption=json.loads((run/'interruptions.jsonl').read_text())
            self.assertEqual(interruption['attempts'][0]['response']['raw'],raw)

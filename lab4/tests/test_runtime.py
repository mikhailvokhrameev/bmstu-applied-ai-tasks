import unittest
import random
import json
from unittest.mock import patch
from types import SimpleNamespace
from contextlib import redirect_stdout
from io import StringIO
from lab4.optimizer.runtime import ModelGenerator, build_runtime
from lab4.optimizer.proposals import Proposal, ModelResponse, ProposalError
class AdapterTests(unittest.TestCase):
    def test_retries_and_cumulative_parent_context(self):
        calls=[]
        def propose(context,error):
            calls.append((context,error));return ModelResponse('bad' if len(calls)==1 else 'ok','fake',{'response':'raw'})
        with patch('lab4.optimizer.runtime.parse_proposal',side_effect=[ProposalError('bad JSON'),Proposal('why',['b'],[]) ]):
            g=ModelGenerator(propose,lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6))
            out=g({'add':['a'],'remove':[]},None)
        self.assertEqual(out,dict(add=['a','b'],remove=[]))
        self.assertEqual(len(g.attempts),2)
        self.assertIn('bad JSON',calls[1][1])
        self.assertIn('parent',g.attempts[0]['request'])

    def test_exhaustion_retains_every_response(self):
        from lab4.optimizer.proposals import ProposalError
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        g=ModelGenerator(lambda c,e:'malformed',context)
        with patch('lab4.optimizer.runtime.parse_proposal',side_effect=ProposalError('bad')):
            with self.assertRaisesRegex(ProposalError,'Three unsuccessful'):
                g({'add':[],'remove':[]},None)
        self.assertEqual(len(g.attempts),3)
        self.assertTrue(all(a['response']=='malformed' and a['parse_error']=='bad' for a in g.attempts))

    def test_mutation_cancels_parent_addition_without_changing_crossover(self):
        from lab4.optimizer.search import merge
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        parent=dict(add=['a','b'],remove=[])
        with patch('lab4.optimizer.runtime.parse_proposal',return_value=Proposal('cancel',['c'],['a','core'])):
            result=ModelGenerator(lambda c,e:'ok',context)(parent,None)
        self.assertEqual(result,dict(add=['b','c'],remove=['core']))
        self.assertEqual(parent,dict(add=['a','b'],remove=[]))
        self.assertEqual(merge(parent,dict(add=[],remove=['a'])),dict(add=['a','b'],remove=['a']))

    def test_incomplete_http_response_retained_before_completion_check(self):
        from lab4.optimizer.proposals import OllamaModels
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        for completion in ({'done':False},{}):
            raw=dict(response='partial text',model='pinned',extra={'tokens':[1,2]},**completion)
            client=OllamaModels('pinned','embed');g=ModelGenerator(client.propose,context)
            with patch.object(client,'_post',return_value=raw):
                with self.assertRaisesRegex(RuntimeError,'Incomplete'):
                    g(dict(add=[],remove=[]),random.Random(100))
            self.assertEqual(g.attempts[0]['response']['raw'],raw)
            self.assertEqual(g.attempts[0]['response']['text'],'partial text')

    def test_service_error_is_not_retried_as_a_bad_proposal(self):
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        for source in ('propose','parser'):
            with self.subTest(source=source):
                g=ModelGenerator(lambda c,e:'response',context)
                target=patch.object(g,'propose',side_effect=ValueError('broken service')) if source=='propose' else patch('lab4.optimizer.runtime.parse_proposal',side_effect=ValueError('broken service'))
                with target:
                    with self.assertRaisesRegex(ValueError,'broken service'):
                        g(dict(add=[],remove=[]),None)
                self.assertEqual(len(g.attempts),1)
                self.assertNotIn('parse_error',g.attempts[0])

    def test_debug_precedes_acceptance_but_main_requires_it(self):
        manifest=dict(model='pinned',embedding_model='embed',model_sha256='a'*64,
                      embedding_sha256='b'*64,server_version='test',
                      inventory=dict(classes=[':A']),entities=[],duplicate_threshold=.87)
        for approved in (None,False):
            with self.subTest(approved=approved):
                candidate={**manifest,'acceptance_approved':approved}
                runtime=build_runtime(candidate,100,phase='debug')
                self.assertEqual(runtime['duplicate_checker'].threshold,.87)
                with self.assertRaisesRegex(ValueError,'T04'):
                    build_runtime(candidate,101)
        self.assertIn('model_generator',build_runtime({**manifest,'acceptance_approved':True},101))
        with self.assertRaises(ValueError):build_runtime(manifest,100,phase='unknown')
        with self.assertRaisesRegex(ValueError,'pinned'):
            build_runtime({},100,phase='debug')

    def test_cli_forwards_explicit_debug_phase_and_keeps_main_default(self):
        from lab4.optimizer.__main__ import main
        result=SimpleNamespace(best=SimpleNamespace(id=0,F=1.),evaluations=[None]*34)
        for arguments,phase in ((['--phase','debug'],'debug'),([], 'main')):
            with self.subTest(phase=phase), patch('lab4.optimizer.journal.start',return_value=result) as start, redirect_stdout(StringIO()):
                code=main(['run','--config','config.json','--mode','model','--seed','100','--run-dir','run',*arguments])
                self.assertEqual(code,0)
                start.assert_called_once_with('config.json','model',100,'run',phase=phase)

    def test_ollama_mutation_seeds_vary_reproduce_and_match_audited_requests(self):
        from lab4.optimizer.proposals import OllamaModels
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        client=OllamaModels('pinned','embed')
        generator=ModelGenerator(client.propose,context)
        rng=random.Random(100)
        observed=[]
        def post(path,payload):
            observed.append(payload)
            return dict(response='response',model='pinned',done=True)
        with patch.object(client,'_post',side_effect=post), patch('lab4.optimizer.runtime.parse_proposal',return_value=Proposal('why',['new'],[])):
            generator(dict(add=[],remove=[]),rng)
            first_seed=observed[-1]['options']['seed']
            self.assertEqual(generator.attempts[0]['http_request']['payload'],observed[-1])
            saved_state=rng.getstate()
            generator(dict(add=[],remove=[]),rng)
            second_seed=observed[-1]['options']['seed']
            self.assertNotEqual(first_seed,second_seed)
            restored=random.Random();restored.setstate(saved_state)
            generator(dict(add=[],remove=[]),restored)
            self.assertEqual(observed[-1]['options']['seed'],second_seed)
            self.assertEqual(generator.attempts[0]['http_request']['payload'],observed[-1])
            self.assertEqual(first_seed,random.Random(100).getrandbits(31))

    def test_removal_provenance_reaches_real_prompt_and_owl_parser(self):
        from lab4.optimizer.proposals import OllamaModels
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        added='SubClassOf(:New :Component)'
        removed='SubClassOf(:Old :Component)'
        payload=json.dumps(dict(rationale='Отмена учебного добавления',add=[],remove=[added]),ensure_ascii=False)
        client=OllamaModels('pinned','embed')
        generator=ModelGenerator(client.propose,context)
        observed=[]
        def post(path,body):
            observed.append(body)
            return dict(response=payload,model='pinned',done=True)
        with patch.object(client,'_post',side_effect=post):
            result=generator(dict(add=[added],remove=[removed]),random.Random(100))
        self.assertEqual(result,dict(add=[],remove=[removed]))
        self.assertEqual(generator.attempts[0]['context']['added_axioms'],[added])
        self.assertEqual(generator.attempts[0]['context']['removed_axioms'],[removed])
        prompt=observed[0]['prompt']
        self.assertIn(json.dumps([added],ensure_ascii=False),prompt)
        self.assertIn(json.dumps([removed],ensure_ascii=False),prompt)
        self.assertIn('Если этот список пуст, верни remove=[]',prompt)
        self.assertEqual(generator.attempts[0]['http_request']['payload'],observed[0])

    def test_retry_keeps_mutation_seed_and_audits_feedback_payload(self):
        from lab4.optimizer.proposals import OllamaModels
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        client=OllamaModels('pinned','embed');generator=ModelGenerator(client.propose,context)
        observed=[]
        def post(path,payload):
            observed.append(payload)
            return dict(response='response',model='pinned',done=True)
        with patch.object(client,'_post',side_effect=post), patch('lab4.optimizer.runtime.parse_proposal',side_effect=[ProposalError('retry feedback'),Proposal('why',['new'],[])]):
            generator(dict(add=[],remove=[]),random.Random(100))
        self.assertEqual(len(observed),2)
        self.assertEqual(observed[0]['options'],observed[1]['options'])
        self.assertNotEqual(observed[0]['prompt'],observed[1]['prompt'])
        self.assertIn('retry feedback',observed[1]['prompt'])
        self.assertEqual([attempt['http_request']['payload'] for attempt in generator.attempts],observed)

    def test_delivered_length_limit_retries_with_feedback_and_preserves_raw(self):
        from lab4.optimizer.proposals import OllamaModels
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        raw=dict(response='{"rationale":',model='pinned',done=True,done_reason='length',eval_count=2000)
        valid=dict(response=json.dumps(dict(rationale='Учебное уточнение',add=['SubClassOf(:New :Component)'],remove=[])),model='pinned',done=True)
        client=OllamaModels('pinned','embed');generator=ModelGenerator(client.propose,context)
        with patch.object(client,'_post',side_effect=[raw,valid]) as post:
            result=generator(dict(add=[],remove=[]),random.Random(100))
        self.assertEqual(result,dict(add=['SubClassOf(:New :Component)'],remove=[]))
        self.assertEqual(len(generator.attempts),2)
        self.assertEqual(generator.attempts[0]['response']['raw'],raw)
        self.assertIn('JSON',generator.attempts[0]['parse_error'])
        self.assertIn('JSON',post.call_args_list[1].args[1]['prompt'])
        self.assertTrue(all('service_error' not in attempt for attempt in generator.attempts))

    def test_three_delivered_length_limits_are_invalid_candidates_not_interruptions(self):
        from lab4.optimizer.proposals import OllamaModels
        from lab4.optimizer.search import run
        from lab4.optimizer.validator import ValidationResult
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        raw=dict(response='{"rationale":',model='pinned',done=True,done_reason='length',eval_count=2000)
        client=OllamaModels('pinned','embed');generator=ModelGenerator(client.propose,context)
        audits=[]
        services=dict(model_generator=generator,validate=lambda delta:ValidationResult('valid',F=1.),
                      on_evaluation=lambda candidate,validation,elapsed,error:audits.append(list(generator.attempts)))
        with patch.object(client,'_post',return_value=raw):
            result=run(dict(runtime=services),'model',100,phase='debug')
        rejected=[candidate for candidate in result.evaluations if candidate.operator!='crossover']
        self.assertEqual(len(result.evaluations),34)
        self.assertTrue(rejected)
        self.assertTrue(all(candidate.status=='invalid' and candidate.code=='PROPOSAL' and candidate.F==0. for candidate in rejected))
        for candidate in rejected:
            attempts=audits[candidate.id]
            self.assertEqual(len(attempts),3)
            self.assertTrue(all(attempt['response']['raw']==raw and 'parse_error' in attempt and 'service_error' not in attempt for attempt in attempts))

    def test_compact_parser_feedback_preserves_full_audit_and_first_failure(self):
        context=lambda d:dict(ontology_manchester='parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        invalid=json.dumps(dict(rationale='bad',add=['SubClassOf(:Fresh)'],remove=[]))
        valid=json.dumps(dict(rationale='good',add=['SubClassOf(:Fresh :VideoCardModel)'],remove=[]))
        observed=[]
        def propose(ctx,error):
            observed.append(error);return invalid if len(observed)==1 else valid
        generator=ModelGenerator(propose,context)
        generator(dict(add=[],remove=[]),None)
        self.assertEqual(len(generator.attempts),2)
        first=generator.attempts[0]
        self.assertIn('parse_error',first)
        self.assertLess(len(observed[1]),900)
        self.assertGreater(len(first['parse_diagnostic']['detail']),1000)
        self.assertEqual(first['response'],invalid)
        self.assertEqual(generator.attempts[1]['previous_error'],first['parse_error'])

    def test_runtime_context_uses_each_current_candidate_violation_list(self):
        from lab4.optimizer.metrics import BASELINE_COUNTS
        from lab4.optimizer.proposals import render_prompt
        manifest=dict(model='pinned',embedding_model='embed',model_sha256='a'*64,
                      embedding_sha256='b'*64,server_version='test',
                      inventory=dict(classes=[':VideoCardModel']),entities=[])
        runtime=build_runtime(manifest,100,phase='debug')
        remaining=dict(code='P13',key='https://example.org/ontologies/videocard#usesGPU')
        resolved=dict(code='P13',key='https://example.org/ontologies/videocard#hasMemory')
        baseline=dict(manchester='Class: Original',counts=dict(BASELINE_COUNTS),violations=[resolved,remaining])
        candidate=dict(manchester='Class: Candidate\nObjectProperty: memoryConfigurationOf',
                       counts=dict(BASELINE_COUNTS,Q=9),violations=[remaining])
        with patch('lab4.optimizer.runtime.evaluate',side_effect=[baseline,candidate]) as evaluate:
            before=runtime['model_generator'].context(dict(add=[],remove=[]))
            after=runtime['model_generator'].context(dict(add=['InverseObjectProperties(:memoryConfigurationOf :hasMemory)'],remove=[]))
        self.assertEqual(before['violations'],[resolved,remaining])
        self.assertEqual(after['violations'],[remaining])
        self.assertEqual(after['metrics']['M6'],9)
        self.assertEqual(evaluate.call_args_list[1].args[1],['InverseObjectProperties(:memoryConfigurationOf :hasMemory)'])
        prompt=render_prompt(after)
        self.assertIn(candidate['manchester'],prompt)
        self.assertIn(json.dumps([remaining],ensure_ascii=False,separators=(',',':')),prompt)
        self.assertNotIn(resolved['key'],prompt)
        for instruction in ('Не повторяй аксиомы','ещё не устранённых P13','обратное самому себе','Другие разрешённые изменения также допустимы'):
            self.assertIn(instruction,prompt)

    def test_runtime_wires_independent_generation_and_embedding_endpoints(self):
        manifest=dict(model='generation:model',embedding_model='sentence-transformers/LaBSE',
                      model_sha256='a'*64,embedding_sha256='b'*64,server_version='test',
                      inventory=dict(classes=[':VideoCardModel']),entities=[],
                      endpoint='http://generation.invalid:11435',
                      embedding_endpoint='http://embedding.invalid:11436',
                      embedding_instruction='Represent ontology concept meaning.')
        runtime=build_runtime(manifest,100,phase='debug')
        generation=runtime['model_generator'].propose.__self__
        embedding=runtime['duplicate_checker'].embed.__self__
        self.assertIs(generation,embedding)
        self.assertEqual(generation.endpoint,manifest['endpoint'])
        self.assertEqual(embedding.embedding_endpoint,manifest['embedding_endpoint'])
        self.assertEqual(embedding.embedding_model,'sentence-transformers/LaBSE')
        self.assertEqual(embedding.embedding_instruction,manifest['embedding_instruction'])

    def test_inverse_operand_table_mirrors_all_current_p13_without_selecting_a_property(self):
        from lab4.optimizer.metrics import BASELINE_COUNTS
        from lab4.optimizer.proposals import render_prompt
        iri=lambda name:'<https://example.org/ontologies/videocard#'+name+'>'
        inventory=dict(classes=[iri('VideoCardModel')],
                       object_property_domains={iri('usesGPU'):[iri('VideoCardModel')],
                                                iri('producedByManufacturer'):[iri('VideoCardModel')],
                                                iri('hasMemory'):[iri('VideoCardModel')]},
                       object_property_ranges={iri('usesGPU'):[iri('GPUModel')],
                                               iri('producedByManufacturer'):[iri('Manufacturer')],
                                               iri('hasMemory'):[iri('MemoryConfiguration')]})
        manifest=dict(model='pinned',embedding_model='embed',model_sha256='a'*64,
                      embedding_sha256='b'*64,server_version='test',inventory=inventory,entities=[])
        violations=[dict(code='P13',key=iri('usesGPU')[1:-1]),
                    dict(code='P08',key='unrelated annotation'),
                    dict(code='P13',key=iri('producedByManufacturer')[1:-1]),
                    dict(code='P13',key=iri('MissingInventory')[1:-1])]
        result=dict(manchester='Class: ExactCurrentParent',counts=dict(BASELINE_COUNTS),violations=violations)
        runtime=build_runtime(manifest,100,phase='debug')
        with patch('lab4.optimizer.runtime.evaluate',return_value=result):
            context=runtime['model_generator'].context(dict(add=[],remove=[]))
        table=context['inverse_operands']
        self.assertEqual([row['direct_property'] for row in table],
                         [iri('usesGPU'),iri('producedByManufacturer'),iri('MissingInventory')])
        self.assertEqual(table[0]['DIRECT'],dict(domain=[iri('VideoCardModel')],range=[iri('GPUModel')]))
        self.assertEqual(table[0]['MIRRORED_INVERSE'],dict(domain=[iri('GPUModel')],range=[iri('VideoCardModel')]))
        self.assertEqual(table[1]['MIRRORED_INVERSE'],dict(domain=[iri('Manufacturer')],range=[iri('VideoCardModel')]))
        self.assertFalse(table[0]['incomplete_inventory'])
        self.assertEqual(table[2]['DIRECT'],dict(domain=[],range=[]))
        self.assertTrue(table[2]['incomplete_inventory'])
        self.assertNotIn(iri('hasMemory'),[row['direct_property'] for row in table])
        prompt=render_prompt(context)
        self.assertIn(json.dumps(table,ensure_ascii=False,separators=(',',':')),prompt)
        self.assertIn(result['manchester'],prompt)
        self.assertIn('другие разрешённые изменения остаются доступны',prompt)

    def test_invalid_parent_assessment_is_preserved_in_context_attempt_and_prompt(self):
        context=lambda delta:dict(ontology_manchester='Class: Parent',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        generator=ModelGenerator(lambda ctx,error:json.dumps(dict(rationale='Отмена ошибочного добавления',add=[],remove=['IrreflexiveObjectProperty(:hasMemory)'])),context)
        validation=dict(id=7,status='invalid',code='CONSISTENCY',F=0.)
        generator.set_parent_context(validation)
        validation['F']=99. # Caller mutation cannot alter the copied assessment.
        result=generator(dict(add=['IrreflexiveObjectProperty(:hasMemory)'],remove=[]),None)
        self.assertEqual(result,dict(add=[],remove=[]))
        attempt=generator.attempts[0]
        self.assertEqual(attempt['context']['parent_validation'],dict(id=7,status='invalid',code='CONSISTENCY',F=0.))
        self.assertIn('"status":"invalid"',attempt['request'])
        self.assertIn('F=0 независимо от арифметических метрик',attempt['request'])
        self.assertIn('исправь причину или отмени ошибочные ранее добавленные аксиомы',attempt['request'])
        generator.set_parent_context(dict(kind='immutable_core'))
        with patch('lab4.optimizer.runtime.parse_proposal',return_value=Proposal('why',['new'],[])):
            generator(dict(add=[],remove=[]),None)
        self.assertEqual(generator.attempts[0]['context']['parent_validation'],dict(kind='immutable_core'))

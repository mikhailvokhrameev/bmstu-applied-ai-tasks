import json
import unittest
from lab4.optimizer.proposals import parse_proposal, ProposalError, propose_with_retries, SemanticDeduplicator, assess_pairs, render_prompt

class ProposalTests(unittest.TestCase):
    def payload(self, axioms=None):
        return json.dumps(dict(rationale='Уточнение',add=axioms or ['SubClassOf(:GPU :Component)'],remove=[]))
    def test_valid(self):
        self.assertEqual(len(parse_proposal(self.payload()).add),1)
    def test_invalid(self):
        for text in ['{', self.payload(['SubClassOf(:GPU)']), self.payload(['Declaration(Class(:New))']), self.payload(['SubClassOf(:A :B)']*6), '{"rationale":"x","add":[],"remove":[],"extra":1}']:
            with self.subTest(text=text), self.assertRaises(ProposalError): parse_proposal(text)
    def test_three_attempts_and_feedback(self):
        errors=[]
        def model(context,error):
            errors.append(error)
            return '{'
        with self.assertRaises(ProposalError): propose_with_retries(model,{})
        self.assertEqual(len(errors),3)
        self.assertIsNone(errors[0]); self.assertIn('JSON',errors[1])
    def test_prompt(self):
        p=render_prompt(dict(ontology_manchester='Class: GPU', metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6), 'ошибка')
        for token in ['Class: GPU','M6','ошибка','встроенная','rationale']: self.assertIn(token,p)
    def test_parent_assessment_follows_full_ontology_examples_and_all_context_facts(self):
        ontology='Class: EntireParent\n    Annotations: "Полный Manchester без сокращений"@ru\n'
        validation=dict(id=7,status='invalid',code='CONSISTENCY',F=0.)
        context=dict(ontology_manchester=ontology,metrics={f'M{i}':i for i in range(1,7)},
                     relative=[.9,1.,1.1,1.2,1.3,1.4],
                     added_axioms=['SubClassOf(:New :VideoCardModel)'],removed_axioms=[],
                     violations=[dict(code='P13',key='https://example.org/ontologies/videocard#usesGPU')],
                     inverse_operands=[dict(direct_property=':usesGPU',
                         DIRECT=dict(domain=[':VideoCardModel'],range=[':GPUModel']),
                         MIRRORED_INVERSE=dict(domain=[':GPUModel'],range=[':VideoCardModel']))],
                     parent_validation=validation)
        prompt=render_prompt(context,'Точная причина предыдущего отклонения')
        parent_json=json.dumps(validation,ensure_ascii=False,separators=(',',':'))
        parent_offset=prompt.index(parent_json)
        self.assertLess(prompt.index(ontology)+len(ontology),parent_offset)
        self.assertLess(prompt.index('Пример отмены,'),parent_offset)
        self.assertLess(parent_offset,prompt.index('Сейчас верни один новый ответ'))
        for key in ('added_axioms','removed_axioms','metrics','relative'):
            self.assertIn(json.dumps(context[key],ensure_ascii=False),prompt)
        for key in ('violations','inverse_operands'):
            self.assertIn(json.dumps(context[key],ensure_ascii=False,separators=(',',':')),prompt)
        self.assertIn('Точная причина предыдущего отклонения',prompt)
        self.assertIn('F=0 независимо от арифметических метрик.',prompt)
        self.assertNotIn('арифметических метрик ниже',prompt)
        self.assertEqual(prompt.count(parent_json),1)
        # Equal candidate facts with a different audit ID share the entire
        # ontology/few-shot prefix; the ID is retained in the request suffix.
        changed=render_prompt({**context,'parent_validation':{**validation,'id':8}},
                              'Точная причина предыдущего отклонения')
        self.assertTrue(changed.startswith(prompt[:parent_offset]))
        self.assertNotEqual(changed,prompt)
    def test_boundary_and_category(self):
        vectors={'Новый. текст':[.9,(1-.9**2)**.5], 'Старый. текст':[1,0]}
        d=SemanticDeduplicator(lambda texts:[vectors[t] for t in texts],[dict(label='Старый',comment='текст',category='class')])
        self.assertTrue(d.is_duplicate('Новый','текст','class'))
        self.assertFalse(d.is_duplicate('Новый','текст','object_property'))
    def test_pair_split(self):
        pairs=[dict(left='a',right='a',synonym='1')]*10+[dict(left='a',right='b',synonym='0')]*10
        r=assess_pairs(pairs,lambda texts:[[1,0] if t=='a' else [0,1] for t in texts])
        self.assertEqual((r['errors'],r['count']),(0,20))
        with self.assertRaises(ValueError): assess_pairs(pairs[:19],lambda _:[])

class TransportTests(unittest.TestCase):
    def test_options_and_incomplete_generation(self):
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('pinned','embed')
        observed=[]
        def post(path,payload):
            observed.append(payload)
            return dict(response='{}',model='pinned',done=False)
        client._post=post
        with self.assertRaises(RuntimeError):
            client.propose(dict(ontology_manchester='Class: GPU',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6))
        self.assertEqual(observed[0]['options'],dict(temperature=.7,top_p=.95,num_predict=2000,num_ctx=32768,seed=100))

    def test_separate_embedding_backend_receives_only_embedding_requests(self):
        from io import BytesIO
        from unittest.mock import patch
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('generation:model','sentence-transformers/LaBSE',
                            'http://generation.invalid:11435/',17,
                            embedding_endpoint='http://embedding.invalid:11436/')
        requests=[]
        def transport(request,timeout):
            payload=json.loads(request.data);requests.append((request.full_url,payload))
            self.assertEqual(timeout,180)
            raw=dict(done=True,response='{}',model='generation:model') if request.full_url.endswith('/api/generate') else dict(embeddings=[[1.,0.],[0.,1.]])
            return BytesIO(json.dumps(raw).encode())
        context=dict(ontology_manchester='Class: Original',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6)
        with patch('lab4.optimizer.proposals.urlopen',side_effect=transport):
            self.assertEqual(client.propose(context).text,'{}')
            self.assertEqual(client.embed(['один','два']),[[1.,0.],[0.,1.]])
        self.assertEqual([url for url,_ in requests],['http://generation.invalid:11435/api/generate','http://embedding.invalid:11436/api/embed'])
        self.assertEqual(requests[0][1]['options'],dict(temperature=.7,top_p=.95,num_predict=2000,num_ctx=32768,seed=17))
        self.assertEqual(requests[1][1],dict(model='sentence-transformers/LaBSE',input=['один','два'],truncate=False))

    def test_default_embedding_endpoint_preserves_existing_post_seam(self):
        from unittest.mock import patch
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('generation','embedding','http://one.invalid/',seed=42)
        self.assertEqual(client.embedding_endpoint,client.endpoint)
        with patch.object(client,'_post',return_value=dict(embeddings=[[1.,0.]])) as post, patch('lab4.optimizer.proposals.urlopen') as transport:
            self.assertEqual(client.embed(['текст']),[[1.,0.]])
        post.assert_called_once_with('/api/embed',dict(model='embedding',input=['текст'],truncate=False))
        transport.assert_not_called()

    def test_embedding_instruction_is_applied_uniformly_to_every_text(self):
        from unittest.mock import patch
        from lab4.optimizer.proposals import OllamaModels
        instruction='Represent the meaning of an ontology concept.'
        client=OllamaModels('generation','embedding',embedding_instruction=instruction)
        with patch.object(client,'_post',return_value=dict(embeddings=[[1.,0.],[0.,1.]])) as post:
            self.assertEqual(client.embed(['первое понятие','второе понятие']),[[1.,0.],[0.,1.]])
        post.assert_called_once_with('/api/embed',dict(model='embedding',truncate=False,input=[
            'Instruct: '+instruction+'\nQuery: первое понятие',
            'Instruct: '+instruction+'\nQuery: второе понятие']))

class ReviewRegressionTests(unittest.TestCase):
    def test_semantically_equal_axioms_rejected(self):
        for add,remove in [(['SubClassOf(:A :B)','SubClassOf( :A :B )'],[]),(['SubClassOf(:A :B)'],['SubClassOf( :A :B )'])]:
            with self.subTest(add=add,remove=remove), self.assertRaises(ProposalError):
                parse_proposal(json.dumps(dict(rationale='x',add=add,remove=remove)))
    def test_delivered_length_limit_retains_response_for_syntax_validation(self):
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('pinned','embed')
        raw=dict(response='{"rationale":',model='pinned',done=True,done_reason='length',eval_count=2000)
        client._post=lambda *args:raw
        response=client.propose(dict(ontology_manchester='Class: GPU',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6))
        self.assertEqual(response.raw,raw)
        self.assertEqual(response.text,raw['response'])
        with self.assertRaises(ProposalError):parse_proposal(response.text)
    def test_process_failure_does_not_retry_model(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        calls=[]
        def model(context,error):
            calls.append(error)
            return json.dumps(dict(rationale='x',add=['SubClassOf(:A :B)'],remove=[]))
        with patch('subprocess.run',return_value=SimpleNamespace(returncode=-9,stdout='',stderr='killed')):
            with self.assertRaises(RuntimeError): propose_with_retries(model,{})
        self.assertEqual(len(calls),1)

    def test_owl_feedback_is_compact_and_identifies_axiom_with_full_diagnostic(self):
        malformed='SubClassOf(:Fresh)'
        text=json.dumps(dict(rationale='x',add=['Declaration(Class(:Fresh))',malformed],remove=[]))
        with self.assertRaises(ProposalError) as caught:parse_proposal(text)
        error=caught.exception
        self.assertLess(len(str(error)),900)
        self.assertIn('add[1]',str(error))
        self.assertIn(malformed,str(error))
        self.assertIn('Functional Syntax',str(error))
        self.assertNotIn('Stack trace',str(error))
        self.assertEqual(error.diagnostic['axiom'],malformed)
        self.assertEqual(error.diagnostic['index'],1)
        self.assertGreater(len(error.diagnostic['detail']),1000)

    def test_each_array_element_must_be_a_single_axiom(self):
        with self.assertRaises(ProposalError):
            parse_proposal(json.dumps(dict(
                rationale='x',add=['SubClassOf(:A :B) SubClassOf(:B :C)'],remove=[])))

    def test_objective_full_context_and_four_few_shots(self):
        from pathlib import Path
        from lab4.optimizer import proposals
        ontology='Class: Original\n'+'    Annotations: preserved\n'*2000
        rendered=render_prompt(dict(ontology_manchester=ontology,metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6))
        self.assertIn(ontology,rendered)
        self.assertIn('F = 0.15*r1 + 0.15*r2 + 0.10*r3 + 0.15*r4 + 0.15*r5 + 0.30*r6',rendered)
        for token in ('r6=min((Q0+1)/(Q+1),2)','Q0=10','P13','серверные ускорители','первичного источника'):
            self.assertIn(token,rendered)
        template=(Path(proposals.__file__).parent/'prompts/proposal.txt').read_text()
        examples=[line for line in template.splitlines() if line.startswith('{')]
        self.assertEqual(len(examples),4)
        for example in examples:
            with self.subTest(example=example):parse_proposal(example)


class EmbeddingCacheTests(unittest.TestCase):
    def entity(self,label,category='Class'):
        return dict(label=label,comment='точный текст',category=category)

    def test_reuses_exact_texts_between_candidates_and_preserves_categories(self):
        calls=[]
        vectors={'Новый. точный текст':[0,1], 'Другой. точный текст':[0,1],
                 'Исходный. точный текст':[1,0], 'новый. точный текст':[0,1]}
        def embed(texts):
            calls.append(list(texts));return [vectors[text] for text in texts]
        checker=SemanticDeduplicator(embed,[self.entity('Исходный'),self.entity('Исходный','ObjectProperty')])
        self.assertFalse(checker([self.entity('Новый')]))
        self.assertFalse(checker([self.entity('Новый')]))
        self.assertEqual(len(calls),1)
        self.assertFalse(checker([self.entity('Другой')]))
        self.assertEqual(calls[-1],['Другой. точный текст'])
        self.assertFalse(checker([self.entity('новый')]))
        self.assertEqual(calls[-1],['новый. точный текст'])
        self.assertFalse(checker([self.entity('Новый','ObjectProperty')]))
        self.assertEqual(calls[-1],['Новый. точный текст','Исходный. точный текст'])

    def test_bound_model_and_endpoint_are_part_of_cache_identity(self):
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('unused-generation','embedding-a')
        calls=[]
        def post(path,payload):
            calls.append((client.endpoint,payload['model'],list(payload['input'])))
            return dict(embeddings=[[0,1] if text.startswith('Новый.') else [1,0] for text in payload['input']])
        client._post=post
        checker=SemanticDeduplicator(client.embed,[self.entity('Исходный')])
        for model,endpoint in [('embedding-a','http://one'),('embedding-a','http://one'),
                               ('embedding-b','http://one'),('embedding-b','http://two')]:
            client.embedding_model=model;client.endpoint=endpoint;client.embedding_endpoint=endpoint
            self.assertFalse(checker([self.entity('Новый')]))
        self.assertEqual(len(calls),3)
        self.assertEqual([(endpoint,model) for endpoint,model,_ in calls],
                         [('http://one','embedding-a'),('http://one','embedding-b'),('http://two','embedding-b')])

    def test_transport_and_invalid_embeddings_are_never_cached(self):
        bad_results=[RuntimeError('transport'),[[0,1]],[[0,1],[float('nan'),0]],
                     [[0,1],[0,0]],[[0,1],[1,0,0]]]
        for bad in bad_results:
            with self.subTest(bad=bad):
                calls=[]
                def embed(texts):
                    calls.append(list(texts))
                    if len(calls)==1:
                        if isinstance(bad,Exception):raise bad
                        return bad
                    return [[0,1],[1,0]]
                checker=SemanticDeduplicator(embed,[self.entity('Исходный')])
                with self.assertRaises((RuntimeError,ValueError)):checker([self.entity('Новый')])
                self.assertFalse(checker([self.entity('Новый')]))
                self.assertEqual(calls[0],calls[1])

    def test_new_entities_compare_each_other_without_leaking_to_next_candidate(self):
        calls=[]
        def embed(texts):
            calls.append(list(texts));return [[1,0] for text in texts]
        checker=SemanticDeduplicator(embed,[])
        self.assertTrue(checker([self.entity('Первый'),self.entity('Второй')]))
        self.assertEqual(calls,[['Второй. точный текст','Первый. точный текст']])
        self.assertFalse(checker([self.entity('Третий')]))
        self.assertEqual(len(calls),1)

    def test_cache_tracks_embedding_backend_independently_of_generation_endpoint(self):
        from io import BytesIO
        from unittest.mock import patch
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('generation','sentence-transformers/LaBSE',
                            'http://generation.invalid',embedding_endpoint='http://embedding-one.invalid')
        observed=[]
        def transport(request,timeout):
            payload=json.loads(request.data)
            observed.append((request.full_url,payload['model']))
            vectors=[[0.,1.] if text.startswith('Новый.') else [1.,0.] for text in payload['input']]
            return BytesIO(json.dumps(dict(embeddings=vectors)).encode())
        checker=SemanticDeduplicator(client.embed,[self.entity('Исходный')])
        with patch('lab4.optimizer.proposals.urlopen',side_effect=transport), patch.object(client,'_post',side_effect=AssertionError('embedding reached generation backend')):
            self.assertFalse(checker([self.entity('Новый')]))
            client.endpoint='http://different-generation.invalid'
            self.assertFalse(checker([self.entity('Новый')]))
            self.assertEqual(len(observed),1)
            client.embedding_endpoint='http://embedding-two.invalid'
            self.assertFalse(checker([self.entity('Новый')]))
            client.embedding_model='sentence-transformers/LaBSE-revision-two'
            self.assertFalse(checker([self.entity('Новый')]))
        self.assertEqual(observed,[('http://embedding-one.invalid/api/embed','sentence-transformers/LaBSE'),
                                   ('http://embedding-two.invalid/api/embed','sentence-transformers/LaBSE'),
                                   ('http://embedding-two.invalid/api/embed','sentence-transformers/LaBSE-revision-two')])

    def test_embedding_instruction_is_an_exact_cache_input(self):
        from unittest.mock import patch
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('generation','embedding')
        checker=SemanticDeduplicator(client.embed,[self.entity('Исходный')])
        with patch.object(client,'_post',return_value=dict(embeddings=[[0.,1.],[1.,0.]])) as post:
            for instruction in ('','Represent concept meaning.','Represent concept meaning.',
                                'Represent concept meaning precisely.',''):
                client.embedding_instruction=instruction
                self.assertFalse(checker([self.entity('Новый')]))
        self.assertEqual(post.call_count,3)
        inputs=[call.args[1]['input'] for call in post.call_args_list]
        self.assertEqual(inputs[0],['Новый. точный текст','Исходный. точный текст'])
        self.assertEqual(inputs[1],['Instruct: Represent concept meaning.\nQuery: Новый. точный текст',
                                    'Instruct: Represent concept meaning.\nQuery: Исходный. точный текст'])
        self.assertTrue(all(text.startswith('Instruct: Represent concept meaning precisely.\nQuery: ') for text in inputs[2]))

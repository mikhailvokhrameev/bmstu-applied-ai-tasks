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

class ReviewRegressionTests(unittest.TestCase):
    def test_semantically_equal_axioms_rejected(self):
        for add,remove in [(['SubClassOf(:A :B)','SubClassOf( :A :B )'],[]),(['SubClassOf(:A :B)'],['SubClassOf( :A :B )'])]:
            with self.subTest(add=add,remove=remove), self.assertRaises(ProposalError):
                parse_proposal(json.dumps(dict(rationale='x',add=add,remove=remove)))
    def test_length_limit_is_not_complete(self):
        from lab4.optimizer.proposals import OllamaModels
        client=OllamaModels('pinned','embed')
        client._post=lambda *args:dict(response='{}',model='pinned',done=True,done_reason='length')
        with self.assertRaises(RuntimeError):
            client.propose(dict(ontology_manchester='Class: GPU',metrics={f'M{i}':1 for i in range(1,7)},relative=[1]*6))
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

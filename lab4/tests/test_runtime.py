import unittest
from unittest.mock import patch
from lab4.optimizer.runtime import ModelGenerator
from lab4.optimizer.proposals import Proposal, ModelResponse
class AdapterTests(unittest.TestCase):
    def test_retries_and_cumulative_parent_context(self):
        calls=[]
        def propose(context,error):
            calls.append((context,error));return ModelResponse('bad' if len(calls)==1 else 'ok','fake',{'response':'raw'})
        with patch('lab4.optimizer.runtime.parse_proposal',side_effect=[ValueError('bad JSON'),Proposal('why',['b'],[]) ]):
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
        for completion in ({'done':False},{'done':True,'done_reason':'length'}):
            raw=dict(response='partial text',model='pinned',extra={'tokens':[1,2]},**completion)
            client=OllamaModels('pinned','embed');g=ModelGenerator(client.propose,context)
            with patch.object(client,'_post',return_value=raw):
                with self.assertRaisesRegex(RuntimeError,'Incomplete'):
                    g(dict(add=[],remove=[]),None)
            self.assertEqual(g.attempts[0]['response']['raw'],raw)
            self.assertEqual(g.attempts[0]['response']['text'],'partial text')

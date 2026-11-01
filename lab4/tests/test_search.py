import random
import unittest
from lab4.optimizer import search
from lab4.optimizer.validator import ValidationResult

class SearchTests(unittest.TestCase):
    def config(self):
        self.calls=[]
        def validate(delta):
            self.calls.append(delta)
            n=len(self.calls)
            return ValidationResult('invalid','TEST',0.) if n%7==0 else ValidationResult('valid',F=1+n/1000)
        def generate(parent,rng):
            return {'add':parent['add']+[f'axiom-{rng.randrange(100000)}'], 'remove':[]}
        return {'runtime':{'validate':validate,'model_generator':generate,
                           'control_generator':search.ControlGenerator({'classes':[':A',':B'],'object_properties':[':p',':q'],'data_properties':[':x',':y']})}}
    def test_model_budget_elitism_and_operators(self):
        result=search.run(self.config(),'model',101)
        self.assertEqual(len(self.calls),170)
        self.assertEqual([len(g) for g in result.generations],[10]*21)
        self.assertEqual(result.best_f,tuple(sorted(result.best_f)))
        self.assertEqual({c.operator for c in result.evaluations},{'initial','mutation','crossover'})
        self.assertEqual(sum(c.status=='invalid' for c in result.evaluations),24)
        self.assertTrue(all(c.delta in self.calls for c in result.evaluations))
    def test_control_never_calls_model_and_reproduces(self):
        config=self.config()
        def forbidden(*args): raise AssertionError('language model called')
        config['runtime']['model_generator']=forbidden
        a=search.run(config,'control',201)
        self.assertEqual(len(self.calls),170)
        b=search.run(self.config(),'control',201)
        self.assertEqual(a,b)
        self.assertEqual(a.best_f,tuple(sorted(a.best_f)))
    def test_configuration_and_errors(self):
        for patch in ({'population_size':9},{'mutation_probability':2},{'generations':True}):
            with self.assertRaises(ValueError):search.run({**self.config(),**patch},'control',1)
        with self.assertRaises(ValueError):search.run(self.config(),'wrong',1)
        c=self.config();c['runtime']['validate']=lambda d:ValidationResult('error','TIMEOUT')
        with self.assertRaises(search.SearchError):search.run(c,'control',1)
    def test_ties_choose_oldest_and_rng_state(self):
        c=self.config();c['runtime']['validate']=lambda d:ValidationResult('valid',F=1.)
        r=search.run(c,'model',101)
        self.assertEqual(r.best.id,0)
        rng=random.Random();rng.setstate(r.rng_state)
        self.assertEqual(rng.getstate(),r.rng_state)
    def test_conflicting_crossover_is_validated_and_rejected(self):
        c=self.config()
        n=[0]
        def gen(parent,rng):
            n[0]+=1
            return {'add':['same'] if n[0]%2 else [],'remove':[] if n[0]%2 else ['same']}
        c['runtime']['model_generator']=gen
        r=search.run(c,'model',101)
        conflicts=[x for x in r.evaluations if x.code=='CONFLICT']
        self.assertTrue(conflicts)
        self.assertTrue(all(x.delta in self.calls and x.F==0 for x in conflicts))

    def test_control_templates_and_conflict_kept(self):
        g=search.ControlGenerator({'classes':[':A',':B'],'object_properties':[':p',':q'],'data_properties':[':x',':y']})
        out=[g({'add':[],'remove':[]},random.Random(i)) for i in range(30)]
        self.assertTrue(any('SubClassOf' in ' '.join(x['add']) for x in out))
        self.assertTrue(all(x['add'] for x in out))
        self.assertEqual(search.merge({'add':['a'],'remove':[]},{'add':[],'remove':['a']}),{'add':['a'],'remove':['a']})

if __name__=='__main__':unittest.main()

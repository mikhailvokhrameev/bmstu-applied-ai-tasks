import random
import unittest
from lab4.optimizer import search
from lab4.optimizer.validator import ValidationResult, validate

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
    def test_debug_budget_and_resume_keep_frozen_configuration(self):
        config={**search.DEFAULTS,**self.config()}
        checkpoints=[]
        config['runtime']['on_generation']=lambda g,p,e,s:checkpoints.append(dict(history=tuple(checkpoints[-1]['history'])+(p,) if checkpoints else (p,),evaluations=e,rng_state=s))
        result=search.run(config,'model',100,phase='debug')
        self.assertEqual(len(self.calls),34)
        self.assertEqual(len(result.generations),4)
        self.assertEqual(config['generations'],20)
        self.assertEqual([len(c['evaluations']) for c in checkpoints],[10,18,26,34])
        # Resume from a committed debug generation using the same RNG state.
        resumed=self.config()
        n=[18]
        def check(delta):
            n[0]+=1
            return ValidationResult('invalid','TEST',0.) if n[0]%7==0 else ValidationResult('valid',F=1+n[0]/1000)
        resumed['runtime']['validate']=check
        again=search.run(resumed,'model',100,resume=checkpoints[1],phase='debug')
        self.assertEqual(again,result)
        with self.assertRaises(ValueError):search.run(config,'model',100,phase='unknown')
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

    def test_new_entity_templates_pass_real_validator(self):
        # Use an inhabited defined core class without direct class assertions;
        # this satisfies both the instance rule and the FORBIDDEN check.
        generator=search.ControlGenerator({'classes':[':CardWith8GBMemory']})
        templates={}
        for seed in range(100):
            delta=generator({'add':[],'remove':[]},random.Random(seed))
            text=' '.join(delta['add'])
            for kind,axiom in (('subclass','SubClassOf('),('defined','EquivalentClasses('),('data_property','DataPropertyDomain(')):
                if axiom in text and 'DisjointClasses(' not in text and kind not in templates:templates[kind]=delta
            if len(templates)==3:break
        self.assertEqual(set(templates),{'subclass','defined','data_property'})
        for kind,delta in templates.items():
            with self.subTest(template=kind):
                inspected=[]
                def no_semantic_duplicate(entities):
                    inspected.extend(entities)
                    return False # Isolate the external embedding service only.
                result=validate(delta,duplicate_checker=no_semantic_duplicate)
                self.assertEqual((result.status,result.code),('valid',None),result.detail)
                self.assertEqual(len(inspected),1)
                self.assertGreater(result.F,0)

    def test_control_templates_and_conflict_kept(self):
        g=search.ControlGenerator({'classes':[':A',':B'],'object_properties':[':p',':q'],'data_properties':[':x',':y']})
        out=[g({'add':[],'remove':[]},random.Random(i)) for i in range(30)]
        self.assertTrue(any('SubClassOf' in ' '.join(x['add']) for x in out))
        self.assertTrue(all(x['add'] for x in out))
        self.assertEqual(search.merge({'add':['a'],'remove':[]},{'add':[],'remove':['a']}),{'add':['a'],'remove':['a']})

    def test_optional_control_inventory_and_all_added_templates(self):
        inventory=dict(classes=[':VideoCardModel'],object_properties=[':hasMemory'],
                       object_property_domains={':hasMemory':[':VideoCardModel']},
                       object_property_ranges={':hasMemory':[':MemoryConfiguration']},
                       individuals=[':U01'],teaching_class=':VideoCardModel')
        generator=search.ControlGenerator(inventory)
        self.assertEqual(generator.inventory['object_property_domains'],{':hasMemory':(':VideoCardModel',)})
        self.assertEqual(generator.inventory['teaching_class'],':VideoCardModel')
        parent=dict(add=[],remove=[])
        found={}
        for seed in range(100):
            delta=generator(parent,random.Random(seed));text=' '.join(delta['add'])
            for kind,marker in [('inverse','InverseObjectProperties('),('teaching_value','DataPropertyAssertion('),('disjoint','DisjointClasses(')]:
                if marker in text:found.setdefault(kind,delta)
        self.assertEqual(set(found),{'inverse','teaching_value','disjoint'})
        self.assertEqual(parent,dict(add=[],remove=[]))
        inverse=found['inverse']['add']
        self.assertTrue(any(a.startswith('ObjectPropertyDomain(') and a.endswith(' :MemoryConfiguration)') for a in inverse))
        self.assertTrue(any(a.startswith('ObjectPropertyRange(') and a.endswith(' :VideoCardModel)') for a in inverse))
        teaching=' '.join(found['teaching_value']['add'])
        self.assertIn('Count :VideoCardModel)',teaching)
        self.assertIn(' :U01 "',teaching)
        self.assertIn('rdfs:comment :U01 "Условные учебные данные',teaching)
        self.assertEqual(sum(a.startswith('SubClassOf(') for a in found['disjoint']['add']),2)
        self.assertEqual(sum(a.startswith('Declaration(Class(') for a in found['disjoint']['add']),2)
        # Without explicit domain/range or teaching individuals these two
        # templates are unavailable; existing three inventory keys still work.
        old=search.ControlGenerator(dict(classes=[':A'],object_properties=[':p']))
        partial=search.ControlGenerator(dict(classes=[':A'],object_properties=[':p'],object_property_domains={':p':[':A']}))
        for g in (old,partial):
            outputs=[' '.join(g(parent,random.Random(seed))['add']) for seed in range(100)]
            self.assertFalse(any('InverseObjectProperties(' in text or 'DataPropertyAssertion(' in text for text in outputs))

    def test_new_table_four_templates_pass_real_parser_and_validator(self):
        from lab4.optimizer.prepare import ontology_inventory
        from lab4.optimizer.bridge import CORE
        from lab4.optimizer.proposals import parse_proposal
        import json
        inventory,_=ontology_inventory(CORE)
        generator=search.ControlGenerator(inventory)
        selected={}
        for seed in range(300):
            delta=generator(dict(add=[],remove=[]),random.Random(seed));text=' '.join(delta['add'])
            for kind,marker in [('inverse','InverseObjectProperties('),('teaching_value','DataPropertyAssertion('),('disjoint','DisjointClasses(')]:
                if marker in text:selected.setdefault(kind,delta)
            if len(selected)==3:break
        self.assertEqual(set(selected),{'inverse','teaching_value','disjoint'})
        for kind,delta in selected.items():
            with self.subTest(template=kind):
                parse_proposal(json.dumps(dict(rationale='Проверка учебного шаблона',**delta),ensure_ascii=False))
                result=validate(delta,duplicate_checker=lambda entities:False)
                self.assertEqual((result.status,result.code),('valid',None),result.detail)
                self.assertGreater(result.F,0)

    def test_control_removal_requires_a_previously_added_logical_axiom(self):
        generator=search.ControlGenerator(dict(classes=[':VideoCardModel']))
        annotations=['Declaration(Class(:Earlier))',
                     'AnnotationAssertion(rdfs:label :Earlier "Ранее добавленный класс"@ru)',
                     'AnnotationAssertion(rdfs:comment :Earlier "Условное учебное определение"@ru)']
        parent=dict(add=list(annotations),remove=[])
        for seed in range(100):
            result=generator(parent,random.Random(seed))
            self.assertTrue(set(annotations)<=set(result['add']))
            self.assertGreater(len(result['add']),len(annotations))
        self.assertEqual(parent,dict(add=annotations,remove=[]))

        logical=['SubClassOf(:Earlier :VideoCardModel)',
                 '  DisjointClasses(:Earlier :AnotherEarlier)']
        mixed=dict(add=annotations+logical,remove=[])
        removals=[]
        for seed in range(100):
            result=generator(mixed,random.Random(seed))
            if len(result['add'])<len(mixed['add']):
                removed=set(mixed['add'])-set(result['add'])
                self.assertEqual(len(removed),1)
                self.assertTrue(removed<=set(logical))
                self.assertTrue(set(annotations)<=set(result['add']))
                self.assertEqual(result['remove'],[])
                removals.extend(removed)
        self.assertEqual(set(removals),set(logical))
        self.assertEqual(mixed,dict(add=annotations+logical,remove=[]))

    def test_optional_parent_context_uses_saved_validation_without_new_evaluations(self):
        class Generator:
            def __init__(self):self.parents=[]
            def set_parent_context(self,info):self.parents.append(dict(info))
            def __call__(self,parent,rng):
                return dict(add=parent['add']+[str(rng.getrandbits(32))],remove=[])
        generator=Generator();checks=[];candidates=[]
        def check(delta):
            checks.append(delta)
            return ValidationResult('invalid','CONSISTENCY',0.)
        def audited(candidate,validation,elapsed,error):candidates.append(candidate)
        runtime=dict(model_generator=generator,validate=check,on_evaluation=audited)
        result=search.run(dict(runtime=runtime),'model',100,phase='debug')
        self.assertEqual(len(checks),34)
        self.assertEqual(generator.parents[:10],[dict(kind='immutable_core')]*10)
        generated=[candidate for candidate in candidates if candidate.operator!='crossover']
        self.assertEqual(len(generator.parents),len(generated))
        for candidate,info in zip(generated,generator.parents):
            if candidate.parents:
                parent=result.evaluations[candidate.parents[0]]
                self.assertEqual(info,dict(id=parent.id,status='invalid',code='CONSISTENCY',F=0.))
            else:
                self.assertEqual(info,dict(kind='immutable_core'))
                self.assertNotIn('status',info)
        # A hook adds audit context only; the original two-argument callable
        # contract and the random search trajectory remain unchanged.
        plain=lambda parent,rng:dict(add=parent['add']+[str(rng.getrandbits(32))],remove=[])
        expected=search.run(dict(runtime=dict(model_generator=plain,validate=check)),
                            'model',100,phase='debug')
        self.assertEqual(result,expected)

if __name__=='__main__':unittest.main()

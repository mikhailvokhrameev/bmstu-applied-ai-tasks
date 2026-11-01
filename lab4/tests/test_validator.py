import unittest
from unittest.mock import patch
from lab4.optimizer.validator import validate

class ValidatorTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual(validate({'add': [], 'remove': []}, duplicate_checker=lambda _: False).status, 'valid')
    def test_error_is_not_invalid(self):
        with patch('lab4.optimizer.validator._inspect', side_effect=TimeoutError('deadline')):
            r = validate({}, duplicate_checker=lambda _: False)
        self.assertEqual(r.status, 'error')
        self.assertIsNone(r.F)
        self.assertEqual(r.code,'TIMEOUT')
    def test_order(self):
        with patch('lab4.optimizer.validator._inspect', return_value={'code':'OWL2_DL'}):
            self.assertEqual(validate({}, duplicate_checker=lambda _: True).code, 'OWL2_DL')

class FixtureTests(unittest.TestCase):
    def test_ten_invalid_candidates(self):
        import json
        from pathlib import Path
        for path in sorted((Path(__file__).parent/'validator_fixtures').glob('*.json')):
            f = json.loads(path.read_text())
            with self.subTest(path=path.name):
                r = validate(f['candidate'], duplicate_checker=lambda _, flag=f['duplicate']: flag)
                self.assertEqual((r.status,r.code,r.F),('invalid',f['expected_code'],0.0),r.detail)

class TemplateTests(unittest.TestCase):
    @staticmethod
    def annotated(kind,name):
        return [f'Declaration({kind}(:{name}))',f'AnnotationAssertion(rdfs:label :{name} "Тест"@ru)',f'AnnotationAssertion(rdfs:comment :{name} "Определение"@ru)']
    def check(self,add,code):
        r=validate({'add':add,'remove':[]},duplicate_checker=lambda _:False)
        self.assertEqual(r.code,code,r.detail)
    def test_empty_defined_class(self):
        self.check(self.annotated('Class','Fresh')+['EquivalentClasses(:Fresh ObjectIntersectionOf(:VideoCardModel ObjectHasValue(:hasVideoOutput :VGA) ObjectHasValue(:hasVideoOutput :DisplayPort)))'],'CHANGE_KIND')
    def test_inverse_requires_mirrored_domains(self):
        self.check(self.annotated('ObjectProperty','inverseGPU')+['InverseObjectProperties(:inverseGPU :usesGPU)'],'CHANGE_KIND')
    def test_new_data_property_requires_unit(self):
        self.check(self.annotated('DataProperty','extra')+['DataPropertyDomain(:extra :VideoCardModel)','DataPropertyRange(:extra xsd:integer)'],'CHANGE_KIND')
    def test_new_values_require_mark(self):
        self.check(self.annotated('DataProperty','extraW')+['DataPropertyDomain(:extraW :VideoCardModel)','DataPropertyRange(:extraW xsd:integer)','DataPropertyAssertion(:extraW :U01 "1"^^xsd:integer)'],'CHANGE_KIND')
    def test_disallowed_axiom(self):
        self.check(['SymmetricObjectProperty(:hasVideoOutput)'],'CONSISTENCY')
    def test_safe_characteristic(self):
        self.check(['FunctionalObjectProperty(:usesGPU)'],None)
    def test_property_hierarchy(self):
        self.check(['SubObjectPropertyOf(:hasVideoOutput :hasVideoOutput)'],None)
    def test_valid_subclass(self):
        self.check(self.annotated('Class','Fresh')+['SubClassOf(:Fresh :VideoCardModel)'],None)
    def test_defined_class_with_instance(self):
        self.check(self.annotated('Class','Fresh')+['EquivalentClasses(:Fresh :CardWith8GBMemory)'],None)
    def test_valid_inverse(self):
        self.check(self.annotated('ObjectProperty','inverseGPU')+['InverseObjectProperties(:inverseGPU :usesGPU)','ObjectPropertyDomain(:inverseGPU :GPUModel)','ObjectPropertyRange(:inverseGPU :VideoCardModel)'],None)
    def test_disjoint_new_classes(self):
        self.check(self.annotated('Class','FreshA')+self.annotated('Class','FreshB')+['SubClassOf(:FreshA :VideoCardModel)','SubClassOf(:FreshB :VideoCardModel)','DisjointClasses(:FreshA :FreshB)'],None)
    def test_removing_previously_added_noncore_axiom(self):
        r=validate({'add':['FunctionalObjectProperty(:usesGPU)'],'remove':['FunctionalObjectProperty(:usesGPU)']},duplicate_checker=lambda _:False)
        self.assertEqual(r.status,'valid',r.detail)
    def test_external_import_is_rejected_without_fetch(self):
        from lab4.optimizer.bridge import CORE
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'candidate.owl'
            p.write_text(CORE.read_text().replace('</owl:Ontology>','<owl:imports rdf:resource="https://invalid.example/unreachable.owl"/></owl:Ontology>',1))
            r=validate(p,duplicate_checker=lambda _:False)
            self.assertEqual((r.status,r.code),('invalid','FORBIDDEN'),r.detail)
    def test_conditional_teaching_value(self):
        self.check(self.annotated('DataProperty','extraW')+['DataPropertyDomain(:extraW :VideoCardModel)','DataPropertyRange(:extraW xsd:integer)','DataPropertyAssertion(:extraW :U01 "1"^^xsd:integer)','AnnotationAssertion(rdfs:comment :U01 "Условные учебные данные для extraW"@ru)'],None)

class ReviewRegressionTests(unittest.TestCase):
    annotated = staticmethod(TemplateTests.annotated)
    check = TemplateTests.check
    def test_foreign_unsatisfiable_class_precedes_namespace_violation(self):
        self.check(['Declaration(Class(<https://foreign.example/Impossible>))','SubClassOf(<https://foreign.example/Impossible> <http://www.w3.org/2002/07/owl#Nothing>)'],'CONSISTENCY')
    def test_existing_property_domain_and_range_reject_new_class(self):
        for axiom,parent in [
            ('ObjectPropertyDomain(:usesGPU :Fresh)','VideoCardModel'),
            ('ObjectPropertyRange(:hasVideoOutput :Fresh)','VideoOutput'),
            ('DataPropertyDomain(:powerW :Fresh)','VideoCardModel'),
        ]:
            with self.subTest(axiom=axiom):
                self.check(self.annotated('Class','Fresh')+[f'SubClassOf(:Fresh :{parent})',axiom],'CHANGE_KIND')
    def test_existing_data_property_range_is_rejected(self):
        self.check(['DataPropertyRange(:powerW xsd:decimal)'],'CHANGE_KIND')

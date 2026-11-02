"""Deterministic search kernel. Real series require separately verified services.

Runtime callbacks are deliberately excluded from the serializable configuration.
Checkpoint storage/resume is supplied by the journaling layer (task 6).
"""
from dataclasses import dataclass
import json
import math
import time
from pathlib import Path
import random
from .proposals import Proposal, ProposalError
from .validator import validate

DEFAULTS = dict(population_size=10, generations=20, elite_count=2,
                offspring_count=8, tournament_size=3, mutation_probability=.7)
PHASE_GENERATIONS = dict(debug=3, main=20)

class SearchError(RuntimeError):
    pass

@dataclass(frozen=True)
class Candidate:
    id: int
    generation: int
    parents: tuple
    operator: str
    delta: dict
    status: str
    F: float
    code: str = None

@dataclass(frozen=True)
class RunResult:
    mode: str
    seed: int
    generations: tuple
    evaluations: tuple
    best: Candidate
    best_f: tuple
    rng_state: tuple


def load_config(path):
    # JSON is a strict subset of YAML 1.2; no third-party YAML dependency.
    return json.loads(Path(path).read_text(encoding='utf-8'))


def merge(a,b):
    """Set union, preserving contradictory requests for explicit rejection."""
    return {k:sorted(set(a[k]) | set(b[k])) for k in ('add','remove')}


def _delta(value):
    if isinstance(value,Proposal): value={'add':value.add,'remove':value.remove}
    if not isinstance(value,dict) or set(value)!= {'add','remove'}:
        raise ProposalError('Expected cumulative add/remove delta')
    for k in ('add','remove'):
        if not isinstance(value[k],list) or any(not isinstance(x,str) or not x.strip() for x in value[k]):
            raise ProposalError('Expected nonempty axiom strings')
    return {k:sorted(set(value[k])) for k in ('add','remove')}


def run(config,mode,seed,resume=False,phase='main'):
    """Run generation 0 plus 3 debug or 20 main generations; no fitness caching.

    runtime.model_generator/control_generator(parent_delta, rng) returns a
    cumulative delta; runtime.validate(delta) is the complete candidate validator.
    Default validation always uses validator.validate and requires a real
    duplicate_checker. Infrastructure errors abort and never enter selection.
    runtime.on_generation(generation,population,evaluations,rng_state) is the
    persistence seam. resume accepts a validated journaling snapshot.
    """
    if isinstance(config,(str,Path)):config=load_config(config)
    unknown=set(config)-set(DEFAULTS)-{'runtime'}
    if unknown:raise ValueError('Unknown search parameters: '+str(sorted(unknown)))
    p={**DEFAULTS,**{k:v for k,v in config.items() if k!='runtime'}}
    for k,v in DEFAULTS.items():
        if type(p[k]) is not type(v) or p[k]!=v:
            raise ValueError(k+' must equal the frozen specification value '+str(v))
    if phase not in PHASE_GENERATIONS:raise ValueError('Invalid experiment phase')
    p['generations']=PHASE_GENERATIONS[phase]
    if mode not in ('model','control') or type(seed) is not int:raise ValueError('Invalid mode/seed')
    if resume is True:raise ValueError('Resume requires a checkpoint snapshot')
    services=config.get('runtime',{})
    generator=services.get(mode+'_generator')
    if generator is None:raise ValueError(mode+'_generator is required')
    check=services.get('validate')
    if check is None:
        checker=services.get('duplicate_checker')
        if checker is None:raise ValueError('A real duplicate_checker is required')
        check=lambda d:validate(d,duplicate_checker=checker)
    rng=random.Random(seed)
    evaluated=list(resume['evaluations']) if resume else []; history=list(resume['history']) if resume else []
    if resume:rng.setstate(resume['rng_state'])
    def rank(c):return (-c.F,c.id) # exact equal F: oldest evaluation wins
    def tournament(pop):return min(rng.sample(pop,p['tournament_size']),key=rank)
    def evaluate(delta,generation,parents,operator,proposal_error=None,started=None):
        # Full validation also runs for crossed/conflicting candidates.
        started=time.perf_counter() if started is None else started
        result=check(delta)
        if result.status=='error':raise SearchError(f'{result.code}: {result.detail}')
        if result.status not in ('valid','invalid'):raise SearchError('Unknown validation status')
        conflict=bool(set(delta['add']) & set(delta['remove']))
        invalid=proposal_error or conflict or result.status=='invalid'
        score=0. if invalid else result.F
        if not isinstance(score,(float,int)) or not math.isfinite(score):raise SearchError('Invalid fitness')
        code='PROPOSAL' if proposal_error else 'CONFLICT' if conflict else result.code
        c=Candidate(len(evaluated),generation,parents,operator,delta,'invalid' if invalid else 'valid',score,code)
        if services.get('on_evaluation'):
            services['on_evaluation'](c,result,time.perf_counter()-started,proposal_error)
        evaluated.append(c)
        return c
    def mutation(parent,generation,parents,operator):
        started=time.perf_counter()
        set_parent_context=getattr(generator,'set_parent_context',None)
        if set_parent_context is not None:
            if parents:
                previous=evaluated[parents[0]]
                info=dict(id=previous.id,status=previous.status,code=previous.code,F=previous.F)
            else:
                info=dict(kind='immutable_core')
            set_parent_context(info)
        # Copy isolates elites against in-place mutation by generators.
        try:d=_delta(generator({k:list(v) for k,v in parent.items()},rng));error=None
        except ProposalError as e:d={'add':[],'remove':[]};error=str(e)
        return evaluate(d,generation,parents,operator,error,started)
    pop=list(history[-1]) if resume else [mutation({'add':[],'remove':[]},0,(),'initial') for _ in range(p['population_size'])]
    def completed(g):
        # Tournament sampling uses indices, so live and restored populations
        # must have exactly the same order as the persisted checkpoint.
        nonlocal pop
        pop=sorted(pop,key=rank)
        history.append(tuple(pop))
        if services.get('on_generation'):services['on_generation'](g,history[-1],tuple(evaluated),rng.getstate())
    if not resume:completed(0)
    for generation in range(len(history),p['generations']+1):
        next_pop=sorted(pop,key=rank)[:p['elite_count']]
        for _ in range(p['offspring_count']):
            parent=tournament(pop)
            if rng.random()<p['mutation_probability']:
                child=mutation(parent.delta,generation,(parent.id,),'mutation')
            else:
                other=tournament(pop)
                child=evaluate(merge(parent.delta,other.delta),generation,(parent.id,other.id),'crossover')
            next_pop.append(child)
        pop=next_pop
        completed(generation)
    return RunResult(mode,seed,tuple(history),tuple(evaluated),history[-1][0],tuple(g[0].F for g in history),rng.getstate())


class ControlGenerator:
    """Random Table-4 templates over an explicit ontology entity inventory.

    No model/embedding endpoint is referenced here. Semantic checking belongs to
    the shared validator. Inventory IRIs use Functional Syntax (:name or <IRI>).
    Optional object_property_domains/ranges map each property to a list of named
    class IRIs. Optional individuals contains existing teaching individuals;
    teaching_class identifies their domain (default :VideoCardModel).
    Available template kinds are sampled uniformly, then compatible entities.
    """
    LOGICAL_AXIOM_KINDS=frozenset((
        'SubClassOf','EquivalentClasses','InverseObjectProperties',
        'FunctionalObjectProperty','InverseFunctionalObjectProperty',
        'AsymmetricObjectProperty','IrreflexiveObjectProperty',
        'SubObjectPropertyOf','SubDataPropertyOf','DataPropertyDomain',
        'DataPropertyRange','DataPropertyAssertion','DisjointClasses',
        'ObjectPropertyDomain','ObjectPropertyRange'))

    def __init__(self,inventory):
        self.inventory={k:tuple(sorted(set(inventory.get(k,())))) for k in
                        ('classes','object_properties','data_properties','individuals')}
        for kind in ('object_property_domains','object_property_ranges'):
            self.inventory[kind]={p:tuple(sorted(set(classes))) for p,classes in inventory.get(kind,{}).items()}
        self.inventory['teaching_class']=inventory.get('teaching_class',':VideoCardModel')
        if not self.inventory.get('classes'):raise ValueError('classes inventory required')
    def __call__(self,parent,rng):
        i=self.inventory;c=i['classes'];op=i.get('object_properties',());dp=i.get('data_properties',())
        domains=i['object_property_domains'];ranges=i['object_property_ranges']
        # One inverse axiom plus all explicit mirrored domain/range axioms must
        # fit the same five-logical-axiom limit as a model proposal.
        inverse_properties=[p for p in op if domains.get(p) and ranges.get(p) and len(domains[p])+len(ranges[p])<=4]
        kinds=['subclass','defined','data_property','disjoint']
        if op:kinds+=['characteristic']
        if len(op)>1:kinds+=['object_hierarchy']
        if len(dp)>1:kinds+=['data_hierarchy']
        if inverse_properties:kinds+=['inverse']
        if i['individuals']:kinds+=['teaching_value']
        # Control-generated Functional Syntax has one axiom per string. Only
        # logical template axioms can satisfy the one-to-five change budget;
        # cancelling a declaration or annotation alone would count as zero.
        removable=[axiom for axiom in parent['add']
                   if axiom.lstrip().partition('(')[0].strip() in self.LOGICAL_AXIOM_KINDS]
        if removable:kinds+=['remove']
        kind=rng.choice(kinds)
        add=list(parent['add']);remove=list(parent['remove'])
        if kind=='remove':
            # Cancel only a prior addition; no core removal request is emitted.
            add.remove(rng.choice(removable))
            return {'add':add,'remove':remove}
        name=':Search'+str(rng.getrandbits(64))
        cls=rng.choice(c)
        def entity(iri,entity_type,label,comment):
            add.extend([f'Declaration({entity_type}({iri}))',
                        f'AnnotationAssertion(rdfs:label {iri} "{label}"@ru)',
                        f'AnnotationAssertion(rdfs:comment {iri} "{comment}"@ru)'])
        if kind in ('subclass','defined','data_property','teaching_value'):
            if kind in ('data_property','teaching_value'):name+='Count'
            entity_type='DataProperty' if kind in ('data_property','teaching_value') else 'Class'
            label='Учебный показатель' if entity_type=='DataProperty' else 'Учебный класс'
            domain=i['teaching_class'] if kind=='teaching_value' else cls
            entity(name,entity_type,label,f'Условное учебное определение для класса {domain.replace(chr(34), chr(39))}')
        if kind=='subclass':add += [f'SubClassOf({name} {cls})']
        elif kind=='defined':add += [f'EquivalentClasses({name} {cls})']
        elif kind=='data_property':add += [f'DataPropertyDomain({name} {cls})',f'DataPropertyRange({name} xsd:integer)']
        elif kind=='teaching_value':
            individual=rng.choice(i['individuals']);value=rng.randrange(1,101)
            add += [f'DataPropertyDomain({name} {i["teaching_class"]})',f'DataPropertyRange({name} xsd:integer)',
                    f'DataPropertyAssertion({name} {individual} "{value}"^^xsd:integer)',
                    f'AnnotationAssertion(rdfs:comment {individual} "Условные учебные данные: значение нового показателя Count, не характеристика коммерческого изделия"@ru)']
        elif kind=='inverse':
            direct=rng.choice(inverse_properties)
            entity(name,'ObjectProperty','Обратная учебная связь',f'Условное учебное обратное свойство к {direct.replace(chr(34), chr(39))}')
            add += [f'InverseObjectProperties({name} {direct})']
            add += [f'ObjectPropertyDomain({name} {value})' for value in ranges[direct]]
            add += [f'ObjectPropertyRange({name} {value})' for value in domains[direct]]
        elif kind=='disjoint':
            other=name+'Alternative'
            entity(name,'Class','Учебный вариант А','Условный первый вариант классификации, исключающий второй учебный вариант')
            entity(other,'Class','Учебный вариант Б','Условный второй вариант классификации, исключающий первый учебный вариант')
            add += [f'SubClassOf({name} {cls})',f'SubClassOf({other} {cls})',f'DisjointClasses({name} {other})']
        elif kind=='characteristic':add += [f'{rng.choice(("Functional","InverseFunctional","Asymmetric","Irreflexive"))}ObjectProperty({rng.choice(op)})']
        elif kind=='object_hierarchy':
            a,b=rng.sample(op,2);add += [f'SubObjectPropertyOf({a} {b})']
        elif kind=='data_hierarchy':
            a,b=rng.sample(dp,2);add += [f'SubDataPropertyOf({a} {b})']
        return {'add':sorted(set(add)),'remove':remove}

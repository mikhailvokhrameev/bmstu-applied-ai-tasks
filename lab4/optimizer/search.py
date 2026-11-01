"""Deterministic search kernel. Real series require separately verified services.

Runtime callbacks are deliberately excluded from the serializable configuration.
Checkpoint storage/resume is supplied by the journaling layer (task 6).
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
from .proposals import Proposal, ProposalError
from .validator import validate

DEFAULTS = dict(population_size=10, generations=20, elite_count=2,
                offspring_count=8, tournament_size=3, mutation_probability=.7)

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


def run(config,mode,seed,resume=False):
    """Run generation 0 plus 20 generations; no early stop or fitness caching.

    runtime.model_generator/control_generator(parent_delta, rng) returns a
    cumulative delta; runtime.validate(delta) is the complete candidate validator.
    Default validation always uses validator.validate and requires a real
    duplicate_checker. Infrastructure errors abort and never enter selection.
    runtime.on_generation(generation,population,evaluations,rng_state) is the
    persistence seam. resume=True is reserved for the checkpoint integration.
    """
    if isinstance(config,(str,Path)):config=load_config(config)
    unknown=set(config)-set(DEFAULTS)-{'runtime'}
    if unknown:raise ValueError('Unknown search parameters: '+str(sorted(unknown)))
    p={**DEFAULTS,**{k:v for k,v in config.items() if k!='runtime'}}
    for k,v in DEFAULTS.items():
        if type(p[k]) is not type(v) or p[k]!=v:
            raise ValueError(k+' must equal the frozen specification value '+str(v))
    if mode not in ('model','control') or type(seed) is not int:raise ValueError('Invalid mode/seed')
    if resume:raise NotImplementedError('Resume requires the checkpoint integration layer')
    services=config.get('runtime',{})
    generator=services.get(mode+'_generator')
    if generator is None:raise ValueError(mode+'_generator is required')
    check=services.get('validate')
    if check is None:
        checker=services.get('duplicate_checker')
        if checker is None:raise ValueError('A real duplicate_checker is required')
        check=lambda d:validate(d,duplicate_checker=checker)
    rng=random.Random(seed)
    evaluated=[]; history=[]
    def rank(c):return (-c.F,c.id) # exact equal F: oldest evaluation wins
    def tournament(pop):return min(rng.sample(pop,p['tournament_size']),key=rank)
    def evaluate(delta,generation,parents,operator,proposal_error=None):
        # Full validation also runs for crossed/conflicting candidates.
        result=check(delta)
        if result.status=='error':raise SearchError(f'{result.code}: {result.detail}')
        if result.status not in ('valid','invalid'):raise SearchError('Unknown validation status')
        conflict=bool(set(delta['add']) & set(delta['remove']))
        invalid=proposal_error or conflict or result.status=='invalid'
        score=0. if invalid else result.F
        if not isinstance(score,(float,int)) or not math.isfinite(score):raise SearchError('Invalid fitness')
        code='PROPOSAL' if proposal_error else 'CONFLICT' if conflict else result.code
        c=Candidate(len(evaluated),generation,parents,operator,delta,'invalid' if invalid else 'valid',score,code)
        evaluated.append(c)
        return c
    def mutation(parent,generation,parents,operator):
        # Copy isolates elites against in-place mutation by generators.
        try:d=_delta(generator({k:list(v) for k,v in parent.items()},rng));error=None
        except ProposalError as e:d={'add':[],'remove':[]};error=str(e)
        return evaluate(d,generation,parents,operator,error)
    pop=[mutation({'add':[],'remove':[]},0,(),'initial') for _ in range(p['population_size'])]
    def completed(g):
        history.append(tuple(sorted(pop,key=rank)))
        if services.get('on_generation'):services['on_generation'](g,history[-1],tuple(evaluated),rng.getstate())
    completed(0)
    for generation in range(1,p['generations']+1):
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
    Available template kinds are sampled uniformly, then compatible entities.
    """
    def __init__(self,inventory):
        self.inventory={k:tuple(sorted(set(v))) for k,v in inventory.items()}
        if not self.inventory.get('classes'):raise ValueError('classes inventory required')
    def __call__(self,parent,rng):
        i=self.inventory;c=i['classes'];op=i.get('object_properties',());dp=i.get('data_properties',())
        kinds=['subclass','defined','data_property']
        if op:kinds+=['characteristic']
        if len(op)>1:kinds+=['object_hierarchy']
        if len(dp)>1:kinds+=['data_hierarchy']
        if parent['add']:kinds+=['remove']
        kind=rng.choice(kinds)
        add=list(parent['add']);remove=list(parent['remove'])
        if kind=='remove':
            # Cancel only a prior addition; no core removal request is emitted.
            add.remove(rng.choice(add))
            return {'add':add,'remove':remove}
        name=':Search'+str(rng.getrandbits(64))
        cls=rng.choice(c)
        if kind in ('subclass','defined','data_property'):
            if kind=='data_property':name+='Count'
            label='Учебный показатель' if kind=='data_property' else 'Учебный класс'
            add += [f'AnnotationAssertion(rdfs:label {name} "{label}"@ru)',f'AnnotationAssertion(rdfs:comment {name} "Условное учебное определение для класса {cls.replace(chr(34), chr(39))}"@ru)']
        if kind=='subclass':add += [f'SubClassOf({name} {cls})']
        elif kind=='defined':add += [f'EquivalentClasses({name} {cls})']
        elif kind=='data_property':add += [f'DataPropertyDomain({name} {cls})',f'DataPropertyRange({name} xsd:integer)']
        elif kind=='characteristic':add += [f'{rng.choice(("Functional","InverseFunctional","Asymmetric","Irreflexive"))}ObjectProperty({rng.choice(op)})']
        elif kind=='object_hierarchy':
            a,b=rng.sample(op,2);add += [f'SubObjectPropertyOf({a} {b})']
        elif kind=='data_hierarchy':
            a,b=rng.sample(dp,2);add += [f'SubDataPropertyOf({a} {b})']
        return {'add':sorted(set(add)),'remove':remove}

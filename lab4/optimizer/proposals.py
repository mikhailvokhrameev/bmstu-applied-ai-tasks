"""Strict proposals, bounded retries and category-scoped semantic comparison.

No model availability, analyst approval or acceptance performance is inferred here.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from string import Template
from urllib.request import Request, urlopen
from .bridge import LIB, _run

class ProposalError(ValueError):
    pass

@dataclass(frozen=True)
class Proposal:
    rationale: str
    add: list
    remove: list

@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str
    raw: dict

def _unique_object(pairs):
    result = {}
    for key,value in pairs:
        if key in result: raise ProposalError('JSON: duplicate field '+key)
        result[key]=value
    return result

def parse_proposal(text):
    try:
        p=json.loads(text,object_pairs_hook=_unique_object)
    except (ValueError,TypeError) as e:
        raise ProposalError('JSON: '+str(e)) from e
    if not isinstance(p,dict) or set(p)!= {'rationale','add','remove'}:
        raise ProposalError('JSON fields must be rationale, add, remove')
    if not isinstance(p['rationale'],str) or not p['rationale'].strip():
        raise ProposalError('rationale must be nonempty text')
    for field in ('add','remove'):
        if not isinstance(p[field],list) or any(not isinstance(a,str) or not a.strip() for a in p[field]):
            raise ProposalError(field+' must be an array of nonempty axiom strings')
        if len(set(p[field]))!=len(p[field]): raise ProposalError('Repeated axiom')
    if set(p['add']) & set(p['remove']): raise ProposalError('Conflicting add/remove')
    source=Path(__file__).parent/'owl_bridge'
    files=[source/'OntologyEvaluator.java',source/'ProposalSyntax.java']
    import tempfile
    build=Path(tempfile.gettempdir())/('proposal-syntax-'+hashlib.sha256(b''.join(f.read_bytes() for f in files)).hexdigest()[:20])
    build.mkdir(exist_ok=True)
    if not (build/'ProposalSyntax.class').exists():
        _run(['javac','-encoding','UTF-8','-cp',str(LIB/'*'),'-d',str(build),*[str(f) for f in files]])
    # Infrastructure errors propagate; malformed OWL is returned by the parser process.
    import subprocess
    proc=subprocess.run(['java','-Dfile.encoding=UTF-8','-cp',str(build)+':'+str(LIB/'*'),'ProposalSyntax'],input=json.dumps(p),text=True,capture_output=True,timeout=120)
    if proc.returncode: raise ProposalError('OWL syntax: '+proc.stderr[-2000:])
    if not 1<=int(proc.stdout.strip())<=5: raise ProposalError('Expected 1..5 logical axioms')
    return Proposal(**p)

def render_prompt(context,previous_error=None):
    metrics=context['metrics']; relative=context['relative']
    if set(metrics)!={f'M{i}' for i in range(1,7)} or len(relative)!=6:
        raise ValueError('M1–M6 and six ri required')
    return Template((Path(__file__).parent/'prompts/proposal.txt').read_text()).substitute(
        ontology_manchester=context['ontology_manchester'],metrics=json.dumps(metrics,ensure_ascii=False),relative=json.dumps(relative),previous_error=previous_error or 'нет')

class OllamaModels:
    """Explicit local endpoint. Caller must attest pinned weights/context before series."""
    def __init__(self,model,embedding_model,endpoint='http://127.0.0.1:11434',seed=100):
        self.model,self.embedding_model,self.endpoint,self.seed=model,embedding_model,endpoint.rstrip('/'),seed
    def _post(self,path,payload):
        request=Request(self.endpoint+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=180) as response: return json.load(response)
    def propose(self,context,previous_error=None):
        raw=self._post('/api/generate',dict(model=self.model,prompt=render_prompt(context,previous_error),stream=False,format='json',options=dict(temperature=.7,top_p=.95,num_predict=2000,num_ctx=32768,seed=self.seed)))
        if raw.get('done') is not True: raise RuntimeError('Incomplete model response')
        return ModelResponse(raw['response'],raw['model'],raw)
    def embed(self,texts):
        raw=self._post('/api/embed',dict(model=self.embedding_model,input=texts,truncate=False))
        vectors=raw['embeddings']
        if len(vectors)!=len(texts): raise ValueError('Embedding response length')
        return vectors

def propose_with_retries(propose,context):
    error=None
    for _ in range(3):
        response=propose(context,error)
        try: return parse_proposal(response.text if isinstance(response,ModelResponse) else response)
        except ProposalError as e: error=str(e)
    raise ProposalError('Three unsuccessful attempts: '+error)

def cosine(a,b):
    if len(a)!=len(b) or not a or any(not math.isfinite(x) for x in [*a,*b]): raise ValueError('Invalid embeddings')
    na=math.sqrt(sum(x*x for x in a)); nb=math.sqrt(sum(x*x for x in b))
    if not na or not nb: raise ValueError('Zero embedding')
    return sum(x*y for x,y in zip(a,b))/(na*nb)

class SemanticDeduplicator:
    def __init__(self,embed,entities,threshold=.90):
        if not 0<=threshold<=1: raise ValueError('threshold')
        self.embed,self.entities,self.threshold=embed,list(entities),threshold
    def is_duplicate(self,label,comment,category):
        peers=[e for e in self.entities if e['category']==category]
        if not peers: return False
        texts=[f'{label}. {comment}']+[f"{e['label']}. {e['comment']}" for e in peers]
        vectors=self.embed(texts)
        if len(vectors)!=len(texts): raise ValueError('Embedding response length')
        return any(cosine(vectors[0],v)>=self.threshold for v in vectors[1:])
    def __call__(self,new_entities):
        # Include earlier novel entities so duplicates within the same proposal are caught.
        checker=SemanticDeduplicator(self.embed,self.entities,self.threshold)
        for e in new_entities:
            if checker.is_duplicate(e['label'],e['comment'],e['category']): return True
            checker.entities.append(e)
        return False

def assess_pairs(pairs,embed,threshold=.90):
    pairs=list(pairs)
    if len(pairs)!=20 or sum(str(p['synonym'])=='1' for p in pairs)!=10 or sum(str(p['synonym'])=='0' for p in pairs)!=10:
        raise ValueError('Exactly 10 synonym and 10 distinct pairs required')
    rows=[]
    for p in pairs:
        a,b=embed([p['left'],p['right']]); score=cosine(a,b)
        rows.append(dict(id=p.get('id'),score=score,expected=str(p['synonym'])=='1',duplicate=score>=threshold))
    return dict(count=20,threshold=threshold,errors=sum(r['expected']!=r['duplicate'] for r in rows),rows=rows,analyst_approved=all(p.get('review_status')=='approved' for p in pairs))

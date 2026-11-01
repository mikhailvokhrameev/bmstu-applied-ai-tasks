"""Durable local run journals. JSON checkpoint data is never executable."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sys
import subprocess
import uuid
from . import search
from .bridge import CORE, CORE_SHA256, LIB, evaluate
from .metrics import compute_metrics, fitness, BASELINE

SCHEMA=1
class JournalError(RuntimeError): pass

def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()
def digest(value):return hashlib.sha256(value).hexdigest()
def atomic(path,data):
    temp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    try:
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
        fd=os.open(str(path.parent),os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if temp.exists():temp.unlink()
def tuples(value):return tuple(tuples(v) for v in value) if isinstance(value,list) else value

def _metadata(root):
    try:
        raw=(root/'metadata.json').read_bytes(); seal=(root/'metadata.sha256').read_text()
        if digest(raw)!=seal:raise ValueError('metadata checksum')
        meta=json.loads(raw)
        if meta['schema']!=SCHEMA or meta['core_sha256']!=CORE_SHA256:raise ValueError('incompatible schema/core')
        if digest(CORE.read_bytes())!=meta['core_sha256']:raise ValueError('core changed')
        if digest((root/'config.yaml').read_bytes())!=meta['config_sha256']:raise ValueError('configuration changed')
        return meta
    except (OSError,ValueError,KeyError,TypeError) as e:raise JournalError('Invalid run metadata: '+str(e)) from e

def start(config,mode,seed,run_dir,runtime=None):
    raw=Path(config).read_bytes(); spec=search.load_config(config)
    root=Path(run_dir);root.mkdir(parents=True,exist_ok=False)
    manifest=spec.pop('services',{})
    meta=dict(schema=SCHEMA,mode=mode,seed=seed,config_sha256=digest(raw),core_sha256=CORE_SHA256,
              environment=dict(python=sys.version,platform=platform.platform(),java=subprocess.run(['java','-version'],capture_output=True,text=True,timeout=10).stderr.strip(),libraries={p.name:digest(p.read_bytes()) for p in sorted(LIB.glob('*.jar'))}),models=manifest)
    atomic(root/'config.yaml',raw);atomic(root/'metadata.json',encoded(meta));atomic(root/'metadata.sha256',digest(encoded(meta)).encode())
    return _run(root,meta,spec,runtime,None)

def _run(root,meta,spec,runtime,snapshot):
    if runtime is None:
        from .runtime import build_runtime
        runtime=build_runtime(meta['models'],meta['seed'])
    runtime=dict(runtime); inspect=runtime.pop('inspect',lambda d:evaluate(CORE,d['add'],d['remove']))
    generator=runtime.get(meta['mode']+'_generator')
    def on_evaluation(candidate,validation,elapsed,error):
        row=asdict(candidate);row.update(run_id=root.name,mode=meta['mode'],seed=meta['seed'],validation=asdict(validation),metrics=asdict(validation.metrics) if validation.metrics is not None else None,
            ri=validation.relative,elapsed_seconds=elapsed,proposal_error=error,
            attempts=getattr(generator,'attempts',[]) if candidate.operator!='crossover' else [])
        try:
            reconstructed=inspect(candidate.delta)
            row['axioms']=sorted(set(reconstructed['axioms']))
            if row['metrics'] is None and 'counts' in reconstructed:
                m=compute_metrics(reconstructed['counts']);row['metrics']=asdict(m);row['ri']=fitness(m,BASELINE).relative
        except Exception as exc:
            if candidate.status=='valid':raise
            row['axioms']=None;row['reconstruction_error']=str(exc)
        with (root/'evaluations.jsonl').open('ab') as f:f.write(encoded(row)+b'\n');f.flush();os.fsync(f.fileno())
    history=list(snapshot['history']) if snapshot else []
    def on_generation(g,pop,evaluations,state):
        history.append(pop)
        data=dict(schema=SCHEMA,metadata_sha256=digest((root/'metadata.json').read_bytes()),generation=g,
                  history=[[asdict(c) for c in p] for p in history],evaluations=[asdict(c) for c in evaluations],
                  best=asdict(pop[0]),rng_state=state,log_sha256=digest((root/'evaluations.jsonl').read_bytes()))
        data['payload_sha256']=digest(encoded(data))
        atomic(root/'checkpoint.json',encoded(data))
    runtime.update(on_evaluation=on_evaluation,on_generation=on_generation)
    try:
        return search.run({**spec,'runtime':runtime},meta['mode'],meta['seed'],resume=snapshot or False)
    except BaseException as error:
        with (root/'interruptions.jsonl').open('ab') as f:
            f.write(encoded(dict(error=type(error).__name__,detail=str(error),attempts=getattr(generator,'attempts',[])))+b'\n');f.flush();os.fsync(f.fileno())
        raise

def resume(run_dir,runtime=None):
    root=Path(run_dir);meta=_metadata(root)
    try:
        cp=json.loads((root/'checkpoint.json').read_text()) if (root/'checkpoint.json').exists() else None
        raw=(root/'evaluations.jsonl').read_bytes() if (root/'evaluations.jsonl').exists() else b''
        count=len(cp['evaluations']) if cp else 0
        lines=raw.splitlines(keepends=True); committed=b''.join(lines[:count]);tail=b''.join(lines[count:])
        if cp:
            checksum=cp.pop('payload_sha256',None)
            if checksum!=digest(encoded(cp)):raise ValueError('checkpoint checksum (corrupt or incompatible)')
            if cp['schema']!=SCHEMA or cp['metadata_sha256']!=digest((root/'metadata.json').read_bytes()):raise ValueError('incompatible checkpoint')
            if digest(committed)!=cp['log_sha256']:raise ValueError('checkpoint journal mismatch')
            if count!=10+8*cp['generation'] or len(cp['history'])!=cp['generation']+1 or not 0<=cp['generation']<=20:raise ValueError('checkpoint budget/history')
            rows=[json.loads(line) for line in lines[:count]]
            for index,(row,c) in enumerate(zip(rows,cp['evaluations'])):
                if c['id']!=index or any(row[k]!=v for k,v in c.items()):raise ValueError('checkpoint candidate mismatch')
            for population in cp['history']:
                if len(population)!=10 or any(c!=cp['evaluations'][c['id']] for c in population):raise ValueError('checkpoint population mismatch')
            if cp['best']!=cp['history'][-1][0]:raise ValueError('checkpoint best mismatch')
            def candidate(d):return search.Candidate(**{**d,'parents':tuple(d['parents'])})
            snapshot=dict(evaluations=[candidate(d) for d in cp['evaluations']],history=[tuple(candidate(d) for d in p) for p in cp['history']],rng_state=tuples(cp['rng_state']))
            random.Random().setstate(snapshot['rng_state'])
        else:snapshot=None
        if tail:atomic(root/('audit-'+uuid.uuid4().hex+'.jsonl'),tail);atomic(root/'evaluations.jsonl',committed)
        spec=search.load_config(root/'config.yaml');spec.pop('services',None)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as e:raise JournalError('Invalid checkpoint: '+str(e)) from e
    return _run(root,meta,spec,runtime,snapshot)

def replay(run_dir,candidate,inspect=None,score=None):
    root=Path(run_dir);_metadata(root)
    rows=[json.loads(s) for s in (root/'evaluations.jsonl').read_text().splitlines()]
    matches=[r for r in rows if r['id']==candidate]
    if len(matches)!=1:raise JournalError('Candidate not found or duplicated')
    row=matches[0];delta=row['delta']
    try:result=(inspect or (lambda d:evaluate(CORE,d['add'],d['remove'])))(delta)
    except Exception:
        if row['status']!='invalid' or row['axioms'] is not None:raise
        return dict(candidate=candidate,axioms_match=False,F=0.,matches=False,reconstruction='Rejected candidate has no reconstructible axiom set')
    f=score(delta) if score else (0. if row['status']=='invalid' else fitness(compute_metrics(result['counts']),BASELINE).F)
    return dict(candidate=candidate,axioms_match=sorted(set(result['axioms']))==row['axioms'],F=f,
                matches=sorted(set(result['axioms']))==row['axioms'] and f==row['F'])

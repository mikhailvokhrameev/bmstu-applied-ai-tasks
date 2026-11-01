"""Read-only analysis of schema-1 journals; never starts a search or model.

Exact one-sided permutation Mann–Whitney handles ties by midranks. Timing
stored by schema 1 measures evaluations only, not series wall-clock duration.
"""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from statistics import median
from . import journal


def mann_whitney(model, control):
    if len(model) != 5 or len(control) != 5:
        raise ValueError('Exactly five results per series required')
    pooled = list(model) + list(control)
    if any(not math.isfinite(v) for v in pooled):
        raise ValueError('Non-finite fitness')
    ranks = [1 + sum(x < v for x in pooled) + (sum(x == v for x in pooled)-1)/2 for v in pooled]
    observed = sum(ranks[:5])-15
    null = [sum(ranks[i] for i in group)-15 for group in itertools.combinations(range(10), 5)]
    p = sum(u >= observed for u in null)/len(null)
    return dict(U=observed, p=p, alternative='model > control', alpha=.05,
                method='exact label permutation, midranks for ties, 252 allocations',
                significant=p < .05,
                conclusion='Evidence of higher model fitness' if p < .05 else 'Insufficient evidence at alpha=0.05; this alone does not fail T09')


def timing_summary(root):
    timing=journal.read_timing(root)
    if timing is None:
        return dict(wall_clock_seconds=None, duration_acceptance='UNVERIFIED: legacy journal lacks timestamps')
    sessions=timing['sessions']
    end=timing.get('completed_at')
    valid=(timing.get('complete_origin') is True and end is not None and end>=timing['started_at'])
    previous=timing['started_at']
    for session in sessions:
        start=session['started_at'];finish=session.get('ended_at')
        if start < previous or (finish is not None and finish < start):valid=False
        previous=finish if finish is not None else start
    if not valid:
        return dict(wall_clock_seconds=None,duration_acceptance='UNVERIFIED: incomplete origin/completion or clock regression')
    return dict(wall_clock_seconds=end-timing['started_at'],
                started_at=timing['started_at'],completed_at=end,
                active_seconds=sum(s.get('active_seconds',0) for s in sessions) if all('active_seconds' in s for s in sessions) else None,
                duration_acceptance='Run wall-clock span recorded; series span checked separately')


def analyze_run(directory, replay=False):
    root = Path(directory)
    meta = journal._metadata(root)
    cp = json.loads((root/'checkpoint.json').read_text())
    seal = cp.pop('payload_sha256')
    if seal != journal.digest(journal.encoded(cp)):
        raise ValueError('Checkpoint checksum mismatch')
    raw = (root/'evaluations.jsonl').read_bytes()
    if cp['log_sha256'] != journal.digest(raw) or cp['metadata_sha256'] != journal.digest((root/'metadata.json').read_bytes()):
        raise ValueError('Journal/checkpoint checksum mismatch or uncommitted tail')
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != 170 or cp['generation'] != 20 or len(cp['history']) != 21 or len(cp['evaluations']) != 170:
        raise ValueError('Incomplete run: expected 170 evaluations and generations 0–20')
    for i, row in enumerate(rows):
        if row['id'] != i or any(row[k] != v for k,v in cp['evaluations'][i].items()):
            raise ValueError('Candidate/checkpoint mismatch')
        if row['seed'] != meta['seed'] or row['mode'] != meta['mode']:
            raise ValueError('Row seed/mode mismatch')
        if not math.isfinite(row['F']) or row['status'] not in ('valid','invalid') or (row['status']=='invalid' and row['F'] != 0):
            raise ValueError('Invalid fitness/status')
        if not math.isfinite(row['elapsed_seconds']) or row['elapsed_seconds'] < 0:
            raise ValueError('Invalid evaluation duration')
        if row['generation'] != (0 if i < 10 else 1+(i-10)//8):
            raise ValueError('Generation evaluation budget mismatch')
    generations=[]
    previous=None
    for g,pop in enumerate(cp['history']):
        if len(pop)!=10 or len({c['id'] for c in pop})!=10 or any(c != cp['evaluations'][c['id']] for c in pop):
            raise ValueError('Population membership mismatch')
        expected=sorted(pop,key=lambda c:(-c['F'],c['id']))
        if pop != expected:
            raise ValueError('Population rank mismatch')
        if g:
            if pop[0]['F'] < previous[0]['F'] or not {c['id'] for c in previous[:2]} <= {c['id'] for c in pop}:
                raise ValueError('Elitism/monotonicity violation')
            if {c['id'] for c in pop} != {c['id'] for c in previous[:2]} | {r['id'] for r in rows if r['generation']==g}:
                raise ValueError('Generation population mismatch')
        elif {c['id'] for c in pop} != set(range(10)):
            raise ValueError('Initial population mismatch')
        evaluated=[r for r in rows if r['generation']==g]
        codes={str(r['code']) for r in evaluated if r['status']=='invalid'}
        generations.append(dict(generation=g,best_F=pop[0]['F'],median_F=median(c['F'] for c in pop),
                                invalid_fraction=sum(r['status']=='invalid' for r in evaluated)/len(evaluated),
                                invalid_by_code={code:sum(r['status']=='invalid' and str(r['code'])==code for r in evaluated)/len(evaluated) for code in sorted(codes)}))
        previous=pop
    best=min(rows,key=lambda r:(-r['F'],r['id']))
    if cp['best'] != cp['history'][-1][0] or best['id'] != cp['best']['id']:
        raise ValueError('Best candidate mismatch')
    return dict(path=str(root),mode=meta['mode'],seed=meta['seed'],config_sha256=meta['config_sha256'],
                best_F=best['F'],best_generation=best['generation'],best_id=best['id'],generations=generations,
                evaluation_seconds=sum(r['elapsed_seconds'] for r in rows),
                **timing_summary(root),
                replay=journal.replay(root,best['id']) if replay else None)


def export_run(result, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    stem=f"{result['mode']}-{result['seed']}"
    codes=sorted({c for g in result['generations'] for c in g['invalid_by_code']})
    with (output/(stem+'.csv')).open('w',newline='') as f:
        fields=['generation','best_F','median_F','best_candidate_generation','invalid_fraction']+['invalid_'+c for c in codes]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for g in result['generations']:
            writer.writerow({**{k:v for k,v in g.items() if k!='invalid_by_code'},'best_candidate_generation':result['best_generation'],**{'invalid_'+c:g['invalid_by_code'].get(c,0) for c in codes}})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(9,7),sharex=True)
    gs=result['generations'];x=[g['generation'] for g in gs]
    for key in ('best_F','median_F'):axes[0].plot(x,[g[key] for g in gs],label=key)
    axes[0].set_title(f"{stem}; best candidate generation {result['best_generation']}");axes[0].legend();axes[0].set_ylabel('F')
    axes[1].plot(x,[g['invalid_fraction'] for g in gs],label='all invalid')
    for code in codes:axes[1].plot(x,[g['invalid_by_code'].get(code,0) for g in gs],label=code)
    axes[1].set(xlabel='Generation',ylabel='Fraction of evaluations',ylim=(0,1));axes[1].legend();fig.tight_layout();fig.savefig(output/(stem+'.png'));plt.close(fig)


def series_timing(group):
    if any(r.get('wall_clock_seconds') is None for r in group):
        return dict(seconds=None,within_eight_hours=None,status='UNVERIFIED: missing trustworthy timestamps')
    seconds=max(r['completed_at'] for r in group)-min(r['started_at'] for r in group)
    return dict(seconds=seconds,within_eight_hours=seconds<=8*3600,
                status='Includes all gaps between first start and final completion; UTC system clock must be stable')


def summarize(results):
    for mode,seeds in [('model',set(range(101,106))),('control',set(range(201,206)))]:
        group=[r for r in results if r['mode']==mode]
        if len(group)!=5 or {r['seed'] for r in group}!=seeds:
            raise ValueError('Missing/duplicate/incorrect series seeds: '+mode)
    if len(results)!=10 or len({r['config_sha256'] for r in results})!=1:
        raise ValueError('Expected ten runs with identical frozen configuration')
    if any(r['replay'] is None or not r['replay']['matches'] for r in results):
        raise ValueError('All ten best candidates must pass model-free replay')
    model=[r['best_F'] for r in results if r['mode']=='model'];control=[r['best_F'] for r in results if r['mode']=='control']
    return dict(model_best=model,control_best=control,model_max=max(model),model_median=median(model),control_median=median(control),
                targets=dict(maximum=max(model)>=1.25,median=median(model)>=1.15,each_above_one=all(v>1 for v in model),median_above_control=median(model)>median(control)),
                mann_whitney=mann_whitney(model,control),series_timing={mode: series_timing([r for r in results if r['mode']==mode]) for mode in ('model','control')})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runs',nargs='+');parser.add_argument('--output',required=True);parser.add_argument('--replay',action='store_true');parser.add_argument('--series',action='store_true');args=parser.parse_args()
    results=[analyze_run(p,args.replay) for p in args.runs]
    for r in results:export_run(r,args.output)
    data=dict(runs=results,series=summarize(results) if args.series else None)
    (Path(args.output)/'analysis.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':main()

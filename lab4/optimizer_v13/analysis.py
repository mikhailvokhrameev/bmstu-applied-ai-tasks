"""Read-only analysis of schema-2 journals; never starts a search or model.

Exact one-sided permutation Mann–Whitney handles ties by midranks. Debug
qualification reports parsed first responses separately from ontology validity.
"""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from statistics import median
from . import journal
from .search import PHASE_GENERATIONS
from dataclasses import asdict
from .metrics import compute_metrics, fitness, BASELINE


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
    sessions=timing.get('sessions',[])
    end=timing.get('completed_at')
    origin=timing.get('started_at')
    finite=lambda value: isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
    valid=(timing.get('complete_origin') is True and finite(origin) and finite(end)
           and end>=origin and bool(sessions))
    previous=origin
    for index,session in enumerate(sessions):
        start=session.get('started_at');finish=session.get('ended_at')
        if not finite(start) or not finite(previous) or start < previous:
            valid=False
        if finish is None:
            # Unclean earlier sessions have an unknown end, bounded by resume.
            if index==len(sessions)-1 or session.get('outcome')!='unclean interruption; active duration unknown':valid=False
        elif not finite(finish) or not finite(start) or finish < start or not finite(end) or finish>end:
            valid=False
        previous=finish if finish is not None else start
    if sessions and (sessions[-1].get('outcome')!='completed' or sessions[-1].get('ended_at')!=end):
        valid=False
    if not valid:
        return dict(wall_clock_seconds=None,duration_acceptance='UNVERIFIED: incomplete origin/completion or clock regression')
    return dict(wall_clock_seconds=end-timing['started_at'],
                started_at=timing['started_at'],completed_at=end,
                active_seconds=sum(s['active_seconds'] for s in sessions) if all(
                    finite(s.get('active_seconds')) and s['active_seconds'] >= 0
                    and s.get('ended_at') is not None
                    and s['active_seconds'] <= s['ended_at'] - s['started_at'] + 1
                    for s in sessions) else None,
                duration_acceptance='Run wall-clock span recorded; series span checked separately')


def debug_assessment(rows, mode, timing):
    """Describe observed debug quality; projections never qualify run duration."""
    requests = [row for row in rows if mode == 'model' and row['operator'] != 'crossover']
    first_attempts = [
        row['attempts'][0] if isinstance(row.get('attempts'), list)
        and row['attempts'] and isinstance(row['attempts'][0], dict) else {}
        for row in requests]
    complete = bool(requests) and all('response' in attempt for attempt in first_attempts)
    successes = sum(
        attempt.get('response') is not None
        and 'parse_error' not in attempt and 'service_error' not in attempt
        for attempt in first_attempts)
    fraction = successes / len(requests) if requests else None
    wall_seconds = timing.get('wall_clock_seconds')
    projected = wall_seconds * 170 / 34 if wall_seconds is not None else None
    projected_series = wall_seconds * 850 / 34 if wall_seconds is not None else None
    durations = [row.get('elapsed_seconds') for row in rows]
    complete_durations = all(isinstance(value, (float, int)) and not isinstance(value, bool)
                             and math.isfinite(value) and value >= 0 for value in durations)
    steady_series = sum(durations) * 850 / 34 if complete_durations else None
    return dict(model_requests=len(requests), first_response_success_count=successes,
                first_response_fraction=fraction, first_response_evidence_complete=complete,
                meets_70_percent=(fraction >= .70) if complete else None,
                valid_ontology_fraction=sum(row['status'] == 'valid' for row in rows) / len(rows),
                projected_170_evaluation_seconds=projected,
                projection_factor=170 / 34,
                projected_within_eight_hours=(projected <= 8 * 3600) if projected is not None else None,
                projected_850_evaluation_seconds=projected_series,
                projection_series_factor=850 / 34,
                projected_series_within_eight_hours=(projected_series <= 8 * 3600) if projected_series is not None else None,
                steady_projection_series_seconds=steady_series,
                steady_projection_status='Estimate from committed evaluation durations only; excludes repairs, gaps and discarded audit evaluations; not acceptance',
                duration_acceptance=None,
                projection_status='Estimates from debug wall-clock span: 170 evaluations is one run (legacy projected_within_eight_hours); 850 evaluations is a five-run series. The eight-hour requirement applies to the series; neither projection confirms acceptance')


def analyze_run(directory, replay=False):
    root = Path(directory)
    meta = journal._metadata(root)
    if meta.get('schema') != journal.SCHEMA or meta.get('methodology') != journal.METHODOLOGY:
        raise ValueError('Incompatible journal schema/methodology')
    phase = meta.get('phase', 'main')
    if phase not in PHASE_GENERATIONS:
        raise ValueError('Invalid experiment phase')
    last_generation = PHASE_GENERATIONS[phase]
    evaluation_count = 10 + 8 * last_generation
    cp = json.loads((root/'checkpoint.json').read_text())
    seal = cp.pop('payload_sha256')
    if cp.get('schema') != journal.SCHEMA:
        raise ValueError('Incompatible checkpoint schema')
    if seal != journal.digest(journal.encoded(cp)):
        raise ValueError('Checkpoint checksum mismatch')
    raw = (root/'evaluations.jsonl').read_bytes()
    if cp['log_sha256'] != journal.digest(raw) or cp['metadata_sha256'] != journal.digest((root/'metadata.json').read_bytes()):
        raise ValueError('Journal/checkpoint checksum mismatch or uncommitted tail')
    rows = [json.loads(line) for line in raw.splitlines()]
    if (len(rows) != evaluation_count or cp['generation'] != last_generation
            or len(cp['history']) != last_generation + 1 or len(cp['evaluations']) != evaluation_count):
        raise ValueError(f'Incomplete {phase} run: expected {evaluation_count} evaluations and generations 0–{last_generation}')
    for i, row in enumerate(rows):
        if row.get('schema') != journal.SCHEMA or row.get('methodology') != journal.METHODOLOGY:
            raise ValueError('Row schema/methodology mismatch')
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
        _verify_recorded_metrics(row)
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
        population_rows = [rows[c['id']] for c in pop]
        best_row = population_rows[0]
        def numeric_median(key):
            values = [row[key] for row in population_rows if row[key] is not None]
            return median(values) if values else None
        generations.append(dict(generation=g,best_F=pop[0]['F'],median_F=median(c['F'] for c in pop),
                                best_B=best_row['B'],median_B=numeric_median('B'),
                                best_S=best_row['S'],median_S=numeric_median('S'),
                                invalid_fraction=sum(r['status']=='invalid' for r in evaluated)/len(evaluated),
                                invalid_by_code={code:sum(r['status']=='invalid' and str(r['code'])==code for r in evaluated)/len(evaluated) for code in sorted(codes)}))
        previous=pop
    best=min(rows,key=lambda r:(-r['F'],r['id']))
    if cp['best'] != cp['history'][-1][0] or best['id'] != cp['best']['id']:
        raise ValueError('Best candidate mismatch')
    timing = timing_summary(root)
    return dict(path=str(root),mode=meta['mode'],phase=phase,seed=meta['seed'],config_sha256=meta['config_sha256'],
                schema=journal.SCHEMA,methodology=journal.METHODOLOGY,
                best_F=best['F'],best_B=best['B'],best_S=best['S'],
                best_counts=best['counts'],best_metrics=best['metrics'],
                best_coefficients=best['coefficients'],best_graph=best['graph'],
                baseline_metrics=meta.get('baseline_metrics'),baseline_counts=meta.get('baseline_counts'),
                best_generation=best['generation'],best_id=best['id'],generations=generations,
                evaluation_seconds=sum(r['elapsed_seconds'] for r in rows),
                **timing,
                t04=debug_assessment(rows,meta['mode'],timing) if phase=='debug' else None,
                replay=journal.replay(root,best['id']) if replay else None)


def _verify_recorded_metrics(row):
    """Validate the saved arithmetic without running Java, reasoning or ML."""
    if row.get('axioms') is None:
        if row['status'] != 'invalid' or not row.get('reconstruction_error'):
            raise ValueError('Missing candidate reconstruction')
        return
    try:
        metrics = compute_metrics(row['counts'], graph=row['graph'])
        score = fitness(metrics, BASELINE)
        checks = [journal.equivalent(asdict(metrics), row['metrics']),
                  journal.equivalent(score.B, row['B']),
                  journal.equivalent(score.S, row['S']),
                  journal.equivalent(score.F, row['formula_F']),
                  journal.equivalent(score.coefficients, row['coefficients']),
                  journal.equivalent(list(score.relative), row['ri'])]
        if row['status'] == 'valid':
            checks.extend([journal.structure_valid(metrics, score),
                           journal.equivalent(score.F, row['F'])])
        if not all(checks):
            raise ValueError('Recorded metrics/components disagree with graph/counts')
    except (KeyError, TypeError) as error:
        raise ValueError('Incomplete candidate metrics') from error


def export_run(result, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    stem=f"{result['mode']}-{result['seed']}"
    codes=sorted({c for g in result['generations'] for c in g['invalid_by_code']})
    with (output/(stem+'.csv')).open('w',newline='') as f:
        fields=['generation','best_F','median_F','best_B','median_B','best_S','median_S','best_candidate_generation','invalid_fraction']+['invalid_'+c for c in codes]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for g in result['generations']:
            writer.writerow({**{k:v for k,v in g.items() if k!='invalid_by_code'},'best_candidate_generation':result['best_generation'],**{'invalid_'+c:g['invalid_by_code'].get(c,0) for c in codes}})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(9,10),sharex=True)
    gs=result['generations'];x=[g['generation'] for g in gs]
    for key in ('best_F','median_F','best_B','median_B'):axes[0].plot(x,[g[key] for g in gs],label=key)
    axes[0].set_title(f"{stem}; best candidate generation {result['best_generation']}");axes[0].legend();axes[0].set_ylabel('F / B')
    for key in ('best_S','median_S'):
        axes[1].plot(x,[g[key] for g in gs],label=key)
    axes[1].set(ylabel='S',ylim=(0,1.02));axes[1].legend()
    axes[2].plot(x,[g['invalid_fraction'] for g in gs],label='all invalid')
    for code in codes:axes[2].plot(x,[g['invalid_by_code'].get(code,0) for g in gs],label=code)
    axes[2].set(xlabel='Generation',ylabel='Fraction of evaluations',ylim=(0,1));axes[2].legend()
    fig.tight_layout();fig.savefig(output/(stem+'.png'));plt.close(fig)
    (output/(stem+'-best.json')).write_text(json.dumps({key:value for key,value in result.items()
        if key.startswith('best_') or key in ('schema','methodology','mode','seed','phase')},
        ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def series_timing(group):
    if any(r.get('wall_clock_seconds') is None for r in group):
        return dict(seconds=None,within_eight_hours=None,status='UNVERIFIED: missing trustworthy timestamps')
    seconds=max(r['completed_at'] for r in group)-min(r['started_at'] for r in group)
    active = sum(r['active_seconds'] for r in group) if all(r.get('active_seconds') is not None for r in group) else None
    return dict(seconds=seconds,within_eight_hours=seconds<=8*3600,active_seconds=active,
                status='Includes all gaps between first start and final completion; UTC system clock must be stable')


def summarize(results):
    if any(r.get('phase', 'main') != 'main' for r in results):
        raise ValueError('Debug runs cannot enter main series')
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

import json,re,math,sys,argparse,tempfile
from dataclasses import asdict
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path.cwd()))
from lab4.optimizer_v13.metrics import BASELINE, compute_metrics, fitness

NS='https://example.org/ontologies/videocard#'
DECL=re.compile(r'^Declaration\((Class|ObjectProperty|DataProperty|NamedIndividual)\(<([^>]+)>\)\)$')
SUB=re.compile(r'^SubClassOf\(<([^>]+)> <([^>]+)>\)$')
NAMED=re.compile(r'^<([^>]+)>$')

def arguments(axiom):
    content=axiom[axiom.index('(')+1:-1]
    depth=0; quoted=False;escaped=False;start=0;out=[]
    for i,ch in enumerate(content):
        if quoted:
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':quoted=False
            continue
        if ch=='"':quoted=True
        elif ch=='(':depth+=1
        elif ch==')':depth-=1
        elif ch.isspace() and depth==0:
            if i>start:out.append(content[start:i])
            start=i+1
    if start<len(content):out.append(content[start:])
    return out

def recalc(row):
    axioms=row.get('axioms')
    if not isinstance(axioms,list):raise ValueError('no stored reconstructible axiom set')
    if not row.get('metrics'):raise ValueError('no stored schema metrics')
    if len(set(axioms))!=len(axioms):raise ValueError('duplicate stored axioms')
    entities={k:set() for k in ['Class','ObjectProperty','DataProperty','NamedIndividual']}
    for ax in axioms:
        m=DECL.match(ax)
        if m and m[2].startswith(NS):entities[m[1]].add(m[2])
    # Incomplete declarations in invalid OWL2_DL proposals do not remove a
    # property from the actual OWL signature. Recover explicit inverse operands.
    undeclared_inverse_properties=set()
    for ax in axioms:
        if ax.startswith('InverseObjectProperties('):
            for arg in arguments(ax):
                match=NAMED.match(arg)
                if match and match[1].startswith(NS):
                    if match[1] not in entities['ObjectProperty']:undeclared_inverse_properties.add(match[1])
                    entities['ObjectProperty'].add(match[1])
    classes=entities['Class'];edges=set();defined=set();unknown=[]
    for ax in axioms:
        m=SUB.match(ax)
        if m and m[1].startswith(NS) and m[2].startswith(NS):
            edges.add((m[2],m[1]))
            if m[1] not in classes or m[2] not in classes:unknown.append(ax)
        if ax.startswith('EquivalentClasses('):
            for arg in arguments(ax):
                m=NAMED.match(arg)
                if m and m[1].startswith(NS):
                    defined.add(m[1])
                    if m[1] not in classes:unknown.append(ax)
    if unknown:raise ValueError('named class operand has no declaration')
    logical=sum(not ax.startswith(('Declaration(','AnnotationAssertion(','SubAnnotationPropertyOf(','AnnotationPropertyDomain(','AnnotationPropertyRange(')) for ax in axioms)
    counts=dict(C=len(classes),H=len(edges),Po=len(entities['ObjectProperty']),Pd=len(entities['DataProperty']),E=len(defined),Al=logical,A=len(axioms),Individuals=len(entities['NamedIndividual']),Q=row['metrics']['M6'])
    graph=dict(vertices=sorted(classes),edges=[list(edge) for edge in sorted(edges)])
    measured=compute_metrics(counts,graph=graph)
    for key in ['M1','M2','M3','M4','M5','M6']:
        if abs(getattr(measured,key)-row['metrics'][key])>1e-12:raise ValueError('recomputed '+key+' differs from saved schema metric')
    score=fitness(measured,BASELINE)
    if row['status']=='valid' and abs(score.B-row['F'])>1e-12:raise ValueError('recomputed B differs from saved old F')
    restrictions=dict(acyclic=measured.structural.CY1==0 and measured.structural.CY2==0,structure=score.S is not None and score.S>=.85,relative=min(score.relative)>=.85,size=counts['C']<=30 and counts['Individuals']<=60 and counts['A']<=710)
    admissible=row['status']=='valid' and all(restrictions.values())
    return dict(id=row['id'],generation=row['generation'],old_status=row['status'],old_F=row['F'],counts=counts,metrics=asdict(measured),B=score.B,S=score.S,formula_F=score.F,F=score.F if admissible else 0,coefficients=score.coefficients,relative=score.relative,new_restrictions=restrictions,new_admissible=admissible,undeclared_inverse_properties=sorted(undeclared_inverse_properties),graph=graph)

root=Path('lab4/runs/series-v1');best=[];summaries=[]
for directory in sorted(root.iterdir()):
    if not re.fullmatch(r'(model-10[1-5]|control-20[1-5])',directory.name):continue
    checkpoint=json.loads((directory/'checkpoint.json').read_text());best_id=checkpoint['best']['id'];rows=[json.loads(line) for line in (directory/'evaluations.jsonl').open()]
    failures=Counter();changed=[];scores=[]
    for row in rows:
        try:
            result=recalc(row);scores.append(result)
            if abs(result['F']-row['F'])>1e-12:changed.append(dict(id=row['id'],old_F=row['F'],new_F=result['F'],S=result['S'],old_status=row['status'],restrictions=result['new_restrictions']))
            if row['id']==best_id:best.append(dict(run=directory.name,**result))
        except ValueError as exc:
            failures[str(exc)]+=1
            if row['id']==best_id:best.append(dict(run=directory.name,id=best_id,error=str(exc)))
    selected=min(scores,key=lambda r:(-r['F'],r['id'])) if scores else None
    score_map={r['id']:r['F'] for r in scores}; ranking_changes=[];elite_changes=[]
    if len(scores)==len(rows):
        for g,pop in enumerate(checkpoint['history']):
            old_ids=[r['id'] for r in pop]
            new_ids=sorted(old_ids,key=lambda i:(-score_map[i],i))
            if old_ids!=new_ids:ranking_changes.append(g)
            if old_ids[:2]!=new_ids[:2]:elite_changes.append(g)

    summaries.append(dict(run=directory.name,rows=len(rows),recomputed=len(scores),unavailable=dict(failures),new_score_changes=len(changed),valid_score_changes=sum(c['old_status']=='valid' for c in changed),changes=changed,new_structural_rejections=sum(r['old_status']=='valid' and not r['new_admissible'] for r in scores),ranking_changes_in_old_populations=ranking_changes,elite_changes_in_old_populations=elite_changes,undeclared_inverse_signature_rows=sum(bool(r['undeclared_inverse_properties']) for r in scores),old_best=best_id,recomputed_archived_best=selected['id'] if selected else None,recomputed_archived_best_F=selected['F'] if selected else None))
parser=argparse.ArgumentParser(description='Reassess archived candidates without models or Java')
parser.add_argument('--output',type=Path,default=None)
args=parser.parse_args()
output=args.output or Path(tempfile.mkdtemp(prefix='videocard-reassessment-'))
output.mkdir(parents=True,exist_ok=True)
print('Output:', output)
(output/'best-recalculation.json').write_text(json.dumps(dict(method='Pure Python structural reassessment of archived axiom strings; M1-M5 cross-checked against saved values; Q and prior semantic validity reused from original audits; no ML or Java',best=best),ensure_ascii=False,indent=2)+'\n')
(output/'all-recalculation-summary.json').write_text(json.dumps(dict(runs=summaries,total_rows=sum(s['rows'] for s in summaries),total_recomputed=sum(s['recomputed'] for s in summaries)),ensure_ascii=False,indent=2)+'\n')
for b in best:print(b['run'],b['id'],'B',b.get('B'),'S',b.get('S'),'new F',b.get('F'),'new admissible',b.get('new_admissible'),'error',b.get('error'))
for s in summaries:print(s['run'],'coverage',s['recomputed'],'/',s['rows'],'unavailable',s['unavailable'],'score changes',s['new_score_changes'],'oldbest',s['old_best'],'newbest',s['recomputed_archived_best'],'rankgen',s['ranking_changes_in_old_populations'],'elitegen',s['elite_changes_in_old_populations'],'newrejects',s['new_structural_rejections'])

from statistics import median
from lab4.optimizer.analysis import mann_whitney
model=[b['F'] for b in best if b['run'].startswith('model-')]
control=[b['F'] for b in best if b['run'].startswith('control-')]
test=mann_whitney(model,control)
statistics=dict(model_best=model,control_best=control,model_median=median(model),control_median=median(control),U=test['U'],p=test['p'],method=test['method'])
(output/'recalculation-statistics.json').write_text(json.dumps(statistics,ensure_ascii=False,indent=2)+'\n')

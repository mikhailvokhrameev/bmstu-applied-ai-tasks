import json,sys,argparse,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path.cwd()))
from lab4.optimizer.search import run,ControlGenerator,DEFAULTS
ns={};exec(Path(__file__).with_name('recalc_offline.py').read_text().split("root=Path('lab4/runs/series-v1')")[0],ns)
class Divergence(Exception):pass

def replay(directory,new_scores=False,relax_kind=False):
    rows=[json.loads(line) for line in (directory/'evaluations.jsonl').open()]
    cfg=json.loads((directory/'config.yaml').read_text());meta=json.loads((directory/'metadata.json').read_text())
    values=[ns['recalc'](row) for row in rows]
    position=0
    mismatch=None
    def check(delta):
        nonlocal mismatch
        row=rows[position]
        if delta!=row['delta']:
            mismatch=dict(id=position,generation=row['generation'],kind='generated delta differs from archived candidate')
            raise Divergence()
        score=values[position]['F'] if new_scores else row['F']
        status=row['status']
        code=row['code']
        if relax_kind and code=='CHANGE_KIND' and row['validation']['detail']=='new class needs existing named superclass':
            status='valid';code=None;score=values[position]['formula_F']
        return SimpleNamespace(status=status,code=code,F=score,detail='')
    def evaluated(candidate,validation,elapsed,error):
        nonlocal position,mismatch
        row=rows[position]
        for field in ['id','generation','parents','operator','delta']:
            actual=getattr(candidate,field);wanted=row[field]
            if field=='parents':actual=list(actual)
            if actual!=wanted:
                mismatch=dict(id=position,generation=row['generation'],kind=field+' differs',old=wanted,new=actual)
                raise Divergence()
        position+=1
    try:
        result=run({**DEFAULTS,'runtime':dict(control_generator=ControlGenerator(cfg['services']['inventory']),validate=check,on_evaluation=evaluated)},'control',meta['seed'])
    except Divergence:
        return dict(matched_evaluations=position,first_divergence=mismatch)
    return dict(matched_evaluations=position,first_divergence=None,best_id=result.best.id,best_F=result.best.F)

parser=argparse.ArgumentParser(description='Replay archived control selection without models')
parser.add_argument('--output',type=Path,default=None)
args=parser.parse_args()
output=args.output or Path(tempfile.mkdtemp(prefix='videocard-selection-'))/'selection-replay.json'
output.parent.mkdir(parents=True,exist_ok=True)
print('Output:', output)
results=[]
for directory in sorted(Path('lab4/runs/series-v1').glob('control-20[1-5]')):
    baseline=replay(directory)
    assert baseline['matched_evaluations']==170,(directory.name,baseline)
    updated=replay(directory,True)
    relaxed=replay(directory,True,True)
    row=dict(run=directory.name,old_trace_reproduced=baseline,new_numeric_scores_prior_validity=updated,new_scores_possible_relaxed_kind=relaxed)
    results.append(row);print(row)
output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')

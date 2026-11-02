"""python -m optimizer (from lab4) or python -m lab4.optimizer."""
import argparse
import json
from pathlib import Path
import sys
import uuid
from . import journal

def main(argv=None):
    parser=argparse.ArgumentParser(description='Ontology search journal / resume / model-free replay')
    commands=parser.add_subparsers(dest='command',required=True)
    run=commands.add_parser('run');run.add_argument('--config',required=True);run.add_argument('--mode',choices=['model','control'],required=True);run.add_argument('--seed',type=int,required=True);run.add_argument('--run-dir')
    run.add_argument('--phase',choices=['debug','main'],default='main',help='debug: 34 evaluations before T04; main: 170 evaluations after T04')
    resume=commands.add_parser('resume');resume.add_argument('--run-dir',required=True)
    replay=commands.add_parser('replay');replay.add_argument('--run-dir',required=True);replay.add_argument('--candidate',required=True,help='Active ID or audit-<32 hex>:ID')
    args=parser.parse_args(argv)
    try:
        if args.command=='replay':
            result=journal.replay(args.run_dir,args.candidate);print(json.dumps(result));return 0 if result['matches'] else 1
        if args.command=='run':
            directory=args.run_dir or str(Path('runs')/(args.mode+'-'+str(args.seed)+'-'+uuid.uuid4().hex[:12]))
            result=journal.start(args.config,args.mode,args.seed,directory,phase=args.phase)
        else:
            directory=args.run_dir;result=journal.resume(directory)
        print(json.dumps(dict(run_dir=directory,best=result.best.id,F=result.best.F,evaluations=len(result.evaluations))))
        return 0
    except (journal.JournalError,ValueError,RuntimeError,OSError) as error:
        print(str(error),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())

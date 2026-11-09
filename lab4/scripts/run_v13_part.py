"""Run exactly one v1.3 experiment part; completed parts are never rerun."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from lab4.optimizer_v13 import bridge, journal, validator
from lab4.optimizer_v13.metrics import BASELINE
from lab4.optimizer_v13.runtime import build_runtime
from lab4.optimizer_v13.proposals import OllamaModels


ROOT = Path(__file__).resolve().parents[2]
PARTS = ['debug'] + [f'model-{seed}' for seed in range(101, 106)] + [
    f'control-{seed}' for seed in range(201, 206)]


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as target:
        target.write(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def recover_delivered_responses(directory):
    """Reuse delivered responses from an unfinished generation, never resample.

    Checkpoint/RNG restoration still belongs to journal.resume. Every intercepted
    HTTP payload must exactly match the saved request, including its random seed.
    New requests begin only after all saved responses have been consumed.
    """
    checkpoint = json.loads((directory / 'checkpoint.json').read_text())
    committed = len(checkpoint['evaluations'])
    lines = (directory / 'evaluations.jsonl').read_text().splitlines()
    tail = [json.loads(line) for line in lines[committed:]]
    interruptions = (directory / 'interruptions.jsonl').read_text().splitlines()
    pending = json.loads(interruptions[-1])['attempts'] if interruptions else []
    entries = [attempt for row in tail for attempt in row.get('attempts', [])] + pending
    entries = [item for item in entries if item.get('response', {}).get('raw') is not None]
    if not entries:
        return None
    plan = dict(
        checkpoint_evaluations=committed, completed_tail_evaluations=len(tail),
        delivered_responses=len(entries),
        metadata_sha256=hashlib.sha256((directory / 'metadata.json').read_bytes()).hexdigest(),
        original_journal_sha256=hashlib.sha256((directory / 'evaluations.jsonl').read_bytes()).hexdigest(),
        entries=entries,
        policy='Exact recorded HTTP requests and raw delivered responses; no model call for replayed requests',
    )
    plan_path = directory / 'response-recovery-plan.json'
    if plan_path.exists():
        raise ValueError('A response recovery plan already exists; inspect recovery state before another resume')
    write_new(plan_path, plan)
    original = OllamaModels._post
    state = dict(delivered_responses=len(entries), reused_responses=0, new_generation_requests=0)

    def post(client, path, payload):
        if path == '/api/generate':
            if state['reused_responses'] < len(entries):
                expected = entries[state['reused_responses']]
                actual = dict(url=client.endpoint + path, payload=payload)
                if actual != expected['http_request']:
                    raise ValueError('Recorded generation request differs from restored RNG/context; refusing to resample')
                state['reused_responses'] += 1
                journal.atomic(directory / 'response-recovery-state.json', journal.encoded(state))
                return expected['response']['raw']
            state['new_generation_requests'] += 1
            journal.atomic(directory / 'response-recovery-state.json', journal.encoded(state))
        return original(client, path, payload)

    OllamaModels._post = post
    print(json.dumps(dict(event='recovering_delivered_responses', **{k: v for k, v in plan.items()
                                                                   if k not in ('entries',)})), flush=True)
    return state


def run_part(part, config_path, runs_root):
    if part not in PARTS:
        raise ValueError('Unknown part')
    config_path, runs_root = Path(config_path), Path(runs_root)
    debug = part == 'debug'
    mode, seed = ('model', 100) if debug else (part.split('-')[0], int(part.split('-')[1]))
    phase = 'debug' if debug else 'main'
    directory = runs_root / ('debug-100' if debug else part)
    expected = 34 if debug else 170
    timing = journal.read_timing(directory) if directory.exists() else None
    if timing and timing.get('completed_at') is not None:
        journal._metadata(directory)
        checkpoint = json.loads((directory / 'checkpoint.json').read_text())
        if len(checkpoint['evaluations']) != expected:
            raise ValueError('Completed part has an incorrect budget')
        print(json.dumps(dict(event='already_completed', part=part, evaluations=expected)), flush=True)
        return
    config = json.loads(config_path.read_text())
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    preflight = json.loads((ROOT / 'lab4/assessment/evidence/v13/preflight.json').read_text())
    if preflight['config_sha256'] != config_sha:
        raise ValueError('Prepared configuration changed')
    runtime = build_runtime(config['services'], seed, phase=phase)
    checker = runtime['duplicate_checker']
    count = 0
    if directory.exists() and (directory / 'checkpoint.json').exists():
        count = len(json.loads((directory / 'checkpoint.json').read_text())['evaluations'])
    started = time.monotonic()

    def check(delta):
        nonlocal count
        result = validator.validate(delta, duplicate_checker=checker)
        count += 1
        if count == 1 or count % 8 == 0 or count == expected:
            print(json.dumps(dict(event='evaluation', part=part, evaluations=count, budget=expected,
                                  F=result.F, B=result.B, S=result.S, status=result.status,
                                  code=result.code, cache_hit=result.cache_hit,
                                  elapsed_seconds=time.monotonic() - started)), flush=True)
        return result

    runtime['validate'] = check
    print(json.dumps(dict(event='starting', part=part, phase=phase, run_dir=str(directory))), flush=True)
    if directory.exists():
        if (directory / 'source-migration.json').exists():
            recover_delivered_responses(directory)
        result = journal.resume(directory, runtime=runtime)
    else:
        result = journal.start(config_path, mode, seed, directory, runtime=runtime, phase=phase)
    if len(result.evaluations) != expected:
        raise ValueError('Experiment part did not complete its budget')
    replay = journal.replay(directory, result.best.id)
    if replay['matches'] is not True:
        raise ValueError('Best-candidate replay failed')
    rows = [json.loads(line) for line in (directory / 'evaluations.jsonl').read_text().splitlines()]
    summary = dict(
        part=part, phase=phase, evaluations=expected, generation_count=len(result.generations) - 1,
        best=asdict(result.best), replay=replay,
        completed_utc=datetime.now(timezone.utc).isoformat(),
        timing=journal.read_timing(directory),
        engine_cache=bridge.cache_info(), validation_cache=validator.cache_info(),
        config_sha256=config_sha,
    )
    write_new(directory / 'part-summary.json', summary)
    if debug:
        valid_count = sum(row['status'] == 'valid' for row in rows)
        first = [row['attempts'][0] for row in rows if row.get('attempts')]
        correct = sum('response' in item and not item.get('parse_error')
                      and not item.get('service_error') for item in first)
        proof = dict(
            qualified=valid_count > 0 and correct > 0 and replay['matches'],
            methodology='videocard-lr4-v1.3',
            config_sha256=config_sha,
            debug_run=str(directory.relative_to(ROOT) if directory.is_absolute() else directory),
            debug_log_sha256=hashlib.sha256((directory / 'evaluations.jsonl').read_bytes()).hexdigest(),
            valid_candidates=valid_count,
            first_responses=dict(total=len(first), syntax_correct=correct),
            completed_evaluations=expected, completed_generations=3,
            baseline_metrics=asdict(BASELINE),
            preflight_sha256=hashlib.sha256((ROOT / 'lab4/assessment/evidence/v13/preflight.json').read_bytes()).hexdigest(),
            scope='Technical readiness after full v1.3 tests and the single debug run; experiment quality is assessed after both series',
        )
        write_new(ROOT / config['services']['qualification_path'], proof)
        if not proof['qualified']:
            raise ValueError('Debug did not qualify the new implementation; main series remain blocked')
    print(json.dumps(dict(event='completed', part=part, best_F=result.best.F,
                          best_id=result.best.id, evaluations=expected,
                          elapsed_seconds=time.monotonic() - started,
                          cache=validator.cache_info())), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=PARTS, required=True)
    parser.add_argument('--config', type=Path, default=ROOT / 'lab4/optimizer_v13/series-v13.json')
    parser.add_argument('--runs-root', type=Path, default=ROOT / 'lab4/runs/series-v13')
    args = parser.parse_args()
    run_part(args.part, args.config, args.runs_root)


if __name__ == '__main__':
    main()

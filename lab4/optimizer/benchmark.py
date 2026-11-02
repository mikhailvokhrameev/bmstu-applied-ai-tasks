"""First-response model comparison before T04; never starts an accepted series."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from .bridge import CORE, CORE_SHA256, evaluate
from .metrics import BASELINE, compute_metrics, fitness
from .prepare import read_api, verify_weights, write_json
from .proposals import ModelResponse, OllamaModels, ProposalError, parse_proposal, render_prompt


def benchmark(models, endpoint, models_dir, output, count=10):
    if type(count) is not int or count < 1:
        raise ValueError('count must be a positive integer')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    baseline = evaluate(CORE, [], [])
    context = dict(ontology_manchester=baseline['manchester'],
                   metrics=asdict(compute_metrics(baseline['counts'])),
                   relative=fitness(compute_metrics(baseline['counts']), BASELINE).relative,
                   added_axioms=[], removed_axioms=[], violations=baseline['violations'])
    prompt = render_prompt(context)
    tags = read_api(endpoint, '/api/tags')
    version = read_api(endpoint, '/api/version')
    summary = dict(kind='preliminary first-response benchmark; not T04',
                   started_utc=datetime.now(timezone.utc).isoformat(),
                   core_sha256=CORE_SHA256,
                   prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                   seeds=list(range(1000, 1000 + count)), server_version=version,
                   fixed_options=dict(temperature=.7, top_p=.95, num_predict=2000, num_ctx=32768),
                   models=[])
    write_json(output / 'protocol.json', summary)
    for model in models:
        weights = verify_weights(model, models_dir, tags)
        directory = output / model.replace(':', '-')
        directory.mkdir()
        write_json(directory / 'weights.json', weights)
        client = OllamaModels(model, 'unused-in-format-benchmark', endpoint)
        rows = []
        for seed in summary['seeds']:
            client.seed = seed
            row = dict(model=model, seed=seed, request=dict(
                url=endpoint.rstrip('/') + '/api/generate',
                payload=dict(model=model, prompt=prompt, stream=False, format='json',
                             options=dict(**summary['fixed_options'], seed=seed))))
            started = time.perf_counter()
            try:
                response = client.propose(context)
                row['response'] = asdict(response)
                try:
                    proposal = parse_proposal(response.text)
                    row.update(syntax_valid=True, proposal=asdict(proposal))
                except ProposalError as error:
                    row.update(syntax_valid=False, parse_error=str(error),
                               parse_diagnostic=getattr(error, 'diagnostic', str(error)))
            except Exception as error:
                response = getattr(error, 'response', None)
                if isinstance(response, ModelResponse):
                    row['response'] = asdict(response)
                row['service_error'] = type(error).__name__ + ': ' + str(error)
                row['elapsed_seconds'] = time.perf_counter() - started
                write_json(directory / f'{seed}.json', row)
                raise
            row['elapsed_seconds'] = time.perf_counter() - started
            write_json(directory / f'{seed}.json', row)
            rows.append(row)
            print(json.dumps(dict(model=model, seed=seed, syntax_valid=row['syntax_valid'],
                                  seconds=round(row['elapsed_seconds'], 3))), flush=True)
        seconds = sum(row['elapsed_seconds'] for row in rows)
        result = dict(model=model, weights=weights, count=count,
                      first_response_correct=sum(row['syntax_valid'] for row in rows),
                      first_response_fraction=sum(row['syntax_valid'] for row in rows)/count,
                      wall_evaluation_seconds=seconds, seconds_per_request=seconds/count,
                      limitation='Baseline-only format probes; no candidate acceptance or T04 attestation')
        summary['models'].append(result)
        write_json(directory / 'summary.json', result)
    summary['completed_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:11435')
    parser.add_argument('--models-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=10)
    args = parser.parse_args()
    benchmark(args.models, args.endpoint, args.models_dir, args.output, args.count)


if __name__ == '__main__':
    main()

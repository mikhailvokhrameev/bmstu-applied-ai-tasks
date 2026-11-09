"""Verify the existing pinned models once and freeze a v1.3 experiment config."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from lab4.optimizer.prepare import (
    assess_pairs, file_sha256, load_pairs, ontology_inventory, read_api,
    verify_sentence_transformer, verify_weights,
)
from lab4.optimizer.proposals import OllamaModels
from lab4.optimizer_v13.metrics import BASELINE, BASELINE_COUNTS, BASELINE_GRAPH


ROOT = Path(__file__).resolve().parents[2]


def prepare(spec, config_path, evidence_path):
    config_path, evidence_path = Path(config_path), Path(evidence_path)
    if config_path.exists() or evidence_path.exists():
        raise FileExistsError('Refusing to replace a prepared configuration or evidence')
    previous = json.loads((ROOT / 'lab4/optimizer/series-v1.yaml').read_text())
    services = previous['services']
    endpoint, embedding_endpoint = services['endpoint'], services['embedding_endpoint']
    version = read_api(endpoint, '/api/version')
    if version.get('version') != services['server_version']:
        raise ValueError('The pinned Ollama version changed')
    tags = read_api(endpoint, '/api/tags')
    weights = verify_weights(services['model'], ROOT / '.local-runtime/models', tags)
    if weights['sha256'] != services['model_sha256']:
        raise ValueError('The pinned generation weights changed')
    show = read_api(embedding_endpoint, '/api/show', {'model': services['embedding_model']})
    embeddings = verify_sentence_transformer(show, services['embedding_model'], services['embedding_revision'])
    if embeddings['sha256'] != services['embedding_sha256']:
        raise ValueError('The pinned embedding snapshot changed')
    inventory, entities = ontology_inventory()
    if inventory != services['inventory'] or entities != services['entities']:
        raise ValueError('The original ontology inventory changed')
    pair_paths = [ROOT / 'lab4/assessment/concept_pairs_context.csv',
                  ROOT / 'lab4/assessment/concept_pairs_holdout.csv']
    pairs = [load_pairs(path) for path in pair_paths]
    texts = list(dict.fromkeys(text for group in pairs for pair in group
                               for text in (pair['left'], pair['right'])))
    client = OllamaModels(services['model'], services['embedding_model'], endpoint,
                         embedding_endpoint=embedding_endpoint,
                         embedding_instruction=services['embedding_instruction'])
    vectors = dict(zip(texts, client.embed(texts)))
    assessments = [assess_pairs(group, lambda values: [vectors[text] for text in values],
                               services['duplicate_threshold']) for group in pairs]
    if any(result['errors'] for result in assessments):
        raise ValueError('Pinned embedding threshold failed the control pairs')
    services.update(
        methodology='videocard-lr4-v1.3',
        spec_sha256=file_sha256(spec),
        baseline_counts=BASELINE_COUNTS, baseline_graph=BASELINE_GRAPH,
        baseline_metrics=asdict(BASELINE),
        generation_options=dict(temperature=.7, top_p=.95, num_predict=2000, num_ctx=32768),
        acceptance_approved=True,
        qualification_path='lab4/assessment/evidence/v13/qualification.json',
        qualification_scope='Pinned models verified; main runs additionally require the completed v1.3 debug proof',
        main_blockers=[],
    )
    raw = (json.dumps(previous, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    evidence = dict(
        schema=1, verified_at=datetime.now(timezone.utc).isoformat(),
        spec_path=str(Path(spec).resolve()), spec_sha256=services['spec_sha256'],
        config_sha256=hashlib.sha256(raw).hexdigest(),
        model_weights=weights, embedding_snapshot=embeddings, api_version=version,
        duplicate_threshold=services['duplicate_threshold'],
        control_pair_assessments=[dict(path=str(path.relative_to(ROOT)), sha256=file_sha256(path),
                                       assessment=result) for path, result in zip(pair_paths, assessments)],
        baseline_counts=BASELINE_COUNTS, baseline_graph=BASELINE_GRAPH,
        baseline_metrics=asdict(BASELINE),
        source_of_parameters='Unchanged model identities and generation parameters from series-v1; new v1.3 metrics and prompt',
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open('xb') as target:
        target.write(raw)
    with evidence_path.open('x', encoding='utf-8') as target:
        target.write(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return dict(config=str(config_path), config_sha256=evidence['config_sha256'],
                pair_errors=[item['errors'] for item in assessments], weights_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--config', default='lab4/optimizer_v13/series-v13.json', type=Path)
    parser.add_argument('--evidence', default='lab4/assessment/evidence/v13/preflight.json', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.spec, args.config, args.evidence)))


if __name__ == '__main__':
    main()

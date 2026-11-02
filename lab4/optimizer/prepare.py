"""Prepare an auditable debug configuration from local weights and live APIs.

This command never approves T04 or opens the main experiment series.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .bridge import CORE, CORE_SHA256, ROOT
from .proposals import OllamaModels, assess_pairs
from .search import DEFAULTS
from .paths import ASSESSMENT


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_api(endpoint, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    request = Request(endpoint.rstrip('/') + path, data=data,
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=180) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError('Expected API object: ' + path)
    return result


def ontology_inventory(path=CORE):
    """Read schema annotations and explicit operands for control templates.

    Domain/range maps contain only directly named declared classes. Teaching
    individuals are separate operands and never enter semantic entity matching.
    """
    ns = dict(rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#',
              rdfs='http://www.w3.org/2000/01/rdf-schema#',
              owl='http://www.w3.org/2002/07/owl#')
    types = {'Class': ('classes', 'Class'),
             'ObjectProperty': ('object_properties', 'ObjectProperty'),
             'DatatypeProperty': ('data_properties', 'DataProperty')}
    inventory = {group: [] for group, _ in types.values()}
    entities = []
    seen = set()
    root = ET.parse(path).getroot()
    for element in root:
        local = element.tag.removeprefix('{' + ns['owl'] + '}')
        if local not in types:
            continue
        iri = element.get('{' + ns['rdf'] + '}about')
        if not iri or not iri.startswith('https://example.org/ontologies/videocard#'):
            continue
        group, category = types[local]
        if (category, iri) in seen:
            raise ValueError('Repeated ontology declaration: ' + iri)
        seen.add((category, iri))
        annotation = {}
        for name in ('label', 'comment'):
            values = [node.text.strip() for node in element.findall('rdfs:' + name, ns)
                      if (node.text or '').strip() and
                      node.get('{http://www.w3.org/XML/1998/namespace}lang', '').lower() == 'ru']
            if not values:
                raise ValueError('Missing Russian ' + name + ': ' + iri)
            annotation[name] = sorted(values)[0]
        inventory[group].append('<' + iri + '>')
        entities.append(dict(iri=iri, category=category, **annotation))
    if not all(inventory.values()):
        raise ValueError('Incomplete ontology inventory')
    inventory = {key: sorted(values) for key, values in inventory.items()}
    classes = set(inventory['classes'])
    resource = '{' + ns['rdf'] + '}resource'
    for relation in ('domain', 'range'):
        mapping = {}
        for element in root.findall('owl:ObjectProperty', ns):
            iri = element.get('{' + ns['rdf'] + '}about')
            key = '<' + iri + '>' if iri else None
            if key not in inventory['object_properties']:
                continue
            values = {'<' + node.get(resource) + '>'
                      for node in element.findall('rdfs:' + relation, ns)
                      if node.get(resource) and '<' + node.get(resource) + '>' in classes}
            mapping[key] = sorted(values)
        inventory['object_property_' + relation + 's'] = dict(sorted(mapping.items()))
    teaching_iri = 'https://example.org/ontologies/videocard#VideoCardModel'
    if '<' + teaching_iri + '>' in classes:
        inventory['teaching_class'] = '<' + teaching_iri + '>'
    individuals = set()
    for element in root.findall('owl:NamedIndividual', ns):
        iri = element.get('{' + ns['rdf'] + '}about', '')
        if (re.fullmatch(r'https://example\.org/ontologies/videocard#U0[1-8]', iri) and
                any(node.get(resource) == teaching_iri for node in element.findall('rdf:type', ns))):
            individuals.add('<' + iri + '>')
    inventory['individuals'] = sorted(individuals)
    return inventory, sorted(entities, key=lambda entity: (entity['category'], entity['iri']))


def verify_weights(model, models_dir, tags):
    """Match the server manifest digest, then hash the actual model layer."""
    # The required local models are in Ollama's default library registry.
    if not re.fullmatch(r'[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+', model):
        raise ValueError('Expected explicit library model:tag: ' + model)
    name, tag = model.split(':')
    path = Path(models_dir) / 'manifests/registry.ollama.ai/library' / name / tag
    raw = path.read_bytes()
    manifest_sha256 = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(raw)
    matches = [entry for entry in tags.get('models', [])
               if entry.get('name') == model or entry.get('model') == model]
    if len(matches) != 1:
        raise ValueError('Server/local manifest digest mismatch: ' + model)
    api_digest = matches[0].get('digest', '').removeprefix('sha256:')
    registry = None
    if api_digest != manifest_sha256:
        # New Ollama versions preserve the original registry manifest as a
        # layer in a local wrapper. Tags still advertises the original digest.
        media_type = 'application/vnd.docker.distribution.manifest.v2+json'
        descriptors = [layer for layer in manifest['layers']
                       if layer.get('mediaType') == media_type]
        if len(descriptors) != 1 or descriptors[0].get('digest') != 'sha256:' + api_digest:
            raise ValueError('Server/local manifest digest mismatch: ' + model)
        descriptor = descriptors[0]
        if not re.fullmatch(r'[0-9a-f]{64}', api_digest):
            raise ValueError('Invalid registry manifest digest: ' + model)
        registry_path = Path(models_dir) / 'blobs' / ('sha256-' + api_digest)
        registry_raw = registry_path.read_bytes()
        if hashlib.sha256(registry_raw).hexdigest() != api_digest or len(registry_raw) != descriptor['size']:
            raise ValueError('Registry manifest checksum/size mismatch: ' + model)
        registry = json.loads(registry_raw)
        local_layers = [layer for layer in manifest['layers']
                        if layer.get('mediaType') != media_type]
        if (registry.get('config') != manifest.get('config') or
                registry.get('layers') != local_layers or
                registry.get('schemaVersion') != manifest.get('schemaVersion') or
                registry.get('mediaType') != manifest.get('mediaType')):
            raise ValueError('Registry/local manifest content mismatch: ' + model)
    layers = [layer for layer in manifest['layers']
              if layer.get('mediaType') == 'application/vnd.ollama.image.model']
    if len(layers) != 1:
        raise ValueError('Expected exactly one weight layer: ' + model)
    layer = layers[0]
    digest = layer.get('digest', '')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('Invalid weight digest: ' + model)
    blob = Path(models_dir) / 'blobs' / digest.replace(':', '-')
    actual = file_sha256(blob)
    if actual != digest.split(':')[1] or blob.stat().st_size != layer['size']:
        raise ValueError('Weight checksum/size mismatch: ' + model)
    return dict(model=model, sha256=actual, bytes=blob.stat().st_size,
                manifest_sha256=manifest_sha256, api_manifest_sha256=api_digest,
                registry_manifest=registry, manifest=manifest)


def calibrate_pairs(pairs, embed):
    pairs = list(pairs)
    original = assess_pairs(pairs, embed, threshold=.90)
    positives = [row['score'] for row in original['rows'] if row['expected']]
    negatives = [row['score'] for row in original['rows'] if not row['expected']]
    minimum_positive, maximum_negative = min(positives), max(negatives)
    threshold = .90
    blockers = []
    if not original['analyst_approved']:
        blockers.append('Pair labels are not approved')
    if original['errors']:
        lower, upper = max(0., maximum_negative), min(1., minimum_positive)
        candidate = (lower + upper) / 2
        if lower <= upper and maximum_negative < candidate <= minimum_positive:
            threshold = candidate
            reason = 'Midpoint of separating interval (max_negative, min_positive]'
        else:
            reason = 'No separating threshold in [0, 1]; retain 0.90 for debug diagnosis'
            blockers.append('No single admissible threshold separates all labelled pairs')
    else:
        reason = 'Original threshold 0.90 has no errors on the 20 labelled pairs'
    rows = [dict(row, duplicate=row['score'] >= threshold) for row in original['rows']]
    return dict(initial_threshold=.90, initial_errors=original['errors'],
                chosen_threshold=threshold, errors=sum(row['expected'] != row['duplicate'] for row in rows),
                min_positive=minimum_positive, max_negative=maximum_negative,
                rows=rows, analyst_approved=original['analyst_approved'],
                review_performed_by='AI; see assessment/AI_REVIEW.md',
                decision=reason, main_blockers=blockers,
                limitation=('20 ontology-grounded label.comment pairs, including cross-category negatives; '
                            'all pairs embedding-scored without category skips; semisynthetic definitions'
                            if all('left_comment' in pair for pair in pairs) else
                            '20 short phrase pairs; runtime uses same-category label.comment texts'))


def load_pairs(path):
    with Path(path).open(encoding='utf-8', newline='') as source:
        pairs = list(csv.DictReader(source))
    if len({pair['id'] for pair in pairs}) != len(pairs):
        raise ValueError('Repeated pair ID')
    contextual = any('left_label' in pair or 'right_label' in pair for pair in pairs)
    if contextual:
        for pair in pairs:
            for side in ('left', 'right'):
                if pair[side] != pair[side + '_label'] + '. ' + pair[side + '_comment']:
                    raise ValueError('Context pair must embed exact label.comment text')
                if pair[side + '_category'] not in ('Class', 'ObjectProperty', 'DataProperty'):
                    raise ValueError('Unknown context pair category')
                if not pair[side + '_iri'].startswith('https://example.org/ontologies/videocard#'):
                    raise ValueError('Unknown context pair IRI')
    return pairs


def context_metadata(show):
    info = show.get('model_info', {})
    architecture = info.get('general.architecture')
    key = str(architecture) + '.context_length'
    value = info.get(key)
    supported = type(value) is int and value >= 32000
    return dict(architecture=architecture, context_length_key=key,
                advertised_context_length=value, advertised_at_least_32000=supported,
                actual_context_verified=False,
                limitation='API metadata advertises capacity; no long-context inference was measured')


def verify_sentence_transformer(show, model, revision):
    """Independently hash the served local snapshot; do not trust API hashes alone."""
    if show.get('model') != model or show.get('backend') != 'sentence-transformers':
        raise ValueError('Embedding backend/model mismatch')
    if not re.fullmatch(r'[0-9a-f]{40}', revision or '') or show.get('commit_sha') != revision:
        raise ValueError('Explicit pinned embedding revision required')
    snapshot = Path(show['snapshot']).resolve(strict=True)
    if not snapshot.is_relative_to((ROOT / '.local-runtime/hf').resolve()):
        raise ValueError('Embedding snapshot must be inside project HF storage')
    record = json.loads((snapshot / '.embedding-snapshot.json').read_text())
    if record.get('repo') != model or record.get('commit_sha') != revision:
        raise ValueError('Embedding provenance mismatch')
    files = show.get('files')
    if not isinstance(files, list) or files != record.get('files') or not files:
        raise ValueError('Embedding file inventory mismatch')
    actual_names = {path.relative_to(snapshot).as_posix() for path in snapshot.rglob('*')
                    if path.is_file() and '.cache' not in path.relative_to(snapshot).parts
                    and path.name != '.embedding-snapshot.json'}
    declared_names = [item['path'] for item in files]
    if len(set(declared_names)) != len(declared_names) or actual_names != set(declared_names):
        raise ValueError('Embedding actual asset inventory mismatch')
    for item in files:
        relative = Path(item['path'])
        path = (snapshot / relative).resolve(strict=True)
        if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(snapshot):
            raise ValueError('Invalid embedding asset path')
        if path.stat().st_size != item['bytes'] or file_sha256(path) != item['sha256']:
            raise ValueError('Embedding asset checksum/size mismatch: ' + item['path'])
    weights = [item for item in files if Path(item['path']).suffix in ('.safetensors', '.bin', '.pt', '.pth')]
    if not weights or weights != show.get('weights'):
        raise ValueError('Embedding weight inventory mismatch')
    fingerprint = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if fingerprint != show.get('snapshot_sha256'):
        raise ValueError('Embedding snapshot fingerprint mismatch')
    return dict(model=model, backend='sentence-transformers', revision=revision,
                sha256=fingerprint, sha256_kind='complete inference asset manifest',
                files=files, weights=weights, snapshot=str(snapshot),
                device=show['device'], max_seq_length=show['max_seq_length'], packages=show['packages'])


def prepare(endpoint, model, embedding_model, models_dir, pairs_path=None, holdout_path=None,
            embedding_backend='ollama', embedding_endpoint=None, embedding_revision=None,
            embedding_instruction=''):
    pairs_path = Path(pairs_path or ASSESSMENT / 'concept_pairs.csv')
    pairs = load_pairs(pairs_path)
    holdout = load_pairs(holdout_path) if holdout_path is not None else None
    if file_sha256(CORE) != CORE_SHA256:
        raise ValueError('Original ontology checksum mismatch')
    version = read_api(endpoint, '/api/version')
    if not isinstance(version.get('version'), str) or not version['version']:
        raise ValueError('Missing Ollama server version')
    tags = read_api(endpoint, '/api/tags')
    model_show = read_api(endpoint, '/api/show', {'model': model})
    embedding_endpoint = embedding_endpoint or endpoint
    embedding_show = read_api(embedding_endpoint, '/api/show', {'model': embedding_model})
    model_weights = verify_weights(model, models_dir, tags)
    if embedding_backend == 'ollama':
        embedding_tags = tags if embedding_endpoint == endpoint else read_api(embedding_endpoint, '/api/tags')
        embedding_weights = verify_weights(embedding_model, models_dir, embedding_tags)
    elif embedding_backend == 'sentence-transformers':
        embedding_weights = verify_sentence_transformer(embedding_show, embedding_model, embedding_revision)
    else:
        raise ValueError('Unsupported embedding backend')
    inventory, entities = ontology_inventory()
    models = OllamaModels(model, embedding_model, endpoint, embedding_endpoint=embedding_endpoint,
                          embedding_instruction=embedding_instruction)
    calibration = calibrate_pairs(pairs, models.embed)
    holdout_assessment = (assess_pairs(holdout, models.embed, calibration['chosen_threshold'])
                          if holdout is not None else None)
    context = context_metadata(model_show)
    blockers = list(calibration['main_blockers'])
    if not context['advertised_at_least_32000']:
        blockers.append('Model API metadata does not confirm context capacity >=32000')
    blockers.extend(['T04 debug first-response correctness has not been measured',
                     'Actual long-context inference has not been measured',
                     'Russian generation and eight-hour run budget have not been qualified'])
    services = dict(model=model, embedding_model=embedding_model,
                    model_sha256=model_weights['sha256'], embedding_sha256=embedding_weights['sha256'],
                    server_version=version['version'], endpoint=endpoint.rstrip('/'),
                    embedding_endpoint=embedding_endpoint.rstrip('/'), embedding_backend=embedding_backend,
                    embedding_revision=embedding_revision,
                    embedding_instruction=embedding_instruction,
                    acceptance_approved=False, duplicate_threshold=calibration['chosen_threshold'],
                    inventory=inventory, entities=entities, main_blockers=blockers,
                    core_sha256=CORE_SHA256, concept_pairs_sha256=file_sha256(pairs_path),
                    concept_pairs_path=str(pairs_path),
                    context_verification=context)
    evidence = dict(schema=1, prepared_at=datetime.now(timezone.utc).isoformat(),
                    api=dict(version=version, tags=tags, model_show=model_show, embedding_show=embedding_show),
                    weights=dict(model=model_weights, embedding_model=embedding_weights),
                    calibration=calibration, core_sha256=CORE_SHA256,
                    calibration_inputs=pairs,
                    concept_pairs_sha256=services['concept_pairs_sha256'],
                    embedding_backend=embedding_backend, embedding_endpoint=embedding_endpoint,
                    embedding_instruction=embedding_instruction,
                    context_verification=context, acceptance_approved=False, main_blockers=blockers)
    if holdout is not None:
        evidence['holdout'] = dict(assessment=holdout_assessment, inputs=holdout,
                                   sha256=file_sha256(holdout_path),
                                   protocol='Fixed calibration threshold; holdout does not retune it')
    return dict(**DEFAULTS, services=services), evidence


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', default='http://127.0.0.1:11434')
    parser.add_argument('--model', required=True)
    parser.add_argument('--embedding-model', required=True)
    parser.add_argument('--models-dir', required=True, type=Path)
    parser.add_argument('--embedding-backend', choices=['ollama', 'sentence-transformers'], default='ollama')
    parser.add_argument('--embedding-endpoint', help='Separate local embedding endpoint, if used')
    parser.add_argument('--embedding-revision', help='Required exact HF commit for sentence-transformers')
    parser.add_argument('--embedding-instruction', default='', help='One model task instruction applied uniformly to every text')
    parser.add_argument('--pairs', type=Path, help='Frozen calibration CSV; default is original short phrases')
    parser.add_argument('--holdout-pairs', type=Path, help='Optional frozen holdout evaluated without threshold tuning')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    evidence_path = args.evidence_dir / 'preflight.json'
    if args.output.exists() or evidence_path.exists():
        print('Output/evidence already exists; choose new paths to preserve previous evidence', file=sys.stderr)
        return 2
    try:
        config, evidence = prepare(args.endpoint, args.model, args.embedding_model, args.models_dir,
                                   pairs_path=args.pairs, holdout_path=args.holdout_pairs,
                                   embedding_backend=args.embedding_backend,
                                   embedding_endpoint=args.embedding_endpoint,
                                   embedding_revision=args.embedding_revision,
                                   embedding_instruction=args.embedding_instruction)
        write_json(evidence_path, evidence)
        write_json(args.output, config)
    except (OSError, ValueError, KeyError, TypeError) as error:
        failure_path = args.evidence_dir / 'failure.json'
        if not failure_path.exists():
            write_json(failure_path, dict(error=type(error).__name__, detail=str(error), acceptance_approved=False))
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(dict(config=str(args.output), evidence=str(evidence_path),
                          acceptance_approved=False, duplicate_threshold=config['services']['duplicate_threshold']),
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

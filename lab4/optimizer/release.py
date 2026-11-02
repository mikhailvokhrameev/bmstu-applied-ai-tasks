"""Validated, unaccepted RDF/XML exports and isolated engine acceptance checks.

An export is a technical artifact, never an expert decision or a GUI result.
"""
import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from .bridge import CORE, CORE_SHA256, LIB, ROOT, _run
from .validator import validate
from .paths import HARNESS, EXPECTED


class ReleaseError(RuntimeError):
    pass


def _check_core():
    if hashlib.sha256(CORE.read_bytes()).hexdigest() != CORE_SHA256:
        raise ReleaseError('CORE_CHECKSUM: original ontology changed')


def _java(request):
    sources = [Path(__file__).parent / 'owl_bridge/OntologyRelease.java',
               Path(__file__).parent / 'owl_bridge/OntologyEvaluator.java',
               *sorted((HARNESS / 'src').glob('*.java'))]
    key = hashlib.sha256(str(ROOT).encode() + b''.join(path.read_bytes() for path in sources)).hexdigest()[:20]
    build = Path(tempfile.gettempdir()) / ('videocard-release-' + key)
    build.mkdir(exist_ok=True)
    if not (build / 'OntologyRelease.class').exists():
        _run(['javac', '-encoding', 'UTF-8', '-cp', str(LIB / '*'), '-d', str(build),
              *map(str, sources)])
    raw = _run(['java', '-Dfile.encoding=UTF-8', '-Dslf4j.internal.verbosity=ERROR',
                '-cp', str(build) + ':' + str(LIB / '*'), 'OntologyRelease'],
               input=json.dumps(request, ensure_ascii=False))
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ReleaseError('Invalid release engine response')
    return result


def export_candidate(delta, output, version='2.0.0', *, duplicate_checker=None):
    """Validate with the caller's real semantic checker, then write a new file.

    The caller must record expert decisions separately. This API does not attest
    series targets, accept those decisions, or declare an ontology released.
    """
    output = Path(output)
    if version != '2.0.0':
        raise ValueError('Only the specified version 2.0.0 is supported')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output already exists: ' + str(output))
    if not callable(duplicate_checker):
        raise ValueError('A real duplicate_checker is required')
    if not isinstance(delta, dict) or set(delta) != {'add', 'remove'}:
        raise ValueError('Expected cumulative add/remove delta')
    _check_core()
    validation = validate(delta, duplicate_checker=duplicate_checker)
    if validation.status != 'valid':
        raise ReleaseError(f'Candidate is {validation.status}: {validation.code}: {validation.detail}')
    result = _java(dict(command='export', core=str(CORE), core_sha256=CORE_SHA256,
                        delta=delta, version=version))
    content = base64.b64decode(result.pop('document_base64'), validate=True)
    content.decode('utf-8', errors='strict')
    if (result.get('roundtrip_verified') is not True or result.get('core_preserved') is not True
            or hashlib.sha256(content).hexdigest() != result.get('sha256')):
        raise ReleaseError('Export verification failed')
    _check_core()
    with output.open('xb') as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())
    return dict(**result, output=str(output), status='exported-unaccepted', accepted=False,
                validation=asdict(validation), gui_verified=False,
                limitation='Technical export only; expert manifest, series targets, Protégé and OOPS remain separate checks')


def run_acceptance(ontology, evidence_dir):
    """Run shared T04–T10 on an isolated copy; never call these GUI checks."""
    _check_core()
    ontology = Path(ontology).resolve(strict=True)
    root = Path(evidence_dir)
    root.mkdir(parents=True, exist_ok=False)
    (root / 'ontology').mkdir()
    (root / 'tests').mkdir()
    shutil.copyfile(ontology, root / 'ontology/videocard.owl')
    shutil.copyfile(EXPECTED, root / 'tests/expected.json')
    result = _java(dict(command='acceptance', root=str(root.resolve())))
    _check_core()
    result.update(source=str(ontology), evidence_dir=str(root), gui_verified=False,
                  accepted=False, limitation='Local OWL API/HermiT checks only; no Protégé GUI or OOPS result')
    with (root / 'acceptance.json').open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ontology', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_acceptance(args.ontology, args.evidence_dir)
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Build the canonical delivery only from an explicitly accepted, verified result.

This does not replace the working-material packager. Runtime/source bytes are
copied unchanged; only relative Markdown link destinations may be adapted and
are recorded explicitly. paths.py supports the delivery layout.
"""
import argparse
import hashlib
import json
import math
import posixpath
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile
from urllib.parse import quote, unquote, urlsplit, urlunsplit

_here = Path(__file__).resolve()
_project = _here.parent.parent if (_here.parent.parent / 'DELIVERY_MANIFEST.json').is_file() else _here.parents[2]
sys.path.insert(0, str(_project))
from lab4.optimizer import analysis
from lab4.optimizer.bridge import evaluate
from lab4.optimizer.metrics import compute_metrics, fitness, BASELINE


LAYOUT = 'videocard-nn-delivery-v1'
DOCS = {'PROGRAM.md', 'OPERATOR.md', 'EXPERIMENTS.md', 'ONTOLOGY.md',
        'ACCEPTANCE_STATUS.md', 'assessment/METHODOLOGY.md'}
SKIP_DIRS = {'__pycache__', '.pytest_cache', '.venv', '.git', 'lib', 'out', 'cache', 'models'}
SKIP_SUFFIXES = {'.pyc', '.class', '.jar', '.zip', '.part', '.bin', '.gguf', '.safetensors'}
SHIM = b'"""Compatibility namespace; implementation files have a single canonical copy."""\nfrom pathlib import Path\n_root = Path(__file__).resolve().parent.parent\n__path__ = [str(_root), str(_root / "docs")]\n'


def safe_name(value):
    return (isinstance(value, str) and bool(value) and '\\' not in value
            and not PurePosixPath(value).is_absolute() and ':' not in value.split('/')[0]
            and all(part not in ('', '.', '..') for part in value.split('/')))


def source(root, value):
    root = Path(root).resolve(strict=True)
    if not safe_name(value):
        raise ValueError('Expected a safe relative project path')
    path = root / value
    if not path.resolve(strict=True).is_relative_to(root):
        raise ValueError('Source escapes the project: ' + value)
    current = root
    for part in PurePosixPath(value).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink source is unsupported: ' + value)
    return path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_layout(root):
    marker = root / 'DELIVERY_MANIFEST.json'
    if marker.is_file():
        if json.loads(marker.read_text(encoding='utf-8')).get('layout') != LAYOUT:
            raise ValueError('Unsupported source delivery layout')
        return dict(optimizer='optimizer', tests='tests', harness='tests/harness',
                    assessment='docs/assessment', core='ontology/1.0.0/videocard.owl',
                    expected='tests/expected.json', specification='docs/tz_videokarta_lr4_nn_v1.0.docx',
                    requirements='requirements.txt', script='scripts/delivery.py')
    return dict(optimizer='lab4/optimizer', tests='lab4/tests', harness='lab2/tests/harness',
                assessment='lab4/assessment', core='lab2/ontology/videocard.owl',
                expected='lab2/tests/expected.json', specification='lab4/tz_videokarta_lr4_nn_v1.0.docx',
                requirements='lab4/requirements.txt', script='lab4/scripts/delivery.py')


def qualify(root, manifest):
    if manifest.get('schema') != 1 or manifest.get('accepted') is not True:
        raise ValueError('An explicit accepted schema-1 manifest is required')
    if any(manifest.get('checks', {}).get(f'T{i:02d}') != 'passed' for i in range(1, 12)):
        raise ValueError('T01–T11 must be explicitly passed before delivery')
    final = source(root, manifest['final_ontology'])
    if sha256(final) != manifest['final_sha256']:
        raise ValueError('Final ontology checksum mismatch')
    import xml.etree.ElementTree as ET
    ns = dict(owl='http://www.w3.org/2002/07/owl#', rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    header = ET.parse(final).getroot().find('owl:Ontology', ns)
    if (header is None or header.get('{' + ns['rdf'] + '}about') != 'https://example.org/ontologies/videocard'
            or header.find('owl:versionIRI', ns) is None
            or header.find('owl:versionIRI', ns).get('{' + ns['rdf'] + '}resource') != 'https://example.org/ontologies/videocard/2.0.0'
            or header.find('owl:versionInfo', ns) is None or header.find('owl:versionInfo', ns).text != '2.0.0'):
        raise ValueError('Expected the original ontology IRI and version IRI 2.0.0')
    if ET.parse(final).getroot().findall('.//owl:imports', ns):
        raise ValueError('External imports are forbidden in the final ontology')
    expert = json.loads(source(root, manifest['expert_review']).read_text(encoding='utf-8'))
    score = expert.get('validation', {}).get('F')
    if (expert.get('approved') is not True or expert.get('final_sha256') != manifest['final_sha256']
            or expert.get('validation', {}).get('status') != 'valid'
            or not isinstance(score, (int, float)) or isinstance(score, bool)
            or not math.isfinite(score) or score < 1.25):
        raise ValueError('Approved expert review with valid final F>=1.25 and matching SHA-256 is required')
    runs = manifest.get('runs', [])
    if not isinstance(runs, list) or len(runs) != 10 or len(set(runs)) != 10:
        raise ValueError('Exactly ten distinct main run paths are required')
    results = [analysis.analyze_run(source(root, name), replay=True) for name in runs]
    summary = analysis.summarize(results)
    if not all(summary['targets'].values()):
        raise ValueError('The accepted series must satisfy all fitness targets')
    clock = manifest.get('performance_clock', 'series_wall_clock')
    if clock == 'series_wall_clock':
        if any(item.get('within_eight_hours') is not True for item in summary['series_timing'].values()):
            raise ValueError('Each five-run series must actually fit eight hours')
    elif clock == 'active_sessions':
        # A performance measurement may explicitly use recorded process-session
        # durations. The original calendar spans remain unchanged in the report.
        for mode in ('model', 'control'):
            durations = [item.get('active_seconds') for item in results if item['mode'] == mode]
            if (len(durations) != 5 or any(type(value) not in (int, float)
                    or not math.isfinite(value) or value < 0 for value in durations)
                    or sum(durations) > 8 * 3600):
                raise ValueError('Each five-run series needs complete active timing within eight hours')
    else:
        raise ValueError('Unsupported explicit performance clock')
    baseline = evaluate(source(root, source_layout(root)['core']), [], [])
    final_result = evaluate(final, [], [])
    measured = fitness(compute_metrics(final_result['counts']), BASELINE)
    counts = final_result['counts']
    if (not set(baseline['axioms']) <= set(final_result['axioms'])
            or counts['C'] > 30 or counts['Individuals'] > 60 or counts['A'] > 710
            or min(measured.relative) < .85 or abs(measured.F - score) > 1e-9):
        raise ValueError('Final core or measured metrics disagree with the approved expert result')
    debug = analysis.analyze_run(source(root, manifest['debug_run']), replay=True)
    if (debug.get('phase') != 'debug' or debug.get('seed') != 100 or debug.get('mode') != 'model'
            or debug.get('t04', {}).get('meets_70_percent') is not True):
        raise ValueError('A qualified seed-100 debug run is required')
    if not DOCS <= set(manifest.get('docs', {})):
        raise ValueError('Missing final delivery documents')
    return results, summary


def collect_sources(root, manifest):
    """Return destination -> original source path; no source byte substitutions."""
    root = Path(root).resolve(strict=True)
    layout = source_layout(root)
    files = {}
    def add(path, destination):
        if not safe_name(destination):
            raise ValueError('Unsafe delivery destination: ' + str(destination))
        path = source(root, path.relative_to(root).as_posix())
        if not path.is_file():
            raise ValueError('Missing source file: ' + str(path))
        if destination in files and files[destination] != path:
            raise ValueError('Repeated delivery destination: ' + destination)
        files[destination] = path
    def tree(relative, destination, exclude=()):
        start = source(root, relative)
        def visit(path):
            if (path.name.startswith('.') or path.name in SKIP_DIRS
                    or path.suffix.lower() in SKIP_SUFFIXES or path.name in exclude):
                return
            checked = source(root, path.relative_to(root).as_posix())
            if checked.is_dir():
                for child in sorted(checked.iterdir()):visit(child)
            else:add(checked, destination + '/' + checked.relative_to(start).as_posix())
        visit(start)
    tree(layout['optimizer'], 'optimizer')
    tree(layout['tests'], 'tests', exclude=('test_package.py','harness'))
    tree(layout['harness'] + '/src', 'tests/harness/src')
    evidence = manifest.get('assessment_evidence')
    if evidence is None:
        tree(layout['assessment'], 'docs/assessment')
    else:
        if (not isinstance(evidence, list) or not evidence
                or any(not safe_name(name) for name in evidence)
                or len(evidence) != len(set(evidence))):
            raise ValueError('Expected distinct safe assessment evidence paths')
        tree(layout['assessment'], 'docs/assessment', exclude=('evidence',))
        for name in evidence:
            relative = layout['assessment'] + '/evidence/' + name
            destination = 'docs/assessment/evidence/' + name
            selected = source(root, relative)
            if selected.is_dir():
                tree(relative, destination)
            else:
                add(selected, destination)
    add(source(root, layout['harness'] + '/fetch_libs.sh'), 'tests/harness/fetch_libs.sh')
    add(source(root, layout['expected']), 'tests/expected.json')
    add(source(root, layout['core']), 'ontology/1.0.0/videocard.owl')
    add(source(root, manifest['final_ontology']), 'ontology/2.0.0/videocard.owl')
    add(source(root, layout['specification']), 'docs/tz_videokarta_lr4_nn_v1.0.docx')
    add(source(root, layout['requirements']), 'requirements.txt')
    tree(PurePosixPath(layout['script']).parent.as_posix(), 'scripts', exclude=('package.py',))
    add(source(root, manifest['readme']), 'README.md')
    add(source(root, manifest['expert_review']), 'docs/expert-review.json')
    for name, relative in manifest['docs'].items():
        if not safe_name(name):raise ValueError('Unsafe document name')
        add(source(root, relative), 'docs/' + name)
    for relative in [manifest['debug_run'], *manifest['runs']]:
        metadata = json.loads((source(root, relative) / 'metadata.json').read_text())
        name = 'debug-100' if metadata.get('phase') == 'debug' else f"{metadata['mode']}-{metadata['seed']}"
        tree(relative, 'runs/' + name)
    return files


def adapt_documentation(content, original, destination, files):
    """Relocate Markdown links only; code fences/spans and external URLs survive."""
    exact = {}
    directories = {}
    for name, path in files.items():
        path = path.resolve()
        exact.setdefault(path, set()).add(name)
        for source_parent, target_parent in zip(path.parents, PurePosixPath(name).parents):
            directories.setdefault(source_parent, set()).add(target_parent.as_posix())
    members = set(files)
    archive_directories = {parent.as_posix() for name in files for parent in PurePosixPath(name).parents}
    changes = []
    unresolved = []
    def relocate(target):
        angle = target.startswith('<') and target.endswith('>')
        raw = target[1:-1] if angle else target
        parts = urlsplit(raw)
        if parts.scheme or parts.netloc or not parts.path:
            return target
        if parts.path.startswith('/') or '\\' in parts.path:
            unresolved.append(raw)
            return target
        candidate = (original.parent / unquote(parts.path)).resolve()
        destinations = exact.get(candidate) or directories.get(candidate, set())
        if len(destinations) == 1:
            selected = next(iter(destinations))
        else:
            # A real, unselected source must never silently become a different
            # packaged resource that happens to have the same relative name.
            if candidate.exists():
                unresolved.append(raw)
                return target
            # Documentation may already use canonical paths before packaging.
            canonical = posixpath.normpath(posixpath.join(posixpath.dirname(destination), unquote(parts.path)))
            if canonical in members or canonical in archive_directories:
                return target
            unresolved.append(raw)
            return target
        relative = posixpath.relpath(selected, posixpath.dirname(destination) or '.')
        if parts.path.endswith('/') and not relative.endswith('/'):
            relative += '/'
        rewritten = urlunsplit(('', '', quote(relative, safe="/@:+~!$&',;=-._"), parts.query, parts.fragment))
        if rewritten != raw:
            changes.append(dict(original=raw, packaged=rewritten))
        return '<' + rewritten + '>' if angle else rewritten
    inline = re.compile(r'!?\[[^\]\n]*\]\([ \t]*(?P<target><[^>\n]+>|[^\s()]+)(?:[ \t]+(?:"[^"\n]*"|\x27[^\x27\n]*\x27))?[ \t]*\)')
    reference = re.compile(r'^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?P<target><[^>\n]+>|[^\s]+)')
    fence = None
    output = []
    for line in content.decode('utf-8').splitlines(keepends=True):
        delimiter = re.match(r'^[ \t]{0,3}(`{3,}|~{3,})', line)
        if delimiter:
            token = delimiter.group(1)
            if fence is None:fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):fence = None
            output.append(line)
            continue
        if fence is not None:
            output.append(line)
            continue
        spans = [(match.start(), match.end()) for match in re.finditer(r'(`+).*?\1', line)]
        def replace(match):
            start, end = match.span('target')
            if any(begin <= start < finish for begin, finish in spans):return match.group()
            token = relocate(match.group('target'))
            return match.group()[:start-match.start()] + token + match.group()[end-match.start():]
        line = inline.sub(replace, line)
        line = reference.sub(replace, line)
        output.append(line)
    return ''.join(output).encode('utf-8'), changes, unresolved


def build_delivery(project_root, accepted_manifest_path, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Delivery output already exists: ' + str(output))
    root = Path(project_root).resolve(strict=True)
    raw = Path(accepted_manifest_path).read_bytes()
    manifest = json.loads(raw)
    results, summary = qualify(root, manifest)
    files = collect_sources(root, manifest)
    if sha256(files['ontology/1.0.0/videocard.owl']) != 'd8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661':
        raise ValueError('Immutable baseline checksum mismatch')
    marker = dict(schema=1, layout=LAYOUT, accepted=True, accepted_manifest_sha256=hashlib.sha256(raw).hexdigest(),
                  final_sha256=manifest['final_sha256'], series=summary,
                  performance_clock=manifest.get('performance_clock', 'series_wall_clock'),
                  active_series_seconds={mode: sum(item['active_seconds'] for item in results if item['mode'] == mode)
                                         for mode in ('model', 'control')}
                      if manifest.get('performance_clock') == 'active_sessions' else None,
                  excluded_repo_tests=['test_package.py: working-material repository packager only'],
                  excluded_repo_scripts=['package.py: working-material repository layout only'],
                  documentation_link_policy='Only relative Markdown link destinations are adapted; runtime code, prompts, configuration and journals remain byte-identical',
                  documentation_link_adaptations=[], sha256={})
    generated = {'lab4/__init__.py': SHIM, 'docs/accepted-manifest.json': raw}
    if set(files) & set(generated):
        raise ValueError('A source conflicts with reserved delivery metadata')
    documentation = {}
    for name, path in files.items():
        if path.suffix.lower() != '.md':continue
        original = path.read_bytes()
        adapted, changes, unresolved = adapt_documentation(original, path, name, files)
        if unresolved:
            raise ValueError('Unresolved local documentation links in ' + name + ': ' + ', '.join(unresolved))
        documentation[name] = adapted
        if changes:
            marker['documentation_link_adaptations'].append(dict(
                destination=name, source=path.relative_to(root).as_posix(),
                source_sha256=hashlib.sha256(original).hexdigest(),
                packaged_sha256=hashlib.sha256(adapted).hexdigest(), links=changes))
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            content = documentation[name] if name in documentation else path.read_bytes()
            archive.writestr(name, content)
            marker['sha256'][name] = hashlib.sha256(content).hexdigest()
        for name, content in generated.items():
            archive.writestr(name, content)
            marker['sha256'][name] = hashlib.sha256(content).hexdigest()
        if marker['sha256']['ontology/2.0.0/videocard.owl'] != manifest['final_sha256']:
            raise ValueError('Final ontology changed while packaging')
        archive.writestr('DELIVERY_MANIFEST.json', json.dumps(marker,ensure_ascii=False,indent=2) + '\n')
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP CRC verification failed')
        for name, expected in marker['sha256'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('ZIP SHA-256 verification failed: ' + name)
    return marker


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=_project)
    parser.add_argument('--accepted-manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    try:result = build_delivery(args.project_root,args.accepted_manifest,args.output)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
        print(str(error),file=sys.stderr)
        return 2
    print(json.dumps(dict(archive=str(args.output),layout=result['layout'],files=len(result['sha256']))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

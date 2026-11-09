"""Build a small ZIP of working materials; this is not an acceptance package."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRECTORIES = {'.git', '__pycache__', '.pytest_cache', '.venv',
                        '.local-runtime', 'models', 'cache', 'out', 'results', 'lib'}
EXCLUDED_SUFFIXES = {'.pyc', '.class', '.jar', '.zip', '.part', '.dylib', '.so', '.exe',
                     '.bin', '.gguf', '.safetensors', '.pt', '.pth', '.ckpt', '.o', '.a',
                     '.whl', '.tar', '.gz', '.dmg'}
REQUIRED = ('README.md', 'lab4/README.md', 'lab4/optimizer/search.yaml',
            'lab2/ontology/videocard.owl', 'lab2/tests/expected.json',
            'lab2/tests/harness/fetch_libs.sh', 'lab2/tests/harness/src/Main.java',
            'lab2/tests/run_tests.sh', 'lab2/tests/harness/convert.sh',
            'lab2/README.md', 'lab2/docs/test_protocol.md',
            'lab2/docs/ontology_description.md', 'lab2/ontology/src/build_ontology.py',
            'lab2/ontology/src/ontology_data.py', 'lab2/ontology/src/build.sh',
            'lab2/tests/negative/T06_active_and_passive.owl',
            'lab2/tests/negative/T07_two_gpus.owl',
            'lab2/tests/negative/T08_negative_volume.owl',
            'lab2/tests/negative/T09_missing_hasMemory.owl')


def safe_name(name):
    path = PurePosixPath(name)
    return (bool(name) and '\\' not in name and not path.is_absolute()
            and all(part not in ('', '.', '..') for part in name.split('/'))
            and ':' not in path.parts[0])


def collect_files(root):
    root = Path(root).resolve()
    for name in REQUIRED:
        if not (root / name).is_file():
            raise ValueError('Missing required source: ' + name)
    selected = []
    def visit(path):
        relative = path.relative_to(root)
        if (path.name.startswith('.') or path.name in EXCLUDED_DIRECTORIES
                or path.suffix.lower() in EXCLUDED_SUFFIXES):
            return
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Symlink is not a reproducible source: ' + str(relative))
        if path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        elif path.is_file():
            if not safe_name(relative.as_posix()):
                raise ValueError('Unsafe archive path: ' + str(relative))
            selected.append(path)
    baseline_files = [name for name in REQUIRED if name.startswith('lab2/')
                      and not name.startswith('lab2/tests/harness/src/')]
    for name in ('README.md', 'lab4', 'lab2/tests/harness/src', *baseline_files):
        visit(root / name)
    return root, selected


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or not all(safe_name(name) for name in names):
            raise ValueError('Unsafe or repeated archive member')
        if archive.testzip() is not None:
            raise ValueError('Corrupt ZIP member')
        manifest = json.loads(archive.read('WORKING_MATERIALS.json'))
        if set(names) != set(manifest['sha256']) | {'WORKING_MATERIALS.json'}:
            raise ValueError('Archive manifest inventory mismatch')
        for name, expected in manifest['sha256'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('Archive checksum mismatch: ' + name)
    return manifest


def build_package(root, output):
    root, files = collect_files(root)
    output = Path(output)
    manifest = dict(kind='working materials; acceptance incomplete',
                    dependencies='Python >=3.10, JDK 17, Ollama; JAR installation requires network via fetch_libs.sh',
                    missing_specification=not (root / 'lab4/tz_videokarta_lr4_nn_v1.0.docx').is_file(),
                    excluded='model weights, runtime binaries, downloaded JARs, caches, lab2 generated results',
                    sha256={})
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(root).as_posix()
            content = path.read_bytes()
            manifest['sha256'][name] = hashlib.sha256(content).hexdigest()
            archive.writestr(name, content)
        archive.writestr('WORKING_MATERIALS.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    verify_archive(output)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New ZIP path; existing files are never replaced')
    args = parser.parse_args(argv)
    try:
        manifest = build_package(ROOT, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(dict(archive=str(args.output), files=len(manifest['sha256']),
                          kind=manifest['kind'], missing_specification=manifest['missing_specification'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

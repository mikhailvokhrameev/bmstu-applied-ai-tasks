"""Local, pinned LaBSE/E5 SentenceTransformer pipelines via Ollama-shaped HTTP.

No optimizer configuration or calibration data is changed by this module.
Optional dependencies are imported only when downloading/loading a snapshot.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
from .paths import ROOT


HF_ROOT = ROOT / '.local-runtime/hf'
PROVENANCE = '.embedding-snapshot.json'
SERVER_VERSION = 'sentence-transformers-local/1'
PIPELINE = ['sentence_transformers.models.' + name
            for name in ('Transformer', 'Pooling', 'Dense', 'Normalize')]
E5_PIPELINE = ['sentence_transformers.models.' + name
               for name in ('Transformer', 'Pooling', 'Normalize')]
PROFILES = {
    'sentence-transformers/LaBSE': dict(name='labse-cls-dense', modules=PIPELINE,
                                        pooling='pooling_mode_cls_token', dense=True),
    'intfloat/multilingual-e5-large-instruct': dict(name='e5-mean', modules=E5_PIPELINE,
                                                   pooling='pooling_mode_mean_tokens', dense=False),
}
WEIGHT_SUFFIXES = {'.bin', '.safetensors', '.pt', '.pth'}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def runtime_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(HF_ROOT.resolve()) or path == HF_ROOT.resolve():
        raise ValueError('Snapshot/cache must be inside project .local-runtime/hf')
    return path


def assets(snapshot):
    result = []
    for path in sorted(snapshot.rglob('*')):
        relative = path.relative_to(snapshot)
        if not path.is_file() or '.cache' in relative.parts or relative.name == PROVENANCE:
            continue
        if not path.resolve().is_relative_to(HF_ROOT.resolve()):
            raise ValueError('Snapshot asset resolves outside project HF storage')
        result.append(dict(path=relative.as_posix(), sha256=sha256_file(path), bytes=path.stat().st_size))
    return result


def validate_pipeline(snapshot, repo='sentence-transformers/LaBSE'):
    if repo not in PROFILES:
        raise ValueError('Unsupported SentenceTransformer repository profile')
    profile = PROFILES[repo]
    modules = json.loads((snapshot / 'modules.json').read_text(encoding='utf-8'))
    if not isinstance(modules, list) or [module.get('type') for module in modules] != profile['modules']:
        raise ValueError('Expected complete ' + profile['name'] + ' pipeline')
    for index, module in enumerate(modules):
        relative = Path(module.get('path', ''))
        if module.get('idx') != index or relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid module index/path')
        if not (snapshot / relative).resolve().is_relative_to(snapshot.resolve()):
            raise ValueError('Module resolves outside snapshot')
    pool = json.loads((snapshot / modules[1]['path'] / 'config.json').read_text())
    if pool.get(profile['pooling']) is not True or any(
            value for key, value in pool.items()
            if key.startswith('pooling_mode_') and key != profile['pooling']):
        raise ValueError('Expected ' + ('CLS-only' if profile['dense'] else 'mean-only') + ' pooling')
    if profile['dense']:
        dense = snapshot / modules[2]['path']
        if not (dense / 'config.json').is_file() or not any(
                path.is_file() and path.suffix in WEIGHT_SUFFIXES for path in dense.iterdir()):
            raise ValueError('Missing trained Dense projection')
    return modules


def prepare_snapshot(repo, revision, snapshot, cache, download=False):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Revision must be an explicit 40-character commit SHA')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Expected explicit public Hugging Face repo')
    if repo not in PROFILES:
        raise ValueError('Unsupported SentenceTransformer repository profile')
    snapshot, cache = runtime_path(snapshot), runtime_path(cache)
    if snapshot == cache or snapshot.is_relative_to(cache) or cache.is_relative_to(snapshot):
        raise ValueError('Snapshot and cache must be separate directories')
    record_path = snapshot / PROVENANCE
    if download:
        if record_path.exists():
            # A pinned, recorded directory is immutable; verify/reuse offline.
            return prepare_snapshot(repo, revision, snapshot, cache, download=False)
        if snapshot.exists() and any(snapshot.iterdir()):
            raise ValueError('Download target must be empty; do not mix snapshots')
        from huggingface_hub import HfApi, snapshot_download
        info = HfApi(endpoint='https://huggingface.co', token=False).model_info(
            repo_id=repo, revision=revision, token=False)
        if info.sha != revision:
            raise ValueError('Hub commit does not match pinned revision')
        snapshot_download(repo_id=repo, revision=revision, token=False,
                          endpoint='https://huggingface.co', local_dir=str(snapshot),
                          cache_dir=str(cache), allow_patterns=[
                              '*.json', '*.safetensors', '*.model', '*.txt'],
                          ignore_patterns=['onnx/*', 'openvino/*', '*.py', 'tf_model.h5'])
        modules = validate_pipeline(snapshot, repo)
        files = assets(snapshot)
        record = dict(schema=1, repo=repo, commit_sha=revision, modules=modules, files=files,
                      identity_source='Public HF model_info and snapshot_download at exact commit; token=False')
        with record_path.open('x', encoding='utf-8') as output:
            output.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    else:
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if (record.get('schema') != 1 or record.get('repo') != repo or
                record.get('commit_sha') != revision):
            raise ValueError('Snapshot provenance does not match requested repo/commit')
        modules = validate_pipeline(snapshot, repo)
        files = assets(snapshot)
        if record.get('files') != files or record.get('modules') != modules:
            raise ValueError('Snapshot files changed after provenance was recorded')
    if not any(Path(item['path']).suffix in WEIGHT_SUFFIXES for item in files):
        raise ValueError('No snapshot weight files')
    return snapshot, record


class SentenceTransformerEngine:
    def __init__(self, repo, revision, snapshot, cache, device, download=False):
        snapshot, record = prepare_snapshot(repo, revision, snapshot, cache, download)
        # Require the safe tensor-only torch loader even for old Dense .bin
        # checkpoints. No Python modules from the snapshot are imported.
        os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '1'
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(str(snapshot), device=device, cache_folder=str(runtime_path(cache)),
                                         token=False, trust_remote_code=False, local_files_only=True)
        self.model.eval()
        self.lock = threading.Lock()
        self.repo = repo
        files = record['files']
        self.metadata = dict(version=SERVER_VERSION, model=repo, backend='sentence-transformers',
                             commit_sha=record['commit_sha'], snapshot=str(snapshot),
                             weights=[item for item in files if Path(item['path']).suffix in WEIGHT_SUFFIXES],
                             files=files, modules=record['modules'],
                             pipeline_profile=PROFILES[repo]['name'],
                             device=str(self.model.device), max_seq_length=int(self.model.max_seq_length),
                             embedding_dimension=int(self.model.get_sentence_embedding_dimension()),
                             trust_remote_code=False, local_files_only=True, public_download_token=False,
                             packages={name: importlib.metadata.version(name) for name in (
                                 'sentence-transformers', 'transformers', 'torch', 'huggingface-hub', 'safetensors')})
        encoded = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
        self.metadata['snapshot_sha256'] = hashlib.sha256(encoded).hexdigest()

    def encode(self, texts, truncate=False):
        with self.lock:
            tokenized = self.model.tokenizer(texts, padding=False, truncation=False,
                                             add_special_tokens=True, return_attention_mask=False)
            if not truncate and any(len(tokens) > self.metadata['max_seq_length']
                                    for tokens in tokenized['input_ids']):
                raise ValueError('Input exceeds actual max_seq_length; truncation disabled')
            # Preserve all saved modules (including LaBSE Dense). No hand-written
            # pooling, instruction prefixes or extra postprocessing is applied.
            return self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True,
                                     normalize_embeddings=False).tolist()


def make_handler(engine):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def send_json(self, status, value):
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path in ('/api/version', '/api/show'):
                self.send_json(200, engine.metadata)
            elif self.path == '/api/tags':
                self.send_json(200, dict(models=[dict(name=engine.repo, model=engine.repo,
                                                     digest='sha256:' + engine.metadata['snapshot_sha256'],
                                                     details=dict(format='sentence-transformers'))]))
            else:
                self.send_json(404, dict(error='unknown_endpoint'))

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8 * 1024 * 1024:
                    raise ValueError('Invalid request size')
                self.connection.settimeout(180)
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or payload.get('model', engine.repo) != engine.repo:
                    raise ValueError('Invalid model/request')
                if self.path == '/api/show':
                    self.send_json(200, engine.metadata)
                    return
                if self.path != '/api/embed':
                    self.send_json(404, dict(error='unknown_endpoint'))
                    return
                texts = payload.get('input')
                texts = [texts] if isinstance(texts, str) else texts
                if (not isinstance(texts, list) or not 1 <= len(texts) <= 256 or
                        any(not isinstance(text, str) or not text.strip() for text in texts)):
                    raise ValueError('Expected nonempty text batch')
                truncate = payload.get('truncate', False)
                if type(truncate) is not bool:
                    raise ValueError('Invalid truncate option')
                embeddings = engine.encode(texts, truncate=truncate)
                if (not isinstance(embeddings, list) or len(embeddings) != len(texts) or
                        any(not isinstance(vector, list) or len(vector) != engine.metadata['embedding_dimension']
                            or any(type(number) not in (int, float) or not math.isfinite(number) for number in vector)
                            or not any(vector) for vector in embeddings)):
                    raise RuntimeError('Invalid embedding engine output')
                self.send_json(200, dict(model=engine.repo, embeddings=embeddings))
            except (ValueError, TypeError, UnicodeError):
                self.send_json(400, dict(error='invalid_input_or_context_limit'))
            except Exception:
                # Do not echo engine exceptions, which may contain input text.
                self.send_json(500, dict(error='embedding_engine_failure'))

    return Handler


def make_server(engine, host='127.0.0.1', port=11436):
    if host != '127.0.0.1':
        raise ValueError('Embedding server binds only to 127.0.0.1')

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def handle_error(self, request, client_address):
            pass

    return Server((host, port), make_handler(engine))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--revision', required=True, help='Exact 40-character HF commit SHA')
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--device', required=True, choices=['cpu', 'mps', 'cuda'])
    parser.add_argument('--host', default='127.0.0.1', choices=['127.0.0.1'])
    parser.add_argument('--port', default=11436, type=int)
    parser.add_argument('--download', action='store_true', help='Download public pinned snapshot with token=False')
    args = parser.parse_args(argv)
    try:
        engine = SentenceTransformerEngine(args.repo, args.revision, args.snapshot, args.cache,
                                           args.device, download=args.download)
        server = make_server(engine, args.host, args.port)
    except Exception as error:
        print(json.dumps(dict(status='startup_failed', error_type=type(error).__name__)), file=sys.stderr)
        return 2
    print(json.dumps(dict(status='ready', host=args.host, port=server.server_port,
                          model=engine.repo, commit_sha=engine.metadata['commit_sha'],
                          device=engine.metadata['device'], max_seq_length=engine.metadata['max_seq_length'])), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Isolated OWL requests through a content-addressed, persistent Java worker.

The worker reuses only the JVM. Each request constructs its own OWL managers and
reasoners. Exact reconstruction results are cached independently of search IDs.
"""
import atexit
import copy
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import threading
import time

from .paths import ROOT, CORE, LIB, HARNESS

SOURCE = Path(__file__).parent / 'owl_bridge/OntologyEvaluator.java'
CORE_SHA256 = 'd8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661'
_FILE_HASHES = {}
_EVALUATIONS = {}
_CACHE_STATS = dict(evaluate_hits=0, evaluate_misses=0, worker_requests=0)
_WORKER_LOCK = threading.RLock()


class BridgeError(RuntimeError):
    pass


def _run(command, **kwargs):
    try:
        proc = subprocess.run(command, text=True, encoding='utf-8', capture_output=True, timeout=120, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BridgeError(str(error)) from error
    if proc.returncode:
        raise BridgeError(f'Process failed ({proc.returncode}): {proc.stderr[-4000:]}')
    return proc.stdout


def file_digest(path):
    """Refresh content hashes when file identity, size or timestamps change."""
    path = Path(path).resolve()
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    previous = _FILE_HASHES.get(path)
    if previous is None or previous[0] != identity:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _FILE_HASHES[path] = (identity, digest)
    return _FILE_HASHES[path][1]


def engine_identity():
    sources = sorted(SOURCE.parent.glob('*.java'))
    harness = sorted((HARNESS / 'src').glob('*.java'))
    jars = sorted(LIB.glob('*.jar'))
    if not jars:
        raise BridgeError('No OWL API/HermiT libraries; run fetch_libs.sh')
    values = [(str(path.resolve()), file_digest(path)) for path in sources + harness + jars]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def check_core():
    if file_digest(CORE) != CORE_SHA256:
        raise BridgeError('CORE_CHECKSUM: original ontology changed')


class _Worker:
    def __init__(self):
        self.process = None
        self.identity = None
        self.stderr = None
        self.buffer = b''

    def close(self):
        proc = self.process
        self.process = None
        self.identity = None
        self.buffer = b''
        if proc is not None:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
            for pipe in (proc.stdin, proc.stdout):
                if pipe is not None:
                    pipe.close()
        if self.stderr is not None:
            self.stderr.close()
            self.stderr = None

    def start(self, identity):
        if self.process is not None and self.process.poll() is None and self.identity == identity:
            return
        self.close()
        build = Path(tempfile.gettempdir()) / ('videocard-v13-worker-' + identity[:24])
        build.mkdir(exist_ok=True)
        marker = build / 'StreamWorker.class'
        if not marker.exists():
            sources = sorted(SOURCE.parent.glob('*.java')) + sorted((HARNESS / 'src').glob('*.java'))
            _run(['javac', '-encoding', 'UTF-8', '-cp', str(LIB / '*'), '-d', str(build), *map(str, sources)])
        self.stderr = tempfile.TemporaryFile(mode='w+b')
        self.process = subprocess.Popen(
            ['java', '-Dfile.encoding=UTF-8', '-Dslf4j.internal.verbosity=ERROR',
             '-cp', str(build) + ':' + str(LIB / '*'), 'StreamWorker'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
        )
        self.identity = identity

    def request(self, command, payload, timeout):
        self.start(engine_identity())
        proc = self.process
        try:
            proc.stdin.write((json.dumps(dict(command=command, payload=payload), ensure_ascii=False) + '\n').encode())
            proc.stdin.flush()
            deadline = time.monotonic() + timeout
            while b'\n' not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([proc.stdout], [], [], remaining)[0]:
                    raise TimeoutError('OWL worker response deadline')
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    self.stderr.seek(0, os.SEEK_END)
                    size = self.stderr.tell()
                    self.stderr.seek(max(0, size - 4000))
                    raise BridgeError('OWL worker exited: ' + self.stderr.read().decode(errors='replace'))
                self.buffer += chunk
            line, self.buffer = self.buffer.split(b'\n', 1)
            response = json.loads(line)
            if not isinstance(response, dict) or type(response.get('ok')) is not bool:
                raise BridgeError('Invalid worker envelope')
            if response['ok'] is not True:
                raise BridgeError(response.get('error', 'OWL worker request failed'))
            _CACHE_STATS['worker_requests'] += 1
            return response['result']
        except (OSError, ValueError, TimeoutError, BridgeError):
            self.close()
            raise


_WORKER = _Worker()
atexit.register(_WORKER.close)


def java_request(command, payload, timeout=120):
    """Run one checked JSON request; never cache errors or reuse ontology state."""
    with _WORKER_LOCK:
        check_core()
        return _WORKER.request(command, payload, timeout)


def cache_info():
    return dict(_CACHE_STATS, evaluations=len(_EVALUATIONS))


def clear_caches():
    with _WORKER_LOCK:
        _EVALUATIONS.clear()
        _FILE_HASHES.clear()
        for key in _CACHE_STATS:
            _CACHE_STATS[key] = 0
        _WORKER.close()


def evaluate(base_path, add, remove):
    path = Path(base_path).resolve()
    check_core()
    if not isinstance(add, (list, tuple)) or not isinstance(remove, (list, tuple)) or any(
            not isinstance(axiom, str) for axiom in (*add, *remove)):
        raise BridgeError('add/remove must contain axiom strings')
    request = dict(base_path=str(path), add=sorted(set(add)), remove=sorted(set(remove)))
    key = (engine_identity(), file_digest(path), json.dumps(request, sort_keys=True, ensure_ascii=False))
    with _WORKER_LOCK:
        if key in _EVALUATIONS:
            _CACHE_STATS['evaluate_hits'] += 1
            return copy.deepcopy(_EVALUATIONS[key])
        _CACHE_STATS['evaluate_misses'] += 1
        result = java_request('evaluate', request)
        try:
            if not isinstance(result, dict) or result.get('core_preserved') is not True:
                raise ValueError('Missing core preservation result')
            counts = result['counts']
            for name in ('C', 'H', 'Po', 'Pd', 'E', 'Al', 'A', 'Q'):
                if type(counts[name]) is not int or counts[name] < 0:
                    raise ValueError('Invalid counts')
            if not isinstance(result['violations'], list) or len(result['violations']) != counts['Q']:
                raise ValueError('Invalid violations')
            if not isinstance(result['axioms'], list) or any(not isinstance(a, str) for a in result['axioms']):
                raise ValueError('Invalid axiom text')
            keys = set()
            for violation in result['violations']:
                if (not isinstance(violation, dict) or violation.get('code') not in ('P04', 'P08', 'P10', 'P11', 'P13', 'P22')
                        or not isinstance(violation.get('key'), str)):
                    raise ValueError('Invalid violation')
                keys.add((violation['code'], violation['key']))
            if len(keys) != counts['Q']:
                raise ValueError('Duplicate violations')
            graph = result['graph']
            if not isinstance(graph, dict) or set(graph) != {'vertices', 'edges'}:
                raise ValueError('Missing named-class graph')
            vertices = graph['vertices']
            edges = graph['edges']
            if (not isinstance(vertices, list) or any(not isinstance(v, str) for v in vertices)
                    or len(set(vertices)) != counts['C'] or len(vertices) != counts['C']):
                raise ValueError('Invalid graph vertices')
            if (not isinstance(edges, list) or any(not isinstance(e, list) or len(e) != 2
                    or any(v not in vertices for v in e) for e in edges)):
                raise ValueError('Invalid graph edges')
            if len({tuple(edge) for edge in edges}) != len(edges) or len(edges) != counts['H']:
                raise ValueError('Graph edge count differs from H')
        except (ValueError, KeyError, TypeError) as error:
            raise BridgeError(f'Invalid bridge response: {error}') from error
        _EVALUATIONS[key] = copy.deepcopy(result)
        return result

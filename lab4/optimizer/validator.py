"""Ordered candidate validation. Errors have no fitness and must not enter selection."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from .bridge import ROOT, CORE, CORE_SHA256, LIB, BridgeError, _run
from .metrics import compute_metrics, fitness

@dataclass(frozen=True)
class ValidationResult:
    status: str
    code: str = None
    F: float = None
    detail: str = ''
    metrics: object = None
    relative: tuple = ()


def _inspect(candidate, baseline):
    sources = sorted((Path(__file__).parent/'owl_bridge').glob('*.java'))
    harness = sorted((ROOT/'lab2/tests/harness/src').glob('*.java'))
    key = hashlib.sha256(b''.join(p.read_bytes() for p in sources+harness)).hexdigest()[:20]
    build = Path(tempfile.gettempdir())/('videocard-validator-'+key)
    build.mkdir(exist_ok=True)
    if not (build/'CandidateValidator.class').exists():
        _run(['javac','-encoding','UTF-8','-cp',str(LIB/'*'),'-d',str(build),*[str(p) for p in sources+harness]])
    request = dict(candidate) if isinstance(candidate, dict) else {'path':str(Path(candidate).resolve())}
    request['baseline'] = str(Path(baseline).resolve())
    request['expected'] = str(ROOT/'lab2/tests/expected.json')
    proc = subprocess.run(['java','-Dfile.encoding=UTF-8','-Dslf4j.internal.verbosity=ERROR','-cp',str(build)+':'+str(LIB/'*'),'CandidateValidator'], input=json.dumps(request, ensure_ascii=False), text=True, encoding='utf-8', capture_output=True, timeout=120)
    if proc.returncode:
        raise BridgeError(proc.stderr[-4000:])
    return json.loads(proc.stdout)


def validate(candidate, baseline=CORE, duplicate_checker=None):
    """candidate is a path or cumulative {'add': [...], 'remove': [...]} delta.

    duplicate_checker receives new entity dictionaries (IRI/category/label/comment),
    and returns True iff a semantic duplicate exists; service failures remain errors.
    """
    try:
        if CORE.read_bytes() and hashlib.sha256(CORE.read_bytes()).hexdigest() != CORE_SHA256:
            raise BridgeError('CORE_CHECKSUM')
        result = _inspect(candidate, baseline)
        if result.get('code'):
            return ValidationResult('invalid', result['code'], 0.0, result.get('detail',''))
        if duplicate_checker is None:
            raise BridgeError('duplicate_checker is required; no semantic result may be assumed')
        duplicate = duplicate_checker(result['new_entities'])
        if type(duplicate) is not bool:
            raise BridgeError('duplicate_checker must return bool')
        if duplicate:
            return ValidationResult('invalid','DUPLICATE',0.0)
        c, b = result['counts'], result['baseline_counts']
        if c['C'] > 30 or c['Individuals'] > 60 or c['A'] > 710:
            return ValidationResult('invalid','GROWTH',0.0)
        m = compute_metrics(c)
        f = fitness(m, compute_metrics(b))
        if min(f.relative) < .85:
            return ValidationResult('invalid','RELATIVE_METRIC',0.0,metrics=m,relative=f.relative)
        if result.get('change_violation'):
            return ValidationResult('invalid','CHANGE_KIND',0.0,result['change_violation'])
        return ValidationResult('valid',F=f.F,metrics=m,relative=f.relative)
    except (TimeoutError, subprocess.TimeoutExpired) as error:
        return ValidationResult('error','TIMEOUT',None,str(error))
    except Exception as error:
        return ValidationResult('error','VALIDATION_ERROR',None,str(error))

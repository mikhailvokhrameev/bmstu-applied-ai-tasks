"""UTF-8 JSON process bridge. Infrastructure failures never become candidates."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).parent / 'owl_bridge/OntologyEvaluator.java'
LIB = ROOT / 'lab2/tests/harness/lib'
CORE = ROOT / 'lab2/ontology/videocard.owl'
CORE_SHA256 = 'd8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661'

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


def evaluate(base_path, add, remove):
    path = Path(base_path).resolve()
    if path == CORE.resolve():
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise BridgeError(str(error)) from error
        if digest != CORE_SHA256:
            raise BridgeError('CORE_CHECKSUM: original ontology changed')
    if not isinstance(add, (list, tuple)) or not isinstance(remove, (list, tuple)) or any(not isinstance(a,str) for a in (*add,*remove)):
        raise BridgeError('add/remove must contain axiom strings')
    # Content-addressed build directory avoids stale classes and repository artifacts.
    key = hashlib.sha256((str(ROOT)+SOURCE.read_text()).encode()).hexdigest()[:20]
    build = Path(tempfile.gettempdir()) / ('videocard-bridge-'+key)
    build.mkdir(exist_ok=True)
    if not (build/'OntologyEvaluator.class').exists():
        _run(['javac','-encoding','UTF-8','-cp',str(LIB/'*'),'-d',str(build),str(SOURCE)])
    output = _run(['java','-Dfile.encoding=UTF-8','-Dslf4j.internal.verbosity=ERROR','-cp',str(build)+':'+str(LIB/'*'),'OntologyEvaluator'],
                  input=json.dumps(dict(base_path=str(path), add=add, remove=remove), ensure_ascii=False))
    try:
        result = json.loads(output)
        if not isinstance(result, dict) or result.get('core_preserved') is not True:
            raise ValueError('Missing core preservation result')
        counts = result['counts']
        for key in ('C','H','Po','Pd','E','Al','A','Q'):
            if type(counts[key]) is not int or counts[key] < 0:
                raise ValueError('Invalid counts')
        if not isinstance(result['violations'],list) or len(result['violations']) != counts['Q'] or not isinstance(result['axioms'],list):
            raise ValueError('Invalid result schema')
        if any(not isinstance(a, str) for a in result['axioms']):
            raise ValueError('Invalid axiom text')
        violation_keys = set()
        for violation in result['violations']:
            if not isinstance(violation, dict) or violation.get('code') not in ('P04','P08','P10','P11','P13','P22') or not isinstance(violation.get('key'), str):
                raise ValueError('Invalid violation')
            violation_keys.add((violation['code'], violation['key']))
        if len(violation_keys) != counts['Q']:
            raise ValueError('Duplicate violations')
        return result
    except (ValueError, KeyError, TypeError) as error:
        raise BridgeError(f'Invalid bridge response: {error}') from error

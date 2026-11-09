"""Complete v1.3 validation with structural prechecks and proven-result caching.

A cache hit reuses a completed deterministic validation for the same ontology,
methodology, reference data and semantic-checker provenance. Search evaluation
IDs and budgets are independent of this cache and are never omitted.
"""
import copy
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import subprocess

from .bridge import CORE, LIB, ROOT, BridgeError, check_core, engine_identity, evaluate, file_digest, java_request
from .metrics import MetricError, compute_metrics, fitness
from .paths import EXPECTED


@dataclass(frozen=True)
class ValidationResult:
    status: str
    code: str = None
    F: float = None
    detail: str = ''
    metrics: object = None
    relative: tuple = ()
    B: float = None
    S: float = None
    coefficients: object = None
    cache_hit: bool = False
    cache_key: str = None


_VALIDATIONS = {}
_STATS = dict(hits=0, misses=0)


def _inspect(candidate, baseline):
    request = dict(candidate) if isinstance(candidate, dict) else {'path': str(Path(candidate).resolve())}
    request['baseline'] = str(Path(baseline).resolve())
    request['expected'] = str(EXPECTED)
    return java_request('inspect', request)


def cache_info():
    return dict(_STATS, validations=len(_VALIDATIONS))


def clear_cache():
    _VALIDATIONS.clear()
    for key in _STATS:
        _STATS[key] = 0


def _cache_key(candidate, baseline, duplicate_checker):
    identity = getattr(duplicate_checker, 'cache_identity', None)
    if identity is None:
        return None
    local = Path(__file__).parent
    implementation = {name: file_digest(local / name)
                      for name in ('validator.py', 'bridge.py', 'metrics.py', 'structural.py')}
    source = dict(delta={k: sorted(set(candidate[k])) for k in ('add', 'remove')}) if isinstance(candidate, dict) else dict(
        path=str(Path(candidate).resolve()), sha256=file_digest(candidate))
    payload = dict(candidate=source, baseline=file_digest(baseline), core=file_digest(CORE),
                   engine=engine_identity(), expected=file_digest(EXPECTED),
                   implementation=implementation, semantic_checker=identity)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate(candidate, baseline=CORE, duplicate_checker=None):
    metrics = None
    measured = None
    key = None

    def outcome(status, code=None, detail=''):
        return ValidationResult(status, code, measured.F if status == 'valid' else 0.0, detail,
                                metrics, measured.relative if measured else (),
                                measured.B if measured else None, measured.S if measured else None,
                                measured.coefficients if measured else None, cache_key=key)

    def completed(result):
        if key is not None and result.status in ('valid', 'invalid'):
            _VALIDATIONS[key] = copy.deepcopy(result)
        return result

    try:
        check_core()
        key = _cache_key(candidate, baseline, duplicate_checker)
        if key is not None and key in _VALIDATIONS:
            _STATS['hits'] += 1
            return replace(copy.deepcopy(_VALIDATIONS[key]), cache_hit=True)
        _STATS['misses'] += 1
        if isinstance(candidate, dict):
            if set(candidate) != {'add', 'remove'}:
                raise ValueError('Expected cumulative add/remove delta')
            reconstruction = evaluate(baseline, candidate['add'], candidate['remove'])
        else:
            reconstruction = evaluate(candidate, [], [])
        reference = evaluate(baseline, [], [])
        metrics = compute_metrics(reconstruction['counts'], graph=reconstruction['graph'])
        measured = fitness(metrics, compute_metrics(reference['counts'], graph=reference['graph']))
        # No depth/width computation or reasoner invocation can precede a cycle
        # check: compute_metrics represents unavailable cyclic values as None.
        if metrics.structural.CY1 or metrics.structural.CY2:
            return completed(outcome('invalid', 'CYCLE', 'Named SubClassOf graph contains directed cycles'))
        if measured.S is None or measured.S < .85:
            return completed(outcome('invalid', 'STRUCTURE', 'Structural coefficient S must be at least 0.85'))
        counts = reconstruction['counts']
        if counts['C'] > 30 or counts['Individuals'] > 60 or counts['A'] > 710:
            return completed(outcome('invalid', 'GROWTH'))
        if min(measured.relative) < .85:
            return completed(outcome('invalid', 'RELATIVE_METRIC'))
        inspected = _inspect(candidate, baseline)
        if not isinstance(inspected, dict):
            raise BridgeError('Invalid validator response')
        if inspected.get('code'):
            return completed(outcome('invalid', inspected['code'], inspected.get('detail', '')))
        if duplicate_checker is None:
            raise BridgeError('duplicate_checker is required; no semantic result may be assumed')
        duplicate = duplicate_checker(inspected['new_entities'])
        if type(duplicate) is not bool:
            raise BridgeError('duplicate_checker must return bool')
        if duplicate:
            return completed(outcome('invalid', 'DUPLICATE'))
        if inspected.get('change_violation'):
            return completed(outcome('invalid', 'CHANGE_KIND', inspected['change_violation']))
        return completed(outcome('valid'))
    except (TimeoutError, subprocess.TimeoutExpired) as error:
        return ValidationResult('error', 'TIMEOUT', None, str(error), metrics=metrics, cache_key=key)
    except BridgeError as error:
        detail = str(error)
        if 'UNSUPPORTED_IMPORTS' in detail:
            return completed(outcome('invalid', 'FORBIDDEN', detail))
        if 'CORE_REMOVAL' in detail:
            return completed(outcome('invalid', 'CORE', detail))
        if 'UNSUPPORTED_NAMESPACE' in detail:
            return completed(outcome('invalid', 'ANNOTATIONS', detail))
        return ValidationResult('error', 'VALIDATION_ERROR', None, detail, metrics=metrics, cache_key=key)
    except MetricError as error:
        return completed(outcome('invalid', 'METRICS', str(error)))
    except Exception as error:
        return ValidationResult('error', 'VALIDATION_ERROR', None, str(error), metrics=metrics, cache_key=key)

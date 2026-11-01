"""Metrics from assessment/METHODOLOGY.md; undefined ratios raise MetricError."""
from dataclasses import dataclass
import math

Q0 = 10  # Frozen before search, local methodology v1.
BASELINE_COUNTS = dict(C=15, H=5, Po=10, Pd=7, E=2, Al=253, A=472, Q=Q0)

class MetricError(ValueError):
    pass

@dataclass(frozen=True)
class Metrics:
    M1: float
    M2: float
    M3: float
    M4: float
    M5: float
    M6: int

    @property
    def values(self):
        return (self.M1, self.M2, self.M3, self.M4, self.M5, self.M6)

@dataclass(frozen=True)
class Fitness:
    relative: tuple
    F: float

    @property
    def r(self):
        return self.relative


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MetricError(f'{name} must be a nonnegative integer')
    return value


def compute_metrics(counts, q0=Q0):
    _count(q0, 'q0')
    c = {k: _count(counts[k], k) for k in BASELINE_COUNTS}
    if not c['C'] or not c['H'] + c['Po'] or not c['A']:
        raise MetricError('Undefined metric: zero denominator (C, H+Po or A)')
    return Metrics(c['H']/c['C'], c['Po']/(c['H']+c['Po']), c['Pd']/c['C'],
                   c['E']/c['C'], c['Al']/c['A'], c['Q'])


def fitness(metrics, baseline):
    for v in metrics.values + baseline.values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise MetricError('Metrics must be finite nonnegative numbers')
    if any(v == 0 for v in baseline.values[:5]):
        raise MetricError('Undefined relative metric: zero baseline')
    relative = tuple(min(v/b, 2.0) for v,b in zip(metrics.values[:5], baseline.values[:5]))
    relative += (min((baseline.M6+1)/(metrics.M6+1), 2.0),)
    return Fitness(relative, sum(w*r for w,r in zip((.15,.15,.10,.15,.15,.30), relative)))

BASELINE = compute_metrics(BASELINE_COUNTS, Q0)

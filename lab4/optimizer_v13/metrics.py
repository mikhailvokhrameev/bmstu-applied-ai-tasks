"""Schema metrics and structural fitness from specification 1.3, section 4.2."""
from dataclasses import dataclass
import math

from .structural import StructuralError, StructuralMetrics, compute_structural_metrics


Q0 = 10
BASELINE_COUNTS = dict(C=15, H=5, Po=10, Pd=7, E=2, Al=253, A=472, Q=Q0)
_NAMESPACE = 'https://example.org/ontologies/videocard#'
_BASELINE_CLASSES = (
    'ActiveCooling', 'CardWith8GBMemory', 'CardWithActiveCooling',
    'ConnectionInterface', 'CoolingSystem', 'GPUArchitecture', 'GPUModel',
    'Manufacturer', 'MemoryConfiguration', 'MemoryType', 'ModelComponent',
    'PassiveCooling', 'Purpose', 'VideoCardModel', 'VideoOutput',
)
BASELINE_GRAPH = dict(
    vertices=[_NAMESPACE + name for name in _BASELINE_CLASSES],
    edges=[[_NAMESPACE + parent, _NAMESPACE + child] for parent, child in (
        ('CoolingSystem', 'ActiveCooling'),
        ('CoolingSystem', 'PassiveCooling'),
        ('ModelComponent', 'CoolingSystem'),
        ('ModelComponent', 'GPUModel'),
        ('ModelComponent', 'MemoryConfiguration'),
    )],
)


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
    structural: StructuralMetrics

    @property
    def values(self):
        return (self.M1, self.M2, self.M3, self.M4, self.M5, self.M6)


@dataclass(frozen=True)
class Fitness:
    relative: tuple
    F: float
    B: float
    S: float | None
    coefficients: dict

    @property
    def r(self):
        return self.relative


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MetricError(name + ' must be a nonnegative integer')
    return value


def compute_metrics(counts, q0=Q0, graph=None):
    """Compute M1–M6 and graph metrics, requiring the actual explicit graph."""
    _count(q0, 'q0')
    try:
        measured = {key: _count(counts[key], key) for key in BASELINE_COUNTS}
    except (KeyError, TypeError) as error:
        raise MetricError('Missing schema counts') from error
    if not measured['C'] or not measured['H'] + measured['Po'] or not measured['A']:
        raise MetricError('Undefined metric: zero denominator (C, H+Po or A)')
    try:
        structural = compute_structural_metrics(graph)
    except StructuralError as error:
        raise MetricError(str(error)) from error
    if structural.N != measured['C'] or structural.H != measured['H']:
        raise MetricError('Graph N/H differs from schema C/H counts')
    return Metrics(
        measured['H'] / measured['C'],
        measured['Po'] / (measured['H'] + measured['Po']),
        measured['Pd'] / measured['C'],
        measured['E'] / measured['C'],
        measured['Al'] / measured['A'],
        measured['Q'], structural,
    )


def fitness(metrics, baseline):
    """Return B, structural coefficients, S and F; cycles are invalid with F=0."""
    for value in metrics.values + baseline.values:
        if (isinstance(value, bool) or not isinstance(value, (float, int))
                or not math.isfinite(value) or value < 0):
            raise MetricError('Metrics must be finite nonnegative numbers')
    if any(value == 0 for value in baseline.values[:5]):
        raise MetricError('Undefined relative metric: zero baseline')
    relative = tuple(min(value / origin, 2.0)
                     for value, origin in zip(metrics.values[:5], baseline.values[:5]))
    relative += (min((baseline.M6 + 1) / (metrics.M6 + 1), 2.0),)
    weighted = sum(weight * ratio for weight, ratio in
                   zip((.15, .15, .10, .15, .15, .30), relative))
    current, origin = metrics.structural, baseline.structural
    if not isinstance(current, StructuralMetrics) or not isinstance(origin, StructuralMetrics):
        raise MetricError('Actual structural metrics are required')
    if origin.CY1 or origin.CY2 or origin.D1 is None or origin.W1 is None:
        raise MetricError('Baseline class graph must be acyclic')
    for structural in (current, origin):
        for name in ('N', 'H', 'U', 'T1', 'CY1'):
            _count(getattr(structural, name), name)
        if not structural.N:
            raise MetricError('Structural metrics require at least one class')
    coefficients = dict(
        KD=None if current.D1 is None else min((origin.D1 + 1) / (current.D1 + 1), 1.0),
        KW=None if current.W1 is None else min((origin.W1 + 1) / (current.W1 + 1), 1.0),
        KT=min((origin.T1 + 1) / (current.T1 + 1), 1.0),
        KI=min((origin.U + 1) / (current.U + 1), 1.0),
    )
    if current.CY1 or current.CY2:
        return Fitness(relative, 0.0, weighted, None, coefficients)
    if current.D1 is None or current.W1 is None:
        raise MetricError('Acyclic graph is missing depth or width')
    structural_factor = math.prod(coefficients.values()) ** .25
    return Fitness(relative, weighted * structural_factor, weighted,
                   structural_factor, coefficients)


BASELINE = compute_metrics(BASELINE_COUNTS, Q0, BASELINE_GRAPH)

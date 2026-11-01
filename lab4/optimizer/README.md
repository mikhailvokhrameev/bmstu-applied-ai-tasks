# Evaluation component (task 2)

Run from the repository root with Python >= 3.10 and Java 17; use pinned
`lab2/tests/harness/lib` jars (OWL API 4.5.29). No Maven or network is required.

```sh
python3 -m unittest lab4.tests.test_metrics_bridge
```

```python
from lab4.optimizer.bridge import evaluate
from lab4.optimizer.metrics import compute_metrics, fitness, BASELINE, Q0
result = evaluate('lab2/ontology/videocard.owl', [], [])
metrics = compute_metrics(result['counts'], Q0)
score = fitness(metrics, BASELINE)
```

`evaluate(base_path, add, remove)` returns a dict containing `counts`, sorted
`axioms` (OWL Functional Syntax axiom strings), sorted `violations` (`code`, `key`),
and `core_preserved`. Java has the equivalent public static method returning
`OntologyEvaluator.EvaluationResult`. The command-line Java process reads one
UTF-8 JSON request (`base_path`, `add`, `remove`) from stdin and writes one JSON
result; errors exit 2 and use stderr. Python errors raise `BridgeError`, including
timeouts, missing jars/compiler, syntax errors and malformed responses.

Each add/remove item must contain exactly one OWL axiom, using full IRIs or
prefixes `:`, `owl:`, `rdfs:`, `xsd:`. Changes represent a cumulative delta from
base: additions are applied before removals; removing an added axiom cancels it.
Removing an original axiom raises `CORE_REMOVAL`, even if the same axiom also
appears in additions. Duplicate additions have set semantics. The original
ontology is never saved. Imports and foreign user namespaces are unsupported
under the current methodology. The known production core path is checksum checked.
The Java compilation cache is outside the repository, keyed by source and root.

`Metrics` exposes M1–M6 and `values`; `Fitness` exposes `relative`, alias `r`,
and `F`. Exact baseline counts are fixed in code, with Q0=10. `compute_metrics`
accepts `q0` for the specified interface and validates it; Q0 is used for relative
M6 through the baseline passed to `fitness`. Counts must be nonnegative integers.
Undefined metrics and relative ratios raise `MetricError`; NaN/infinity never
produce an accepted numeric result. See `../assessment/METHODOLOGY.md` for the
precise counting and violation definitions.

This stage computes structural metrics only. It does not declare a candidate
valid: consistency, competency queries, growth limits, supported mutation kinds
and the 0.85 thresholds belong to the following validator stage. Fixture formula
F values therefore remain available independently of production core validation.

### Candidate validation

`validator.validate(candidate, baseline=CORE, duplicate_checker=checker)` accepts a
path or cumulative Functional Syntax `add`/`remove` lists. The baseline is the
immutable original ontology, never a parent candidate. Every invocation rebuilds
an isolated ontology. `checker(new_entities)` must perform the real semantic
comparison and return a boolean; each entity has `iri`, `category`, `label`,
`comment`. No embedding similarity is assumed by the validator.

`ValidationResult.status` is `valid`, `invalid`, or `error`. Invalid candidates
have `F=0`; errors have `F=None` and must not enter selection or be counted as
ontology violations. A process timeout is `TIMEOUT`; other infrastructure failures
are `VALIDATION_ERROR`. Validation conditions are ordered:
`OWL2_DL`, `CONSISTENCY`, `QUERIES`, `NEGATIVE_TESTS`, `CORE`, `FORBIDDEN`,
`ANNOTATIONS`, `DUPLICATE`, `GROWTH` / `RELATIVE_METRIC`. Table 4 conditions are
reported afterward as `CHANGE_KIND`, so they cannot mask the required first code.
External imports are never fetched by candidate-file loading.

The new-data-property unit suffix vocabulary is GiB, MiB, MHz, GHz, Hz, Bit, Byte,
MM, Cm, W, V, A, Percent, Count; extend it explicitly for another physical unit.
A teaching value requires a Russian comment on its teaching individual containing
`условн`. New inverse properties require explicit mirrored domain/range sets.
These are deterministic local operationalizations of Table 4.

Run `PYTHONPYCACHEPREFIX=/private/tmp/nn-pycache python3 -m unittest lab4.tests.test_validator`.
Ten cumulative fixture mutations with expected first code and defect reason are
in `lab4/tests/validator_fixtures`; they are applied to the original OWL document
at runtime, rather than storing ten nearly identical ontology copies.

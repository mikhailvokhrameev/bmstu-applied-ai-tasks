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

### Evolutionary search kernel (task 5)

`search.run(config, mode, seed, resume=False)` returns `RunResult`. `search.yaml`
is YAML 1.2 written in its JSON subset, loaded without additional dependencies.
The specification parameters are frozen: 10 initial evaluations, then 20 × 8
new evaluations; population 10, two unchanged elites, tournaments of 3 distinct
population members, mutation probability 0.7. Equal fitness selects the oldest
candidate ID. Invalid proposals count once and have F=0; infrastructure errors
abort instead of entering selection. Crossover unions cumulative deltas and
always invokes full validation; contradictory add/remove requests are rejected.

Runtime integration is explicit (never serialized into YAML):

```python
from lab4.optimizer.search import load_config, run, ControlGenerator
config = load_config('lab4/optimizer/search.yaml')
config['runtime'] = {
    'control_generator': ControlGenerator(entity_inventory),
    'model_generator': cumulative_model_mutation,
    'duplicate_checker': real_semantic_checker,
    'on_generation': save_completed_generation,
}
result = run(config, 'control', 201)
```

Both generators receive `(parent_delta, run_rng)` and return a **cumulative**
`{'add': [...], 'remove': [...]}` delta relative to the immutable baseline.
The model adapter must use the bounded parser/retry service in `proposals.py`
and include parent state in its context; `ProposalError` after retries consumes
one invalid evaluation. Runtime `validate` is an optional injection seam for
unit tests or a wrapper around the **complete** validator. Production defaults
to `validator.validate` with the supplied real semantic checker.

The control library samples available allowed templates uniformly and then
suitable ontology entities: new subclass, defined class, new data property with
unit suffix/domain/range, four property characteristics, object/data property
hierarchy, cancellation of a previous addition. Its inventory contains sorted
Functional Syntax IRIs in `classes`, `object_properties`, `data_properties`.
It invokes no language model. Templates may produce semantically invalid
candidates; the shared validator decides, with no retry/filtering of invalid
candidates and no budget reduction. This is a library of permitted changes,
not a claim that every permitted Table 4 kind is currently generated.

`RunResult` exposes populations, all evaluations, best candidate, best F per
generation and the final `random.Random.getstate()`. `on_generation` receives
`(generation, population, evaluations, rng_state)` only after a whole generation
completes. Durable checkpoint files and resume are task 6 responsibilities;
`resume=True` explicitly raises until that layer is connected. This module does
not launch series or attest T04/model/analyst acceptance.

Unit tests: `python3 -m unittest lab4.tests.test_search`.

### Durable runs (task 6)

From `lab4`, use `python -m optimizer run --config optimizer/search.yaml
--mode model --seed 101`; from the repository root the equivalent module is
`lab4.optimizer`. Optional `--run-dir PATH` selects a new directory; otherwise a
unique directory under `runs` is created. Continue with `resume --run-dir PATH`;
reconstruct with `replay --run-dir PATH --candidate ID`. Replay uses the OWL bridge
and metric formula, with no language model or embeddings. Exit 1 means a replay
mismatch; configuration/storage errors exit 2 with a diagnostic.

Production config adds a `services` object with explicit `model`, `embedding_model`,
`model_sha256`, `embedding_sha256`, `server_version`, `acceptance_approved: true`,
`inventory` (classes/object_properties/data_properties), and `entities` (full
IRI/category/label/comment inventory for semantic comparison), plus optional
`endpoint`. These values are an operator attestation, not an automatic model
qualification. The supplied frozen search config deliberately has no accepted
manifest: actual models and T04 remain unconfirmed. No real series was run.

The copied config, sealed metadata, Python/platform and pinned jar checksums are
never overwritten. Every evaluation is fsynced in `evaluations.jsonl`, including
full proposal attempts, request context, raw response, validation outcome,
metrics/ri/F, elapsed time, and reconstructed axiom set. Rejected candidates can
have null metrics/axioms when those quantities cannot be defined. Model service
failures are retained in `interruptions.jsonl` without consuming an evaluation.
Checkpoint files are written via fsync and atomic replace after whole generations.
Resume verifies config/core/metadata, checkpoint schema/budget/populations and
committed log prefix; any uncommitted suffix (including a torn final JSON line)
is copied to a unique `audit-*.jsonl` before truncating the active journal.
IDs from that suffix can be reused only in the active, restored generation;
audit records never enter its 170-evaluation count. Runs are single-writer;
concurrent processes must use different directories.

Audit candidates remain replayable after resume: use
`replay --run-dir PATH --candidate audit-<32 hex>:ID`, where `audit-<32 hex>`
is the archive filename without `.jsonl`. Numeric `--candidate ID` continues
to select the active journal. Archive identity distinguishes discarded evaluations
from evaluations that reuse the same numeric ID. Complete archived JSON records
remain readable even when the final append is a torn fragment.

Resume/replay reject a changed JAR inventory or SHA-256 relative to the saved
OWL API/HermiT environment. Model mutations cancel a parent's introduced axiom
when the proposal removes it; crossover retains its conflict-preserving union.
Incomplete HTTP model responses are retained in full (text and raw JSON) in
attempts/interruption logs before the completion error propagates.

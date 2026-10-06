# Compositional Blame Cores - Reproducibility Artifact

This repository implements and checks certificates for the restricted model in *Compositional Blame Cores for Layered Queue Verification*. The scientific code uses only the Python 3.10+ standard library. It does not require a solver, network access, a downloaded data set, or the paper directory.

## Scope

A trace is the column-sum vector of an unknown binary input-by-time matrix. A selected set of input rows has exact packet-count totals. Each finite trace family includes a concrete root member and explicit strict balancing paths from that root to every descendant. Under complete row-slot admissibility, the artifact decides whether the selected totals are compatible with the root and therefore with the whole rooted family. For an incompatible instance it emits and checks a globally minimum-cardinality selected-counter conflict.

This is not an upstream queue verifier, a causal fault diagnosis, a noisy-counter model, or a production deployment. The finite corpus tests the stated interface and implementation.

## Components

- `src/producer.py`: deterministic certificate producer; may call the lower-bound circulation implementation in `src/flow.py`.
- `src/checker.py`: standalone strict checker. It imports no producer, flow, theorem/model, mutation, or oracle module.
- `src/dp_oracle.py`: structurally different dynamic-programming oracle; it imports no producer, flow, model, checker, or mutation module.
- `src/generate_corpus.py`: deterministic 96-case corpus generator.
- `src/micro_exhaustive.py`: bounded exhaustive theorem-versus-DP campaign.
- `src/mutations.py`: complete deterministic malformed-certificate generator; there is no tail limit.
- `src/run.py`: candidate production, checking, oracle comparison, and negative-test execution.
- `src/verify_bundle.py`: replays all frozen certificates and reconstructs/replays every frozen negative mutation. It reads, but does not recompute, the stored micro-exhaustive record.
- `src/compare.py`: compares every deterministic scientific field and every certificate in two result directories, preserving JSON scalar types. Its corpus-only mode applies the same comparison to generated and frozen inputs.

## Retained result

The current frozen result was freshly regenerated from the retained 96-case corpus after the checker repair. The unavailable prior run was not claimed as recovered. The first 12 surviving old certificates matched the regenerated certificates as parsed JSON values; this is not a claim of serialized byte identity. Cases 012-095 and all aggregate result files are new deterministic outputs of the retained source. See `results/regeneration-provenance.md` for the earlier run's provenance and historical host timings.

The frozen evidence contains:

- 96 trace families and 384 traces;
- 32 compatible, 32 upper-conflict, and 32 lower-conflict cases;
- 864 aggregate root-path steps;
- 1,728 concrete matrix-transfer replays (one root matrix for compatible cases and one matrix per deletion witness for incompatible cases);
- 3,616 executed malformed-certificate checks, all rejected;
- 69,421 bounded exhaustive theorem-versus-DP instances and 3,231 sampled exhaustive minimum-core instances, with zero disagreements.

These are separate counters. In particular, 864 aggregate path steps are not the same quantity as 1,728 concrete matrix-transfer executions.

## Fast verification

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 src/verify_bundle.py
```

The test suite covers exact runtime types, `0/false`, `1/true`, equal-valued floats, production-side path vectors, selected-counter ordering, minimum-core checks, import boundaries, and duplicate JSON keys. `verify_bundle.py` uses the standalone checker's duplicate-key-rejecting loader, actually sends every deterministic mutation to the checker, and validates mutation-set uniqueness and ledger equality. It reports micro-exhaustive totals as **recorded, not recomputed**. Separate gate regressions check typed result/corpus comparison and retention of mismatch counts before the exhaustive driver's nonzero failure exit.

## Full isolated regeneration

```bash
sh run_all.sh
```

`run_all.sh` creates a separate temporary candidate directory. It regenerates and compares the corpus, runs the full certificate/oracle/mutation campaign, recomputes the micro-exhaustive campaign, replays candidate evidence, runs all tests, and compares all candidate scientific fields and certificates with `results/frozen/`. It never rewrites `data/corpus.json` or `results/frozen/`. A failed candidate is preserved for inspection.

Manual equivalent:

```bash
work="$(mktemp -d)"
python3 src/generate_corpus.py --output "$work/corpus.json"
python3 src/compare.py --reference-corpus data/corpus.json --candidate-corpus "$work/corpus.json"
python3 src/run.py --corpus "$work/corpus.json" --output "$work/run"
python3 src/micro_exhaustive.py --output "$work/run/micro-exhaustive.json"
python3 src/verify_bundle.py --corpus "$work/corpus.json" --results "$work/run"
python3 src/compare.py results/frozen "$work/run"
```

Comparison ignores JSON whitespace and object-key order, not scalar types or list order; in particular, `1`, `true`, and `1.0` are distinct. Duplicate object keys are rejected before comparison. Only the summary's `python` and `platform` metadata fields are excluded. The exhaustive driver writes its complete count record even when a feasibility or minimum-core discrepancy makes the run fail.

The separate `.github/workflows/scientific-checks.yml` runs the tests, corpus comparison, isolated regeneration, exhaustive recomputation, replay and frozen-result comparison from this flat artifact root. A current Ubuntu 24.04/Python 3.12.14 execution passes all 25 tests and regenerates the exact 96-case corpus, 96 certificates, and four aggregate result objects. The 69,421 feasibility instances and 3,231 sampled minimum-core instances have zero mismatches. Current test and comparison records are in `results/measurements/current-linux/`; prior host timings remain historical. Whole-run time and process resource limits are enforced, with raw output uploaded on failure as well as success.

## Contract details

- Objects use exact key sets; unknown and missing fields are rejected.
- Integer-bearing fields are parsed before comparison and require `type(value) is int`; booleans and equal-valued floats are rejected.
- Selected counters and remaining-port lists are semantic sets with unique ports; serialization order is ignored.
- Compatible certificates contain one full root matrix.
- Incompatible certificates contain the extremal prefix, evaluated inequality, and one full compatible matrix for every one-element deletion.
- Each matrix is independently checked and replayed along every rooted path.
- The released checker copies a full matrix per trace and rescans all columns before and after every path step. Its runtime is therefore not claimed to be linear in serialized certificate size.

## Bibliography assets

`references/` retains the inherited candidate manifest, the resolved 55-record bibliography registry, documented identifier corrections, generated BibTeX and citation-group files, and an offline integrity audit. Bibliographic resolution is not required for the scientific replay and no paper PDFs are redistributed.

## License

See `LICENSE`.

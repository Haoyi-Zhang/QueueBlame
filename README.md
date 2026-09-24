# Compositional Blame Cores — Reproducibility Artifact

This repository implements and checks certificates for a restricted layered queue-verification model. It is deliberately dependency-light: the scientific code uses only the Python 3.10+ standard library and does not require a solver, network access, downloaded dataset, or the paper directory.

## Model

A queue-height trace is represented by column totals of an unknown binary input-by-time matrix. A selected subset of input rows has exact packet-count totals. A trace family carries a common dominating root and explicit unit balancing paths from that root. The checker decides whether the selected totals are compatible with the family. On incompatibility, it verifies a globally minimum-cardinality selected-counter core.

## Components

- `src/producer.py`: deterministic certificate producer; may call the lower-bound circulation implementation in `src/flow.py`.
- `src/checker.py`: standalone strict checker. It does not import producer, flow, model, or oracle code.
- `src/dp_oracle.py`: independently implemented dynamic-programming oracle. It does not import producer, flow, model, or checker code.
- `src/generate_corpus.py`: deterministic 96-case corpus generator.
- `src/micro_exhaustive.py`: independent exhaustive small-instance comparison.
- `src/mutations.py`: systematic malformed-certificate generator.
- `src/run.py`: corpus production, checking, oracle comparison, and mutation campaign.
- `src/verify_bundle.py`: replay of the frozen evidence set.
- `src/compare.py`: semantic comparison of a regeneration against frozen results.

## Fast verification

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 tests/test_contract.py
python3 tests/test_frozen_results.py
python3 src/verify_bundle.py
```

Expected final verifier status includes 96 replayed cases, 69,421 independent micro instances, zero mismatches, and 64 rejected malformed certificates.

## Full deterministic regeneration

```bash
sh run_all.sh
```

The script generates a fresh corpus and result directory, runs the independent exhaustive campaign, and compares all deterministic scientific fields with `results/frozen/`. Runtime, wall-clock, and memory telemetry are excluded from semantic equality because they depend on the host.

## Manual regeneration

```bash
work="$(mktemp -d)"
python3 src/generate_corpus.py --output "$work/corpus.json"
python3 src/run.py --corpus "$work/corpus.json" --output "$work/run"
python3 src/micro_exhaustive.py --output "$work/run/micro-exhaustive.json"
python3 src/compare.py results/frozen "$work/run"
```

## Trust and data notes

- JSON schemas use exact key sets; unknown or missing keys are rejected.
- Integer fields require actual Python integers. Booleans are rejected even though `bool` subclasses `int` in Python.
- Compatible certificates contain a full matrix witness.
- Incompatible certificates contain the extremal prefix, evaluated inequality, and a compatible witness for each one-element deletion.
- Root paths are replayed as concrete same-row matrix transfers for all compatible and deletion witnesses.
- The frozen results are data, not executable code.

## Results and audits

- `results/frozen/`: certificates and immutable paper inputs.
- `results/code-audit.json`: implementation-separation and invariant audit.
- `results/coverage-audit.json`: supplementary branch/line coverage record when coverage.py is available.
- `results/FINAL-AUDIT.json`: combined release snapshot.
- `references/`: provenance-audited bibliography inputs used by the paper.

## License

See `LICENSE`. Publication metadata in `references/` remains subject to the policies of its source registries and publishers; the repository does not redistribute paper PDFs.

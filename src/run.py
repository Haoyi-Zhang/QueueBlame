"""Generate and independently verify the frozen corpus certificates."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from collections import Counter
from pathlib import Path

from checker import Rejection, verify
from common import load_json, write_json
from dp_oracle import feasible, minimum_violating_subset
from mutations import generate
from producer import produce


def run(corpus_path: Path, output: Path, mutation_limit: int = 16) -> dict:
    corpus = load_json(corpus_path)
    if type(corpus) is not dict or set(corpus) != {"schema", "description", "cases"}:
        raise ValueError("corpus shape invalid")
    if corpus["schema"] != "cbcqv-corpus-v2" or type(corpus["cases"]) is not list:
        raise ValueError("corpus schema invalid")
    output.mkdir(parents=True, exist_ok=True)
    certificate_dir = output / "certificates"
    certificate_dir.mkdir(parents=True, exist_ok=True)

    outcomes = []
    mutation_records = []
    status_counts: Counter[str] = Counter()
    violation_counts: Counter[str] = Counter()
    core_sizes: Counter[int] = Counter()
    aggregate_path_steps = 0
    matrix_transport_steps = 0
    oracle_disagreements = 0

    for case in corpus["cases"]:
        selected = {item["port"]: item["count"] for item in case["selected"]}
        oracle_feasible = feasible(case["n"], case["root_h"], selected)
        oracle_core = minimum_violating_subset(case["n"], case["root_h"], selected)
        certificate = produce(case)
        checked = verify(case, certificate)
        producer_feasible = certificate["status"] == "compatible"
        if producer_feasible != oracle_feasible:
            oracle_disagreements += 1
        if not producer_feasible:
            if oracle_core is None or len(oracle_core) != len(certificate["core_ports"]):
                oracle_disagreements += 1
        cert_path = certificate_dir / f"{case['id']}.json"
        write_json(cert_path, certificate)

        status_counts[certificate["status"]] += 1
        if certificate["status"] == "incompatible":
            kind = certificate["violation"]["kind"]
            violation_counts[kind] += 1
            core_sizes[len(certificate["core_ports"])] += 1
        steps = sum(len(trace["path"]) for trace in case["traces"])
        aggregate_path_steps += steps
        matrix_transport_steps += checked["matrix_transport_steps"]
        outcomes.append(
            {
                "case_id": case["id"],
                "status": certificate["status"],
                "violation": None if certificate["status"] == "compatible" else certificate["violation"]["kind"],
                "core_size": None if certificate["status"] == "compatible" else len(certificate["core_ports"]),
                "trace_count": len(case["traces"]),
                "trace_steps": steps,
                "checker": checked["accepted"],
                "oracle_feasible": oracle_feasible,
            }
        )

        for mutation_name, mutated in generate(certificate, limit=mutation_limit):
            accepted = False
            error = None
            try:
                verify(case, mutated)
                accepted = True
            except Rejection as exc:
                error = str(exc)
            if accepted:
                raise AssertionError(f"checker accepted mutation {case['id']}:{mutation_name}")
            mutation_records.append({"case_id": case["id"], "mutation": mutation_name, "rejected": True, "reason": error})

    if oracle_disagreements:
        raise AssertionError(f"producer/oracle disagreements: {oracle_disagreements}")

    summary = {
        "schema": "cbcqv-results-v2",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cases": len(corpus["cases"]),
        "trace_families": len(corpus["cases"]),
        "traces": sum(len(case["traces"]) for case in corpus["cases"]),
        "aggregate_path_steps_validated": aggregate_path_steps,
        "matrix_transport_steps_replayed": matrix_transport_steps,
        "compatible": status_counts["compatible"],
        "incompatible": status_counts["incompatible"],
        "upper_cores": violation_counts["upper"],
        "lower_cores": violation_counts["lower"],
        "core_size_histogram": {str(key): core_sizes[key] for key in sorted(core_sizes)},
        "certificates_accepted": len(outcomes),
        "mutations_rejected": len(mutation_records),
        "mutations_accepted": 0,
        "oracle_disagreements": oracle_disagreements,
        "scientific_work_units": {
            "corpus_oracle_instances": len(corpus["cases"]),
            "certificate_replays": len(outcomes),
            "aggregate_path_steps": aggregate_path_steps,
            "matrix_transport_steps": matrix_transport_steps,
            "malformed_certificate_checks": len(mutation_records),
        },
    }
    write_json(output / "summary.json", summary)
    write_json(output / "outcomes.json", outcomes)
    write_json(output / "mutations.json", mutation_records)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/corpus.json")
    parser.add_argument("--output", default="results/frozen")
    parser.add_argument("--mutation-limit", type=int, default=16)
    args = parser.parse_args()
    summary = run(Path(args.corpus), Path(args.output), args.mutation_limit)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

"""Replay every frozen certificate and all frozen negative-test records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from checker import verify
from common import load_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/corpus.json")
    parser.add_argument("--results", default="results/frozen")
    args = parser.parse_args()
    corpus = load_json(args.corpus)
    cases = {case["id"]: case for case in corpus["cases"]}
    result_root = Path(args.results)
    accepted = 0
    matrix_steps = 0
    for case_id, case in sorted(cases.items()):
        certificate = load_json(result_root / "certificates" / f"{case_id}.json")
        checked = verify(case, certificate)
        accepted += 1
        matrix_steps += checked["matrix_transport_steps"]
    summary = load_json(result_root / "summary.json")
    if accepted != summary["certificates_accepted"]:
        raise AssertionError("summary certificate count mismatch")
    if matrix_steps != summary["matrix_transport_steps_replayed"]:
        raise AssertionError("matrix transport step count mismatch")
    micro = load_json(result_root / "micro-exhaustive.json")
    if micro["feasibility_mismatches"] or micro["core_size_mismatches"]:
        raise AssertionError("micro-exhaustive evidence records a mismatch")
    mutations = load_json(result_root / "mutations.json")
    if len(mutations) != summary["mutations_rejected"] or any(not item["rejected"] for item in mutations):
        raise AssertionError("mutation summary mismatch")
    print(json.dumps({
        "status": "ACCEPT",
        "certificates_replayed": accepted,
        "aggregate_path_steps_validated": summary["aggregate_path_steps_validated"],
        "matrix_transport_steps_replayed": matrix_steps,
        "mutations_recorded_rejected": len(mutations),
        "micro_instances_checked": micro["instances"],
        "sampled_core_instances": micro["sampled_core_instances"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

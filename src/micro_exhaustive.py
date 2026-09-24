"""Exhaustive theorem-vs-DP cross-check on bounded small instances."""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from common import write_json
from dp_oracle import feasible, minimum_violating_subset
from model import classify


def all_dicts(n: int, width: int, max_selected: int):
    ports = range(n)
    yield {}
    for size in range(1, max_selected + 1):
        for subset in itertools.combinations(ports, size):
            for counts in itertools.product(range(width + 1), repeat=size):
                yield dict(zip(subset, counts))


def check_family(n: int, width: int, max_selected: int, core_stride: int) -> dict:
    instances = 0
    mismatches = 0
    core_instances = 0
    core_mismatches = 0
    for h in itertools.product(range(n + 1), repeat=width):
        h_list = list(h)
        for selected in all_dicts(n, width, max_selected):
            instances += 1
            theorem = classify(n, h_list, selected)
            oracle = feasible(n, h_list, selected)
            if theorem.compatible != oracle:
                mismatches += 1
            if (not oracle) and instances % core_stride == 0:
                core_instances += 1
                oracle_core = minimum_violating_subset(n, h_list, selected)
                if oracle_core is None or theorem.cardinality != len(oracle_core):
                    core_mismatches += 1
    return {
        "n": n,
        "width": width,
        "max_selected": max_selected,
        "instances": instances,
        "feasibility_mismatches": mismatches,
        "sampled_core_instances": core_instances,
        "core_size_mismatches": core_mismatches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/frozen/micro-exhaustive.json")
    args = parser.parse_args()
    families = [
        check_family(3, 4, 3, 17),
        check_family(4, 3, 2, 13),
    ]
    summary = {
        "schema": "cbcqv-micro-exhaustive-v2",
        "families": families,
        "instances": sum(item["instances"] for item in families),
        "feasibility_mismatches": sum(item["feasibility_mismatches"] for item in families),
        "sampled_core_instances": sum(item["sampled_core_instances"] for item in families),
        "core_size_mismatches": sum(item["core_size_mismatches"] for item in families),
    }
    if summary["feasibility_mismatches"] or summary["core_size_mismatches"]:
        raise AssertionError(summary)
    write_json(Path(args.output), summary)


if __name__ == "__main__":
    main()

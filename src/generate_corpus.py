"""Generate the deterministic 96-case frozen evaluation corpus."""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from common import write_json
from dp_oracle import feasible, minimum_violating_subset


BASE_ROOT = [6, 6, 5, 4, 3, 2, 1, 0, 0, 0]
UPPER_PATTERNS = {
    1: [8],
    2: [7, 7],
    3: [7, 6, 6],
    4: [6, 6, 6, 5],
}
LOWER_PATTERNS = {
    1: [1],
    2: [2, 2],
    3: [2, 3, 3],
    4: [3, 3, 3, 4],
}


def root_matrix(root_h: list[int], seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    matrix = [[0 for _ in root_h] for _ in range(6)]
    for column, height in enumerate(root_h):
        rows = list(range(6))
        rng.shuffle(rows)
        for row in rows[:height]:
            matrix[row][column] = 1
    return matrix


def one_move(state: list[int]) -> tuple[list[int], dict]:
    choices = []
    for p, high in enumerate(state):
        for q, low in enumerate(state):
            if high >= low + 2:
                choices.append((-(high - low), p, q))
    if not choices:
        raise RuntimeError("root exhausted before requested path length")
    _, p, q = min(choices)
    after = list(state)
    after[p] -= 1
    after[q] += 1
    return after, {"from_col": p, "to_col": q, "before": list(state), "after": list(after)}


def trace_family(root_h: list[int]) -> list[dict]:
    traces = [{"id": "root", "target_h": list(root_h), "path": []}]
    for label, length in (("balanced-1", 1), ("balanced-3", 3), ("balanced-5", 5)):
        current = list(root_h)
        path = []
        for _ in range(length):
            current, step = one_move(current)
            path.append(step)
        traces.append({"id": label, "target_h": current, "path": path})
    return traces


def permute_columns(values: list[int], seed: int) -> list[int]:
    rng = random.Random(seed)
    order = list(range(len(values)))
    rng.shuffle(order)
    return [values[index] for index in order]


def make_case(index: int, category: str, core_size: int | None, replicate: int) -> dict:
    root_h = permute_columns(BASE_ROOT, 10_000 + index)
    traces = trace_family(root_h)
    matrix = root_matrix(root_h, 20_000 + index)
    if category == "compatible":
        selected_ports = list(range(6))[: 1 + (replicate % 6)]
        counts = [sum(matrix[port]) for port in selected_ports]
        expected = "compatible"
    elif category == "upper":
        assert core_size is not None
        selected_ports = list(range(core_size))
        counts = list(UPPER_PATTERNS[core_size])
        expected = "upper"
    elif category == "lower":
        assert core_size is not None
        selected_ports = list(range(core_size))
        counts = list(LOWER_PATTERNS[core_size])
        expected = "lower"
    else:
        raise ValueError(category)
    selected = [{"port": port, "count": count} for port, count in zip(selected_ports, counts)]
    selected_map = {item["port"]: item["count"] for item in selected}
    oracle_ok = feasible(6, root_h, selected_map)
    core = minimum_violating_subset(6, root_h, selected_map)
    if category == "compatible":
        assert oracle_ok and core is None
    else:
        assert not oracle_ok and core is not None and len(core) == core_size
    return {
        "id": f"case-{index:03d}",
        "n": 6,
        "root_h": root_h,
        "selected": selected,
        "traces": traces,
        "expected": expected,
    }


def build() -> dict:
    cases = []
    index = 0
    for replicate in range(32):
        cases.append(make_case(index, "compatible", None, replicate))
        index += 1
    for category in ("upper", "lower"):
        for core_size in range(1, 5):
            for replicate in range(8):
                cases.append(make_case(index, category, core_size, replicate))
                index += 1
    assert len(cases) == 96
    return {
        "schema": "cbcqv-corpus-v2",
        "description": "Deterministic binary-margin trace families; root belongs to each family and dominates every descendant by certified unit transfers.",
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/corpus.json")
    args = parser.parse_args()
    write_json(Path(args.output), build())


if __name__ == "__main__":
    main()

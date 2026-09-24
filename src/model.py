"""Production-side model, theorem bounds, and strict corpus validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


class ContractError(ValueError):
    pass


def _is_int(value: Any) -> bool:
    return type(value) is int


def require_int(value: Any, name: str, lo: int | None = None, hi: int | None = None) -> int:
    if not _is_int(value):
        raise ContractError(f"{name} must be an integer (booleans are rejected)")
    if lo is not None and value < lo:
        raise ContractError(f"{name} below lower bound")
    if hi is not None and value > hi:
        raise ContractError(f"{name} above upper bound")
    return value


def upper_bound(h: Iterable[int], cardinality: int) -> int:
    return sum(min(value, cardinality) for value in h)


def lower_bound(n: int, h: Iterable[int], cardinality: int) -> int:
    return sum(max(0, value - (n - cardinality)) for value in h)


@dataclass(frozen=True)
class Classification:
    compatible: bool
    kind: str | None
    cardinality: int | None
    core_ports: tuple[int, ...]
    lhs: int | None
    rhs: int | None


def classify(n: int, h: list[int], selected: dict[int, int]) -> Classification:
    """Apply the extremal-prefix theorem and return a minimum-cardinality core."""
    descending = sorted(selected.items(), key=lambda item: (-item[1], item[0]))
    ascending = sorted(selected.items(), key=lambda item: (item[1], item[0]))
    running_upper = 0
    running_lower = 0
    for size in range(1, len(selected) + 1):
        running_upper += descending[size - 1][1]
        running_lower += ascending[size - 1][1]
        ub = upper_bound(h, size)
        lb = lower_bound(n, h, size)
        if running_upper > ub:
            return Classification(
                False,
                "upper",
                size,
                tuple(port for port, _ in descending[:size]),
                running_upper,
                ub,
            )
        if running_lower < lb:
            return Classification(
                False,
                "lower",
                size,
                tuple(port for port, _ in ascending[:size]),
                running_lower,
                lb,
            )
    return Classification(True, None, None, (), None, None)


def validate_case(case: Any) -> dict[str, Any]:
    if type(case) is not dict:
        raise ContractError("case must be an object")
    required = {"id", "n", "root_h", "selected", "traces", "expected"}
    if set(case) != required:
        raise ContractError(f"case keys must be exactly {sorted(required)}")
    if type(case["id"]) is not str or not case["id"]:
        raise ContractError("case id must be a nonempty string")
    n = require_int(case["n"], "n", 1)
    if type(case["root_h"]) is not list or not case["root_h"]:
        raise ContractError("root_h must be a nonempty list")
    root_h = [require_int(v, "root_h entry", 0, n) for v in case["root_h"]]
    width = len(root_h)
    if type(case["selected"]) is not list:
        raise ContractError("selected must be a list")
    selected: dict[int, int] = {}
    for item in case["selected"]:
        if type(item) is not dict or set(item) != {"port", "count"}:
            raise ContractError("selected entry has wrong shape")
        port = require_int(item["port"], "selected port", 0, n - 1)
        count = require_int(item["count"], "selected count", 0, width)
        if port in selected:
            raise ContractError("duplicate selected port")
        selected[port] = count
    if type(case["traces"]) is not list or not case["traces"]:
        raise ContractError("traces must be a nonempty list")
    trace_ids: set[str] = set()
    saw_root = False
    for trace in case["traces"]:
        if type(trace) is not dict or set(trace) != {"id", "target_h", "path"}:
            raise ContractError("trace entry has wrong shape")
        trace_id = trace["id"]
        if type(trace_id) is not str or not trace_id or trace_id in trace_ids:
            raise ContractError("trace id invalid or duplicated")
        trace_ids.add(trace_id)
        target = trace["target_h"]
        if type(target) is not list or len(target) != width:
            raise ContractError("target_h has wrong width")
        [require_int(v, "target_h entry", 0, n) for v in target]
        if type(trace["path"]) is not list:
            raise ContractError("path must be a list")
        current = list(root_h)
        for step in trace["path"]:
            if type(step) is not dict or set(step) != {"from_col", "to_col", "before", "after"}:
                raise ContractError("path step has wrong shape")
            p = require_int(step["from_col"], "from_col", 0, width - 1)
            q = require_int(step["to_col"], "to_col", 0, width - 1)
            if p == q:
                raise ContractError("balancing move must use distinct columns")
            before = step["before"]
            after = step["after"]
            if type(before) is not list or type(after) is not list or len(before) != width or len(after) != width:
                raise ContractError("path state width mismatch")
            if before != current:
                raise ContractError("path is not contiguous")
            if before[p] < before[q] + 2:
                raise ContractError("move is not a strict Robin-Hood transfer")
            expected_after = list(before)
            expected_after[p] -= 1
            expected_after[q] += 1
            if after != expected_after:
                raise ContractError("path after-state is incorrect")
            current = list(after)
        if current != target:
            raise ContractError("path does not end at target_h")
        if trace_id == "root":
            if trace["path"] or target != root_h:
                raise ContractError("root trace must have empty path and root_h target")
            saw_root = True
    if not saw_root:
        raise ContractError("trace family must contain its root")
    if case["expected"] not in {"compatible", "upper", "lower"}:
        raise ContractError("expected must be compatible, upper, or lower")
    return {
        "id": case["id"],
        "n": n,
        "root_h": root_h,
        "selected": selected,
        "traces": case["traces"],
        "expected": case["expected"],
    }

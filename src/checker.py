"""Standalone, strict certificate checker for CBCQV margin certificates.

Trust boundary: Python's JSON parser, integer/list/dictionary semantics, and
this file.  The checker imports no producer, flow, theorem, corpus, or oracle
code.  In particular, ``bool`` is rejected wherever an integer is required.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Rejection(ValueError):
    pass


def reject(condition: bool, message: str) -> None:
    if not condition:
        raise Rejection(message)


def integer(value: Any, name: str, lo: int | None = None, hi: int | None = None) -> int:
    reject(type(value) is int, f"{name}: expected integer, not bool or another type")
    if lo is not None:
        reject(value >= lo, f"{name}: below lower bound")
    if hi is not None:
        reject(value <= hi, f"{name}: above upper bound")
    return value


def exact_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    reject(type(value) is dict, f"{name}: expected object")
    reject(set(value) == keys, f"{name}: unexpected or missing keys")
    return value


def upper(h: list[int], size: int) -> int:
    return sum(min(value, size) for value in h)


def lower(n: int, h: list[int], size: int) -> int:
    return sum(max(0, value - (n - size)) for value in h)


def parse_case(case: Any) -> dict[str, Any]:
    obj = exact_object(case, {"id", "n", "root_h", "selected", "traces", "expected"}, "case")
    reject(type(obj["id"]) is str and bool(obj["id"]), "case.id invalid")
    n = integer(obj["n"], "case.n", 1)
    reject(type(obj["root_h"]) is list and len(obj["root_h"]) > 0, "case.root_h invalid")
    h = [integer(v, "case.root_h[]", 0, n) for v in obj["root_h"]]
    width = len(h)
    reject(type(obj["selected"]) is list, "case.selected invalid")
    selected: dict[int, int] = {}
    selected_list: list[dict[str, int]] = []
    for index, raw in enumerate(obj["selected"]):
        item = exact_object(raw, {"port", "count"}, f"case.selected[{index}]")
        port = integer(item["port"], "selected.port", 0, n - 1)
        count = integer(item["count"], "selected.count", 0, width)
        reject(port not in selected, "duplicate selected port")
        selected[port] = count
        selected_list.append({"port": port, "count": count})
    reject(type(obj["traces"]) is list and bool(obj["traces"]), "case.traces invalid")
    trace_ids: set[str] = set()
    traces: list[dict[str, Any]] = []
    saw_root = False
    for trace_index, raw_trace in enumerate(obj["traces"]):
        trace = exact_object(raw_trace, {"id", "target_h", "path"}, f"trace[{trace_index}]")
        trace_id = trace["id"]
        reject(type(trace_id) is str and bool(trace_id) and trace_id not in trace_ids, "trace id invalid")
        trace_ids.add(trace_id)
        reject(type(trace["target_h"]) is list and len(trace["target_h"]) == width, "target_h width")
        target = [integer(v, "target_h[]", 0, n) for v in trace["target_h"]]
        reject(type(trace["path"]) is list, "path invalid")
        current = list(h)
        path: list[dict[str, Any]] = []
        for step_index, raw_step in enumerate(trace["path"]):
            step = exact_object(
                raw_step,
                {"from_col", "to_col", "before", "after"},
                f"trace[{trace_index}].path[{step_index}]",
            )
            p = integer(step["from_col"], "from_col", 0, width - 1)
            q = integer(step["to_col"], "to_col", 0, width - 1)
            reject(p != q, "move columns equal")
            reject(type(step["before"]) is list and len(step["before"]) == width, "before width")
            reject(type(step["after"]) is list and len(step["after"]) == width, "after width")
            before = [integer(v, "before[]", 0, n) for v in step["before"]]
            after = [integer(v, "after[]", 0, n) for v in step["after"]]
            reject(before == current, "path discontinuity")
            reject(before[p] >= before[q] + 2, "move does not reduce a strict imbalance")
            expected_after = list(before)
            expected_after[p] -= 1
            expected_after[q] += 1
            reject(after == expected_after, "incorrect after state")
            current = after
            path.append({"from_col": p, "to_col": q, "before": before, "after": after})
        reject(current == target, "path endpoint mismatch")
        if trace_id == "root":
            reject(target == h and not path, "root trace malformed")
            saw_root = True
        traces.append({"id": trace_id, "target_h": target, "path": path})
    reject(saw_root, "root trace missing")
    reject(obj["expected"] in {"compatible", "upper", "lower"}, "case.expected invalid")
    return {
        "id": obj["id"],
        "n": n,
        "root_h": h,
        "selected": selected,
        "selected_list": selected_list,
        "traces": traces,
        "expected": obj["expected"],
    }


def parse_matrix(matrix: Any, n: int, width: int, name: str) -> list[list[int]]:
    reject(type(matrix) is list and len(matrix) == n, f"{name}: wrong row count")
    parsed: list[list[int]] = []
    for row_index, raw_row in enumerate(matrix):
        reject(type(raw_row) is list and len(raw_row) == width, f"{name}: wrong width")
        row: list[int] = []
        for column_index, value in enumerate(raw_row):
            integer(value, f"{name}[{row_index}][{column_index}]", 0, 1)
            row.append(value)
        parsed.append(row)
    return parsed


def verify_matrix(
    matrix: Any,
    n: int,
    h: list[int],
    required_rows: dict[int, int],
    name: str,
) -> list[list[int]]:
    parsed = parse_matrix(matrix, n, len(h), name)
    for column, expected in enumerate(h):
        actual = sum(parsed[row][column] for row in range(n))
        reject(actual == expected, f"{name}: column {column} sum mismatch")
    for port, expected in required_rows.items():
        reject(sum(parsed[port]) == expected, f"{name}: selected row {port} sum mismatch")
    return parsed


def replay_trace(root_matrix: list[list[int]], trace: dict[str, Any]) -> None:
    matrix = [list(row) for row in root_matrix]
    n = len(matrix)
    for step in trace["path"]:
        p = step["from_col"]
        q = step["to_col"]
        before = [sum(matrix[row][column] for row in range(n)) for column in range(len(matrix[0]))]
        reject(before == step["before"], "matrix path does not match height path")
        candidates = [row for row in range(n) if matrix[row][p] == 1 and matrix[row][q] == 0]
        reject(bool(candidates), "label-preserving transfer has no witnessing row")
        chosen = candidates[0]
        matrix[chosen][p] = 0
        matrix[chosen][q] = 1
        after = [sum(matrix[row][column] for row in range(n)) for column in range(len(matrix[0]))]
        reject(after == step["after"], "replayed transfer has wrong aggregate state")
    final = [sum(matrix[row][column] for row in range(n)) for column in range(len(matrix[0]))]
    reject(final == trace["target_h"], "replayed trace endpoint mismatch")


def verify(case_data: Any, certificate: Any) -> dict[str, Any]:
    case = parse_case(case_data)
    reject(type(certificate) is dict, "certificate must be an object")
    common = {"version", "case_id", "n", "root_h", "selected", "traces", "status"}
    status = certificate.get("status")
    reject(status in {"compatible", "incompatible"}, "certificate.status invalid")
    if status == "compatible":
        exact_object(certificate, common | {"root_matrix"}, "certificate")
    else:
        exact_object(
            certificate,
            common | {"core_ports", "violation", "deletion_witnesses"},
            "certificate",
        )
    reject(certificate["version"] == "cbcqv-margin-v2", "version mismatch")
    reject(certificate["case_id"] == case["id"], "case id mismatch")
    reject(type(certificate["n"]) is int and certificate["n"] == case["n"], "n mismatch")
    reject(certificate["root_h"] == case["root_h"], "root_h mismatch")
    reject(certificate["selected"] == case["selected_list"], "selected counters mismatch")
    reject(certificate["traces"] == case["traces"], "trace certificate does not equal corpus trace")

    if status == "compatible":
        reject(case["expected"] == "compatible", "certificate contradicts frozen expected class")
        matrix = verify_matrix(
            certificate["root_matrix"],
            case["n"],
            case["root_h"],
            case["selected"],
            "root_matrix",
        )
        steps = 0
        for trace in case["traces"]:
            replay_trace(matrix, trace)
            steps += len(trace["path"])
        return {"case_id": case["id"], "accepted": True, "status": status, "matrix_transport_steps": steps}

    reject(case["expected"] in {"upper", "lower"}, "certificate contradicts frozen expected class")
    reject(type(certificate["core_ports"]) is list and bool(certificate["core_ports"]), "core_ports invalid")
    core: list[int] = []
    for index, value in enumerate(certificate["core_ports"]):
        port = integer(value, f"core_ports[{index}]", 0, case["n"] - 1)
        reject(port in case["selected"], "core contains unconstrained port")
        reject(port not in core, "core contains duplicate port")
        core.append(port)
    size = len(core)
    violation = exact_object(certificate["violation"], {"kind", "cardinality", "lhs", "rhs"}, "violation")
    reject(violation["kind"] in {"upper", "lower"}, "violation.kind invalid")
    cardinality = integer(violation["cardinality"], "violation.cardinality", 1, len(case["selected"]))
    lhs = integer(violation["lhs"], "violation.lhs", 0)
    rhs = integer(violation["rhs"], "violation.rhs", 0)
    reject(cardinality == size, "violation cardinality differs from core size")
    actual_lhs = sum(case["selected"][port] for port in core)
    actual_rhs = upper(case["root_h"], size) if violation["kind"] == "upper" else lower(case["n"], case["root_h"], size)
    reject(lhs == actual_lhs and rhs == actual_rhs, "violation arithmetic mismatch")
    if violation["kind"] == "upper":
        reject(lhs > rhs, "upper certificate is not a strict violation")
    else:
        reject(lhs < rhs, "lower certificate is not a strict violation")
    reject(violation["kind"] == case["expected"], "wrong frozen violation class")

    descending = sorted(case["selected"].items(), key=lambda item: (-item[1], item[0]))
    ascending = sorted(case["selected"].items(), key=lambda item: (item[1], item[0]))
    top_sum = 0
    bottom_sum = 0
    for smaller in range(1, size):
        top_sum += descending[smaller - 1][1]
        bottom_sum += ascending[smaller - 1][1]
        reject(top_sum <= upper(case["root_h"], smaller), "a smaller upper core exists")
        reject(bottom_sum >= lower(case["n"], case["root_h"], smaller), "a smaller lower core exists")

    reject(type(certificate["deletion_witnesses"]) is list, "deletion_witnesses invalid")
    reject(len(certificate["deletion_witnesses"]) == size, "wrong number of deletion witnesses")
    seen_dropped: set[int] = set()
    for index, raw in enumerate(certificate["deletion_witnesses"]):
        witness = exact_object(raw, {"dropped_port", "remaining_ports", "matrix"}, f"deletion_witness[{index}]")
        dropped = integer(witness["dropped_port"], "dropped_port", 0, case["n"] - 1)
        reject(dropped in core and dropped not in seen_dropped, "invalid or duplicate dropped port")
        seen_dropped.add(dropped)
        expected_remaining = sorted(port for port in core if port != dropped)
        reject(witness["remaining_ports"] == expected_remaining, "remaining_ports mismatch")
        required = {port: case["selected"][port] for port in expected_remaining}
        witness_matrix = verify_matrix(witness["matrix"], case["n"], case["root_h"], required, f"deletion_matrix[{dropped}]")
        for trace in case["traces"]:
            replay_trace(witness_matrix, trace)
    reject(seen_dropped == set(core), "deletion witnesses do not cover the core")
    return {"case_id": case["id"], "accepted": True, "status": status, "core_size": size,
            "matrix_transport_steps": size * sum(len(trace["path"]) for trace in case["traces"])}


def verify_files(case_path: str | Path, certificate_path: str | Path) -> dict[str, Any]:
    with Path(case_path).open("r", encoding="utf-8") as handle:
        case = json.load(handle)
    with Path(certificate_path).open("r", encoding="utf-8") as handle:
        certificate = json.load(handle)
    return verify(case, certificate)

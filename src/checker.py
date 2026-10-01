"""Standalone strict certificate checker for CBCQV margin certificates.

Trust boundary: Python's JSON parser, integer/list/dictionary semantics, and
this file. The checker imports no producer, flow, theorem, corpus, or oracle
code. Every integer-bearing metadata field is parsed before comparison, so
``False == 0``, ``True == 1``, and equal-valued floats cannot cross the
certificate boundary.
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


def text(value: Any, name: str) -> str:
    reject(type(value) is str and bool(value), f"{name}: expected nonempty string")
    return value


def exact_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    reject(type(value) is dict, f"{name}: expected object")
    reject(set(value) == keys, f"{name}: unexpected or missing keys")
    return value


def upper(h: list[int], size: int) -> int:
    return sum(min(value, size) for value in h)


def lower(n: int, h: list[int], size: int) -> int:
    return sum(max(0, value - (n - size)) for value in h)


def parse_height_vector(value: Any, n: int, width: int | None, name: str) -> list[int]:
    reject(type(value) is list and bool(value), f"{name}: expected nonempty list")
    if width is not None:
        reject(len(value) == width, f"{name}: wrong width")
    return [integer(entry, f"{name}[{index}]", 0, n) for index, entry in enumerate(value)]


def parse_selected(value: Any, n: int, width: int, name: str) -> tuple[dict[int, int], list[dict[str, int]]]:
    reject(type(value) is list, f"{name}: expected list")
    selected: dict[int, int] = {}
    for index, raw in enumerate(value):
        item = exact_object(raw, {"port", "count"}, f"{name}[{index}]")
        port = integer(item["port"], f"{name}[{index}].port", 0, n - 1)
        count = integer(item["count"], f"{name}[{index}].count", 0, width)
        reject(port not in selected, f"{name}: duplicate port")
        selected[port] = count
    canonical = [{"port": port, "count": selected[port]} for port in sorted(selected)]
    return selected, canonical


def parse_traces(value: Any, n: int, root_h: list[int], name: str) -> list[dict[str, Any]]:
    reject(type(value) is list and bool(value), f"{name}: expected nonempty list")
    width = len(root_h)
    trace_ids: set[str] = set()
    traces: list[dict[str, Any]] = []
    saw_root = False
    for trace_index, raw_trace in enumerate(value):
        trace_name = f"{name}[{trace_index}]"
        trace = exact_object(raw_trace, {"id", "target_h", "path"}, trace_name)
        trace_id = text(trace["id"], f"{trace_name}.id")
        reject(trace_id not in trace_ids, f"{trace_name}.id duplicated")
        trace_ids.add(trace_id)
        target = parse_height_vector(trace["target_h"], n, width, f"{trace_name}.target_h")
        reject(type(trace["path"]) is list, f"{trace_name}.path: expected list")
        current = list(root_h)
        path: list[dict[str, Any]] = []
        for step_index, raw_step in enumerate(trace["path"]):
            step_name = f"{trace_name}.path[{step_index}]"
            step = exact_object(raw_step, {"from_col", "to_col", "before", "after"}, step_name)
            p = integer(step["from_col"], f"{step_name}.from_col", 0, width - 1)
            q = integer(step["to_col"], f"{step_name}.to_col", 0, width - 1)
            reject(p != q, f"{step_name}: move columns equal")
            before = parse_height_vector(step["before"], n, width, f"{step_name}.before")
            after = parse_height_vector(step["after"], n, width, f"{step_name}.after")
            reject(before == current, f"{step_name}: path discontinuity")
            reject(before[p] >= before[q] + 2, f"{step_name}: move does not reduce a strict imbalance")
            expected_after = list(before)
            expected_after[p] -= 1
            expected_after[q] += 1
            reject(after == expected_after, f"{step_name}: incorrect after state")
            current = after
            path.append({"from_col": p, "to_col": q, "before": before, "after": after})
        reject(current == target, f"{trace_name}: path endpoint mismatch")
        if trace_id == "root":
            reject(target == root_h and not path, f"{trace_name}: root trace malformed")
            saw_root = True
        traces.append({"id": trace_id, "target_h": target, "path": path})
    reject(saw_root, f"{name}: root trace missing")
    return traces


def parse_case(case: Any) -> dict[str, Any]:
    obj = exact_object(case, {"id", "n", "root_h", "selected", "traces", "expected"}, "case")
    case_id = text(obj["id"], "case.id")
    n = integer(obj["n"], "case.n", 1)
    root_h = parse_height_vector(obj["root_h"], n, None, "case.root_h")
    selected, selected_list = parse_selected(obj["selected"], n, len(root_h), "case.selected")
    traces = parse_traces(obj["traces"], n, root_h, "case.traces")
    reject(type(obj["expected"]) is str and obj["expected"] in {"compatible", "upper", "lower"}, "case.expected invalid")
    return {
        "id": case_id,
        "n": n,
        "root_h": root_h,
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
            row.append(integer(value, f"{name}[{row_index}][{column_index}]", 0, 1))
        parsed.append(row)
    return parsed


def parse_port_list(value: Any, n: int, name: str, *, nonempty: bool = False) -> list[int]:
    reject(type(value) is list and (bool(value) or not nonempty), f"{name}: expected list")
    ports: list[int] = []
    for index, raw in enumerate(value):
        port = integer(raw, f"{name}[{index}]", 0, n - 1)
        reject(port not in ports, f"{name}: duplicate port")
        ports.append(port)
    return sorted(ports)


def verify_matrix(matrix: Any, n: int, h: list[int], required_rows: dict[int, int], name: str) -> list[list[int]]:
    parsed = parse_matrix(matrix, n, len(h), name)
    for column, expected in enumerate(h):
        actual = sum(parsed[row][column] for row in range(n))
        reject(actual == expected, f"{name}: column {column} sum mismatch")
    for port, expected in required_rows.items():
        reject(sum(parsed[port]) == expected, f"{name}: selected row {port} sum mismatch")
    return parsed


def replay_trace(root_matrix: list[list[int]], trace: dict[str, Any]) -> None:
    """Replay one path using a full matrix copy and full column scans."""
    matrix = [list(row) for row in root_matrix]
    n = len(matrix)
    width = len(matrix[0])
    for step in trace["path"]:
        p = step["from_col"]
        q = step["to_col"]
        before = [sum(matrix[row][column] for row in range(n)) for column in range(width)]
        reject(before == step["before"], "matrix path does not match height path")
        candidates = [row for row in range(n) if matrix[row][p] == 1 and matrix[row][q] == 0]
        reject(bool(candidates), "label-preserving transfer has no witnessing row")
        chosen = candidates[0]
        matrix[chosen][p] = 0
        matrix[chosen][q] = 1
        after = [sum(matrix[row][column] for row in range(n)) for column in range(width)]
        reject(after == step["after"], "replayed transfer has wrong aggregate state")
    final = [sum(matrix[row][column] for row in range(n)) for column in range(width)]
    reject(final == trace["target_h"], "replayed trace endpoint mismatch")


def verify(case_data: Any, certificate: Any) -> dict[str, Any]:
    case = parse_case(case_data)
    reject(type(certificate) is dict, "certificate must be an object")
    common = {"version", "case_id", "n", "root_h", "selected", "traces", "status"}
    status = certificate.get("status")
    reject(type(status) is str and status in {"compatible", "incompatible"}, "certificate.status invalid")
    if status == "compatible":
        exact_object(certificate, common | {"root_matrix"}, "certificate")
    else:
        exact_object(certificate, common | {"core_ports", "violation", "deletion_witnesses"}, "certificate")

    version = text(certificate["version"], "certificate.version")
    case_id = text(certificate["case_id"], "certificate.case_id")
    cert_n = integer(certificate["n"], "certificate.n", 1)
    cert_root = parse_height_vector(certificate["root_h"], cert_n, len(case["root_h"]), "certificate.root_h")
    cert_selected, cert_selected_list = parse_selected(certificate["selected"], cert_n, len(cert_root), "certificate.selected")
    cert_traces = parse_traces(certificate["traces"], cert_n, cert_root, "certificate.traces")

    reject(version == "cbcqv-margin-v2", "version mismatch")
    reject(case_id == case["id"], "case id mismatch")
    reject(cert_n == case["n"], "n mismatch")
    reject(cert_root == case["root_h"], "root_h mismatch")
    reject(cert_selected == case["selected"], "selected counters mismatch")
    reject(cert_selected_list == case["selected_list"], "selected canonicalization mismatch")
    reject(cert_traces == case["traces"], "trace certificate does not equal corpus trace")

    if status == "compatible":
        reject(case["expected"] == "compatible", "certificate contradicts frozen expected class")
        matrix = verify_matrix(certificate["root_matrix"], case["n"], case["root_h"], case["selected"], "root_matrix")
        steps = 0
        for trace in cert_traces:
            replay_trace(matrix, trace)
            steps += len(trace["path"])
        return {"case_id": case["id"], "accepted": True, "status": status, "matrix_transport_steps": steps}

    reject(case["expected"] in {"upper", "lower"}, "certificate contradicts frozen expected class")
    core = parse_port_list(certificate["core_ports"], case["n"], "core_ports", nonempty=True)
    for port in core:
        reject(port in case["selected"], "core contains unconstrained port")
    size = len(core)
    violation = exact_object(certificate["violation"], {"kind", "cardinality", "lhs", "rhs"}, "violation")
    kind = violation["kind"]
    reject(type(kind) is str and kind in {"upper", "lower"}, "violation.kind invalid")
    cardinality = integer(violation["cardinality"], "violation.cardinality", 1, len(case["selected"]))
    lhs = integer(violation["lhs"], "violation.lhs", 0)
    rhs = integer(violation["rhs"], "violation.rhs", 0)
    reject(cardinality == size, "violation cardinality differs from core size")
    actual_lhs = sum(case["selected"][port] for port in core)
    actual_rhs = upper(case["root_h"], size) if kind == "upper" else lower(case["n"], case["root_h"], size)
    reject(lhs == actual_lhs and rhs == actual_rhs, "violation arithmetic mismatch")
    reject(lhs > rhs if kind == "upper" else lhs < rhs, f"{kind} certificate is not a strict violation")
    reject(kind == case["expected"], "wrong frozen violation class")

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
    steps_per_matrix = sum(len(trace["path"]) for trace in cert_traces)
    for index, raw in enumerate(certificate["deletion_witnesses"]):
        witness = exact_object(raw, {"dropped_port", "remaining_ports", "matrix"}, f"deletion_witness[{index}]")
        dropped = integer(witness["dropped_port"], f"deletion_witness[{index}].dropped_port", 0, case["n"] - 1)
        reject(dropped in core and dropped not in seen_dropped, "invalid or duplicate dropped port")
        seen_dropped.add(dropped)
        remaining = parse_port_list(witness["remaining_ports"], case["n"], f"deletion_witness[{index}].remaining_ports")
        expected_remaining = sorted(port for port in core if port != dropped)
        reject(remaining == expected_remaining, "remaining_ports mismatch")
        required = {port: case["selected"][port] for port in expected_remaining}
        witness_matrix = verify_matrix(witness["matrix"], case["n"], case["root_h"], required, f"deletion_matrix[{dropped}]")
        for trace in cert_traces:
            replay_trace(witness_matrix, trace)
    reject(seen_dropped == set(core), "deletion witnesses do not cover the core")
    return {
        "case_id": case["id"], "accepted": True, "status": status, "core_size": size,
        "matrix_transport_steps": size * steps_per_matrix,
    }


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise Rejection(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def load_json_strict(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_no_duplicate_object)


def verify_files(case_path: str | Path, certificate_path: str | Path) -> dict[str, Any]:
    return verify(load_json_strict(case_path), load_json_strict(certificate_path))

"""Certificate producer for the tractable binary-margin blame problem."""
from __future__ import annotations

from typing import Any

from flow import feasible_circulation
from model import Classification, classify, lower_bound, validate_case


def construct_matrix(n: int, h: list[int], selected: dict[int, int]) -> list[list[int]] | None:
    """Construct a full binary realization using lower-bound circulation."""
    ports = sorted(selected)
    k = len(ports)
    width = len(h)
    if k == 0:
        matrix = [[0 for _ in range(width)] for _ in range(n)]
        for column, height in enumerate(h):
            for row in range(height):
                matrix[row][column] = 1
        return matrix

    source = 0
    row_base = 1
    col_base = row_base + k
    sink = col_base + width
    node_count = sink + 1
    edges: list[tuple[int, int, int, int]] = []
    row_col_edge_index: dict[tuple[int, int], int] = {}

    for local_row, port in enumerate(ports):
        count = selected[port]
        edges.append((source, row_base + local_row, count, count))
    for local_row in range(k):
        for column in range(width):
            row_col_edge_index[(local_row, column)] = len(edges)
            edges.append((row_base + local_row, col_base + column, 0, 1))
    for column, height in enumerate(h):
        lo = max(0, height - (n - k))
        hi = min(height, k)
        edges.append((col_base + column, sink, lo, hi))
    edges.append((sink, source, 0, sum(h) + sum(selected.values()) + 1))

    feasible, flows = feasible_circulation(node_count, edges)
    if not feasible:
        return None

    matrix = [[0 for _ in range(width)] for _ in range(n)]
    for local_row, port in enumerate(ports):
        for column in range(width):
            flow = flows[row_col_edge_index[(local_row, column)]]
            if flow not in (0, 1):
                raise AssertionError("integral unit edge carried non-binary flow")
            matrix[port][column] = flow

    unselected = [port for port in range(n) if port not in selected]
    for column, height in enumerate(h):
        used = sum(matrix[row][column] for row in ports)
        remaining = height - used
        if not (0 <= remaining <= len(unselected)):
            raise AssertionError("circulation produced impossible residual column")
        for row in unselected[:remaining]:
            matrix[row][column] = 1
    return matrix


def _violation_payload(classification: Classification) -> dict[str, Any]:
    assert not classification.compatible
    return {
        "kind": classification.kind,
        "cardinality": classification.cardinality,
        "lhs": classification.lhs,
        "rhs": classification.rhs,
    }


def produce(case_data: dict[str, Any]) -> dict[str, Any]:
    case = validate_case(case_data)
    classification = classify(case["n"], case["root_h"], case["selected"])
    base: dict[str, Any] = {
        "version": "cbcqv-margin-v2",
        "case_id": case["id"],
        "n": case["n"],
        "root_h": case["root_h"],
        "selected": [
            {"port": port, "count": case["selected"][port]}
            for port in sorted(case["selected"])
        ],
        "traces": case["traces"],
    }
    if classification.compatible:
        matrix = construct_matrix(case["n"], case["root_h"], case["selected"])
        if matrix is None:
            raise AssertionError("theorem accepted but flow construction failed")
        base.update({"status": "compatible", "root_matrix": matrix})
        return base

    core = list(classification.core_ports)
    witnesses = []
    for dropped in core:
        remaining = {
            port: case["selected"][port]
            for port in core
            if port != dropped
        }
        matrix = construct_matrix(case["n"], case["root_h"], remaining)
        if matrix is None:
            raise AssertionError("minimum-cardinality core deletion was not feasible")
        witnesses.append(
            {
                "dropped_port": dropped,
                "remaining_ports": sorted(remaining),
                "matrix": matrix,
            }
        )
    base.update(
        {
            "status": "incompatible",
            "core_ports": core,
            "violation": _violation_payload(classification),
            "deletion_witnesses": witnesses,
        }
    )
    return base

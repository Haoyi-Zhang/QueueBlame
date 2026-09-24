"""A small deterministic Dinic implementation and lower-bound circulation.

This module is used only by the certificate producer.  The independent
checker and the DP oracle do not import it.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable


@dataclass
class _Arc:
    to: int
    rev: int
    cap: int
    initial: int


class Dinic:
    def __init__(self, n: int) -> None:
        if type(n) is not int or n <= 0:
            raise ValueError("n must be a positive integer")
        self.graph: list[list[_Arc]] = [[] for _ in range(n)]

    def add_edge(self, u: int, v: int, cap: int) -> tuple[int, int]:
        if min(u, v, cap) < 0 or u >= len(self.graph) or v >= len(self.graph):
            raise ValueError("invalid edge")
        forward = _Arc(v, len(self.graph[v]), cap, cap)
        reverse = _Arc(u, len(self.graph[u]), 0, 0)
        self.graph[u].append(forward)
        self.graph[v].append(reverse)
        return u, len(self.graph[u]) - 1

    def max_flow(self, source: int, sink: int) -> int:
        total = 0
        n = len(self.graph)
        while True:
            level = [-1] * n
            level[source] = 0
            queue: deque[int] = deque([source])
            while queue:
                u = queue.popleft()
                for arc in self.graph[u]:
                    if arc.cap > 0 and level[arc.to] < 0:
                        level[arc.to] = level[u] + 1
                        queue.append(arc.to)
            if level[sink] < 0:
                return total
            it = [0] * n

            def send(u: int, amount: int) -> int:
                if u == sink:
                    return amount
                while it[u] < len(self.graph[u]):
                    idx = it[u]
                    arc = self.graph[u][idx]
                    if arc.cap > 0 and level[arc.to] == level[u] + 1:
                        pushed = send(arc.to, min(amount, arc.cap))
                        if pushed:
                            arc.cap -= pushed
                            self.graph[arc.to][arc.rev].cap += pushed
                            return pushed
                    it[u] += 1
                return 0

            while True:
                pushed = send(source, 10**18)
                if not pushed:
                    break
                total += pushed


def feasible_circulation(
    number_of_nodes: int,
    edges: Iterable[tuple[int, int, int, int]],
) -> tuple[bool, list[int]]:
    """Find a feasible circulation with integer lower/upper bounds.

    Returns ``(False, [])`` when infeasible.  Otherwise the second component
    gives flows in the same order as ``edges``.
    """
    materialized = list(edges)
    super_source = number_of_nodes
    super_sink = number_of_nodes + 1
    network = Dinic(number_of_nodes + 2)
    demand = [0] * number_of_nodes
    handles: list[tuple[int, int, int]] = []
    for u, v, lower, upper in materialized:
        if not all(type(x) is int for x in (u, v, lower, upper)):
            raise TypeError("circulation bounds must be integers")
        if not (0 <= u < number_of_nodes and 0 <= v < number_of_nodes):
            raise ValueError("circulation endpoint out of range")
        if lower < 0 or upper < lower:
            raise ValueError("invalid lower/upper bound")
        handle_u, handle_idx = network.add_edge(u, v, upper - lower)
        handles.append((handle_u, handle_idx, lower))
        demand[u] -= lower
        demand[v] += lower

    required = 0
    for node, value in enumerate(demand):
        if value > 0:
            network.add_edge(super_source, node, value)
            required += value
        elif value < 0:
            network.add_edge(node, super_sink, -value)

    if network.max_flow(super_source, super_sink) != required:
        return False, []

    flows: list[int] = []
    for u, idx, lower in handles:
        arc = network.graph[u][idx]
        used = arc.initial - arc.cap
        flows.append(lower + used)
    return True, flows

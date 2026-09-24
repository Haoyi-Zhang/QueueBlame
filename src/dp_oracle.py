"""Independent dynamic-programming feasibility oracle.

No imports from the production flow, model, producer, or checker modules are
permitted.  It decides feasibility by enumerating selected-row subsets per
column and retaining reachable partial row-sum vectors.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any


class OracleInputError(ValueError):
    pass


def _strict_int(value: Any, lo: int, hi: int, name: str) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise OracleInputError(f"invalid {name}")
    return value


def feasible(n: int, h: list[int], selected: dict[int, int]) -> bool:
    if type(n) is not int or n < 1:
        raise OracleInputError("invalid n")
    if type(h) is not list or not h:
        raise OracleInputError("invalid h")
    width = len(h)
    heights = [_strict_int(value, 0, n, "height") for value in h]
    if type(selected) is not dict:
        raise OracleInputError("selected must be a dictionary")
    ports = sorted(selected)
    if any(type(port) is not int or not 0 <= port < n for port in ports):
        raise OracleInputError("invalid selected port")
    if len(set(ports)) != len(ports):
        raise OracleInputError("duplicate selected port")
    targets = tuple(_strict_int(selected[port], 0, width, "count") for port in ports)
    k = len(ports)
    if k == 0:
        return True

    masks_by_size: dict[int, list[tuple[int, ...]]] = {}
    for size in range(k + 1):
        masks_by_size[size] = list(combinations(range(k), size))

    states: set[tuple[int, ...]] = {(0,) * k}
    for height in heights:
        lo = max(0, height - (n - k))
        hi = min(height, k)
        options = [subset for size in range(lo, hi + 1) for subset in masks_by_size[size]]
        next_states: set[tuple[int, ...]] = set()
        for state in states:
            for subset in options:
                candidate = list(state)
                valid = True
                for row in subset:
                    candidate[row] += 1
                    if candidate[row] > targets[row]:
                        valid = False
                        break
                if valid:
                    next_states.add(tuple(candidate))
        states = next_states
        if not states:
            return False
    return targets in states


def minimum_violating_subset(n: int, h: list[int], selected: dict[int, int]) -> tuple[int, ...] | None:
    """Exhaustively find a smallest infeasible selected subset.

    This deliberately avoids the extremal-prefix theorem and is used only as
    an independent oracle on small instances.
    """
    ports = sorted(selected)
    for size in range(1, len(ports) + 1):
        for subset in combinations(ports, size):
            restricted = {port: selected[port] for port in subset}
            if not feasible(n, h, restricted):
                return subset
    return None

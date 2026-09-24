"""Systematic malformed-certificate generator used for negative testing."""
from __future__ import annotations

import copy
import json
from typing import Any, Callable


Mutation = tuple[str, dict[str, Any]]


def _changed(original: dict[str, Any], mutated: dict[str, Any]) -> bool:
    return json.dumps(original, sort_keys=True) != json.dumps(mutated, sort_keys=True)


def generate(certificate: dict[str, Any], limit: int = 24) -> list[Mutation]:
    mutations: list[Mutation] = []

    def add(name: str, edit: Callable[[dict[str, Any]], None]) -> None:
        candidate = copy.deepcopy(certificate)
        edit(candidate)
        if _changed(certificate, candidate):
            mutations.append((name, candidate))

    add("wrong-version-type", lambda c: c.__setitem__("version", 2))
    add("wrong-case-id", lambda c: c.__setitem__("case_id", c["case_id"] + "-forged"))
    add("boolean-n", lambda c: c.__setitem__("n", True))
    add("boolean-root-height", lambda c: c["root_h"].__setitem__(0, True))
    add("boolean-selected-port", lambda c: c["selected"][0].__setitem__("port", True))
    add("boolean-selected-count", lambda c: c["selected"][0].__setitem__("count", False))
    add("forged-trace-target", lambda c: c["traces"][1]["target_h"].__setitem__(0, (c["traces"][1]["target_h"][0] + 1) % (c["n"] + 1)))
    add("boolean-path-index", lambda c: c["traces"][1]["path"][0].__setitem__("from_col", True))
    add("forged-path-after", lambda c: c["traces"][1]["path"][0]["after"].__setitem__(0, c["traces"][1]["path"][0]["after"][0] + 1))
    add("unexpected-top-level-key", lambda c: c.__setitem__("comment", "untrusted"))
    add("missing-root-h", lambda c: c.pop("root_h"))

    if certificate["status"] == "compatible":
        add("boolean-matrix-cell", lambda c: c["root_matrix"][0].__setitem__(0, True))
        add("nonbinary-matrix-cell", lambda c: c["root_matrix"][0].__setitem__(0, 2))
        add("missing-matrix-row", lambda c: c["root_matrix"].pop())
        add("short-matrix-row", lambda c: c["root_matrix"][0].pop())
        def flip(c: dict[str, Any]) -> None:
            c["root_matrix"][0][0] = 1 - c["root_matrix"][0][0]
        add("forged-column-sum", flip)
        add("wrong-status", lambda c: c.__setitem__("status", "incompatible"))
    else:
        add("boolean-core-port", lambda c: c["core_ports"].__setitem__(0, True))
        add("duplicate-core-port", lambda c: c["core_ports"].append(c["core_ports"][0]))
        add("wrong-core-cardinality", lambda c: c["violation"].__setitem__("cardinality", c["violation"]["cardinality"] + 1))
        add("boolean-violation-lhs", lambda c: c["violation"].__setitem__("lhs", True))
        add("wrong-violation-lhs", lambda c: c["violation"].__setitem__("lhs", c["violation"]["lhs"] + 1))
        add("wrong-violation-rhs", lambda c: c["violation"].__setitem__("rhs", c["violation"]["rhs"] + 1))
        add("swapped-violation-kind", lambda c: c["violation"].__setitem__("kind", "lower" if c["violation"]["kind"] == "upper" else "upper"))
        add("missing-deletion-witness", lambda c: c["deletion_witnesses"].pop())
        add("boolean-dropped-port", lambda c: c["deletion_witnesses"][0].__setitem__("dropped_port", False))
        add("forged-remaining-ports", lambda c: c["deletion_witnesses"][0]["remaining_ports"].append(c["core_ports"][0]))
        add("boolean-witness-cell", lambda c: c["deletion_witnesses"][0]["matrix"][0].__setitem__(0, True))
        def flip_witness(c: dict[str, Any]) -> None:
            matrix = c["deletion_witnesses"][0]["matrix"]
            matrix[0][0] = 1 - matrix[0][0]
        add("forged-witness-column", flip_witness)
        add("wrong-status", lambda c: c.__setitem__("status", "compatible"))

    return mutations[:limit]

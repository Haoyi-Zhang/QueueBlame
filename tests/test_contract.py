from __future__ import annotations

import ast
import copy
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from checker import Rejection, verify  # noqa: E402
from common import load_json  # noqa: E402
from dp_oracle import feasible, minimum_violating_subset  # noqa: E402
from model import classify, lower_bound, upper_bound  # noqa: E402
from producer import construct_matrix, produce  # noqa: E402


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_json(ROOT / "data" / "corpus.json")
        cls.cases = cls.corpus["cases"]

    def test_directed_bounds(self) -> None:
        h = [6, 6, 5, 4, 3, 2, 1, 0, 0, 0]
        self.assertEqual([upper_bound(h, k) for k in range(1, 5)], [7, 13, 18, 22])
        self.assertEqual([lower_bound(6, h, k) for k in range(1, 5)], [2, 5, 9, 14])

    def test_directed_upper_core_sizes(self) -> None:
        h = [6, 6, 5, 4, 3, 2, 1, 0, 0, 0]
        patterns = {1: [8], 2: [7, 7], 3: [7, 6, 6], 4: [6, 6, 6, 5]}
        for expected_size, counts in patterns.items():
            selected = dict(enumerate(counts))
            result = classify(6, h, selected)
            self.assertFalse(result.compatible)
            self.assertEqual(result.kind, "upper")
            self.assertEqual(result.cardinality, expected_size)
            self.assertFalse(feasible(6, h, selected))
            self.assertEqual(len(minimum_violating_subset(6, h, selected)), expected_size)

    def test_directed_lower_core_sizes(self) -> None:
        h = [6, 6, 5, 4, 3, 2, 1, 0, 0, 0]
        patterns = {1: [1], 2: [2, 2], 3: [2, 3, 3], 4: [3, 3, 3, 4]}
        for expected_size, counts in patterns.items():
            selected = dict(enumerate(counts))
            result = classify(6, h, selected)
            self.assertFalse(result.compatible)
            self.assertEqual(result.kind, "lower")
            self.assertEqual(result.cardinality, expected_size)
            self.assertFalse(feasible(6, h, selected))
            self.assertEqual(len(minimum_violating_subset(6, h, selected)), expected_size)

    def test_all_frozen_cases_produce_and_verify(self) -> None:
        for case in self.cases:
            certificate = produce(case)
            result = verify(case, certificate)
            self.assertTrue(result["accepted"])

    def test_flow_constructor_agrees_with_dp_randomly(self) -> None:
        rng = random.Random(20260918)
        for _ in range(1200):
            n = rng.randint(1, 6)
            width = rng.randint(1, 8)
            h = [rng.randint(0, n) for _ in range(width)]
            ports = list(range(n))
            rng.shuffle(ports)
            selected_ports = ports[: rng.randint(0, n)]
            selected = {port: rng.randint(0, width) for port in selected_ports}
            oracle = feasible(n, h, selected)
            matrix = construct_matrix(n, h, selected)
            self.assertEqual(matrix is not None, oracle)
            if matrix is not None:
                self.assertEqual([sum(matrix[row][col] for row in range(n)) for col in range(width)], h)
                for port, count in selected.items():
                    self.assertEqual(sum(matrix[port]), count)

    def test_bool_is_not_an_integer(self) -> None:
        case = self.cases[0]
        certificate = produce(case)
        forged = copy.deepcopy(certificate)
        forged["n"] = True
        with self.assertRaises(Rejection):
            verify(case, forged)
        forged = copy.deepcopy(certificate)
        forged["selected"][0]["port"] = False
        with self.assertRaises(Rejection):
            verify(case, forged)
        forged = copy.deepcopy(certificate)
        forged["root_matrix"][0][0] = True
        with self.assertRaises(Rejection):
            verify(case, forged)

    def test_nonminimum_core_is_rejected_before_witness_acceptance(self) -> None:
        case = copy.deepcopy(next(item for item in self.cases if item["expected"] == "upper" and len(item["selected"]) == 1))
        case["selected"] = [{"port": 0, "count": 8}, {"port": 1, "count": 7}]
        certificate = produce(case)
        self.assertEqual(certificate["core_ports"], [0])
        forged = copy.deepcopy(certificate)
        forged["core_ports"] = [0, 1]
        forged["violation"] = {"kind": "upper", "cardinality": 2, "lhs": 15, "rhs": 13}
        with self.assertRaises(Rejection):
            verify(case, forged)

    def test_trace_paths_preserve_every_row_sum(self) -> None:
        compatible = [case for case in self.cases if case["expected"] == "compatible"]
        for case in compatible:
            certificate = produce(case)
            root = certificate["root_matrix"]
            root_sums = [sum(row) for row in root]
            for trace in case["traces"]:
                matrix = [list(row) for row in root]
                for step in trace["path"]:
                    p, q = step["from_col"], step["to_col"]
                    row = next(r for r in range(case["n"]) if matrix[r][p] == 1 and matrix[r][q] == 0)
                    matrix[row][p] = 0
                    matrix[row][q] = 1
                self.assertEqual([sum(row) for row in matrix], root_sums)
                self.assertEqual(
                    [sum(matrix[row][col] for row in range(case["n"])) for col in range(len(case["root_h"]))],
                    trace["target_h"],
                )

    def test_checker_and_oracle_import_boundaries(self) -> None:
        forbidden_checker = {"producer", "flow", "model", "dp_oracle", "generate_corpus"}
        forbidden_oracle = {"producer", "flow", "model", "checker", "generate_corpus"}
        for filename, forbidden in (("checker.py", forbidden_checker), ("dp_oracle.py", forbidden_oracle)):
            tree = ast.parse((SRC / filename).read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & forbidden, f"{filename} imports forbidden modules: {imported & forbidden}")

    def test_certificate_json_round_trip(self) -> None:
        for case in self.cases[:12]:
            certificate = produce(case)
            round_trip = json.loads(json.dumps(certificate))
            self.assertEqual(verify(case, round_trip)["accepted"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

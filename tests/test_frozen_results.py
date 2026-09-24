from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from checker import verify  # noqa: E402
from common import load_json  # noqa: E402


class FrozenResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_json(ROOT / "data" / "corpus.json")
        cls.results = ROOT / "results" / "frozen"

    def test_summary_contract(self) -> None:
        summary = load_json(self.results / "summary.json")
        self.assertEqual(summary["cases"], 96)
        self.assertEqual(summary["traces"], 384)
        self.assertEqual(summary["aggregate_path_steps_validated"], 864)
        self.assertEqual(summary["matrix_transport_steps_replayed"], 1728)
        self.assertEqual(summary["compatible"], 32)
        self.assertEqual(summary["upper_cores"], 32)
        self.assertEqual(summary["lower_cores"], 32)
        self.assertEqual(summary["mutations_accepted"], 0)
        self.assertEqual(summary["oracle_disagreements"], 0)

    def test_every_frozen_certificate_replays(self) -> None:
        for case in self.corpus["cases"]:
            certificate = load_json(self.results / "certificates" / f"{case['id']}.json")
            self.assertTrue(verify(case, certificate)["accepted"])

    def test_micro_exhaustive_has_no_mismatch(self) -> None:
        micro = load_json(self.results / "micro-exhaustive.json")
        self.assertEqual(micro["instances"], 69421)
        self.assertEqual(micro["feasibility_mismatches"], 0)
        self.assertEqual(micro["core_size_mismatches"], 0)

    def test_mutation_ledger_is_all_rejected(self) -> None:
        mutations = load_json(self.results / "mutations.json")
        self.assertGreaterEqual(len(mutations), 1500)
        self.assertTrue(all(item["rejected"] for item in mutations))


if __name__ == "__main__":
    unittest.main(verbosity=2)

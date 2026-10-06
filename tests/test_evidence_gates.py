"""Regressions for exact result comparison, strict replay and failure evidence."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import compare
import micro_exhaustive
import verify_bundle
from checker import Rejection
from common import load_json


class EvidenceGateTests(unittest.TestCase):
    def test_json_types_are_not_value_aliases(self):
        for left, right in ((0, False), (1, True), (96, 96.0), (True, 1),
                            ({"nested": [0, True]}, {"nested": [False, 1]})):
            with self.subTest(left=left, right=right):
                self.assertFalse(compare.same_json(left, right))
        self.assertTrue(compare.same_json({"a": 1, "b": [False]}, {"b": [False], "a": 1}))

    def test_common_loader_rejects_nested_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "duplicate.json"
            path.write_text('{"cases":[{"n":6,"n":6}]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key: n"):
                load_json(path)

    def test_corpus_comparison_rejects_equal_valued_float(self):
        with tempfile.TemporaryDirectory() as work:
            left, right = Path(work) / "left.json", Path(work) / "right.json"
            left.write_text('{"cases":[{"n":6}]}', encoding="utf-8")
            right.write_text('{"cases":[{"n":6.0}]}', encoding="utf-8")
            with patch.object(sys, "argv", ["compare", "--reference-corpus", str(left), "--candidate-corpus", str(right)]):
                with self.assertRaisesRegex(SystemExit, "corpus mismatch"):
                    compare.main()

    def test_result_comparison_checks_types_at_each_payload(self):
        baseline = {"summary.json": {"python": "old", "platform": "old", "cases": 1},
                    "outcomes.json": [{"checker": True}],
                    "mutations.json": [{"rejected": True}],
                    "micro-exhaustive.json": {"instances": 1},
                    "certificates/case-000.json": {"matrix": [[1]]}}
        edits = {"summary.json": {"python": "old", "platform": "old", "cases": 1.0},
                 "outcomes.json": [{"checker": 1}],
                 "mutations.json": [{"rejected": 1}],
                 "micro-exhaustive.json": {"instances": True},
                 "certificates/case-000.json": {"matrix": [[True]]}}
        with tempfile.TemporaryDirectory() as work:
            left, right = Path(work) / "left", Path(work) / "right"
            for name, value in baseline.items():
                for root in (left, right):
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(value), encoding="utf-8")
            # Host/version differences remain the only excluded fields.
            metadata = dict(baseline["summary.json"], python="new", platform="new")
            (right / "summary.json").write_text(json.dumps(metadata), encoding="utf-8")
            with patch.object(sys, "argv", ["compare", str(left), str(right)]), contextlib.redirect_stdout(io.StringIO()):
                compare.main()
            (right / "summary.json").write_text(json.dumps(baseline["summary.json"]), encoding="utf-8")
            for name, value in edits.items():
                with self.subTest(file=name):
                    (right / name).write_text(json.dumps(value), encoding="utf-8")
                    with patch.object(sys, "argv", ["compare", str(left), str(right)]):
                        with self.assertRaises(SystemExit):
                            compare.main()
                    (right / name).write_text(json.dumps(baseline[name]), encoding="utf-8")

    def test_public_bundle_replay_rejects_duplicate_certificate_key(self):
        case = load_json(ROOT / "data" / "corpus.json")["cases"][0]
        certificate = (ROOT / "results" / "frozen" / "certificates" / "case-000.json").read_text(encoding="utf-8").rstrip()
        with tempfile.TemporaryDirectory() as work:
            directory = Path(work)
            corpus = directory / "corpus.json"
            corpus.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
            certdir = directory / "results" / "certificates"
            certdir.mkdir(parents=True)
            (certdir / "case-000.json").write_text(certificate[:-1] + ',"n":6}', encoding="utf-8")
            with patch.object(sys, "argv", ["verify_bundle", "--corpus", str(corpus), "--results", str(certdir.parent)]):
                with self.assertRaisesRegex(Rejection, "duplicate JSON key: n"):
                    verify_bundle.main()

    def test_micro_failure_counts_are_written_before_nonzero_gate(self):
        clean = {"n": 1, "width": 1, "max_selected": 1, "instances": 2,
                 "feasibility_mismatches": 0, "sampled_core_instances": 1, "core_size_mismatches": 0}
        for key in ("feasibility_mismatches", "core_size_mismatches"):
            with self.subTest(mismatch=key), tempfile.TemporaryDirectory() as work:
                changed = copy.deepcopy(clean)
                changed[key] = 1
                output = Path(work) / "counts.json"
                with patch.object(micro_exhaustive, "check_family", side_effect=[clean, changed]), patch.object(sys, "argv", ["micro", "--output", str(output)]):
                    with self.assertRaises(AssertionError):
                        micro_exhaustive.main()
                saved = load_json(output)
                self.assertEqual(saved[key], 1)
                self.assertEqual(saved["instances"], 4)
                self.assertEqual(saved["sampled_core_instances"], 2)
                self.assertEqual(saved["families"], [clean, changed])

    def test_bibliography_identity_tracks_resolved_metadata(self):
        references = ROOT / "references"
        records = load_json(references / "resolved-references.json")["records"]
        report = load_json(references / "reference-audit.json")
        audited = {item["key"]: item for item in report["records"]}
        paths = [references / "references.bib"]
        paper = ROOT.parent / "paper" / "references.bib"
        if paper.is_file():
            paths.append(paper)
        for path in paths:
            entries = {}
            for entry_type, key, body in re.findall(r"(?ms)^@(\w+)\{([^,]+),\n(.*?)^\}", path.read_text(encoding="utf-8")):
                entries[key] = {"type": entry_type, **dict(re.findall(r"(?m)^\s*(\w+)\s*=\s*\{(.*)\},?\s*$", body))}
            self.assertEqual(set(entries), {record["key"] for record in records})
            for record in records:
                with self.subTest(bibliography=path.name, key=record["key"]):
                    expected = {key: str(record[key]) for key in ("type", "author", "title", "journal", "booktitle", "series", "publisher", "volume", "number", "pages", "year", "doi") if record.get(key)}
                    expected["url"] = "https://doi.org/" + record["doi"] if record.get("doi") else record["url"]
                    self.assertEqual(entries[record["key"]], expected)
                    for key in ("identifier", "verification_url", "title", "author", "theme", "year"):
                        self.assertEqual(audited[record["key"]][key], record[key])


if __name__ == "__main__":
    unittest.main(verbosity=2)

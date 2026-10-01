from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
RESULTS = ROOT / "results" / "frozen"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

corpus = load(ROOT / "data" / "corpus.json")
summary = load(RESULTS / "summary.json")
micro = load(RESULTS / "micro-exhaustive.json")
mutations = load(RESULTS / "mutations.json")
certs = sorted((RESULTS / "certificates").glob("case-*.json"))
case_ids = [case["id"] for case in corpus["cases"]]

forbidden = {
    "checker.py": {"producer", "flow", "model", "dp_oracle", "generate_corpus", "mutations"},
    "dp_oracle.py": {"producer", "flow", "model", "checker", "generate_corpus", "mutations"},
}
imports: dict[str, list[str]] = {}
import_ok = True
for filename, denied in forbidden.items():
    tree = ast.parse((SRC / filename).read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    imports[filename] = sorted(found)
    import_ok &= not bool(found & denied)

keys = [(record["case_id"], record["mutation"]) for record in mutations]
checks = {
    "corpus_cases_96": len(case_ids) == 96,
    "certificates_match_cases": [path.stem for path in certs] == case_ids,
    "summary_cases_match": summary["cases"] == len(case_ids),
    "summary_certificate_count_match": summary["certificates_accepted"] == len(certs),
    "summary_mutation_count_match": summary["mutations_attempted"] == len(mutations),
    "mutation_keys_unique": len(keys) == len(set(keys)),
    "all_mutations_rejected": summary["mutations_accepted"] == 0 and all(record["rejected"] for record in mutations),
    "oracle_agreement": summary["oracle_disagreements"] == 0,
    "micro_agreement": micro["feasibility_mismatches"] == 0 and micro["core_size_mismatches"] == 0,
    "checker_oracle_import_boundaries": import_ok,
    "fresh_regeneration_disclosed": summary["provenance"]["lost_prior_run_recovered"] is False,
}
report = {
    "schema": "cbcqv-artifact-release-audit-v1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "counts": {
        "cases": len(case_ids),
        "certificates": len(certs),
        "mutations": len(mutations),
        "micro_instances": micro["instances"],
        "aggregate_path_steps": summary["aggregate_path_steps_validated"],
        "matrix_transport_steps": summary["matrix_transport_steps_replayed"],
    },
    "imports": imports,
}
(ROOT / "results" / "release-audit.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps({"status": report["status"], "checks": checks}, sort_keys=True))
if report["status"] != "PASS":
    raise SystemExit(1)

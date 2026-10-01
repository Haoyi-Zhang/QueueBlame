from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
ARTIFACT = ROOT / "artifact" / "references"

bib_text = (PAPER / "references.bib").read_text(encoding="utf-8")
main_text = (PAPER / "main.tex").read_text(encoding="utf-8")
group_text = (PAPER / "reference-groups.tex").read_text(encoding="utf-8")
aux_text = (PAPER / "main.aux").read_text(encoding="utf-8")
bbl_text = (PAPER / "main.bbl").read_text(encoding="utf-8")

bib_keys = re.findall(r"(?m)^@\w+\{([^,]+),", bib_text)
if len(bib_keys) != len(set(bib_keys)):
    raise SystemExit("duplicate BibTeX key")

macro_defs: dict[str, list[str]] = {}
for macro, keys in re.findall(r"\\newcommand\{\\([A-Za-z]+Refs)\}\{\\cite\{([^}]*)\}\}", group_text):
    macro_defs[macro] = [key.strip() for key in keys.split(",") if key.strip()]

macro_uses: dict[str, list[int]] = {}
for macro in macro_defs:
    macro_uses[macro] = [index for index, line in enumerate(main_text.splitlines(), 1) if f"\\{macro}" in line]

source_keys = set()
for macro, keys in macro_defs.items():
    if macro_uses[macro]:
        source_keys.update(keys)
for block in re.findall(r"\\cite\{([^}]*)\}", main_text):
    source_keys.update(key.strip() for key in block.split(",") if key.strip())

aux_keys = set()
for block in re.findall(r"\\citation\{([^}]*)\}", aux_text):
    aux_keys.update(key.strip() for key in block.split(",") if key.strip())
bbl_keys = set(re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", bbl_text))
bib_set = set(bib_keys)

checks = {
    "bib_keys_unique": len(bib_keys) == len(bib_set),
    "all_group_macros_used_once": all(len(lines) == 1 for lines in macro_uses.values()),
    "no_nocite": "\\nocite" not in main_text and "\\nocite" not in group_text,
    "source_equals_bib": source_keys == bib_set,
    "aux_equals_bib": aux_keys == bib_set,
    "bbl_equals_bib": bbl_keys == bib_set,
}
report = {
    "schema": "cbcqv-bibliography-usage-audit-v1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "reference_count": len(bib_keys),
    "checks": checks,
    "macro_uses": macro_uses,
    "macro_key_counts": {macro: len(keys) for macro, keys in sorted(macro_defs.items())},
    "missing_from_source": sorted(bib_set - source_keys),
    "missing_from_aux": sorted(bib_set - aux_keys),
    "missing_from_bbl": sorted(bib_set - bbl_keys),
    "unknown_in_source": sorted(source_keys - bib_set),
    "unknown_in_aux": sorted(aux_keys - bib_set),
    "unknown_in_bbl": sorted(bbl_keys - bib_set),
    "keys": bib_keys,
}
(ARTIFACT / "bibliography-usage-audit.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(json.dumps({"status": report["status"], "references": len(bib_keys), "checks": checks}, sort_keys=True))
if report["status"] != "PASS":
    raise SystemExit(1)

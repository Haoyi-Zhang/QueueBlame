"""Compare two deterministic result directories, ignoring host metadata."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


IGNORED_SUMMARY_KEYS = {"python", "platform"}


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalized_summary(path: Path):
    value = load(path)
    return {key: value[key] for key in value if key not in IGNORED_SUMMARY_KEYS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference")
    parser.add_argument("candidate")
    args = parser.parse_args()
    reference = Path(args.reference)
    candidate = Path(args.candidate)
    if normalized_summary(reference / "summary.json") != normalized_summary(candidate / "summary.json"):
        raise SystemExit("summary mismatch")
    for filename in ("outcomes.json", "mutations.json", "micro-exhaustive.json"):
        if load(reference / filename) != load(candidate / filename):
            raise SystemExit(f"{filename} mismatch")
    reference_certs = sorted((reference / "certificates").glob("*.json"))
    candidate_certs = sorted((candidate / "certificates").glob("*.json"))
    if [p.name for p in reference_certs] != [p.name for p in candidate_certs]:
        raise SystemExit("certificate filename mismatch")
    for left, right in zip(reference_certs, candidate_certs):
        if load(left) != load(right):
            raise SystemExit(f"certificate mismatch: {left.name}")
    print("MATCH")


if __name__ == "__main__":
    main()

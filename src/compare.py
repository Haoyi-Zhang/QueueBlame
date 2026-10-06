"""Compare two deterministic result directories, ignoring host metadata."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import canonical_json, load_json


IGNORED_SUMMARY_KEYS = {"python", "platform"}


def load(path: Path):
    return load_json(path)


def same_json(left, right) -> bool:
    """Compare JSON values without Python's bool/int/float equality aliases.

    Object-key order and whitespace are not scientific fields; scalar types
    and list order are. Both inputs have already passed duplicate-key parsing.
    """
    return canonical_json(left) == canonical_json(right)


def normalized_summary(path: Path):
    value = load(path)
    return {key: value[key] for key in value if key not in IGNORED_SUMMARY_KEYS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", nargs="?")
    parser.add_argument("candidate", nargs="?")
    parser.add_argument("--reference-corpus")
    parser.add_argument("--candidate-corpus")
    args = parser.parse_args()
    if bool(args.reference) != bool(args.candidate):
        parser.error("both result directories are required")
    if bool(args.reference_corpus) != bool(args.candidate_corpus):
        parser.error("both corpus files are required")
    if not args.reference and not args.reference_corpus:
        parser.error("provide result directories or corpus files")
    if args.reference_corpus:
        if not same_json(load(Path(args.reference_corpus)), load(Path(args.candidate_corpus))):
            raise SystemExit("corpus mismatch")
        print("CORPUS_MATCH")
    if not args.reference:
        return
    reference = Path(args.reference)
    candidate = Path(args.candidate)
    if not same_json(normalized_summary(reference / "summary.json"), normalized_summary(candidate / "summary.json")):
        raise SystemExit("summary mismatch")
    for filename in ("outcomes.json", "mutations.json", "micro-exhaustive.json"):
        if not same_json(load(reference / filename), load(candidate / filename)):
            raise SystemExit(f"{filename} mismatch")
    reference_certs = sorted((reference / "certificates").glob("*.json"))
    candidate_certs = sorted((candidate / "certificates").glob("*.json"))
    if [p.name for p in reference_certs] != [p.name for p in candidate_certs]:
        raise SystemExit("certificate filename mismatch")
    for left, right in zip(reference_certs, candidate_certs):
        if not same_json(load(left), load(right)):
            raise SystemExit(f"certificate mismatch: {left.name}")
    print("MATCH")


if __name__ == "__main__":
    main()

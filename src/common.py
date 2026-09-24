"""Shared *data-only* helpers for the CBCQV artifact.

The independent checker and the dynamic-programming oracle intentionally do
not import this module.  Production code may use it for canonical JSON I/O.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(canonical_json(data), encoding="utf-8")

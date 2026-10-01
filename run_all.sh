#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd); cd "$ROOT"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/cbcqv-candidate.XXXXXX"); SUCCESS=0
cleanup(){ status=$?; if [ "$SUCCESS" -eq 1 ]; then rm -rf "$WORK"; else printf 'Candidate evidence preserved after failure: %s\n' "$WORK" >&2; fi; exit "$status"; }
trap cleanup EXIT HUP INT TERM
python3 src/generate_corpus.py --output "$WORK/corpus.json"
python3 - "$WORK/corpus.json" <<'PY'
import json,sys
from pathlib import Path
if json.loads(Path('data/corpus.json').read_text()) != json.loads(Path(sys.argv[1]).read_text()): raise SystemExit('candidate corpus differs from frozen corpus')
print('CORPUS_MATCH')
PY
python3 src/run.py --corpus "$WORK/corpus.json" --output "$WORK/results"
python3 src/micro_exhaustive.py --output "$WORK/results/micro-exhaustive.json"
python3 src/verify_bundle.py --corpus "$WORK/corpus.json" --results "$WORK/results"
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 src/compare.py results/frozen "$WORK/results"
SUCCESS=1; printf 'REGENERATION_MATCH\n'

#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1
python3 src/generate_corpus.py --output data/corpus.json
rm -rf results/frozen
python3 src/run.py --corpus data/corpus.json --output results/frozen --mutation-limit 16
python3 src/micro_exhaustive.py --output results/frozen/micro-exhaustive.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 src/verify_bundle.py --corpus data/corpus.json --results results/frozen

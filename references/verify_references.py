"""Offline integrity audit for the curated, traceable CBCQV bibliography."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT.parents[1] / 'paper'
resolved = json.loads((ROOT / 'resolved-references.json').read_text(encoding='utf-8'))
records = resolved['records']
report = json.loads((ROOT / 'reference-audit.json').read_text(encoding='utf-8'))

assert resolved['schema'] == 'cbcqv-resolved-references-v1'
assert resolved['count'] == len(records) == 55
keys = [record['key'] for record in records]
identifiers = [record['identifier'].lower() for record in records]
assert len(keys) == len(set(keys))
assert len(identifiers) == len(set(identifiers))
expected_themes = {'combinatorics': 8, 'formal': 10, 'diagnosis': 8, 'network': 12, 'queueing': 12, 'reproducibility': 5}
assert Counter(record['theme'] for record in records) == Counter(expected_themes)
for record in records:
    assert record['author'] and record['title'] and type(record['year']) is int
    assert record['verification_status'] == 'curated_against_stable_identifier'
    assert record['verification_url'].startswith('https://')
    if record.get('doi'):
        assert re.fullmatch(r'10\.\S+?/\S+', record['doi'])
        assert record['identifier'] == record['doi']
    else:
        assert record['identifier'] == record['url']

bib = (PAPER / 'references.bib').read_text(encoding='utf-8')
bib_keys = re.findall(r'^@\w+\{([^,]+),', bib, flags=re.M)
assert bib_keys == keys
assert len(re.findall(r'^\s*doi\s*=', bib, flags=re.M)) == sum('doi' in record for record in records)
assert '\\nocite' not in (PAPER / 'main.tex').read_text(encoding='utf-8')

groups = (PAPER / 'reference-groups.tex').read_text(encoding='utf-8')
used: list[str] = []
for block in re.findall(r'\\cite\{([^}]+)\}', groups):
    used.extend(key.strip() for key in block.split(',') if key.strip())
assert len(used) == len(keys)
assert set(used) == set(keys)
assert len(used) == len(set(used))
assert f'\\newcommand{{\\VerifiedReferenceCount}}{{{len(keys)}}}' in groups

assert report['count'] == len(records)
assert report['theme_counts'] == expected_themes
assert report['failures'] == []
assert {item['key'] for item in report['records']} == set(keys)

# Confirm that every selected key existed in the inherited candidate manifest,
# and that any changed inherited identifier is documented as a correction.
candidates = {item['key']: item for item in json.loads((ROOT / 'candidates.json').read_text(encoding='utf-8'))}
for record in records:
    assert record['key'] in candidates
    inherited = candidates[record['key']].get('doi') or candidates[record['key']].get('official_url')
    if inherited and inherited.lower() != record['identifier'].lower():
        assert record.get('correction'), f"undocumented identifier correction: {record['key']}"

print(json.dumps({
    'status': 'PASS',
    'references': len(keys),
    'themes': expected_themes,
    'documented_corrections': len(report['corrections']),
    'all_grouped_once': True,
    'nocite_used': False,
}, sort_keys=True))

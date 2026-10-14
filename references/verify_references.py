"""Offline integrity audit for the curated, traceable CBCQV bibliography."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from reference_history import reconcile_audit_records

ROOT = Path(__file__).resolve().parent
PAPER = ROOT.parents[1] / 'paper'
resolved = json.loads((ROOT / 'resolved-references.json').read_text(encoding='utf-8'))
records = resolved['records']
report = json.loads((ROOT / 'reference-audit.json').read_text(encoding='utf-8'))

def require(condition: bool, message: str) -> None:
    """Keep audit gates active under Python's optimized mode."""
    if not condition:
        raise ValueError(message)


require(resolved['schema'] == 'cbcqv-resolved-references-v1', 'unexpected resolved-reference schema')
require(resolved['count'] == len(records) == 55, 'reference count mismatch')
keys = [record['key'] for record in records]
identifiers = [record['identifier'].lower() for record in records]
require(len(keys) == len(set(keys)), 'duplicate reference key')
require(len(identifiers) == len(set(identifiers)), 'duplicate reference identifier')
expected_themes = {'combinatorics': 8, 'formal': 10, 'diagnosis': 8, 'network': 12, 'queueing': 12, 'reproducibility': 5}
require(Counter(record['theme'] for record in records) == Counter(expected_themes), 'reference theme counts mismatch')
for record in records:
    require(bool(record['author'] and record['title']) and type(record['year']) is int, f"invalid metadata: {record['key']}")
    require(record['verification_status'] == 'curated_against_stable_identifier', f"unexpected verification status: {record['key']}")
    require(record['verification_url'].startswith('https://'), f"invalid verification URL: {record['key']}")
    if record.get('doi'):
        require(re.fullmatch(r'10\.\S+?/\S+', record['doi']) is not None, f"invalid DOI: {record['key']}")
        require(record['identifier'] == record['doi'], f"DOI identifier mismatch: {record['key']}")
    else:
        require(record['identifier'] == record['url'], f"URL identifier mismatch: {record['key']}")

bib = (PAPER / 'references.bib').read_text(encoding='utf-8')
bib_keys = re.findall(r'^@(?!IEEEtranBSTCTL\b)\w+\{([^,]+),', bib, flags=re.M)
require(bib_keys == keys, 'BibTeX keys or order mismatch')
require(len(re.findall(r'^\s*doi\s*=', bib, flags=re.M)) == sum('doi' in record for record in records), 'BibTeX DOI count mismatch')
require('\\nocite' not in (PAPER / 'main.tex').read_text(encoding='utf-8'), 'nocite is not allowed by this audit')

groups = (PAPER / 'reference-groups.tex').read_text(encoding='utf-8')
used: list[str] = []
for block in re.findall(r'\\cite\{([^}]+)\}', groups):
    used.extend(key.strip() for key in block.split(',') if key.strip())
require(len(used) == len(keys), 'grouped reference count mismatch')
require(set(used) == set(keys), 'grouped reference key mismatch')
require(len(used) == len(set(used)), 'duplicate grouped reference')
require(f'\\newcommand{{\\VerifiedReferenceCount}}{{{len(keys)}}}' in groups, 'rendered reference count mismatch')

require(report['count'] == len(records), 'audit report count mismatch')
require(report['theme_counts'] == expected_themes, 'audit report theme counts mismatch')
require(report['failures'] == [], 'audit report contains failures')
require({item['key'] for item in report['records']} == set(keys), 'audit report reference keys mismatch')
overlay = json.loads((ROOT / 'current-reference-corrections.json').read_text(encoding='utf-8'))
current_identity_corrections = reconcile_audit_records(records, report, overlay)

# Confirm that every selected key existed in the inherited candidate manifest,
# and that any changed inherited identifier is documented as a correction.
candidates = {item['key']: item for item in json.loads((ROOT / 'candidates.json').read_text(encoding='utf-8'))}
for record in records:
    require(record['key'] in candidates, f"reference absent from inherited manifest: {record['key']}")
    inherited = candidates[record['key']].get('doi') or candidates[record['key']].get('official_url')
    if inherited and inherited.lower() != record['identifier'].lower():
        require(bool(record.get('correction')), f"undocumented identifier correction: {record['key']}")

print(json.dumps({
    'status': 'PASS',
    'references': len(keys),
    'themes': expected_themes,
    'documented_corrections': sum(bool(record.get('correction')) for record in records),
    'historical_documented_corrections': len(report['corrections']),
    'current_identity_corrections': current_identity_corrections,
    'all_grouped_once': True,
    'nocite_used': False,
}, sort_keys=True))

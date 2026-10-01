"""Deterministically rebuild paper bibliography assets from resolved metadata."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT.parents[1] / 'paper'
records = json.loads((ROOT / 'resolved-references.json').read_text(encoding='utf-8'))['records']


def field(name: str, value: object) -> str:
    return f"  {name} = {{{value}}}"

entries: list[str] = []
for record in records:
    fields: list[tuple[str, object]] = [('author', record['author']), ('title', record['title'])]
    for key in ('journal', 'booktitle', 'series', 'publisher', 'volume', 'number', 'pages'):
        if record.get(key):
            fields.append((key, record[key]))
    fields.append(('year', record['year']))
    if record.get('doi'):
        fields.append(('doi', record['doi']))
        fields.append(('url', f"https://doi.org/{record['doi']}"))
    else:
        fields.append(('url', record['url']))
    entries.append(
        f"@{record['type']}{{{record['key']},\n"
        + ',\n'.join(field(name, value) for name, value in fields)
        + '\n}'
    )
bibliography = '\n\n'.join(entries) + '\n'
(ROOT / 'references.bib').write_text(bibliography, encoding='utf-8')
(PAPER / 'references.bib').write_text(bibliography, encoding='utf-8')

commands = {
    'combinatorics': 'CombinatoricsRefs',
    'formal': 'FormalRefs',
    'diagnosis': 'DiagnosisRefs',
    'network': 'NetworkRefs',
    'queueing': 'QueueingRefs',
    'reproducibility': 'ReproRefs',
}
lines = ['% Generated from artifact/references/resolved-references.json; do not edit manually.']
for theme, command in commands.items():
    keys = [record['key'] for record in records if record['theme'] == theme]
    lines.append('\\newcommand{\\' + command + '}{\\cite{' + ','.join(keys) + '}}')
lines.append(r'\newcommand{\VerifiedReferenceCount}{' + str(len(records)) + '}')
groups = '\n'.join(lines) + '\n'
(ROOT / 'reference-groups.tex').write_text(groups, encoding='utf-8')
(PAPER / 'reference-groups.tex').write_text(groups, encoding='utf-8')
print(f'BUILT {len(records)} REFERENCES')

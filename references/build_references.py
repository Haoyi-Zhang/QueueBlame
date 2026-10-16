"""Deterministically rebuild paper bibliography assets from resolved metadata."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT.parents[1] / 'paper'
records = json.loads((ROOT / 'resolved-references.json').read_text(encoding='utf-8'))['records']


def field(name: str, value: object) -> str:
    return f"  {name} = {{{value}}}"


def bib_author(record: dict) -> str:
    """Preserve the paper's existing BibTeX family/suffix/given-name encoding."""
    if record['key'] == 'ford1956maxflow':
        return 'Ford, Jr., L. R. and Delbert R. Fulkerson'
    return record['author'].replace('Neil P. Chue Hong', 'Chue Hong, Neil P.')


entries: list[str] = []
for record in records:
    fields: list[tuple[str, object]] = [('author', bib_author(record)), ('title', record['title'])]
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
bibliography = '@IEEEtranBSTCTL{authorDisplay,\n  CTLdash_repeated_names = {no}\n}\n' + '\n\n'.join(entries) + '\n'
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
role_text = {
    'CombinatoricsRefs': r'network flows \cite{ford1956maxflow}; prescribed binary margins \cite{gale1957flows,ryser1957matrices}; bipartite representatives and matching \cite{hall1935representatives,hopcroft1973matching}; NP-completeness and set cover \cite{karp1972reducibility,chvatal1979setcover,feige1998setcover}',
    'FormalRefs': r'program logics and temporal specifications \cite{hoare1969axiomatic,dijkstra1975guarded,pnueli1977temporal}; abstract interpretation, finite-state verification, and BDDs \cite{cousot1977abstract,clarke1986automatic,bryant1986bdd}; timed automata and SMT solving \cite{alur1994timed,mourabjorner2008z3}; proof-carrying code and verified compilation \cite{necula1997pcc,leroy2009compcert}',
    'DiagnosisRefs': r'model-based diagnosis \cite{reiter1987diagnosis,dekleer1987faults}; preferred explanations and MUS computation \cite{junker2004quickxplain,liffiton2008mus}; knowledge compilation \cite{darwiche2002kcmap}; classifier, social-science, and abductive explanation models \cite{ribeiro2016lime,miller2019explanation,ignatiev2019abduction}',
    'NetworkRefs': r'static reachability and data-plane checking \cite{xie2005reachability,mai2011anteater,kazemian2012hsa}; OpenFlow and configuration verification \cite{alshaer2009flowchecker,khurshid2013veriflow,beckett2017minesweeper}; network languages and symbolic execution \cite{anderson2014netkat,foster2011frenetic,stoenescu2016symnet}; path-query compilation, configuration analysis, and queue queries \cite{naryana2016pathqueries,fogel2015batfish,raghunathan2025quasi}',
    'QueueingRefs': r'network-delay calculus \cite{cruz1991calculus1,cruz1991calculus2}; generalized processor sharing \cite{parekh1993gps1,parekh1994gps2}; fair queueing and VirtualClock \cite{demers1989fairqueue,zhang1990virtualclock}; deficit and weighted fair queueing \cite{shreedhar1996drr,bennett1996wf2q}; active queue management \cite{floyd1993red,nichols2012codel}; datacenter congestion control \cite{alizadeh2010dctcp,mittal2015timely}',
    'ReproRefs': r'reproducible research and scientific-computing guidance \cite{peng2011reproducible,sandve2013rules,wilson2014bestpractices}; support for repeatability engineering \cite{collberg2016repeatability}; artifact review \cite{acm2020badging}',
}

def render_groups(records):
    """Render context-specific source duties while retaining every metadata key."""
    lines = ['% Generated from resolved metadata and contextual citation roles by build_references.py.']
    for theme, command in commands.items():
        lines.append('\\newcommand{\\' + command + '}{' + role_text[command] + '}')
    lines.append(r'\newcommand{\VerifiedReferenceCount}{' + str(len(records)) + '}')
    return '\n'.join(lines) + '\n'

groups = render_groups(records)
(ROOT / 'reference-groups.tex').write_text(groups, encoding='utf-8')
(PAPER / 'reference-groups.tex').write_text(groups, encoding='utf-8')
print(f'BUILT {len(records)} REFERENCES')

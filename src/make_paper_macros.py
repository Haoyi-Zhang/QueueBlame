from __future__ import annotations
import json
from pathlib import Path

artifact = Path(__file__).resolve().parents[1]
summary = json.loads((artifact / 'results/frozen/summary.json').read_text())
micro = json.loads((artifact / 'results/frozen/micro-exhaustive.json').read_text())
hist = summary['core_size_histogram']
macros = {
    'ResultCases': summary['cases'],
    'ResultFamilies': summary['trace_families'],
    'ResultTraces': summary['traces'],
    'ResultAggregateSteps': summary['aggregate_path_steps_validated'],
    'ResultMatrixSteps': summary['matrix_transport_steps_replayed'],
    'ResultCompatible': summary['compatible'],
    'ResultIncompatible': summary['incompatible'],
    'ResultUpper': summary['upper_cores'],
    'ResultLower': summary['lower_cores'],
    'ResultMutations': summary['mutations_rejected'],
    'MicroInstances': micro['instances'],
    'MicroCoreInstances': micro['sampled_core_instances'],
    'CoreSizeOne': hist.get('1', 0),
    'CoreSizeTwo': hist.get('2', 0),
    'CoreSizeThree': hist.get('3', 0),
    'CoreSizeFour': hist.get('4', 0),
}
lines = ['% Generated from artifact/results/frozen; do not edit manually.']
for name, value in macros.items():
    lines.append(f'\\newcommand{{\\{name}}}{{{value:,}}}')
(artifact.parent / 'paper' / 'results-macros.tex').write_text('\n'.join(lines) + '\n', encoding='utf-8')

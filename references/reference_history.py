"""Bind current reference identities to preserved historical audit observations."""
from __future__ import annotations


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def reconcile_audit_records(records, report, overlay):
    """Check an exact, explicit overlay; never rewrite the historical report."""
    _require(set(overlay) == {'schema', 'corrections'}, 'invalid correction overlay fields')
    _require(overlay['schema'] == 'cbcqv-reference-corrections-v1', 'invalid correction schema')
    current = {item['key']: item for item in records}
    historical = {item['key']: item for item in report['records']}
    _require(len(current) == len(records), 'duplicate current reference')
    _require(len(historical) == len(report['records']), 'duplicate historical reference')
    _require(set(current) == set(historical), 'historical/current reference keys differ')
    changes = {}
    for change in overlay['corrections']:
        _require(set(change) == {'key', 'before', 'after', 'source'}, 'invalid correction fields')
        key = change['key']
        _require(key in current and key not in changes, 'unknown or duplicate correction key')
        old, new = change['before'], change['after']
        _require(bool(old) and set(old) == set(new), 'correction fields differ')
        _require(bool(current[key].get('correction')), 'current correction lacks provenance')
        _require(change['source'] == current[key]['verification_url'], 'correction source differs')
        for field in old:
            _require(field in historical[key] and historical[key][field] == old[field], 'correction preimage differs')
            _require(old[field] != new[field] and current[key].get(field) == new[field], 'correction postimage differs')
        changes[key] = new
    for key, item in historical.items():
        for field, old_value in item.items():
            expected = changes.get(key, {}).get(field, old_value)
            _require(current[key].get(field) == expected, f'undocumented audit drift: {key}.{field}')
    return len(changes)

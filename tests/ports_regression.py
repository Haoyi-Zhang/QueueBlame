"""Finite, independently specified port-list contract regression; no file writes.

Invoked separately from the historical 25-test discovery suite, and explicitly
by scientific CI. The reference uses pairwise equality, not a seen-set parser.
"""
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from checker import Rejection, parse_port_list, verify


def reference(value, n, name='ports', nonempty=False):
    if type(value) is not list or (nonempty and not value):
        return 'reject', f'{name}: expected list'
    for i, entry in enumerate(value):
        if type(entry) is not int:
            return 'reject', f'{name}[{i}]: expected integer, not bool or another type'
        if entry < 0:
            return 'reject', f'{name}[{i}]: below lower bound'
        if entry >= n:
            return 'reject', f'{name}[{i}]: above upper bound'
        if any(entry == value[j] for j in range(i)):
            return 'reject', f'{name}: duplicate port'
    return 'accept', sorted(value)


def parsed(parser, value, n, name='ports', nonempty=False):
    try:
        return 'accept', parser(value, n, name, nonempty=nonempty)
    except ValueError as error:
        return 'reject', str(error)


def finite_lists():
    alphabet = (0, 1, 2, -1, 3, True, 1.0, None, [], {})
    for n in (1, 2, 3):
        for nonempty in (False, True):
            for length in range(4):
                for entries in product(alphabet, repeat=length):
                    yield n, nonempty, list(entries)


def fixture():
    root = [4, 1, 1, 1]
    traces = [{'id': 'root', 'target_h': root[:], 'path': []},
              {'id': 'balanced', 'target_h': [3, 1, 1, 2], 'path': [
                  {'from_col': 0, 'to_col': 3, 'before': root[:], 'after': [3, 1, 1, 2]}]}]
    case = {'id': 'public-example', 'n': 4, 'root_h': root,
            'selected': [{'port': 0, 'count': 4}, {'port': 1, 'count': 2}],
            'traces': traces, 'expected': 'upper'}
    cert = {k: deepcopy(case[k]) for k in ('n', 'root_h', 'selected', 'traces')}
    cert.update(version='cbcqv-margin-v2', case_id=case['id'], status='incompatible',
                core_ports=[1, 0], violation={'kind': 'upper', 'cardinality': 2, 'lhs': 6, 'rhs': 5},
                deletion_witnesses=[
                    {'dropped_port': 0, 'remaining_ports': [1], 'matrix': [
                        [1, 0, 0, 0], [1, 1, 0, 0], [1, 0, 1, 0], [1, 0, 0, 1]]},
                    {'dropped_port': 1, 'remaining_ports': [0], 'matrix': [
                        [1, 1, 1, 1], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]}])
    return case, cert


class PortRegression(unittest.TestCase):
    def test_complete_finite_lists_and_first_rejection(self):
        count = 0
        for n, nonempty, value in finite_lists():
            self.assertEqual(parsed(parse_port_list, value, n, nonempty=nonempty),
                             reference(value, n, nonempty=nonempty))
            count += 1
        self.assertEqual(count, 6666)

    def test_collection_and_scalar_subclasses_reject_before_membership(self):
        class ListSubclass(list):
            pass
        class IntSubclass(int):
            pass
        for value in (None, (), {}, '0', ListSubclass([0]), [IntSubclass(0)], [0, IntSubclass(0)]):
            for nonempty in (False, True):
                self.assertEqual(parsed(parse_port_list, value, 2, nonempty=nonempty),
                                 reference(value, 2, nonempty=nonempty))

    def test_sparse_large_id_domain_and_duplicates(self):
        # No dimension-sized allocation or new dimension cap is permitted.
        large = 2**200
        for value in ([large, 0, large - 1], [0, large, 0], [large, large], [large + 1]):
            self.assertEqual(parsed(parse_port_list, value, large + 1),
                             reference(value, large + 1))

    def test_no_input_mutation_or_cross_call_state(self):
        value = [2, 0, 1]
        self.assertEqual(parse_port_list(value, 3, 'ports'), [0, 1, 2])
        self.assertEqual(value, [2, 0, 1])
        self.assertEqual(parse_port_list([1], 3, 'ports'), [1])
        self.assertEqual(parse_port_list([1], 3, 'ports'), [1])

    def test_public_matrix_witness_and_negative_lists(self):
        case, cert = fixture()
        self.assertEqual(verify(case, cert), {'case_id': 'public-example', 'accepted': True,
                                            'status': 'incompatible', 'core_size': 2,
                                            'matrix_transport_steps': 2})
        for field, payload in (('core_ports', [0, 0]), ('core_ports', [False, 1]),
                               ('remaining_ports', [1, 1]), ('remaining_ports', [1.0])):
            bad = deepcopy(cert)
            if field == 'core_ports':
                bad[field] = payload
            else:
                bad['deletion_witnesses'][0][field] = payload
            with self.assertRaises(Rejection):
                verify(case, bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Tiny standard-library checks: actual integer dual, exhaustive small covers.
No HiGHS/NumPy imports or solver execution. Checks the float-domain correction.
"""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

dual = module('reviewed_dual', 'dual_lp.py')
v3 = module('reviewed_v3', 'original_v3.py')

def data(n, cols, costs):
    return {'dimensions': {'num_rows': n, 'num_cols': len(cols)},
            'constraint_matrix_A': {'columns': cols}, 'cost_vector': costs,
            'has_base_constraints': False}

def covers(d):
    m = d['dimensions']['num_cols']
    result = []
    for mask in range(1 << m):
        chosen = [j for j in range(m) if mask >> j & 1]
        if v3.exact_cover(d, chosen):
            value = sum((Fraction(str(d['cost_vector'][j])) for j in chosen), Fraction())
            result.append((value, chosen))
    return result

samples = [
    (data(2, [[0], [1], [0, 1], []], [4, 3, 6, 9]),
     [[7.13, 8.91], [-.3, 8.49], [0, 0], [-8.7, -4.2]]),
    (data(3, [[0], [1], [2], [0, 1], [1, 2], [0, 2], [0, 1, 2], []],
          [4, 4, 4, 5, 5, 5, 8, 1]),
     [[4.8, 5.2, 3.3], [-100, -.5, .1], [8.111, 7.005, .99]]),
]
checked = 0
for d, prices in samples:
    witnesses = covers(d)
    optimum = min(v for v, _ in witnesses)
    for floating in prices:
        for scale in (1, 10, 1_000_000):
            cert, reduced = dual.integer_dual(d, floating, scale)
            p, s = cert['row_prices'], cert['scale']
            assert len(reduced) == d['dimensions']['num_cols']
            for cost, rows, slack in zip(d['cost_vector'], d['constraint_matrix_A']['columns'], reduced):
                assert sum(p[r] for r in rows) <= cost * s
                assert slack == cost * s - sum(p[r] for r in rows)
            bound = Fraction(sum(p), s)
            ceil_bound = -(-sum(p) // s)
            assert bound <= optimum and ceil_bound <= optimum
            assert cert['integer_objective_lower_bound'] == ceil_bound
            for value, chosen in witnesses:
                if int(value) == ceil_bound:
                    assert value == optimum
            checked += 1

exact = data(2, [[0], [1], [0, 1]], [2, 3, 5])
cert, _ = dual.integer_dual(exact, [2, 3], 10)
assert v3.exact_cover(exact, [2])
assert v3.cost(exact, [2]) == cert['integer_objective_lower_bound'] == 5

base = data(2, [[0], [1], [0, 1]], [1, 1, 1])
base.update(has_base_constraints=True, base_constraints={'num_constraints': 1})
try:
    dual.integer_dual(base, [0, 0])
except AssertionError:
    pass
else:
    raise AssertionError('K>0 must be rejected by the K0 dual certificate')

for invalid_cost in (.5, 0, -1):
    bad = data(1, [[0]], [invalid_cost])
    try:
        dual.integer_dual(bad, [0])
    except AssertionError:
        pass
    else:
        raise AssertionError('nonintegral/nonpositive cost admitted')

# Current six inputs are Python ints, so their chosen objective is exact.
# The reviewed root correction rejects int-valued floats on the fast path.
wider = data(2, [[0], [1], [0, 1]], [1e16, 1, 10**16])
try:
    dual.integer_dual(wider, [1e16, 0], 1_000_000)
except AssertionError:
    float_domain_rejected = True
else:
    raise AssertionError('integer-valued float must remain outside this fast certificate domain')
# Retain the tiny reason for the domain guard: v3.cost is floating here.
chosen = [0, 1]
assert v3.exact_cover(wider, chosen)
assert int(v3.cost(wider, chosen)) == 10**16
true_selected = sum((Fraction(str(wider['cost_vector'][j])) for j in chosen), Fraction())
true_optimum = min(v for v, _ in covers(wider))
assert true_selected == 10**16 + 1 and true_optimum == 10**16
assert true_selected > true_optimum
print(json.dumps({'status': 'PASS', 'integer_domain_bound_checks': checked,
                  'positive_integer_certificate': True, 'base_rejected': True,
                  'int_valued_float_domain_rejected': float_domain_rejected,
                  'scope': 'standard-library enumeration only; no solver native'}))

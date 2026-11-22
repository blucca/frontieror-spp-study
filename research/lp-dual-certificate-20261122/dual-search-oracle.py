#!/usr/bin/env python3
"""Tiny standard-library exact-cover oracle; no solver or external activity."""
from fractions import Fraction
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_v3 import cost, exact_cover
from dual_search import dual_bitset_probe, dual_lns, dual_pool


def instance(n, cols, costs):
    return {'dimensions': {'num_rows': n, 'num_cols': len(cols)},
            'constraint_matrix_A': {'columns': cols}, 'cost_vector': costs,
            'has_base_constraints': False}


def all_hole_covers(data, target):
    cols = data['constraint_matrix_A']['columns']
    candidates = [j for j, rows in enumerate(cols) if rows and not sum(1 << r for r in rows) & ~target]
    witnesses = []
    for subset in range(1 << len(candidates)):
        chosen = [candidates[p] for p in range(len(candidates)) if subset >> p & 1]
        counts = [0] * data['dimensions']['num_rows']
        for j in chosen:
            for r in cols[j]:
                counts[r] += 1
        if all(counts[r] == int(bool(target & (1 << r))) for r in range(len(counts))):
            witnesses.append((cost(data, chosen), chosen))
    return witnesses


def check_prices(data, prices, scale):
    for c, rows in zip(data['cost_vector'], data['constraint_matrix_A']['columns']):
        assert sum(prices[r] for r in rows) <= c * scale


d = instance(4, [[0], [1], [2], [3], [0, 1], [2, 3], [0, 2], [1, 3], [0, 1, 2, 3], []],
             [5, 5, 5, 5, 4, 4, 6, 6, 7, 1])
prices, scale = [7, 7, 7, 7], 4
check_prices(d, prices, scale)
ordered = list(range(len(d['cost_vector'])))
checks = 0
for target in (15, 3, 12, 1):
    optimum = min(value for value, _ in all_hole_covers(d, target))
    for seed in (1, 2, 3):
        found, info = dual_bitset_probe(d, ordered, time.monotonic()+1, seed, prices, scale,
                                       cutoff=optimum+1, target=target)
        assert found is not None and cost(d, found) == optimum and info['status'] == 'FEASIBLE'
        assert (cost(d, found), found) in all_hole_covers(d, target)
        found, info = dual_bitset_probe(d, ordered, time.monotonic()+1, seed, prices, scale,
                                       cutoff=optimum, target=target)
        assert found is None and info['status'] in ('EXHAUSTED', 'EMPTY_ROW')
        checks += 1

# Strict partial repair retains untouched rows/columns, including a duplicate
# candidate outside the hole being safely filtered by the helper.
removed = [0, 1]
found, _ = dual_bitset_probe(d, ordered, time.monotonic()+1, 1, prices, scale,
                            cutoff=cost(d, removed), target=3)
updated = [2, 3] + found
assert exact_cover(d, updated) and cost(d, updated) == 14 < 20
assert 2 in updated and 3 in updated

# Global LNS uses the same true-cost incumbent contract and reaches an optimum.
prior = [0, 1, 2, 3]
best, stats = dual_lns(d, prior, ordered, time.monotonic()+.08, 1, prices, scale)
assert prior == [0, 1, 2, 3] and exact_cover(d, best)
assert cost(d, best) == 7 and stats['improvements'] >= 1 and stats['global_holes'] >= 1

# Explicitly exercise an RC increment on a forced column: raw partial cost4
# is below cutoff10, but lower8+rc2 reaches10 and forbids a strict improvement.
f = instance(2, [[0], [1]], [4, 6])
found, info = dual_bitset_probe(f, [0, 1], time.monotonic()+1, 1, [2, 6], 1, cutoff=10)
assert found is None and info['forced_columns'] == 1 and info['dual_bound_prunes'] == 1
found, _ = dual_bitset_probe(f, [0, 1], time.monotonic()+1, 1, [2, 6], 1, cutoff=11)
assert found == [0, 1]

# Optimal incumbent remains unchanged through global/partial attempts; timeout
# also returns its prior unchanged. Positive integer costs keep ceil admissible.
o = instance(4, [[0], [1], [2], [3]], [2, 2, 2, 2])
best, stats = dual_lns(o, [0, 1, 2, 3], [0, 1, 2, 3], time.monotonic()+.06, 1, [2]*4, 1)
assert best == [0, 1, 2, 3] and stats['improvements'] == 0 and stats['global_holes'] > 0 and stats['partial_holes'] > 0
unchanged, _ = dual_lns(o, best, [0, 1, 2, 3], time.monotonic()-1, 1, [2]*4, 1)
assert unchanged == best
found, info = dual_bitset_probe(o, [0, 1, 2, 3], time.monotonic()-1, 1, [2]*4, 1)
assert found is None and info['status'] == 'TIME_LIMIT'

# Valid negative prices remain admissible; Base and float costs stay outside.
found, _ = dual_bitset_probe(f, [0, 1], time.monotonic()+1, 1, [-2, 3], 1, cutoff=11)
assert found == [0, 1]
for bad in (instance(1, [[0]], [1.0]), dict(f, has_base_constraints=True, base_constraints={'num_constraints': 1})):
    try:
        dual_bitset_probe(bad, [0], time.monotonic()+1, 1, [0]*bad['dimensions']['num_rows'], 1)
    except AssertionError:
        pass
    else:
        raise AssertionError('noninteger/Base domain requires original backend')

pool, metadata = dual_pool(d, ordered, prices, scale)
assert pool and all(d['constraint_matrix_A']['columns'][j] for j in pool)
theta = Fraction(metadata['theta_numerator'], metadata['theta_denominator'])
upper = Fraction(sum(prices), scale) + theta*4
for value, cover in all_hole_covers(d, 15):
    if set(cover) <= set(pool):
        assert value <= upper
print(json.dumps({'status': 'PASS', 'oracle_target_seed_checks': checks,
                  'forced_reduced_cost_update': True, 'partial_repair': True,
                  'global_lns_optimum': True, 'incumbent_and_deadline_preserved': True,
                  'negative_prices_and_domain_rejection': True, 'pool_bound': True,
                  'native': 0}))

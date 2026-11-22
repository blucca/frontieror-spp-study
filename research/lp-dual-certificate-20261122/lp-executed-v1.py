#!/usr/bin/env python3
"""Complete K0 LP diagnostic with an independently checkable integer dual.

The certified path applies to positive integral costs and 0/1 exact-cover rows.
General Base/real-cost instances retain the separately frozen original method.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
BEGIN = time.monotonic()


def integer_dual(data, row_dual, scale=1_000_000):
    """Floating prices choose integer P; exact whole-column checks prove validity."""
    n = data['dimensions']['num_rows']
    costs, cols = data['cost_vector'], data['constraint_matrix_A']['columns']
    base = data.get('base_constraints') if data.get('has_base_constraints') else None
    assert not base or not base['num_constraints']
    assert len(row_dual) == n and all(math.isfinite(x) for x in row_dual)
    assert type(scale) is int and scale > 0
    assert all(type(c) in (int, float) and c > 0 and c == int(c) for c in costs)
    prices = [math.floor(p * scale) for p in row_dual]
    # One uniform integer shift covers every numerical dual infeasibility.
    correction = max([0] + [(sum(prices[r] for r in rows) - int(c) * scale + len(rows) - 1) // len(rows)
                             for c, rows in zip(costs, cols) if rows])
    prices = [p - correction for p in prices]
    reduced = [int(c) * scale - sum(prices[r] for r in rows) for c, rows in zip(costs, cols)]
    assert min(reduced) >= 0, 'every complete original column satisfies the exact dual inequality'
    total = sum(prices)
    return {'scale': scale, 'row_prices': prices, 'correction': correction,
            'minimum_column_slack': min(reduced), 'lower_bound_numerator': total,
            'integer_objective_lower_bound': -(-total // scale)}, reduced


def self_check():
    d = {'dimensions': {'num_rows': 2}, 'cost_vector': [1, 1, 1],
         'constraint_matrix_A': {'columns': [[0], [1], [0, 1]]}}
    cert, rc = integer_dual(d, [.8, .8], 10)
    assert cert['correction'] == 3 and cert['row_prices'] == [5, 5] and rc == [5, 5, 0]
    assert cert['integer_objective_lower_bound'] == 1
    # Negative duals and a non-integral LP bound retain exact ceil arithmetic.
    cert, rc = integer_dual(d, [-.1, .9], 10)
    assert min(rc) >= 0 and cert['lower_bound_numerator'] == 8 and cert['integer_objective_lower_bound'] == 1
    d['cost_vector'][0] = .5
    try:
        integer_dual(d, [0, 0])
    except AssertionError:
        pass
    else:
        raise AssertionError('non-integer cost requires another certificate contract')
    print('integer dual exactness/correction/negative/nonintegral-domain checks PASS')


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance')
    parser.add_argument('--output')
    parser.add_argument('--lp-seconds', type=float, default=5.0)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    if args.self_check:
        self_check(); return 0
    assert args.instance and args.output and args.lp_seconds > 0
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    spec = importlib.util.spec_from_file_location('spp', Path(__file__).with_name('original_v3.py'))
    spp = importlib.util.module_from_spec(spec); spec.loader.exec_module(spp)
    data = spp.read_instance(args.instance)
    n, m, k, _ = spp.dimensions(data)
    costs, cols = data['cost_vector'], data['constraint_matrix_A']['columns']
    assert k == 0 and all(c > 0 and c == int(c) for c in costs)
    import highspy
    import numpy as np
    lp = highspy.HighsLp(); lp.num_col_, lp.num_row_ = m, n
    lp.col_cost_ = np.asarray(costs, dtype=np.float64)
    lp.col_lower_, lp.col_upper_ = np.zeros(m), np.full(m, highspy.kHighsInf)
    lp.row_lower_, lp.row_upper_ = np.ones(n), np.ones(n)
    starts, indices = [0], []
    for rows in cols:
        indices.extend(rows); starts.append(len(indices))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_, lp.a_matrix_.index_ = np.asarray(starts, dtype=np.int32), np.asarray(indices, dtype=np.int32)
    lp.a_matrix_.value_ = np.ones(len(indices))
    h = highspy.Highs(); h.setOptionValue('output_flag', False); h.setOptionValue('threads', 2)
    h.setOptionValue('time_limit', args.lp_seconds)
    assert h.passModel(lp) != highspy.HighsStatus.kError
    built = time.monotonic()
    h.startSolve(); done, run_status = h.wait(args.lp_seconds)
    record = {'instance': Path(args.instance).name, 'n': n, 'm': m, 'nnz': len(indices),
              'cold_input_only': True, 'threads': 2, 'affinity': sorted(os.sched_getaffinity(0)),
              'highspy': h.version(), 'numpy': np.__version__, 'python': sys.version,
              'ram_limit_bytes': resource.getrlimit(resource.RLIMIT_AS)[0],
              'build_seconds': built-BEGIN, 'native_seconds': time.monotonic()-built, 'done': done}
    if not done:
        record.update(status='LP_DEADLINE', complete_seconds=time.monotonic()-BEGIN)
        dump(args.output, record); print(json.dumps(record), flush=True)
        # The existing HiGHS daemon API overrun contract: no live result read.
        os._exit(0)
    record['lp_status'] = str(h.getModelStatus()); record['run_status'] = str(run_status)
    solution = h.getSolution()
    if h.getModelStatus() != highspy.HighsModelStatus.kOptimal or not solution.dual_valid:
        record.update(status='LP_NOT_OPTIMAL', complete_seconds=time.monotonic()-BEGIN)
        dump(args.output, record); print(json.dumps(record), flush=True); return 0
    cert, reduced = integer_dual(data, list(solution.row_dual))
    chosen = [j for j, v in enumerate(solution.col_value) if v > .5]
    candidate_feasible = spp.exact_cover(data, chosen)
    objective = spp.cost(data, chosen) if candidate_feasible else None
    certified = candidate_feasible and int(objective) == cert['integer_objective_lower_bound']
    if candidate_feasible:
        spp.write_solution(data, chosen, str(Path(args.output).with_name('solution.json')))
    record.update(status='CERTIFIED_OPTIMAL' if certified else 'FRACTIONAL_LP', lp_objective=h.getObjectiveValue(),
                  candidate_feasible=candidate_feasible, candidate_objective=objective, candidate_selected=chosen if candidate_feasible else None,
                  certificate=cert, row_duals=list(solution.row_dual), lp_variable_values=list(solution.col_value),
                  reduced_costs_scaled=reduced, complete_seconds=time.monotonic()-BEGIN,
                  max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    dump(args.output, record)
    print(json.dumps({k:v for k,v in record.items() if k not in ('row_duals','lp_variable_values','reduced_costs_scaled','certificate','candidate_selected')}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

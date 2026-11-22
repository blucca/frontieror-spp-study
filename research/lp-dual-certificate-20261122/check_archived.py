#!/usr/bin/env python3
"""Recheck stored full-column integer certificates and full-M witnesses.

Standard library only. This reads archived official checker receipts and
independently verifies their complete witnesses; no HiGHS/NumPy/native solve.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


v3 = module('archived_v3', 'original_v3.py')
dual = module('archived_dual', 'dual_lp.py')


def read(path):
    return json.loads(path.read_text())


def source(case):
    if case == 'base-k2':
        return REPO / 'main/base-contract-fixture.json'
    stem = 'tiny_instance' if case == 'tiny' else 'large_instance_' + case.removeprefix('large')
    return REPO / 'source' / ('hoffman1993-' + stem + '.json')


def check_certificate(data, cert):
    n, m, k, _ = v3.dimensions(data)
    assert k == 0 and all(type(c) is int and c > 0 for c in data['cost_vector'])
    p, s = cert['row_prices'], cert['scale']
    assert len(p) == n and all(type(value) is int for value in p)
    assert type(s) is int and s > 0
    rc = [c * s - sum(p[r] for r in rows)
          for c, rows in zip(data['cost_vector'], data['constraint_matrix_A']['columns'])]
    assert len(rc) == m and min(rc) >= 0
    assert min(rc) == cert['minimum_column_slack']
    assert sum(p) == cert['lower_bound_numerator']
    assert -(-sum(p) // s) == cert['integer_objective_lower_bound']
    return rc


def check_solution(data, solution):
    n, m, _, _ = v3.dimensions(data)
    chosen = solution['selected_rotations']
    assert v3.exact_cover(data, chosen)
    assert type(solution['objective_value']) is int
    assert solution['objective_value'] == v3.cost(data, chosen)
    values = solution['variable_values']
    assert set(values) == {str(j) for j in range(m)}
    assert all(type(v) in (int, float) and v in (0, 1) for v in values.values())
    assert {int(j) for j, v in values.items() if v == 1} == set(chosen)
    return solution['objective_value']


assert (HERE / 'original_v3.py').read_bytes() == (REPO / 'main/solve.py').read_bytes()
provenance = read(HERE / 'provenance.json')
for name, digest in provenance['source_sha256'].items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
lp_checks, column_checks, certificates = [], 0, []
for case in ('tiny', 'large2', 'large1', 'large3', 'large4', 'large5'):
    data = v3.read_instance(source(case))
    d = HERE / 'results/lp' / case
    report = read(d / 'report.json')
    n, m, _, _ = v3.dimensions(data)
    assert report['done'] and report['lp_status'] == 'HighsModelStatus.kOptimal'
    assert (report['n'], report['m'], report['nnz']) == (n, m, sum(map(len, data['constraint_matrix_A']['columns'])))
    assert report['highspy'] == '1.15.1' and report['numpy'] == '2.5.3'
    rc = check_certificate(data, report['certificate'])
    assert rc == report['reduced_costs_scaled']
    assert len(report['row_duals']) == n and all(math.isfinite(v) for v in report['row_duals'])
    cert, recomputed_rc = dual.integer_dual(data, report['row_duals'])
    assert cert == report['certificate'] and recomputed_rc == rc
    primal = report['lp_variable_values']
    assert len(primal) == m and all(math.isfinite(v) and v >= -1e-8 for v in primal)
    row_sums = [0.0] * n
    for v, rows in zip(primal, data['constraint_matrix_A']['columns']):
        for r in rows:
            row_sums[r] += v
    assert max(abs(v - 1) for v in row_sums) <= 1e-6
    chosen = [j for j, v in enumerate(primal) if v > .5]
    feasible = v3.exact_cover(data, chosen)
    assert feasible == report['candidate_feasible']
    if feasible:
        objective = check_solution(data, read(d / 'solution.json'))
        assert report['status'] == 'CERTIFIED_OPTIMAL'
        assert objective == report['candidate_objective'] == report['certificate']['integer_objective_lower_bound']
        assert chosen == report['candidate_selected']
        certificates.append(case)
    else:
        assert report['status'] == 'FRACTIONAL_LP' and report['candidate_objective'] is None
        assert not (d / 'solution.json').exists()
    column_checks += m
    lp_checks.append(case)
assert column_checks == 75025 and certificates == ['tiny', 'large2']
lp_summary = read(HERE / 'results/lp-summary.json')
assert lp_summary['status'] == 'COMPLETE' and len(lp_summary['runs']) == 6
assert all(r['exit_code'] == 0 for r in lp_summary['runs'])
method_sha = hashlib.sha256((HERE / 'method.py').read_bytes()).hexdigest()
method_checks, hard = [], []
for seed, case, expected in ((1, 'tiny', 16), (1, 'base-k2', 2), (1, 'large3', 240), (2, 'large3', 350), (3, 'large3', 405)):
    data = v3.read_instance(source(case))
    d = HERE / f'results/method/seed{seed}' / case
    record, exact, official = read(d / 'run.json'), read(d / 'exact-check.json'), read(d / 'official-check.json')
    objective = check_solution(data, read(d / 'solution.json'))
    assert objective == expected == record['objective'] == exact['recomputed_objective']
    assert record['status'] == 'PASS' and record['algorithm_exit_code'] == record['worker_exit_code'] == 0
    assert record['script_sha256'] == method_sha
    assert record['independent_exact_feasible'] and record['official_numpy_feasible']
    assert exact['feasible'] and not exact['violations'] and official['feasible']
    assert exact['variable_count'] == data['dimensions']['num_cols']
    assert all(v == 1 for v in exact['row_counts'])
    assert 0 < record['external_end_to_end_seconds'] < 60
    if 'lp' in record['metrics']:
        check_certificate(data, record['metrics']['lp']['certificate'])
    method_checks.append({'case': case, 'seed': seed, 'objective': objective})
    if case == 'large3':
        hard.append(record)
summary = read(HERE / 'results/summary.json')
old = summary['hard3_old_v3_costs']
new = [r['objective'] for r in hard]
assert old == [240, 350, 416] and new == [240, 350, 405]
assert summary['hard3_retained_cold_highs_costs'] == [453, 440, 337]
assert summary['hard3_old_sum'] == sum(old) == 1006 and summary['hard3_new_sum'] == sum(new) == 995
assert abs(summary['hard3_sum_reduction_percent'] - 100 * (sum(old) - sum(new)) / sum(old)) < 1e-12
pair_passes = sum(100 * (a - b) / a >= 5 for a, b in zip(old, new))
assert pair_passes == 0 and summary['hard3_sum_reduction_percent'] < 5
assert not summary['quality_gate_passed'] and not summary['dense_fast_certificate_gate_passed']
trace = hard[-1]['metrics']['improvement_trace']
original = [c for _, c, label in trace if label == 'original_large_hole']
dual_trace = [c for _, c, label in trace if label == 'dual_bound_large_hole']
assert original[-1] == 419 and dual_trace[-1] == 405
contrast = read(HERE / 'results/final-contrast.json')
assert [(d['case'], d['seed'], d['cost']) for d in contrast] == [(x['case'], x['seed'], x['objective']) for x in method_checks]
assert all(abs(c['whole'] - r['external_end_to_end_seconds']) < 1e-12 for c, r in zip(contrast[2:], hard))
print(json.dumps({'status': 'PASS', 'lp_full_cases': lp_checks, 'original_columns_checked': column_checks,
                  'whole_integer_certificates': certificates, 'method_full_witnesses': method_checks,
                  'original_v3_bytes_preserved': True, 'recorded_official_receipts_read': 5,
                  'quality_gate': 'FAILED_STOP', 'sum_reduction_percent': summary['hard3_sum_reduction_percent'],
                  'native_runs': 0}))

#!/usr/bin/env python3
"""Minimum撤销旧rotation的完整 K0 exact-partition repair.

Input attribution: FrontierOR / Hoffman et al., CC BY 4.0.
First research scope: <=128 legs, nonempty old rotations, integer nonnegative
costs, and hard pins drawn from the old plan. Personnel/date mapping is external.
The old cold v3 algorithm is not used; its stdlib input/witness functions are reused.
"""
import time
START = time.monotonic()
import argparse
import json
import resource
from pathlib import Path
import original_v3 as io


def ids(value, m, label):
    if not isinstance(value, list) or any(type(j) is not int or not 0 <= j < m for j in value) or len(value) != len(set(value)):
        raise ValueError(label + ' requires distinct in-range integer rotation IDs')
    return set(value)


def make_solution(data, chosen):
    chosen = sorted(chosen)
    if not io.exact_cover(data, chosen):
        raise ValueError('whole original exact partition failed')
    m = data['dimensions']['num_cols']
    selected = set(chosen)
    return {'objective_value': io.cost(data, chosen), 'selected_rotations': chosen,
            'variable_values': {str(j): int(j in selected) for j in range(m)}}


def check(data, old, event, selected):
    n, m, k, _ = io.dimensions(data)
    old_ids = ids(old['selected_rotations'], m, 'old plan')
    f, p = ids(event['F'], m, 'F'), ids(event['P'], m, 'P')
    picked = ids(selected, m, 'selected')
    if not io.exact_cover(data, sorted(picked)) or picked & f or not p <= picked:
        raise ValueError('full original / forbidden / pinned witness failed')
    return {'whole_feasible': True, 'removed_old_count': len(old_ids - picked),
            'removed_old': sorted(old_ids-picked), 'added_new': sorted(picked-old_ids),
            'retained_old': sorted(old_ids & picked), 'recomputed_cost': io.cost(data, sorted(picked)),
            'rows': n, 'columns': m, 'base_constraints': k}


def read_contract(instance, old_plan, event_path):
    data = io.read_instance(instance)
    old = json.loads(Path(old_plan).read_text())
    event = json.loads(Path(event_path).read_text())
    n, m, k, _ = io.dimensions(data)
    if n > 128 or k:
        raise ValueError('research scope requires <=128 legs and K=0; Base requires a separate complete method')
    if any(type(c) is not int or c < 0 for c in data['cost_vector']):
        raise ValueError('research scope requires integer nonnegative costs')
    i = ids(old['selected_rotations'], m, 'old plan')
    if not io.exact_cover(data, sorted(i)) or any(not data['constraint_matrix_A']['columns'][j] for j in i):
        raise ValueError('old plan must be a whole partition of nonempty rotations')
    expected = make_solution(data, i)
    if old['objective_value'] != expected['objective_value'] or old['variable_values'] != expected['variable_values']:
        raise ValueError('old complete vector/cost must agree with original instance')
    ids(event['F'], m, 'F')
    p = ids(event['P'], m, 'P')
    if not p <= i:
        raise ValueError('first pins scope is P subset of old plan')
    return data, old, event


class SearchDeadline(Exception):
    pass


def solve_primary(data, old, event, deadline):
    began = time.monotonic()
    n, m, _, _ = io.dimensions(data)
    old_ids = sorted(old['selected_rotations'])
    i = set(old_ids)
    f, p = set(event['F']), set(event['P'])
    groups = [sum(1 << r for r in data['constraint_matrix_A']['columns'][j]) for j in old_ids]
    owner = [None] * n
    for g, rows in enumerate(groups):
        while rows:
            bit = rows & -rows; rows -= bit
            owner[bit.bit_length()-1] = g
    pin_groups = sum(1 << g for g,j in enumerate(old_ids) if j in p)
    initial_u = sum(1 << g for g,j in enumerate(old_ids) if j in f)
    initial_rows = sum(rows for g, rows in enumerate(groups) if initial_u >> g & 1)
    counters = {'nodes': 0, 'candidate_checks': 0, 'cache_hits': 0, 'max_removed_groups': initial_u.bit_count()}
    budgets = []
    if f & p:
        return {'status': 'INFEASIBLE', 'lower_bound': None, 'selected_rotations': None,
                'search_seconds': time.monotonic()-began, 'budgets': budgets, **counters}
    masks, touched = [], []
    by_row = [[] for _ in range(n)]
    for j, rows in enumerate(data['constraint_matrix_A']['columns']):
        mask = sum(1 << r for r in rows)
        t = 0
        for r in rows:
            t |= 1 << owner[r]
        masks.append(mask); touched.append(t)
        # Empty nonold columns can be omitted: c>=0 and they never reduce old losses.
        if j not in i and j not in f and rows and not t & pin_groups:
            for r in rows:
                by_row[r].append(j)
    for r in range(n):
        by_row[r].sort(key=lambda j: (touched[j].bit_count(), data['cost_vector'][j], j))
    prep_seconds = time.monotonic()-began
    max_budget = len(old_ids)-len(p)
    lower = initial_u.bit_count()
    for budget in range(lower, max_budget+1):
        if time.monotonic() >= deadline:
            break
        # A failed state is specific to this D budget; never reuse it at a larger k.
        failed = set()
        nodes_before = counters['nodes']
        def dfs(u, covered, region):
            counters['nodes'] += 1
            counters['max_removed_groups'] = max(counters['max_removed_groups'], u.bit_count())
            if time.monotonic() >= deadline:
                raise SearchDeadline()
            missing = region & ~covered
            if not missing:
                assert covered == region, 'every newly exposed leg must be covered at termination'
                return u, []
            state = (u, covered)
            if state in failed:
                counters['cache_hits'] += 1
                return None
            remaining = missing
            best = None
            while remaining:
                bit = remaining & -remaining; remaining -= bit
                r = bit.bit_length()-1
                candidates = []
                for j in by_row[r]:
                    counters['candidate_checks'] += 1
                    if counters['candidate_checks'] % 1024 == 0 and time.monotonic() >= deadline:
                        raise SearchDeadline()
                    if not masks[j] & covered:
                        extra = touched[j] & ~u
                        if u.bit_count()+extra.bit_count() <= budget:
                            candidates.append((extra.bit_count(), data['cost_vector'][j], j))
                if not candidates:
                    failed.add(state)
                    return None
                if best is None or len(candidates) < len(best):
                    best = candidates
                    if len(best) == 1:
                        break
            best.sort()
            for _,_,j in best:
                extra = touched[j] & ~u
                new_region = region
                while extra:
                    bit = extra & -extra; extra -= bit
                    new_region |= groups[bit.bit_length()-1]
                found = dfs(u | touched[j], covered | masks[j], new_region)
                if found is not None:
                    final_u, selected = found
                    return final_u, [j, *selected]
            failed.add(state)
            return None
        try:
            found = dfs(initial_u, 0, initial_rows)
        except SearchDeadline:
            budgets.append({'budget': budget, 'exhausted': False, 'nodes': counters['nodes']-nodes_before})
            break
        if found is None:
            budgets.append({'budget': budget, 'exhausted': True, 'nodes': counters['nodes']-nodes_before})
            lower = budget+1
            continue
        u, new = found
        selected = [j for g,j in enumerate(old_ids) if not u >> g & 1] + new
        verdict = check(data, old, event, selected)
        assert verdict['removed_old_count'] == u.bit_count() == budget
        return {'status': 'OPTIMAL', 'lower_bound': budget, 'objective': budget,
                'selected_rotations': sorted(selected), 'witness': verdict,
                'preparation_seconds': prep_seconds, 'search_seconds': time.monotonic()-began,
                'budgets': budgets, **counters}
    status = 'INFEASIBLE' if lower > max_budget else 'UNKNOWN'
    return {'status': status, 'lower_bound': None if status == 'INFEASIBLE' else lower,
            'objective': None, 'selected_rotations': None, 'preparation_seconds': prep_seconds,
            'search_seconds': time.monotonic()-began, 'budgets': budgets, **counters}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('instance', 'old-plan', 'event', 'output'):
        parser.add_argument('--'+arg, required=True)
    parser.add_argument('--time-limit', type=float, default=55)
    args = parser.parse_args()
    data, old, event = read_contract(args.instance, args.old_plan, args.event)
    primary = solve_primary(data, old, event, START+args.time_limit)
    solution = make_solution(data, primary['selected_rotations']) if primary['selected_rotations'] is not None else None
    result = {'solver': 'conflict-driven complete minimum-old-loss search', 'event': event,
              'primary': primary, 'secondary': None, 'solution': solution,
              'own_wall_seconds': time.monotonic()-START, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='solution'}, allow_nan=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

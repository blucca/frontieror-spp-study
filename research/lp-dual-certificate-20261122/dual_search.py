#!/usr/bin/env python3
"""Input-only integer-dual exact-cover probes and incumbent-preserving repairs.

Caller supplies validated original data and integer prices P / scale whose
inequality holds for every original column. Positive Python-int costs / K0.
This helper imports no numerical solver and never reads witnesses or references.
"""
import math
import random
import time

from original_v3 import ProbeLimit, cost, dimensions, exact_cover


def _contract(data, prices, scale):
    n, m, k, _ = dimensions(data)
    costs, cols = data['cost_vector'], data['constraint_matrix_A']['columns']
    assert type(n) is int and n > 0 and type(m) is int and m > 0
    assert k == 0 and len(costs) == m and len(cols) == m
    assert all(type(c) is int and c > 0 for c in costs)
    assert type(scale) is int and scale > 0
    assert len(prices) == n and all(type(p) is int for p in prices)
    return n, m, costs, cols


def dual_bitset_probe(data, candidates, deadline, seed, prices, scale,
                      cutoff=math.inf, target=None):
    """Find the first exact hole cover strictly cheaper than integer cutoff.

    Full-column validated P/S is an admissible residual lower bound. Along a
    partial path, lower = sum(P on target) + sum(selected reduced costs), so
    forced and branched columns update it with one integer addition. With
    integer completion costs, ceil(lower/S) >= cutoff iff
    lower > (cutoff-1)*S. Positive costs also permit true-cost pruning.

    Candidate columns outside target and positive-cost empty columns are
    filtered. Dynamic compatible-row MRV, forced columns and dead[uncovered]
    reuse the original exact-cover search. No live native data is accessed.
    """
    began = time.monotonic()
    n, m, costs, cols = _contract(data, prices, scale)
    all_rows = (1 << n) - 1
    target = all_rows if target is None else target
    assert type(target) is int and target >= 0 and not target & ~all_rows
    bounded = cutoff != math.inf
    assert not bounded or type(cutoff) is int, 'finite cutoff is an integer true cost'
    dual_cutoff = (cutoff - 1) * scale if bounded else None
    candidates = list(candidates)
    assert len(candidates) == len(set(candidates))
    assert all(type(j) is int and 0 <= j < m for j in candidates)
    raw_columns = len(candidates)
    target_price = sum(prices[r] for r in range(n) if target & (1 << r))
    nodes = dual_prunes = cost_prunes = memo_prunes = forced_columns = 0
    minimum = None
    selected_ids, masks, reduced = [], [], []
    adj = [0] * n
    ranks, conflicts = [], []
    rng = random.Random(seed)

    def timed_check(index):
        if index % 128 == 0 and time.monotonic() >= deadline:
            raise ProbeLimit()

    def finish(found, status):
        return found, {'status': status, 'nodes': nodes, 'columns': len(selected_ids),
                       'input_candidate_columns': raw_columns,
                       'min_row_degree': minimum, 'seconds': time.monotonic() - began,
                       'dual_bound_prunes': dual_prunes, 'cost_prunes': cost_prunes,
                       'memo_prunes': memo_prunes, 'forced_columns': forced_columns,
                       'target_price_numerator': target_price, 'price_scale': scale,
                       'target_integer_lower': -(-target_price // scale),
                       'branch_order': 'reduced_cost/coverage x seed jitter[0.8,1.2]; dynamic compatible-row MRV'}

    try:
        timed_check(0)
        if not target:
            if 0 < cutoff:
                return finish([], 'FEASIBLE')
            return finish(None, 'EXHAUSTED')
        if 0 >= cutoff:
            cost_prunes += 1
            return finish(None, 'EXHAUSTED')
        if bounded and target_price > dual_cutoff:
            dual_prunes += 1
            return finish(None, 'EXHAUSTED')
        # Restriction to whole contained columns makes active a function of
        # uncovered alone; dead[uncovered] may safely compare true path costs.
        for index, j in enumerate(candidates):
            timed_check(index)
            rows = cols[j]
            if not rows:
                continue
            mask = sum(1 << r for r in rows)
            if mask & ~target:
                continue
            rc = costs[j] * scale - sum(prices[r] for r in rows)
            assert rc >= 0, 'candidate reduced cost requires full-column validated prices'
            selected_ids.append(j); masks.append(mask); reduced.append(rc)
        q = len(selected_ids)
        active_rows = [r for r in range(n) if target & (1 << r)]
        for p, j in enumerate(selected_ids):
            timed_check(p)
            bit = 1 << p
            for r in cols[j]:
                adj[r] |= bit
        if any(not adj[r] for r in active_rows):
            minimum = 0
            return finish(None, 'EMPTY_ROW')
        degrees = [a.bit_count() for a in adj]
        minimum = min(degrees[r] for r in active_rows)
        for p, j in enumerate(selected_ids):
            timed_check(p)
            noise = rng.random()
            # A separate tie component also randomizes zero-RC columns.
            ranks.append((-(reduced[p] / len(cols[j])) * (0.8 + 0.4 * noise), noise))
            clash = 0
            for r in cols[j]:
                clash |= adj[r]
            conflicts.append(clash)
        dead = {}

        def pruned(value, lower):
            nonlocal dual_prunes, cost_prunes
            if value >= cutoff:
                cost_prunes += 1
                return True
            if bounded and lower > dual_cutoff:
                dual_prunes += 1
                return True
            return False

        def dfs(uncovered, active, path, value, lower):
            nonlocal nodes, memo_prunes, forced_columns
            nodes += 1
            if nodes % 128 == 1 and time.monotonic() >= deadline:
                raise ProbeLimit()
            if pruned(value, lower):
                return None
            while uncovered:
                remaining, best_count, options = uncovered, q + 1, 0
                while remaining:
                    bit = remaining & -remaining; remaining -= bit
                    r = bit.bit_length() - 1
                    choices = active & adj[r]
                    count = choices.bit_count()
                    if count == 0:
                        return None
                    if count < best_count:
                        best_count, options = count, choices
                        if count == 1:
                            break
                if best_count != 1:
                    break
                p = options.bit_length() - 1
                value += costs[selected_ids[p]]
                lower += reduced[p]
                forced_columns += 1
                if pruned(value, lower):
                    return None
                path.append(selected_ids[p])
                uncovered ^= masks[p]
                active &= ~conflicts[p]
            if not uncovered:
                return path
            if uncovered in dead and value >= dead[uncovered]:
                memo_prunes += 1
                return None
            choices = []
            while options:
                bit = options & -options; options -= bit
                choices.append(bit.bit_length() - 1)
            choices.sort(key=lambda p: ranks[p], reverse=True)
            for p in choices:
                next_value = value + costs[selected_ids[p]]
                next_lower = lower + reduced[p]
                if pruned(next_value, next_lower):
                    continue
                found = dfs(uncovered ^ masks[p], active & ~conflicts[p],
                            path + [selected_ids[p]], next_value, next_lower)
                if found is not None:
                    return found
            if len(dead) < 100000:
                dead[uncovered] = min(value, dead.get(uncovered, math.inf))
            return None

        found = dfs(target, (1 << q) - 1, [], 0, target_price)
        return finish(found, 'FEASIBLE' if found is not None else 'EXHAUSTED')
    except ProbeLimit:
        return finish(None, 'TIME_LIMIT')


def dual_lns(data, best, ordered, deadline, seed, prices, scale):
    """Preserve whole incumbent; global and 75%-100% union repairs, <=600ms.

    Only complete incumbent columns are removed. Untouched rows retain their
    exact cover; repair columns must lie entirely in the removed row union.
    Graph rebuild and candidate restriction are charged to each hole deadline.
    Improvement trace seconds are relative to this dual_lns call's start.
    """
    began = time.monotonic()
    n, m, costs, cols = _contract(data, prices, scale)
    assert exact_cover(data, best)
    best = list(best)
    ordered = list(ordered)
    assert len(ordered) == len(set(ordered))
    assert all(type(j) is int and 0 <= j < m for j in ordered)
    masks = []
    for j, rows in enumerate(cols):
        if j % 128 == 0 and time.monotonic() >= deadline:
            return best, {'holes': 0, 'improvements': 0, 'nodes': 0,
                          'dual_bound_prunes': 0, 'cost_prunes': 0,
                          'global_holes': 0, 'partial_holes': 0,
                          'improvement_trace': [], 'trace_origin': 'dual_lns_start',
                          'hole_seconds_cap': 0.6, 'seconds': time.monotonic()-began,
                          'status': 'TIME_LIMIT'}
        masks.append(sum(1 << r for r in rows))
    rng = random.Random(15485863 * seed)
    holes = improvements = nodes = dual_prunes = cost_prunes = 0
    global_holes = partial_holes = 0
    trace = []
    while time.monotonic() < deadline - 0.02 and len(best) > 1:
        hole_began = time.monotonic()
        hole_deadline = min(deadline, hole_began + 0.6)
        size = len(best) if holes % 2 == 0 else rng.randrange(max(2, math.ceil(.75 * len(best))), len(best)+1)
        removed = rng.sample(best, size)
        hole = 0
        for j in removed:
            hole |= masks[j]
        candidates = []
        for index, j in enumerate(ordered):
            if index % 128 == 0 and time.monotonic() >= hole_deadline:
                break
            if masks[j] and not masks[j] & ~hole:
                candidates.append(j)
        found, metrics = dual_bitset_probe(data, candidates, hole_deadline,
                                          rng.randrange(1, 2**31), prices, scale,
                                          cutoff=cost(data, removed), target=hole)
        holes += 1
        global_holes += size == len(best)
        partial_holes += size < len(best)
        nodes += metrics['nodes']
        dual_prunes += metrics['dual_bound_prunes']
        cost_prunes += metrics['cost_prunes']
        if found is not None:
            removed_set = set(removed)
            updated = [j for j in best if j not in removed_set] + found
            assert exact_cover(data, updated) and cost(data, updated) < cost(data, best), 'whole incumbent-preserving strict repair'
            best = updated
            improvements += 1
            trace.append([time.monotonic() - began, cost(data, best)])
    return best, {'holes': holes, 'improvements': improvements, 'nodes': nodes,
                  'dual_bound_prunes': dual_prunes, 'cost_prunes': cost_prunes,
                  'global_holes': global_holes, 'partial_holes': partial_holes,
                  'improvement_trace': trace, 'trace_origin': 'dual_lns_start',
                  'hole_seconds_cap': 0.6, 'seconds': time.monotonic() - began}


def dual_pool(data, ordered, prices, scale):
    """Original support-prefix/thickness rule, ordered by reduced-cost/coverage.

    Pool size/support is diagnostic. A complete cover inside the pool would
    cost at most sum(P)/S + theta*N. No pool feasibility is assumed.
    """
    n, m, costs, cols = _contract(data, prices, scale)
    ordered = list(ordered)
    assert len(ordered) == len(set(ordered))
    assert all(type(j) is int and 0 <= j < m for j in ordered)
    ordered = [j for j in ordered if cols[j]]
    reduced = {j: costs[j] * scale - sum(prices[r] for r in cols[j]) for j in ordered}
    assert all(rc >= 0 for rc in reduced.values()), 'full-column dual validity required'
    ordered.sort(key=lambda j: (reduced[j] / len(cols[j]), -len(cols[j]), j))
    goal = math.ceil(2 * math.log(max(n, 2)))
    if not ordered:
        return [], {'degree_goal': goal, 'support_prefix_columns': 0, 'columns': 0,
                    'min_row_degree': 0, 'price_scale': scale,
                    'thickness_rule': 'support-prefix x4, within 10%-20% input coverage quantile'}
    total = [0] * n
    for j in ordered:
        for r in cols[j]:
            total[r] += 1
    goals = [min(goal, count) for count in total]
    degrees = [0] * n
    missing, prefix = sum(g > 0 for g in goals), 0
    for j in ordered:
        prefix += 1
        for r in cols[j]:
            if degrees[r] < goals[r] and degrees[r] + 1 == goals[r]:
                missing -= 1
            degrees[r] += 1
        if not missing:
            break
    amount = min(len(ordered), max(prefix, min(max(4 * prefix, math.ceil(.10 * len(ordered))), math.ceil(.20 * len(ordered)))))
    theta_numerator = reduced[ordered[amount - 1]]
    theta_rows = len(cols[ordered[amount - 1]])
    while amount < len(ordered) and reduced[ordered[amount]] * theta_rows <= theta_numerator * len(cols[ordered[amount]]):
        amount += 1
    pool = ordered[:amount]
    degrees = [0] * n
    for j in pool:
        for r in cols[j]:
            degrees[r] += 1
    return pool, {'degree_goal': goal, 'support_prefix_columns': prefix, 'columns': amount,
                  'min_row_degree': min(degrees), 'price_scale': scale,
                  'reduced_density_threshold': theta_numerator / (scale * theta_rows),
                  'theta_numerator': theta_numerator, 'theta_denominator': scale * theta_rows,
                  'partition_cost_upper_bound': sum(prices)/scale + theta_numerator*n/(scale*theta_rows),
                  'thickness_rule': 'support-prefix x4, within 10%-20% input coverage quantile'}

#!/usr/bin/env python3
"""Python-only hoffman1993 exact-cover basin probe and sparse HiGHS refinement.

FrontierOR authors, audited dataset derivative, CC BY 4.0 input attribution.
No reference solutions, subprocess solvers, compilers, network, or auxiliary files.
"""
import time
START = time.monotonic()
import argparse
from fractions import Fraction
import json
import math
import random
import sys


def read_instance(path):
    with open(path) as f:
        data = json.load(f)
    n, m = data["dimensions"]["num_rows"], data["dimensions"]["num_cols"]
    costs, cols = data["cost_vector"], data["constraint_matrix_A"]["columns"]
    if type(n) is not int or type(m) is not int or n <= 0 or m <= 0 or len(costs) != m or len(cols) != m:
        raise ValueError("full positive dimensions/cost/column agreement required")
    for cost, rows in zip(costs, cols):
        if type(cost) not in (int, float) or not math.isfinite(cost):
            raise ValueError("finite cost required")
        if rows != sorted(set(rows)) or any(type(r) is not int or not 0 <= r < n for r in rows):
            raise ValueError("coverage must be sorted, unique and in range")
    base = data.get("base_constraints") if data.get("has_base_constraints", False) else None
    k = base["num_constraints"] if base is not None else 0
    if type(k) is not int or k < 0:
        raise ValueError("nonnegative base.num_constraints required")
    if k and (len(base["D_matrix"]["rows"]) < k or len(base["lower_bounds_d1"]) < k or len(base["upper_bounds_d2"]) < k
              or any(len(base["D_matrix"]["rows"][i]) < m for i in range(k))):
        raise ValueError("all K Base rows and M coefficients required")
    return data


def dimensions(data):
    n, m = data["dimensions"]["num_rows"], data["dimensions"]["num_cols"]
    base = data.get("base_constraints") if data.get("has_base_constraints", False) else None
    return n, m, base["num_constraints"] if base is not None else 0, base


def cost(data, chosen):
    return sum(data["cost_vector"][j] for j in chosen)


def exact_cover(data, chosen):
    n, m, k, base = dimensions(data)
    if not isinstance(chosen, list) or any(type(j) is not int or not 0 <= j < m for j in chosen) or len(chosen) != len(set(chosen)):
        return False
    counts = [0] * n
    for j in chosen:
        for r in data["constraint_matrix_A"]["columns"][j]:
            counts[r] += 1
    if any(count != 1 for count in counts):
        return False
    eps = Fraction(1, 100000)
    for b in range(k):
        lhs = sum((Fraction(str(base["D_matrix"]["rows"][b][j])) for j in chosen), Fraction(0))
        lo, hi = base["lower_bounds_d1"][b], base["upper_bounds_d2"][b]
        if (math.isfinite(lo) and lhs + eps < Fraction(str(lo))) or (math.isfinite(hi) and lhs - eps > Fraction(str(hi))):
            return False
    return True


def write_solution(data, chosen, output):
    chosen = sorted(chosen)
    assert exact_cover(data, chosen), "whole exact cover, binary selected witness, and all K Base rows"
    _, m, _, _ = dimensions(data)
    selected = set(chosen)
    solution = {"objective_value": cost(data, chosen), "selected_rotations": chosen,
                "variable_values": {str(j): float(j in selected) for j in range(m)}}
    with open(output, "w") as f:
        json.dump(solution, f, separators=(",", ":"), allow_nan=False)
        f.write("\n")
    return solution


def finite(value):
    return float(value) if math.isfinite(value) else None


def highs_solve(data, deadline, incumbent=None):
    """Full original sparse MILP, including K=num_constraints Base ranges."""
    begin = time.monotonic()
    import highspy
    import numpy as np
    n, m, k, base = dimensions(data)
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = m, n + k
    lp.col_cost_ = np.asarray(data["cost_vector"], dtype=np.float64)
    lp.col_lower_, lp.col_upper_ = np.zeros(m), np.ones(m)
    rowlower, rowupper = [1.0] * n, [1.0] * n
    if k:
        def bound(v):
            return float(v) if math.isfinite(v) else (highspy.kHighsInf if v > 0 else -highspy.kHighsInf)
        rowlower += [bound(base["lower_bounds_d1"][b]) for b in range(k)]
        rowupper += [bound(base["upper_bounds_d2"][b]) for b in range(k)]
    lp.row_lower_, lp.row_upper_ = np.asarray(rowlower), np.asarray(rowupper)
    starts, indices, values = [0], [], []
    for j, rows in enumerate(data["constraint_matrix_A"]["columns"]):
        indices.extend(rows); values.extend([1.0] * len(rows))
        for b in range(k):
            v = base["D_matrix"]["rows"][b][j]
            if v:
                indices.append(n + b); values.append(float(v))
        starts.append(len(indices))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_, lp.a_matrix_.index_ = np.asarray(starts, dtype=np.int32), np.asarray(indices, dtype=np.int32)
    lp.a_matrix_.value_ = np.asarray(values, dtype=np.float64)
    lp.integrality_ = [highspy.HighsVarType.kInteger] * m
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 2)
    h.setOptionValue("random_seed", 1)
    status = h.passModel(lp)
    if status == highspy.HighsStatus.kError:
        raise ValueError("highspy full sparse model rejected")
    warm_status = None
    if incumbent is not None:
        selected = set(incumbent)
        sol = highspy.HighsSolution()
        sol.col_value = [float(j in selected) for j in range(m)]
        sol.value_valid = True
        warm_status = str(h.setSolution(sol))
    build = time.monotonic() - begin
    remaining = max(0.001, deadline - time.monotonic() - 0.15)
    h.setOptionValue("time_limit", remaining)
    search = time.monotonic()
    run_status = h.run()
    info, sol = h.getInfo(), h.getSolution()
    chosen = [j for j, v in enumerate(sol.col_value) if v > 0.5] if sol.value_valid else None
    if chosen is not None and not exact_cover(data, chosen):
        chosen = None
    metrics = {"solver": "highspy", "solver_version": h.version(), "threads": 2, "seed": 1,
               "model_columns": m, "model_rows": n + k, "model_nnz": len(indices), "model_scope": "full_original",
               "model_status": str(h.getModelStatus()), "run_status": str(run_status), "warm_status": warm_status,
               "model_build_seconds": build, "search_seconds": time.monotonic() - search,
               "best_bound": finite(info.mip_dual_bound), "mip_gap": finite(info.mip_gap), "nodes": int(info.mip_node_count)}
    return chosen, metrics


class ProbeLimit(Exception):
    pass


def bitset_probe(data, candidates, deadline, seed, cutoff=math.inf):
    """First better cover. Pool filtering controls cost; branching favors feasibility."""
    n, _, _, _ = dimensions(data)
    original = data["constraint_matrix_A"]["columns"]
    costs = data["cost_vector"]
    masks = [sum(1 << r for r in original[j]) for j in candidates]
    adj = [0] * n
    for p, j in enumerate(candidates):
        for r in original[j]:
            adj[r] |= 1 << p
    if any(not row for row in adj):
        return None, {"status": "EMPTY_ROW", "nodes": 0, "columns": len(candidates)}
    degrees = [a.bit_count() for a in adj]
    minimum = min(degrees)
    rng = random.Random(seed)
    ranks, conflicts = [], []
    for j in candidates:
        rows = original[j]
        ranks.append(rng.random() + 0.35 * len(rows))
        clash = 0
        for r in rows:
            clash |= adj[r]
        conflicts.append(clash)
    nodes, dead = 0, {}
    began = time.monotonic()
    def dfs(uncovered, active, path, value):
        nonlocal nodes
        nodes += 1
        if nodes % 128 == 1 and time.monotonic() >= deadline:
            raise ProbeLimit()
        while uncovered:
            remaining, best_count, options = uncovered, len(candidates) + 1, 0
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
            value += costs[candidates[p]]
            if value >= cutoff:
                return None
            path.append(candidates[p]); uncovered ^= masks[p]; active &= ~conflicts[p]
        if not uncovered:
            return path if value < cutoff else None
        if value >= cutoff or (uncovered in dead and value >= dead[uncovered]):
            return None
        choices = []
        while options:
            bit = options & -options; options -= bit; choices.append(bit.bit_length() - 1)
        current = {}
        def branch_key(p):
            scarcity = 0.0
            for r in original[candidates[p]]:
                degree = current.get(r)
                if degree is None:
                    degree = (active & adj[r]).bit_count()
                    current[r] = degree
                scarcity += 1.0 / degree
            return ranks[p] + best_count * scarcity
        choices.sort(key=branch_key, reverse=True)
        for p in choices:
            next_value = value + costs[candidates[p]]
            if next_value >= cutoff:
                continue
            found = dfs(uncovered ^ masks[p], active & ~conflicts[p], path + [candidates[p]], next_value)
            if found is not None:
                return found
        if len(dead) < 100000:
            dead[uncovered] = min(value, dead.get(uncovered, math.inf))
        return None
    status = "EXHAUSTED"
    try:
        found = dfs((1 << n) - 1, (1 << len(candidates)) - 1, [], 0)
        if found is not None:
            status = "FEASIBLE"
    except ProbeLimit:
        found, status = None, "TIME_LIMIT"
    return found, {"status": status, "nodes": nodes, "columns": len(candidates), "min_row_degree": minimum,
                   "seconds": time.monotonic() - began, "branch_order": "independent random + coverage + current-compatible scarcity; cost-free"}


def density_pool(data, ordered):
    n, _, _, _ = dimensions(data)
    cols, costs = data["constraint_matrix_A"]["columns"], data["cost_vector"]
    total = [0] * n
    for j in ordered:
        for r in cols[j]:
            total[r] += 1
    goal = math.ceil(2 * math.log(max(n, 2)))
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
    amount = min(len(ordered), max(prefix, min(max(4 * prefix, math.ceil(0.10 * len(ordered))), math.ceil(0.20 * len(ordered)))))
    theta = costs[ordered[amount - 1]] / len(cols[ordered[amount - 1]])
    while amount < len(ordered) and costs[ordered[amount]] / len(cols[ordered[amount]]) <= theta + 1e-12:
        amount += 1
    return ordered[:amount], {"degree_goal": goal, "support_prefix_columns": prefix, "columns": amount,
                             "density_threshold": theta, "cover_cost_upper_bound": theta * n,
                             "thickness_rule": "support-prefix x4, within 10%-20% input coverage quantile"}


def solve(data, deadline):
    n, m, k, _ = dimensions(data)
    costs, cols = data["cost_vector"], data["constraint_matrix_A"]["columns"]
    best, trace, probes = None, [], {}
    if k == 0 and n <= 256 and all(c > 0 for c in costs):
        canonical = {}
        singleton = {}
        for j, rows in enumerate(cols):
            if not rows:
                continue
            key = tuple(rows)
            if key not in canonical or costs[j] < costs[canonical[key]]:
                canonical[key] = j
            if len(rows) == 1 and (rows[0] not in singleton or costs[j] < costs[singleton[rows[0]]]):
                singleton[rows[0]] = j
        ordered = sorted(canonical.values(), key=lambda j: (costs[j] / len(cols[j]), -len(cols[j]), j))
        if len(singleton) == n:
            best = [singleton[r] for r in range(n)]
            probes["cold"] = {"status": "SINGLETON_COVER", "columns": len(ordered)}
        elif ordered:
            best, probes["cold"] = bitset_probe(data, ordered, min(deadline, time.monotonic() + 2), 1)
        if best is not None:
            trace.append([time.monotonic() - START, cost(data, best), "pure_python_cold"])
        if m > 3 * n and sum(map(len, cols)) > 2 * m and ordered and time.monotonic() < deadline - 1:
            pool, probes["pool"] = density_pool(data, ordered)
            found, probes["density_probe"] = bitset_probe(data, pool, min(deadline - 1, time.monotonic() + 6), 104729,
                                                        cost(data, best) if best is not None else math.inf)
            if found is not None:
                best = found
                trace.append([time.monotonic() - START, cost(data, best), "density_pool_basin"])
    candidate, metrics = highs_solve(data, deadline, best)
    if candidate is not None and (best is None or cost(data, candidate) < cost(data, best)):
        best = candidate
        trace.append([time.monotonic() - START, cost(data, best), "warm_full_highs"])
    if best is None:
        raise ValueError("no whole feasible solution within internal budget")
    return best, {"method": "pure Python bitset basin + warm full sparse highspy", "probes": probes,
                  "improvement_trace": trace, "highs": metrics}


def cli_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--time-limit", type=float, required=True)
    args = parser.parse_args()
    if args.problem != "hoffman1993" or args.time_limit <= 0:
        raise ValueError("hoffman1993 and a positive time limit required")
    return args


def main():
    args = cli_args()
    deadline = START + max(0.01, min(55.0, args.time_limit - 5.0))
    data = read_instance(args.instance)
    chosen, metrics = solve(data, deadline)
    solution = write_solution(data, chosen, args.output)
    metrics.update(objective=solution["objective_value"], selected_count=len(chosen), internal_seconds=time.monotonic() - START,
                   internal_budget_seconds=max(0.01, min(55.0, args.time_limit - 5.0)))
    print(json.dumps({"metrics": metrics}, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({"failure": type(error).__name__ + ": " + str(error)}), file=sys.stderr, flush=True)
        sys.exit(2)

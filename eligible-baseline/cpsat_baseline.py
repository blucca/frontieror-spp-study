#!/usr/bin/env python3
import time
START = time.monotonic()
import importlib.util
from fractions import Fraction
import json
import math
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("main_spp", Path(__file__).resolve().parents[1] / "main/solve.py")
spp = importlib.util.module_from_spec(spec); spec.loader.exec_module(spp)


def main():
    args = spp.cli_args()
    data = spp.read_instance(args.instance)
    import ortools
    from ortools.sat.python import cp_model
    n, m, k, base = spp.dimensions(data)
    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{j}") for j in range(m)]
    rows = [[] for _ in range(n)]
    for j, coverage in enumerate(data["constraint_matrix_A"]["columns"]):
        for r in coverage:
            rows[r].append(x[j])
    for row in rows:
        model.add_exactly_one(row)
    costs = data["cost_vector"]
    if any(Fraction(str(c)).denominator != 1 for c in costs):
        raise ValueError("CP-SAT baseline requires schema integer costs")
    model.minimize(sum(int(c) * x[j] for j, c in enumerate(costs)))
    for b in range(k):
        coefficients = [Fraction(str(c)) for c in base["D_matrix"]["rows"][b][:m]]
        lo, hi = base["lower_bounds_d1"][b], base["upper_bounds_d2"][b]
        scale = 1
        for f in coefficients + [Fraction(str(v)) for v in (lo, hi) if math.isfinite(v)]:
            scale = math.lcm(scale, f.denominator)
        if scale > 10 ** 9:
            raise ValueError("exact Base integer scale exceeds declared CP-SAT range")
        expr = sum(int(c * scale) * x[j] for j, c in enumerate(coefficients) if c)
        if math.isfinite(lo): model.add(expr >= int(Fraction(str(lo)) * scale))
        if math.isfinite(hi): model.add(expr <= int(Fraction(str(hi)) * scale))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 2
    solver.parameters.random_seed = 1
    solver.parameters.max_memory_in_mb = 4096
    solver.parameters.log_search_progress = True
    solver.parameters.log_to_stdout = False
    solver.parameters.max_time_in_seconds = max(0.001, START + min(55, args.time_limit - 5) - time.monotonic() - 0.15)
    build = time.monotonic() - START
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError("cold CP-SAT has no whole feasible solution: " + solver.status_name(status))
    chosen = [j for j in range(m) if solver.value(x[j])]
    solution = spp.write_solution(data, chosen, args.output)
    metrics = {"solver": "OR-Tools CP-SAT", "solver_version": ortools.__version__, "threads": 2, "seed": 1,
               "method": "stock full Boolean exactly-one CP-SAT cold", "initial_hints": 0,
               "objective": solution["objective_value"], "best_bound": solver.best_objective_bound,
               "model_status": solver.status_name(status), "model_build_seconds": build,
               "search_seconds": solver.wall_time, "internal_seconds": time.monotonic() - START,
               "branches": solver.num_branches, "conflicts": solver.num_conflicts, "response_stats": solver.response_stats()}
    print(json.dumps({"metrics": metrics}, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({"failure": type(error).__name__ + ": " + str(error)}), file=sys.stderr)
        sys.exit(2)

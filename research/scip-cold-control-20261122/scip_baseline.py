#!/usr/bin/env python3
"""Plain cold SCIP: full original hoffman1993 binary Ax=1 and all K Base rows.

FrontierOR authors, audited dataset derivative, CC BY 4.0 input attribution.
Only the instance is read. No hints, warm starts, reference solutions or fallback.
The original v3 module supplies stdlib-only input, cost and witness validation.
"""
import time
START = time.monotonic()
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import os
import resource
import sys
import traceback
import original_v3 as io


STATUS = {0: "OPTIMAL", 1: "FEASIBLE", 2: "INFEASIBLE", 3: "UNBOUNDED",
          4: "ABNORMAL", 5: "MODEL_INVALID", 6: "NOT_SOLVED"}


def dump(path, data):
    with Path(path).open("w") as f:
        json.dump(data, f, separators=(",", ":"), allow_nan=False)
        f.write("\n")


def finite(value):
    return float(value) if math.isfinite(value) else None


def assemble(data, seed):
    # Do not import highspy: its wheel and OR-Tools have incompatible symbols
    # when loaded together. The original IO functions use only the stdlib.
    from ortools.linear_solver import pywraplp
    n, m, k, base = io.dimensions(data)
    h = pywraplp.Solver.CreateSolver("SCIP")
    if h is None:
        raise ValueError("existing OR-Tools wheel must provide SCIP")
    threads_ok = h.SetNumThreads(2)
    parameters = f"randomization/randomseedshift = {seed}\n"
    parameters_ok = h.SetSolverSpecificParametersAsString(parameters)
    if not parameters_ok:
        raise ValueError("SCIP rejected the declared random seed parameter")
    h.EnableOutput()
    x = [h.BoolVar(f"x{j}") for j in range(m)]
    rows = [h.Constraint(1.0, 1.0, f"A{r}") for r in range(n)]
    nnz = 0
    for j, coverage in enumerate(data["constraint_matrix_A"]["columns"]):
        for r in coverage:
            rows[r].SetCoefficient(x[j], 1.0)
            nnz += 1
    base_rows = []
    for b in range(k):
        lower, upper = base["lower_bounds_d1"][b], base["upper_bounds_d2"][b]
        if type(lower) not in (int, float) or type(upper) not in (int, float) or math.isnan(lower) or math.isnan(upper) or lower > upper:
            raise ValueError("each active Base row requires ordered numeric bounds")
        lo = float(lower) if math.isfinite(lower) else (-h.infinity() if lower < 0 else h.infinity())
        hi = float(upper) if math.isfinite(upper) else (-h.infinity() if upper < 0 else h.infinity())
        row = h.Constraint(lo, hi, f"Base{b}")
        for j, coefficient in enumerate(base["D_matrix"]["rows"][b][:m]):
            if type(coefficient) not in (int, float) or not math.isfinite(coefficient):
                raise ValueError("finite numeric coefficients required in every active Base row")
            if coefficient:
                row.SetCoefficient(x[j], float(coefficient))
                nnz += 1
        base_rows.append(row)
    objective = h.Objective()
    for j, c in enumerate(data["cost_vector"]):
        objective.SetCoefficient(x[j], float(c))
    objective.SetMinimization()
    assert h.NumVariables() == m and h.NumConstraints() == n + k
    metrics = {"solver": "SCIP", "solver_version": h.SolverVersion(),
               "ortools_version": importlib.metadata.version("ortools"),
               "requested_threads": 2, "set_num_threads_returned": bool(threads_ok),
               "actual_native_thread_count": None, "seed": seed,
               "seed_parameters": parameters, "seed_parameters_accepted": bool(parameters_ok),
               "model_scope": "full_original", "model_columns": m, "model_rows": n + k,
               "coverage_rows": n, "base_constraint_count": k,
               "base_num_bases_schema": base.get("num_bases") if base else None,
               "model_nnz": nnz, "warm_start": False,
               "affinity": sorted(os.sched_getaffinity(0)),
               "ram_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
               "cpu_limit_seconds": resource.getrlimit(resource.RLIMIT_CPU)[0]}
    return h, x, objective, rows, base_rows, metrics


def solve(data, deadline, seed, output):
    h, x, objective, _, _, metrics = assemble(data, seed)
    metrics["model_build_and_import_seconds"] = time.monotonic() - START
    remaining_ms = max(1, int((deadline - time.monotonic() - 0.15) * 1000))
    h.SetTimeLimit(remaining_ms)
    metrics["native_time_limit_ms"] = remaining_ms
    search = time.monotonic()
    status = h.Solve()
    metrics.update(native_status_code=int(status), native_status=STATUS.get(int(status), str(status)),
                   native_returned=True, native_search_seconds=time.monotonic() - search,
                   native_wall_seconds=h.WallTime() / 1000.0, nodes=int(h.nodes()),
                   native_objective=None, best_bound=None, primal_bound_relative_gap=None,
                   gap_definition="abs(native objective - best bound) / abs(native objective); derived, SCIP printed gap retained by controller",
                   native_has_feasible_status=status in (h.OPTIMAL, h.FEASIBLE),
                   recomputed_exact_cover_feasible=False, recomputed_cost=None)
    values, chosen = None, None
    if status in (h.OPTIMAL, h.FEASIBLE):
        metrics["native_objective"] = finite(objective.Value())
        metrics["best_bound"] = finite(objective.BestBound())
        obj, bound = metrics["native_objective"], metrics["best_bound"]
        if obj is not None and bound is not None:
            metrics["primal_bound_relative_gap"] = abs(obj - bound) / max(abs(obj), 1e-10)
        values = [float(z.solution_value()) for z in x]
        metrics["native_max_binary_distance"] = max(abs(v - round(v)) for v in values)
        chosen = [j for j, value in enumerate(values) if value > 0.5]
        metrics["recomputed_exact_cover_feasible"] = io.exact_cover(data, chosen)
        metrics["recomputed_cost"] = io.cost(data, chosen)
        if metrics["recomputed_exact_cover_feasible"]:
            io.write_solution(data, chosen, output)
    return {"metrics": metrics, "native_variable_values": values,
            "native_selected_rotations_rounded": chosen}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", choices=("hoffman1993",), required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    raw_path = str(args.output) + ".raw.json"
    raw = {"metrics": {"solver": "SCIP", "native_returned": False,
                        "recomputed_exact_cover_feasible": False}}
    try:
        if args.time_limit <= 5:
            raise ValueError("whole time limit must leave five seconds for external validation")
        data = io.read_instance(args.instance)
        raw = solve(data, START + min(55.0, args.time_limit - 5.0), args.seed, args.output)
    except Exception as error:
        raw["metrics"].update(failure_kind="RESOURCE_ERROR" if isinstance(error, MemoryError) else "SETUP_OR_ADAPTER_ERROR",
                              failure=type(error).__name__ + ": " + str(error))
        traceback.print_exc()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    raw["metrics"].update(own_wall_seconds=time.monotonic() - START,
                          cpu_user_seconds=usage.ru_utime, cpu_system_seconds=usage.ru_stime,
                          peak_rss_kib=usage.ru_maxrss)
    dump(raw_path, raw)
    print(json.dumps({"metrics": raw["metrics"]}, allow_nan=False), flush=True)
    return 0 if raw["metrics"]["recomputed_exact_cover_feasible"] else 2


if __name__ == "__main__":
    sys.exit(main())

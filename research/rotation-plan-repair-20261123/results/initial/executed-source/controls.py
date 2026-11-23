#!/usr/bin/env python3
"""Full K0 hoffman1993 repair controls; FrontierOR authors, CC BY 4.0 input.

Original binary Ax=1, F=0, P=1; lexicographic (removed old rotations, cost).
Separate CLI processes select CP-SAT 9.15.6755 or OR-Tools SCIP 10. No highspy.
"""
import time
START = time.monotonic()
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import sys


def load(path):
    with open(path) as stream:
        return json.load(stream)


def read_instance(path):
    data = load(path)
    n, m = data["dimensions"]["num_rows"], data["dimensions"]["num_cols"]
    cols, costs = data["constraint_matrix_A"]["columns"], data["cost_vector"]
    if type(n) is not int or type(m) is not int or min(n, m) <= 0 or len(cols) != m or len(costs) != m:
        raise ValueError("positive full N/M dimensions and all M columns/costs required")
    k = data["base_constraints"]["num_constraints"] if data.get("has_base_constraints", False) else 0
    if type(k) is not int or k != 0:
        raise ValueError("this repair decision gate requires K0")
    for rows in cols:
        if not isinstance(rows, list) or any(type(r) is not int or not 0 <= r < n for r in rows) or rows != sorted(set(rows)):
            raise ValueError("sorted unique original coverage indices required")
    for c in costs:
        if type(c) not in (int, float) or not math.isfinite(c) or c < 0 or Fraction(str(c)).denominator != 1:
            raise ValueError("original integer nonnegative costs required")
    data["cost_vector"] = [int(c) for c in costs]
    return data


def exact_cover(data, chosen):
    n, m = data["dimensions"]["num_rows"], data["dimensions"]["num_cols"]
    if not isinstance(chosen, list) or any(type(j) is not int or not 0 <= j < m for j in chosen) or len(set(chosen)) != len(chosen):
        return False
    counts = [0] * n
    for j in chosen:
        for r in data["constraint_matrix_A"]["columns"][j]:
            counts[r] += 1
    return all(count == 1 for count in counts)


def check(data, old, event, chosen):
    return exact_cover(data, chosen) and not set(chosen).intersection(event["F"]) and set(event["P"]).issubset(chosen)


def cost(data, chosen):
    return sum(data["cost_vector"][j] for j in chosen)


def make_solution(data, chosen):
    selected = set(chosen)
    return {"objective_value": cost(data, chosen),
            "selected_rotations": sorted(chosen),
            "variable_values": {str(j): float(j in selected) for j in range(data["dimensions"]["num_cols"])}}


def read_plan(data, path):
    plan = load(path)
    chosen, values = plan["selected_rotations"], plan["variable_values"]
    if not exact_cover(data, chosen) or not isinstance(values, dict) or set(values) != {str(j) for j in range(data["dimensions"]["num_cols"])}:
        raise ValueError("plan requires full original exact cover and all M variable_values")
    selected = set(chosen)
    if any(type(v) not in (int, float) or v not in (0, 1) or v != int(int(j) in selected) for j, v in values.items()):
        raise ValueError("plan binary values must exactly agree with selected_rotations")
    if type(plan["objective_value"]) not in (int, float) or plan["objective_value"] != cost(data, chosen):
        raise ValueError("plan objective must equal independently recomputed original cost")
    return sorted(chosen)


def read_event(data, old, path):
    event = load(path)
    m = data["dimensions"]["num_cols"]
    for name in ("F", "P"):
        ids = event[name]
        if not isinstance(ids, list) or any(type(j) is not int or not 0 <= j < m for j in ids) or len(ids) != len(set(ids)):
            raise ValueError("F/P require unique original rotation IDs")
    if not set(event["P"]).issubset(old):
        raise ValueError("this gate requires P subset of the complete old plan")
    if set(event["F"]).intersection(event["P"]):
        raise ValueError("contradictory F/P declarations")
    return event


def stage(status="NOT_RUN"):
    return dict(status=status, status_code=None, objective=None, best_bound=None, seconds=0.0,
                native_returned=False, hint_source=None, hint_count=0)


def finite(value):
    return float(value) if math.isfinite(value) else None


def run(args, data, old, event, result, best=None):
    import ortools
    if ortools.__version__ != "9.15.6755":
        raise ValueError("this matched gate requires OR-Tools 9.15.6755")
    result["ortools_version"] = ortools.__version__
    n, m = data["dimensions"]["num_rows"], data["dimensions"]["num_cols"]
    result["model_scope"] = dict(N=n, M=m, K=0, formulation="full original binary Ax=1 / F=0 / P=1")
    cp = args.solver == "cpsat"
    if cp:
        from ortools.sat.python import cp_model
        model, solver = cp_model.CpModel(), cp_model.CpSolver()
        x = [model.new_bool_var(f"x{j}") for j in range(m)]
        rows = [[] for _ in range(n)]
        for j, coverage in enumerate(data["constraint_matrix_A"]["columns"]):
            for r in coverage:
                rows[r].append(x[j])
        for row in rows:
            model.add_exactly_one(row)
        for j in event["F"]: model.add(x[j] == 0)
        for j in event["P"]: model.add(x[j] == 1)
        solver.parameters.num_search_workers = 2
        solver.parameters.random_seed = args.seed
        solver.parameters.max_memory_in_mb = 4096
        result["solver_version"] = "CP-SAT " + ortools.__version__
    else:
        from ortools.linear_solver import pywraplp
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if solver is None or not solver.SolverVersion().startswith("SCIP 10."):
            raise ValueError("this matched gate requires the existing OR-Tools SCIP 10")
        result["solver_version"] = solver.SolverVersion()
        result["set_num_threads_returned"] = bool(solver.SetNumThreads(2))
        parameters = f"randomization/randomseedshift = {args.seed}\n"
        result["seed_parameters_accepted"] = bool(solver.SetSolverSpecificParametersAsString(parameters))
        if not result["set_num_threads_returned"] or not result["seed_parameters_accepted"]:
            raise ValueError("SCIP rejected the declared threads/seed parameters")
        solver.EnableOutput()
        x = [solver.BoolVar(f"x{j}") for j in range(m)]
        rows = [solver.Constraint(1, 1, f"A{r}") for r in range(n)]
        for j, coverage in enumerate(data["constraint_matrix_A"]["columns"]):
            for r in coverage:
                rows[r].SetCoefficient(x[j], 1)
        for j in event["F"]: x[j].SetBounds(0, 0)
        for j in event["P"]: x[j].SetBounds(1, 1)
        objective = solver.Objective()
    result["model_build_and_import_seconds"] = time.monotonic() - START
    fixed = args.primary_fixed
    if fixed is not None:
        result["primary"] = stage("EXTERNALLY_FIXED")
        result["primary"].update(objective=fixed, source="external_method_value_with_independently_verified_witness")
    for name in ("primary", "secondary"):
        if name == "primary" and fixed is not None:
            continue
        if name == "secondary" and fixed is None:
            result[name] = stage("NOT_RUN_PRIMARY_NOT_OPTIMAL")
            break
        primary = name == "primary"
        hint_ids = old if primary else list(range(m))
        hint_selected = set(best or [])
        hint_values = [int(j not in event["F"]) for j in old] if primary else [int(j in hint_selected) for j in hint_ids]
        hint_source = "legal_old_partial" if primary else ("external_method_witness_verified" if args.primary_fixed is not None else "own_primary_optimal_full")
        record = stage()
        record.update(hint_source=hint_source, hint_count=len(hint_ids))
        result[name] = record
        if cp:
            model.clear_hints()
            for j, value in zip(hint_ids, hint_values): model.add_hint(x[j], value)
            if primary:
                model.minimize(sum(1 - x[j] for j in old))
            else:
                model.add(sum(x[j] for j in old) == len(old) - fixed)
                model.minimize(sum(c * x[j] for j, c in enumerate(data["cost_vector"])))
        else:
            solver.SetHint([x[j] for j in hint_ids], hint_values)
            objective.Clear()
            objective.SetMinimization()
            if primary:
                objective.SetOffset(len(old))
                for j in old: objective.SetCoefficient(x[j], -1)
            else:
                objective.SetOffset(0)
                row = solver.Constraint(len(old) - fixed, len(old) - fixed, "fixed_removed_old")
                for j in old: row.SetCoefficient(x[j], 1)
                for j, c in enumerate(data["cost_vector"]): objective.SetCoefficient(x[j], c)
        remaining = START + args.time_limit - time.monotonic() - 0.15
        if remaining <= 0:
            record["status"] = "NOT_RUN_DEADLINE"
            break
        if cp: solver.parameters.max_time_in_seconds = remaining
        else: solver.SetTimeLimit(max(1, int(remaining * 1000)))
        began = time.monotonic()
        code = solver.solve(model) if cp else solver.Solve()
        feasible = code in (solver.OPTIMAL, solver.FEASIBLE) if not cp else code in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        optimal = code == (cp_model.OPTIMAL if cp else solver.OPTIMAL)
        status = solver.status_name(code) if cp else {0: "OPTIMAL", 1: "FEASIBLE", 2: "INFEASIBLE", 3: "UNBOUNDED", 4: "ABNORMAL", 5: "MODEL_INVALID", 6: "NOT_SOLVED"}.get(code, str(code))
        bound = (solver.best_objective_bound if cp else objective.BestBound()) if status in ("OPTIMAL", "FEASIBLE", "UNKNOWN", "NOT_SOLVED") else None
        value = (solver.objective_value if cp else objective.Value()) if feasible else None
        record.update(status=status, status_code=int(code), native_returned=True, seconds=time.monotonic() - began,
                      objective=finite(value) if value is not None else None, best_bound=finite(bound) if bound is not None else None)
        if feasible:
            chosen = [j for j in range(m) if (solver.value(x[j]) if cp else x[j].solution_value()) > 0.5]
            if not check(data, old, event, chosen):
                raise ValueError("native witness failed the complete original/event checker")
            d, actual_cost = len(set(old).difference(chosen)), cost(data, chosen)
            if abs(value - (d if primary else actual_cost)) > 1e-6 or (not primary and d != fixed):
                raise ValueError("native objective/fixed D failed exact independent recomputation")
            # Cost-stage hints may be ignored; retain the already verified primary
            # witness if a time-limited cost search returns a more expensive one.
            retained = primary or best is None or actual_cost <= cost(data, best)
            record["candidate_retained"] = retained
            if retained:
                best = chosen
                result.update(solution=make_solution(data, best), removed_old_count=d, actual_cost=actual_cost, verified=True)
        if primary and optimal:
            fixed = result["removed_old_count"]
    result.update(primary_native_optimal=result["primary"]["status"] == "OPTIMAL",
                  secondary_native_optimal=result["secondary"]["status"] == "OPTIMAL")
    result["lexicographic_complete"] = result["primary_native_optimal"] and result["secondary_native_optimal"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", choices=("cpsat", "scip"), required=True)
    for name in ("instance", "old-plan", "event", "output"): parser.add_argument("--" + name, required=True)
    parser.add_argument("--time-limit", type=float, default=55)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--primary-fixed", type=int)
    parser.add_argument("--hint-plan")
    args = parser.parse_args()
    result = dict(solver=args.solver, threads=2, seed=args.seed, time_limit_seconds=args.time_limit,
                  primary=stage(), secondary=stage(), solution=None, declared_event=None,
                  removed_old_count=None, actual_cost=None, verified=False,
                  primary_native_optimal=False, secondary_native_optimal=False, lexicographic_complete=False)
    try:
        if not math.isfinite(args.time_limit) or args.time_limit <= 0 or not 0 <= args.seed < 2**31:
            raise ValueError("positive finite whole limit and seed in [0,2^31) required")
        data = read_instance(args.instance)
        old = read_plan(data, args.old_plan)
        event = read_event(data, old, args.event)
        result["declared_event"] = event
        best = None
        if args.primary_fixed is not None:
            if not 0 <= args.primary_fixed <= len(old) or not args.hint_plan:
                raise ValueError("fixed D requires in-range integer and independently verified --hint-plan")
            best = read_plan(data, args.hint_plan)
            if not check(data, old, event, best) or len(set(old).difference(best)) != args.primary_fixed:
                raise ValueError("external hint must satisfy full Ax=1/F/P and the declared fixed D")
            result.update(solution=make_solution(data, best), removed_old_count=args.primary_fixed,
                          actual_cost=cost(data, best), verified=True)
        elif args.hint_plan:
            raise ValueError("external --hint-plan requires --primary-fixed")
        run(args, data, old, event, result, best)
    except Exception as error:
        result["failure"] = type(error).__name__ + ": " + str(error)
    result["own_wall_seconds_before_output"] = time.monotonic() - START
    Path(args.output).write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"output": args.output, "primary": result["primary"]["status"],
                      "secondary": result["secondary"]["status"], "verified": result["verified"]}), flush=True)
    return 0 if result["verified"] and "failure" not in result else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""FrontierOR hoffman1993 sparse transport, full witness check, and bounded runs.

Source attribution: FrontierOR authors, audited derivative, CC BY 4.0.
Cold workers read instances only. Published solutions are never solver inputs.
Transport: N(rows) M(columns) K(base.num_constraints), then M cost/count/rows
lines, then K lower/upper/M-coefficients lines. All temporary files stay here.
"""
import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

RAM = 4 * 1024 ** 3
SOURCE_NAMES = {"tiny": "tiny_instance", "large2": "large_instance_2", "large3": "large_instance_3"}


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def model(path):
    data = json.loads(Path(path).read_text())
    n, m = data["dimensions"]["num_rows"], data["dimensions"]["num_cols"]
    costs, cols = data["cost_vector"], data["constraint_matrix_A"]["columns"]
    if not (isinstance(n, int) and isinstance(m, int) and n > 0 and m > 0):
        raise ValueError("positive integer dimensions required")
    if len(costs) != m or len(cols) != m:
        raise ValueError("full dimension/cost/column agreement required")
    for cost, rows in zip(costs, cols):
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost):
            raise ValueError("finite numeric cost required")
        if rows != sorted(set(rows)) or any(type(r) is not int or not 0 <= r < n for r in rows):
            raise ValueError("sorted unique in-range coverage required")
    base = data.get("base_constraints") if data.get("has_base_constraints", False) else None
    k = base["num_constraints"] if base is not None else 0
    if not isinstance(k, int) or k < 0:
        raise ValueError("base.num_constraints must be a nonnegative integer")
    if k and (len(base["D_matrix"]["rows"]) < k or len(base["lower_bounds_d1"]) < k or len(base["upper_bounds_d2"]) < k):
        raise ValueError("K base rows and bounds required")
    if k and any(len(base["D_matrix"]["rows"][i]) < m for i in range(k)):
        raise ValueError("each active base row must contain M coefficients")
    return data, n, m, k, costs, cols, base


def transport(instance, output):
    data, n, m, k, costs, cols, base = model(instance)
    with Path(output).open("w") as f:
        f.write(f"{n} {m} {k}\n")
        for cost, rows in zip(costs, cols):
            f.write(" ".join(map(str, [cost, len(rows), *rows])) + "\n")
        for i in range(k):
            f.write(" ".join(map(str, [base["lower_bounds_d1"][i], base["upper_bounds_d2"][i], *base["D_matrix"]["rows"][i][:m]])) + "\n")
    return {"rows": n, "columns": m, "base_constraints": k, "nnz": sum(map(len, cols))}


def exact(instance, solution):
    data, n, m, k, costs, cols, base = model(instance)
    problems = []
    chosen, x = solution.get("selected_rotations"), solution.get("variable_values")
    if not isinstance(chosen, list) or any(type(j) is not int or not 0 <= j < m for j in chosen):
        return {"feasible": False, "violations": ["selected_rotations must contain valid integer indices"]}
    if len(chosen) != len(set(chosen)):
        problems.append("selected_rotations contains duplicates")
    if not isinstance(x, dict) or set(x) != {str(j) for j in range(m)}:
        return {"feasible": False, "violations": problems + ["variable_values must contain exactly all M string indices"]}
    if any(type(v) not in (int, float) or v not in (0, 1) for v in x.values()):
        return {"feasible": False, "violations": problems + ["all variable values must be exactly binary"]}
    vector_chosen = {j for j in range(m) if x[str(j)] == 1}
    if vector_chosen != set(chosen):
        problems.append("selected_rotations and variable_values differ")
    counts = [0] * n
    for j in vector_chosen:
        for r in cols[j]:
            counts[r] += 1
    bad_rows = [r for r, count in enumerate(counts) if count != 1]
    if bad_rows:
        problems.append("coverage differs from exact one at rows " + str(bad_rows))
    value = sum((Fraction(str(costs[j])) for j in vector_chosen), Fraction(0))
    reported = solution.get("objective_value")
    if type(reported) not in (int, float) or not math.isfinite(reported) or Fraction(str(reported)) != value:
        problems.append("reported objective differs from exact cost recomputation")
    base_values = []
    for i in range(k):
        lhs = sum((Fraction(str(base["D_matrix"]["rows"][i][j])) for j in vector_chosen), Fraction(0))
        lower, upper = base["lower_bounds_d1"][i], base["upper_bounds_d2"][i]
        eps = Fraction(1, 100000)
        if (math.isfinite(lower) and lhs + eps < Fraction(str(lower))) or (math.isfinite(upper) and lhs - eps > Fraction(str(upper))):
            problems.append(f"base constraint {i} failed")
        base_values.append(str(lhs))
    return {"feasible": not problems, "violations": problems, "row_counts": counts,
            "selected_count": len(chosen), "variable_count": len(x),
            "recomputed_objective": int(value) if value.denominator == 1 else float(value),
            "base_constraint_count": k, "base_lhs_exact": base_values}


def normalize(instance, raw):
    _, _, m, _, _, _, _ = model(instance)
    chosen = raw.get("selected_rotations")
    if not isinstance(chosen, list) or any(type(j) is not int or not 0 <= j < m for j in chosen):
        raise ValueError("raw selected_rotations must be a list of valid integer indices")
    selected = set(chosen)
    solution = {"objective_value": raw.get("objective_value"), "selected_rotations": chosen,
                "variable_values": raw.get("variable_values", {str(j): float(j in selected) for j in range(m)})}
    verdict = exact(instance, solution)
    if not verdict["feasible"]:
        raise ValueError("independent exact witness failure: " + "; ".join(verdict["violations"]))
    return solution, verdict


def cpsat(instance, limit, seed):
    start = time.monotonic()
    import ortools
    from ortools.sat.python import cp_model
    _, n, m, k, costs, cols, base = model(instance)
    cp = cp_model.CpModel()
    x = [cp.new_bool_var(f"x{j}") for j in range(m)]
    rows = [[] for _ in range(n)]
    for j, coverage in enumerate(cols):
        for r in coverage:
            rows[r].append(x[j])
    for row in rows:
        cp.add_exactly_one(row)
    if any(Fraction(str(c)).denominator != 1 for c in costs):
        raise ValueError("CP-SAT baseline requires integer costs")
    cp.minimize(sum(int(c) * x[j] for j, c in enumerate(costs)))
    for i in range(k):
        coefficients = [Fraction(str(c)) for c in base["D_matrix"]["rows"][i][:m]]
        lower, upper = base["lower_bounds_d1"][i], base["upper_bounds_d2"][i]
        scale = 1
        for f in coefficients + [Fraction(str(v)) for v in (lower, upper) if math.isfinite(v)]:
            scale = math.lcm(scale, f.denominator)
        if scale > 10 ** 9:
            raise ValueError("CP-SAT exact Base scaling exceeds declared integer range")
        expr = sum(int(c * scale) * x[j] for j, c in enumerate(coefficients) if c)
        if math.isfinite(lower):
            cp.add(expr >= int(Fraction(str(lower)) * scale))
        if math.isfinite(upper):
            cp.add(expr <= int(Fraction(str(upper)) * scale))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 2
    solver.parameters.random_seed = seed
    solver.parameters.max_time_in_seconds = max(0.001, limit - (time.monotonic() - start))
    solver.parameters.max_memory_in_mb = 4096
    solver.parameters.log_search_progress = True
    solver.parameters.log_to_stdout = False
    build = time.monotonic() - start
    status = solver.solve(cp)
    chosen = [j for j in range(m) if solver.value(x[j])] if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else []
    objective = sum(costs[j] for j in chosen) if chosen else None
    return {"status": solver.status_name(status), "objective_value": objective, "selected_rotations": chosen,
            "metrics": {"solver": "OR-Tools CP-SAT", "solver_version": ortools.__version__, "threads": 2,
                        "seed": seed, "build_seconds": build, "search_seconds": solver.wall_time,
                        "internal_seconds": time.monotonic() - start, "best_bound": solver.best_objective_bound,
                        "branches": solver.num_branches, "conflicts": solver.num_conflicts,
                        "response_stats": solver.response_stats()}}


def usage():
    own = resource.getrusage(resource.RUSAGE_SELF)
    kids = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"cpu_user_seconds": own.ru_utime + kids.ru_utime,
            "cpu_system_seconds": own.ru_stime + kids.ru_stime,
            "max_rss_kib": max(own.ru_maxrss, kids.ru_maxrss)}


def worker(args):
    start = time.monotonic()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    record = {"solver": args.solver, "instance": str(args.instance), "seed": args.seed,
              "search_budget_seconds": args.limit, "threads": 2, "affinity": sorted(os.sched_getaffinity(0)),
              "ram_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0], "status": "STARTED"}
    dump(out / "run.json", record)
    try:
        record["dimensions"] = transport(args.instance, out / "input.dat")
        if args.solver == "cpsat":
            command = [args.python, str(Path(__file__).resolve()), "cpsat", str(args.instance), str(args.limit), str(args.seed)]
        else:
            command = [args.executable, str(out / "input.dat"), str(args.limit), str(args.seed)]
            if args.solver == "highs":
                command.append(str(out / "highs.log"))
        record["command"] = command
        begin = time.monotonic()
        with (out / "raw.json").open("w") as stdout, (out / "solver.stderr.log").open("w") as stderr:
            proc = subprocess.run(command, stdout=stdout, stderr=stderr)
        record["backend_wall_seconds"] = time.monotonic() - begin
        record["solver_exit_code"] = proc.returncode
        if proc.returncode:
            raise ValueError(f"solver exit code {proc.returncode}")
        raw = json.loads((out / "raw.json").read_text())
        record["metrics"] = raw.get("metrics", {})
        record["solver_status"] = raw.get("status")
        solution, checked = normalize(args.instance, raw)
        dump(out / "solution.json", solution)
        dump(out / "exact-check.json", checked)
        record["independent_exact_feasible"] = checked["feasible"]
        record["objective"] = checked["recomputed_objective"]
        record["selected_count"] = checked["selected_count"]
        record["best_bound"] = record["metrics"].get("best_bound")
        with (out / "official-checker.log").open("w") as log:
            check = subprocess.run([args.checker_python, args.checker, "--instance_path", str(args.instance),
                                    "--solution_path", str(out / "solution.json"), "--result_path", str(out / "official-check.json")],
                                   stdout=log, stderr=subprocess.STDOUT)
        official = json.loads((out / "official-check.json").read_text())
        record["official_numpy_feasible"] = check.returncode == 0 and official.get("feasible", False)
        if not record["official_numpy_feasible"]:
            raise ValueError("official NumPy checker failed")
        record["status"] = "PASS"
    except Exception as error:
        record["status"] = "FAILED"
        record["failure"] = type(error).__name__ + ": " + str(error)
    record["worker_end_to_end_seconds"] = time.monotonic() - start
    record.update(usage())
    dump(out / "run.json", record)
    print(json.dumps(record, allow_nan=False), flush=True)
    return 0 if record["status"] == "PASS" else 2


def bounded_child():
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    resource.setrlimit(resource.RLIMIT_AS, (RAM, RAM))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))


def batch(args):
    config = json.loads(Path(args.config).read_text())
    assert config["instances"] == list(SOURCE_NAMES) and 0 < config.get("limit", 55) <= 55 and config.get("seed", 1) == 1, "authorized tiny/large2/large3 first cold run envelope"
    root = Path(config["root"])
    out = root / "baseline" / config["solver"]
    out.mkdir(parents=True, exist_ok=True)
    start, records = time.monotonic(), []
    state = {"status": "RUNNING", "solver": config["solver"], "pid": os.getpid(), "runs": records,
             "batch_cpu_budget_seconds": 3600, "batch_wall_budget_seconds": 1800,
             "instance_wall_budget_seconds": 60, "cpu_affinity": sorted(os.sched_getaffinity(0))[:2],
             "per_process_ram_bytes": RAM, "cold_reference_files_present": False}
    env = dict(os.environ, OPENBLAS_NUM_THREADS="2", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", NUMEXPR_NUM_THREADS="2", PYTHONDONTWRITEBYTECODE="1")
    for name in config["instances"]:
        if time.monotonic() - start > 1800 or resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime > 3600:
            state["status"], state["failure"] = "STOP", "batch resource budget reached"
            break
        rundir = out / name
        rundir.mkdir(parents=True, exist_ok=True)
        state["current_instance"] = name
        dump(out / "state.json", state)
        cmd = [sys.executable, str(Path(__file__).resolve()), "run", "--solver", config["solver"],
               "--instance", str(root / "source" / f"hoffman1993-{SOURCE_NAMES[name]}.json"),
               "--out", str(rundir), "--limit", str(config.get("limit", 55)), "--seed", str(config.get("seed", 1)),
               "--checker", str(root / "source" / "hoffman1993-feasibility_check.py"), "--checker-python", config.get("checker_python", sys.executable)]
        if config["solver"] == "cpsat":
            cmd += ["--python", config["python"]]
        else:
            cmd += ["--executable", config["executable"]]
        began = time.monotonic()
        timed_out = False
        with (rundir / "worker.stdout.log").open("w") as log, (rundir / "worker.stderr.log").open("w") as err:
            p = subprocess.Popen(cmd, stdout=log, stderr=err, env=env, preexec_fn=bounded_child, start_new_session=True)
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
        elapsed = time.monotonic() - began
        record = json.loads((rundir / "run.json").read_text()) if (rundir / "run.json").exists() else {}
        record.update({"instance_name": name, "external_end_to_end_seconds": elapsed, "worker_exit_code": p.returncode})
        if timed_out or elapsed > 60 or record.get("max_rss_kib", 0) > RAM // 1024 or record.get("solver_exit_code", 0) in (-9, -11, -24):
            record["status"], record["failure"] = "STOP", "instance resource gate failed"
            state["status"], state["failure"] = "STOP", record["failure"]
        records.append(record)
        dump(rundir / "run.json", record)
        with (out / "journal.jsonl").open("a") as journal:
            journal.write(json.dumps(record, allow_nan=False) + "\n")
        dump(out / "state.json", state)
        print(json.dumps({"solver": config["solver"], "instance": name, "status": record.get("status"), "objective": record.get("objective"), "bound": record.get("best_bound"), "e2e": elapsed}), flush=True)
        if state["status"] == "STOP":
            break
    if state["status"] == "RUNNING":
        state["status"] = "DONE" if len(records) == 3 and all(r.get("status") == "PASS" for r in records) else "FAILED"
    state["wall_seconds"] = time.monotonic() - start
    child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    state["cpu_seconds"] = child_usage.ru_utime + child_usage.ru_stime
    dump(out / "state.json", state)
    return 0 if state["status"] == "DONE" else 2


def install_cpsat(args):
    root = Path(args.root)
    statepath = root / "baseline" / "install-state.json"
    venv = root / "baseline" / "ortools-venv"
    tmp = root / "baseline" / "install-tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    cap = 600 * 1024 ** 2
    state = {"status": "STARTED", "package": "ortools==9.14.6206", "index": "https://pypi.org/simple",
             "isolated_venv": str(venv), "system_site_packages_enabled": True, "new_file_budget_bytes": cap,
             "wall_budget_seconds": 300, "commands": [], "pid": os.getpid()}
    dump(statepath, state)
    env = dict(os.environ, TMPDIR=str(tmp), PIP_CONFIG_FILE=os.devnull, PIP_NO_CACHE_DIR="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="2", OMP_NUM_THREADS="2",
               UV_NO_CACHE="1", UV_NO_CONFIG="1", UV_PYTHON_DOWNLOADS="never")
    env.pop("PIP_INDEX_URL", None)
    env.pop("PIP_EXTRA_INDEX_URL", None)
    def diskbytes():
        return sum(p.lstat().st_size for p in root.rglob("*") if p.is_file() or p.is_symlink())
    try:
        if venv.exists():
            raise ValueError("isolated ORTools target already exists")
        if args.uv:
            state["existing_installer"] = subprocess.check_output([args.uv, "--version"], text=True).strip()
            commands = [[args.uv, "venv", "--no-config", "--no-cache", "--python", sys.executable,
                         "--system-site-packages", str(venv)],
                        [args.uv, "pip", "install", "--python", str(venv / "bin" / "python"), "--no-config",
                         "--index-url", "https://pypi.org/simple", "--only-binary=:all:", "--no-cache-dir", "ortools==9.14.6206"]]
        else:
            commands = [[sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
                        [str(venv / "bin" / "python"), "-m", "pip", "install", "--index-url", "https://pypi.org/simple",
                         "--only-binary=:all:", "--no-cache-dir", "--no-compile", "ortools==9.14.6206"]]
        with (root / "baseline" / "install.log").open("w") as log:
            for command in commands:
                state["commands"].append(command)
                dump(statepath, state)
                p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                                     preexec_fn=bounded_child, start_new_session=True)
                while p.poll() is None:
                    size = diskbytes()
                    if size > cap or time.monotonic() - start > 300:
                        os.killpg(p.pid, signal.SIGKILL); p.wait()
                        raise ValueError("installation resource gate failed")
                    time.sleep(1)
                if p.returncode:
                    raise ValueError(f"mandatory wheel/venv installation exit code {p.returncode}")
        state["new_file_bytes"] = diskbytes()
        if state["new_file_bytes"] > cap:
            raise ValueError("installation new-file gate failed")
        code = "import json,importlib.metadata as m; from ortools.sat.python import cp_model; print(json.dumps({n:m.version(n) for n in ['ortools','absl-py','protobuf','pandas','numpy','immutabledict']}))"
        state["versions"] = json.loads(subprocess.check_output([str(venv / "bin" / "python"), "-B", "-c", code],
                                        env=env, preexec_fn=bounded_child, timeout=20, text=True))
        state["status"] = "PASS"
        state["wall_seconds"] = time.monotonic() - start
        dump(statepath, state)
        print(json.dumps(state), flush=True)
        return batch(argparse.Namespace(config=args.config))
    except Exception as error:
        state["status"] = "STOP"
        state["failure"] = type(error).__name__ + ": " + str(error)
        state["wall_seconds"] = time.monotonic() - start
        state["new_file_bytes"] = diskbytes()
        dump(statepath, state)
        print(json.dumps(state), flush=True)
        return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--source", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("normalize")
    p.add_argument("--instance", required=True); p.add_argument("--raw", required=True); p.add_argument("--solution", required=True); p.add_argument("--check", required=True)
    p = sub.add_parser("check")
    p.add_argument("--instance", required=True); p.add_argument("--solution", required=True); p.add_argument("--result", required=True)
    p = sub.add_parser("cpsat")
    p.add_argument("instance"); p.add_argument("limit", type=float); p.add_argument("seed", type=int)
    p = sub.add_parser("run")
    p.add_argument("--solver", choices=("highs", "cpsat", "native"), required=True)
    p.add_argument("--instance", required=True); p.add_argument("--out", required=True)
    p.add_argument("--executable"); p.add_argument("--python", default=sys.executable)
    p.add_argument("--limit", type=float, default=55); p.add_argument("--seed", type=int, default=1)
    p.add_argument("--checker", required=True); p.add_argument("--checker-python", default=sys.executable)
    p = sub.add_parser("batch"); p.add_argument("--config", required=True)
    p = sub.add_parser("install-cpsat"); p.add_argument("--root", required=True); p.add_argument("--config", required=True); p.add_argument("--uv")
    args = parser.parse_args()
    if args.action == "prepare":
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        summary = {}
        for name, stem in SOURCE_NAMES.items():
            summary[name] = transport(Path(args.source) / f"hoffman1993-{stem}.json", out / f"{name}.dat")
        dump(out / "manifest.json", summary); print(json.dumps(summary))
    elif args.action == "normalize":
        solution, checked = normalize(args.instance, json.loads(Path(args.raw).read_text()))
        dump(args.solution, solution); dump(args.check, checked); print(json.dumps(checked))
    elif args.action == "check":
        checked = exact(args.instance, json.loads(Path(args.solution).read_text()))
        dump(args.result, checked); print(json.dumps(checked))
    elif args.action == "cpsat":
        print(json.dumps(cpsat(args.instance, args.limit, args.seed), allow_nan=False))
    elif args.action == "run":
        return worker(args)
    elif args.action == "batch":
        return batch(args)
    elif args.action == "install-cpsat":
        return install_cpsat(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

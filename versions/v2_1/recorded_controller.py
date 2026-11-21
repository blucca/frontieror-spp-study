#!/usr/bin/env python3
"""Task-local exact Main dependency gate and serial, resource-bounded measurements."""
import argparse
import importlib.metadata
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

RAM = 4 * 1024 ** 3
NEW_FILES = 600 * 1024 ** 2
VERSIONS = {"highspy": "1.15.1", "ortools": "9.15.6755", "numpy": "2.5.3"}
NAMES = {"tiny": "tiny_instance", "large2": "large_instance_2", "large3": "large_instance_3"}


def dump(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n"); tmp.replace(path)


def bounded():
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    resource.setrlimit(resource.RLIMIT_AS, (RAM, RAM))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))


def environment(root):
    env = dict(os.environ)
    for key in ("UV_INDEX", "UV_INDEX_URL", "UV_EXTRA_INDEX_URL", "UV_DEFAULT_INDEX", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL"):
        env.pop(key, None)
    env.update(TMPDIR=str(root / "eligible-baseline" / "install-tmp"), UV_NO_CONFIG="1", UV_NO_CACHE="1",
               UV_PYTHON_DOWNLOADS="never", PIP_CONFIG_FILE=os.devnull, PYTHONDONTWRITEBYTECODE="1",
               OPENBLAS_NUM_THREADS="2", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", NUMEXPR_NUM_THREADS="2")
    return env


def bytes_used(root):
    return sum(p.lstat().st_size for p in root.rglob("*") if p.is_file() or p.is_symlink())


def install(args):
    root = Path(args.root).resolve(); work = root / "eligible-baseline"
    work.mkdir(parents=True, exist_ok=True); (work / "install-tmp").mkdir(exist_ok=True)
    venv = work / "main-env"; statefile = work / "version-gate.json"
    start = time.monotonic()
    state = {"status": "STARTED", "pid": os.getpid(), "required_versions": VERSIONS,
             "main_python_images": ["3.12", "3.14"], "actual_host_python": sys.version,
             "new_files_cap_bytes": NEW_FILES, "new_files_before": bytes_used(root), "commands": []}
    dump(statefile, state)
    try:
        if venv.exists():
            raise ValueError("fresh main-env target already exists")
        env = environment(root)
        commands = [[args.uv, "venv", "--no-cache", "--no-config", "--system-site-packages", "--python", sys.executable, str(venv)],
                    [args.uv, "pip", "install", "--no-config", "--no-cache-dir", "--only-binary=:all:",
                     "--index-url", "https://pypi.org/simple", "--python", str(venv / "bin/python"),
                     *[f"{name}=={version}" for name, version in VERSIONS.items()]]]
        assert len(commands[1][-3:]) == 3 and commands[1][-3:] == [f"{n}=={v}" for n, v in VERSIONS.items()], "only exact authorized Main package specifications"
        with (work / "install.log").open("w") as log:
            for command in commands:
                state["commands"].append(command); dump(statefile, state)
                p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, preexec_fn=bounded, start_new_session=True)
                while p.poll() is None:
                    if bytes_used(root) > NEW_FILES or time.monotonic() - start > 300:
                        os.killpg(p.pid, signal.SIGKILL); p.wait()
                        raise ValueError("dependency installation resource gate failed")
                    time.sleep(1)
                if p.returncode:
                    raise ValueError(f"exact mandatory-wheel installation failed: exit {p.returncode}")
        code = "import importlib.metadata as m,json,sys,highspy,numpy,ortools; print(json.dumps({'python':sys.version,'versions':{n:m.version(n) for n in ['highspy','ortools','numpy']},'highs_runtime':highspy.Highs().version(),'all_private_dependencies':[{'name':d.metadata['Name'],'version':d.version,'requires':d.requires} for d in m.distributions(path=[sys.prefix+'/lib/python3.13/site-packages'])]}))"
        observed = json.loads(subprocess.check_output([str(venv / "bin/python"), "-B", "-c", code], env=env, preexec_fn=bounded, timeout=20, text=True))
        state["observed"] = observed
        if observed["versions"] != VERSIONS:
            raise ValueError("exact Main dependency versions disagree")
        state["new_file_bytes"] = bytes_used(root)
        if state["new_file_bytes"] > NEW_FILES:
            raise ValueError("cumulative new-file gate failed")
        state["status"] = "PASS"
    except Exception as error:
        state["status"] = "STOP"; state["failure"] = type(error).__name__ + ": " + str(error)
        state["new_file_bytes"] = bytes_used(root)
    state["wall_seconds"] = time.monotonic() - start
    dump(statefile, state); print(json.dumps(state), flush=True)
    return 0 if state["status"] == "PASS" else 2


def run(args):
    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    record = {"status": "STARTED", "algorithm": args.algorithm, "seed": args.seed,
              "instance": args.instance, "affinity": sorted(os.sched_getaffinity(0)),
              "ram_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0], "full_process_time_limit_seconds": 60,
              "internal_budget_seconds": 55, "required_versions": VERSIONS}
    dump(out / "run.json", record)
    start = time.monotonic()
    try:
        gate = json.loads((root / "eligible-baseline/version-gate.json").read_text())
        if gate["status"] != "PASS" or gate["observed"]["versions"] != VERSIONS:
            raise ValueError("exact Main version gate is required")
        python = root / "eligible-baseline/main-env/bin/python"
        script = root / "main/solve.py" if args.algorithm == "main" else root / "eligible-baseline" / f"{args.algorithm}_baseline.py"
        if args.script:
            script = Path(args.script).resolve()
        record["script_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
        command = [str(python), "-B", str(script), "--problem", "hoffman1993", "--instance", args.instance,
                   "--output", str(out / "solution.json"), "--time-limit", "60", "--seed", str(args.seed)]
        record["command"] = command
        began = time.monotonic()
        with (out / "algorithm.stdout.log").open("w") as stdout, (out / "algorithm.stderr.log").open("w") as stderr:
            p = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=environment(root))
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
                raise ValueError("full algorithm process reached 60 seconds")
        record["algorithm_external_wall_seconds"] = time.monotonic() - began
        record["algorithm_exit_code"] = p.returncode
        ru = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(algorithm_cpu_user_seconds=ru.ru_utime, algorithm_cpu_system_seconds=ru.ru_stime,
                      algorithm_max_rss_kib=ru.ru_maxrss)
        if p.returncode:
            raise ValueError(f"algorithm exit {p.returncode}")
        for line in (out / "algorithm.stdout.log").read_text().splitlines():
            try:
                candidate = json.loads(line)
                if isinstance(candidate, dict) and "metrics" in candidate:
                    record["metrics"] = candidate["metrics"]
            except ValueError:
                pass
        spec = importlib.util.spec_from_file_location("spp_io", root / "shared/spp_io.py")
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        solution = json.loads((out / "solution.json").read_text())
        checked = helper.exact(args.instance, solution)
        dump(out / "exact-check.json", checked)
        if not checked["feasible"]:
            raise ValueError("independent whole solution check failed")
        with (out / "official-checker.log").open("w") as log:
            check = subprocess.run([str(python), "-B", str(root / "source/hoffman1993-feasibility_check.py"),
                                    "--instance_path", args.instance, "--solution_path", str(out / "solution.json"),
                                    "--result_path", str(out / "official-check.json")], stdout=log, stderr=subprocess.STDOUT,
                                   env=environment(root))
        official = json.loads((out / "official-check.json").read_text())
        if check.returncode or not official["feasible"]:
            raise ValueError("original NumPy 2.5.3 checker failed")
        record.update(status="PASS", objective=checked["recomputed_objective"], selected_count=checked["selected_count"],
                      independent_exact_feasible=True, official_numpy_feasible=True, output_bytes=(out / "solution.json").stat().st_size)
    except Exception as error:
        record["status"], record["failure"] = "FAILED", type(error).__name__ + ": " + str(error)
    record["worker_end_to_end_seconds"] = time.monotonic() - start
    own, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    record.update(total_cpu_seconds=own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime,
                  max_rss_kib=max(own.ru_maxrss, children.ru_maxrss))
    dump(out / "run.json", record)
    print(json.dumps(record), flush=True)
    return 0 if record["status"] == "PASS" else 2


def batch(args):
    root = Path(args.root).resolve(); work = root / "eligible-baseline"
    gate = json.loads((work / "version-gate.json").read_text())
    if gate["status"] != "PASS":
        raise ValueError("exact Main version gate failed")
    start, runs = time.monotonic(), []
    state = {"status": "RUNNING", "pid": os.getpid(), "algorithms": args.algorithms, "instances": args.instances,
             "runs": runs, "batch_cpu_budget_seconds": 7200, "instance_external_wall_budget_seconds": 60,
             "affinity": [0, 1], "per_process_ram_bytes": RAM}
    statefile = work / f"{args.tag}-state.json"
    for algorithm in args.algorithms:
        for name in args.instances:
            if resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime > 7200:
                state["status"], state["failure"] = "STOP", "batch CPU gate reached"; break
            out = work / algorithm / name
            out.mkdir(parents=True, exist_ok=True)
            state.update(current_algorithm=algorithm, current_instance=name); dump(statefile, state)
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "run", "--root", str(root), "--algorithm", algorithm,
                       "--instance", str(root / "source" / f"hoffman1993-{NAMES[name]}.json"), "--out", str(out)]
            began, timeout = time.monotonic(), False
            with (out / "worker.stdout.log").open("w") as log, (out / "worker.stderr.log").open("w") as stderr:
                p = subprocess.Popen(command, stdout=log, stderr=stderr, env=environment(root), preexec_fn=bounded, start_new_session=True)
                try:
                    p.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    timeout = True; os.killpg(p.pid, signal.SIGKILL); p.wait()
            wall = time.monotonic() - began
            record = json.loads((out / "run.json").read_text()) if (out / "run.json").exists() else {}
            record.update(instance_name=name, external_end_to_end_seconds=wall, worker_exit_code=p.returncode)
            if timeout or wall > 60 or record.get("max_rss_kib", 0) > RAM // 1024 or record.get("algorithm_exit_code", 0) in (-9, -11, -24):
                record["status"], record["failure"] = "STOP", "run resource gate failed"
                state["status"], state["failure"] = "STOP", record["failure"]
            elif record.get("status") != "PASS":
                state["status"], state["failure"] = "FAILED", record.get("failure", "whole entry/checker failed")
            runs.append(record); dump(out / "run.json", record)
            with (work / f"{args.tag}-journal.jsonl").open("a") as journal:
                journal.write(json.dumps(record) + "\n")
            dump(statefile, state)
            print(json.dumps({"algorithm": algorithm, "instance": name, "status": record.get("status"),
                              "objective": record.get("objective"), "algorithm_wall": record.get("algorithm_external_wall_seconds"),
                              "e2e": wall}), flush=True)
            if state["status"] != "RUNNING": break
        if state["status"] != "RUNNING": break
    if state["status"] == "RUNNING":
        state["status"] = "DONE" if all(r.get("status") == "PASS" for r in runs) else "FAILED"
    state["wall_seconds"] = time.monotonic() - start
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    state["cpu_seconds"] = ru.ru_utime + ru.ru_stime
    state["new_file_bytes"] = bytes_used(root)
    dump(statefile, state)
    return 0 if state["status"] == "DONE" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("install"); p.add_argument("--root", required=True); p.add_argument("--uv", default="/usr/local/bin/uv")
    p = sub.add_parser("run"); p.add_argument("--root", required=True); p.add_argument("--out", required=True); p.add_argument("--instance", required=True)
    p.add_argument("--algorithm", choices=("highs", "cpsat", "main"), required=True)
    p.add_argument("--script")
    p.add_argument("--seed", type=int, default=1)
    p = sub.add_parser("batch"); p.add_argument("--root", required=True)
    p.add_argument("--algorithms", choices=("highs", "cpsat", "main"), nargs="+", default=["highs", "cpsat"])
    p.add_argument("--instances", choices=tuple(NAMES), nargs="+", default=list(NAMES)); p.add_argument("--tag", default="matched-baselines")
    args = parser.parse_args()
    return install(args) if args.action == "install" else run(args) if args.action == "run" else batch(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""One requested K!=num_bases Main fallback assertion, with both full checkers."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("controller", root / "eligible-baseline/controller.py")
controller = importlib.util.module_from_spec(spec); spec.loader.exec_module(controller)
out = root / "eligible-baseline/base-contract"
out.mkdir(parents=True, exist_ok=True)
command = [sys.executable, "-B", str(root / "eligible-baseline/controller.py"), "run", "--root", str(root),
           "--algorithm", "main", "--instance", str(root / "main/base-contract-fixture.json"), "--out", str(out)]
start = time.monotonic()
with (out / "worker.stdout.log").open("w") as log, (out / "worker.stderr.log").open("w") as error:
    p = subprocess.Popen(command, stdout=log, stderr=error, preexec_fn=controller.bounded, env=controller.environment(root), start_new_session=True)
    try:
        p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL); p.wait()
record = json.loads((out / "run.json").read_text())
record["external_end_to_end_seconds"] = time.monotonic() - start
solution = json.loads((out / "solution.json").read_text())
assert p.returncode == 0 and record["status"] == "PASS" and solution["selected_rotations"] == [1] and solution["objective_value"] == 2 and record["metrics"]["highs"]["model_rows"] == 3, "K=2 second Base row forces j1 and objective2"
record.update(expected_selected=[1], expected_objective=2, base_contract_assert="PASS", num_bases=1, num_constraints=2)
controller.dump(out / "run.json", record)
controller.dump(out / "assert-check.json", {"status": "PASS", "assertion": "num_bases1/K2: select j1, objective2, 3 native model rows", "solver_runs": 1})
print(json.dumps(record), flush=True)

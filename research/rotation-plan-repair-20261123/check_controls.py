#!/usr/bin/env python3
"""One 2-row/4-column truth check, with a cost-tie variant; no installation."""
import argparse
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import controls as c


def truth(data, old, event):
    m = data["dimensions"]["num_cols"]
    answers = []
    for bits in itertools.product((0, 1), repeat=m):
        chosen = [j for j, bit in enumerate(bits) if bit]
        if c.check(data, old, event, chosen):
            answers.append((len(set(old).difference(chosen)), c.cost(data, chosen), chosen))
    return sorted(answers)


def write(path, value):
    path.write_text(json.dumps(value, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdlib-only", action="store_true")
    args = parser.parse_args()
    base = {"dimensions": {"num_rows": 2, "num_cols": 4}, "has_base_constraints": False,
            "constraint_matrix_A": {"columns": [[0], [1], [0], [0, 1]]}, "cost_vector": [7, 5, 1, 0]}
    old, event = [0, 1], {"F": [0], "P": []}
    assert truth(base, old, event) == [(1, 6, [1, 2]), (2, 0, [3])]
    assert not c.check(base, old, event, old)  # F hard zero
    assert not c.check(base, old, {"F": [0], "P": [1]}, [3])  # P hard one
    assert not c.exact_cover(base, [1, 2, 3])  # every original row exactly one
    tied = copy.deepcopy(base)
    tied["constraint_matrix_A"]["columns"][3] = [0]
    pin_event = {"F": [0], "P": [1]}
    assert truth(tied, old, pin_event) == [(1, 5, [1, 3]), (1, 6, [1, 2])]
    native = not args.stdlib_only and importlib.util.find_spec("ortools") is not None
    count = 0
    with tempfile.TemporaryDirectory(prefix="controls-check-", dir=Path(__file__).resolve().parents[1]) as directory:
        root = Path(directory)
        instance, plan, event_path = root / "instance.json", root / "old.json", root / "event.json"
        write(instance, base)
        write(plan, c.make_solution(base, old))
        write(event_path, event)
        assert c.read_plan(c.read_instance(instance), plan) == old
        assert c.read_event(base, old, event_path) == event
        fractional = copy.deepcopy(base)
        fractional["cost_vector"][2] = 0.5
        write(instance, fractional)
        try:
            c.read_instance(instance)
        except ValueError as error:
            assert "integer nonnegative" in str(error)
        else:
            raise AssertionError("fractional original cost accepted")
        if native:
            for solver in ("cpsat", "scip"):
                for data, declared in ((base, event), (tied, pin_event)):
                    write(instance, data)
                    write(event_path, declared)
                    output = root / f"{solver}.json"
                    command = [sys.executable, "-B", str(Path(c.__file__).resolve()), "--solver", solver,
                               "--instance", str(instance), "--old-plan", str(plan), "--event", str(event_path),
                               "--output", str(output), "--time-limit", "5", "--seed", "1"]
                    proc = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    assert proc.returncode == 0, (command, proc.stdout, proc.stderr)
                    result = c.load(output)
                    d, money, chosen = truth(data, old, declared)[0]
                    assert result["primary"]["status"] == result["secondary"]["status"] == "OPTIMAL", result
                    assert result["primary"]["objective"] == result["primary"]["best_bound"] == d
                    assert result["secondary"]["objective"] == result["secondary"]["best_bound"] == money
                    assert result["removed_old_count"] == d and result["actual_cost"] == money
                    assert result["lexicographic_complete"] and result["verified"]
                    assert result["solution"] == c.make_solution(data, chosen)
                    assert result["declared_event"] == declared
                    assert result["primary"]["hint_source"] == "legal_old_partial"
                    assert result["primary"]["hint_count"] == len(old)
                    assert result["secondary"]["hint_source"] == "own_primary_optimal_full"
                    assert result["secondary"]["hint_count"] == 4
                    count += 1
    print(json.dumps({"stdlib_truth": "PASS", "fractional_cost_reject": "PASS",
                      "native": "PASS" if native else "SKIPPED_existing_ortools_absent_or_stdlib_only",
                      "native_processes": count}), flush=True)


if __name__ == "__main__":
    main()

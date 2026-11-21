#!/usr/bin/env python3
"""Recompute archived complete witnesses; execute no solver or original checker."""
import hashlib
import json
from pathlib import Path

from shared.spp_io import exact

ROOT = Path(__file__).resolve().parent
NAMES = {"tiny": "tiny_instance", "large2": "large_instance_2", "large3": "large_instance_3"}


def check(directory, instance, script):
    record = json.loads((directory / "run.json").read_text())
    assert record["external_end_to_end_seconds"] <= 60, str(directory)
    assert record["max_rss_kib"] <= 4 * 1024 ** 2, str(directory)
    assert record["affinity"] == [0, 1] and record["ram_limit_bytes"] == 4 * 1024 ** 3
    if record["script_sha256"] != hashlib.sha256(script.read_bytes()).hexdigest():
        assert script == ROOT / "main/solve.py"
        script = ROOT / "versions/v1/main/solve.py"
    assert record["script_sha256"] == hashlib.sha256(script.read_bytes()).hexdigest()
    assert record["required_versions"] == {"highspy": "1.15.1", "ortools": "9.15.6755", "numpy": "2.5.3"}
    if record["status"] == "FAILED":
        assert record["algorithm_exit_code"] == record["worker_exit_code"] == 2
        assert record["failure_class"] == "no feasible solution within the fixed cold budget"
        assert record.get("objective") is None and record["whole_native_executed"]
        stderr = (directory / "algorithm.stderr.log").read_text()
        assert stderr == record["algorithm_failure_stderr"]
        assert "has no whole feasible solution" in json.loads(stderr)["failure"]
        assert not (directory / "solution.json").exists()
        assert not (directory / "official-check.json").exists()
        return {"directory": str(directory.relative_to(ROOT)), "outcome": "FAILED_NO_WITNESS",
                "objective": None, "failure_receipt_verified": "PASS",
                "recorded_resource_contract": "PASS", "witness": False}
    assert record["status"] == "PASS" and record["algorithm_exit_code"] == 0, str(directory)
    solution = json.loads((directory / "solution.json").read_text())
    official = json.loads((directory / "official-check.json").read_text())
    archived_exact = json.loads((directory / "exact-check.json").read_text())
    recomputed = exact(instance, solution)
    assert official["feasible"] and archived_exact["feasible"], str(directory)
    assert recomputed["feasible"], recomputed["violations"]
    assert recomputed["recomputed_objective"] == record["objective"]
    high = record.get("metrics", {}).get("highs", {})
    if record.get("metrics", {}).get("force_exit"):
        assert high["run_status"] == "MAIN_DEADLINE_FALLBACK"
        assert high["native_result_available"] is False
        assert "model_status" not in high and "best_bound" not in high and "mip_gap" not in high
    return {"directory": str(directory.relative_to(ROOT)), "objective": record["objective"],
            "variables": recomputed["variable_count"], "independent_exact_recomputed": "PASS",
            "original_numpy_checker_recorded": "PASS", "recorded_resource_contract": "PASS", "witness": True,
            "source": str(script.relative_to(ROOT)),
            "native_outcome": "pending; prior exact incumbent" if record.get("metrics", {}).get("force_exit") else "returned"}


def main():
    checked = []
    evidence = ROOT / "results/2026-11-21"
    for algorithm in ("main", "highs", "cpsat"):
        script = ROOT / "main/solve.py" if algorithm == "main" else ROOT / "eligible-baseline" / f"{algorithm}_baseline.py"
        for case, name in NAMES.items():
            checked.append(check(evidence / algorithm / case, ROOT / "source" / f"hoffman1993-{name}.json", script))
    checked.append(check(evidence / "base-contract", ROOT / "main/base-contract-fixture.json", ROOT / "main/solve.py"))
    base = json.loads((evidence / "base-contract/solution.json").read_text())
    assert base["selected_rotations"] == [1] and base["objective_value"] == 2
    paired = json.loads((evidence / "paired-seeds/state.json").read_text())
    assert paired["status"] == "DONE" and len(paired["runs"]) == 6
    for record in paired["runs"]:
        algorithm, seed, case = record["algorithm"], record["seed"], record["instance_name"]
        source = ROOT / "experiments/paired-seeds"
        script = source / "main/solve.py" if algorithm == "main" else source / "eligible-baseline/highs_baseline.py"
        checked.append(check(evidence / "paired-seeds" / f"seed{seed}" / algorithm / case,
                             ROOT / "source" / f"hoffman1993-{NAMES[case]}.json", script))
    holdouts = json.loads((evidence / "holdouts/state.json").read_text())
    assert holdouts["status"] == "DONE_WITH_NEGATIVE_RESULTS" and len(holdouts["runs"]) == 9
    for record in holdouts["runs"]:
        algorithm, case = record["algorithm"], record["instance_name"]
        script = ROOT / "main/solve.py" if algorithm == "main" else ROOT / "eligible-baseline" / f"{algorithm}_baseline.py"
        checked.append(check(evidence / "holdouts" / case / algorithm,
                             ROOT / "source" / f"hoffman1993-large_instance_{case[5:]}.json", script))
    current = json.loads((evidence / "v3/state.json").read_text())
    assert current["status"] == "DONE" and len(current["runs"]) == 9
    for record in current["runs"]:
        case, seed = record["instance_name"], record["seed"]
        instance = ROOT / "main/base-contract-fixture.json" if case == "base-k2" else ROOT / "source" / f"hoffman1993-{'tiny_instance' if case == 'tiny' else 'large_instance_' + case[5:]}.json"
        checked.append(check(evidence / "v3" / f"seed{seed}" / case, instance, ROOT / "main/solve.py"))
    ls_only = ROOT / "results/2026-11-22/feasibility-jump"
    ls_only_runs = []
    if ls_only.exists():
        gate = json.loads((ls_only / "state.json").read_text())
        assert gate["status"] in ("DONE", "DONE_WITH_NEGATIVE_RESULTS") and len(gate["runs"]) == 9
        assert [(r["instance_name"], r["seed"]) for r in gate["runs"]] == [
            ("tiny", 1), ("large2", 1), ("base-k2", 1), ("large1", 1), ("large3", 1),
            ("large4", 1), ("large5", 1), ("large3", 2), ("large3", 3)]
        for record in gate["runs"]:
            case, seed = record["instance_name"], record["seed"]
            instance = ROOT / "main/base-contract-fixture.json" if case == "base-k2" else ROOT / "source" / f"hoffman1993-{'tiny_instance' if case == 'tiny' else 'large_instance_' + case[5:]}.json"
            ls_only_runs.append(check(ls_only / f"seed{seed}" / case, instance,
                                      ROOT / "eligible-baseline/cpsat_fj_control.py"))
        checked.extend(ls_only_runs)
    rejected = []
    for version in ("v2", "v2_1"):
        gate = json.loads((evidence / version / "state.json").read_text())
        assert gate["status"] == "STOP" and len(gate["runs"]) == 6
        expected = hashlib.sha256((ROOT / "versions" / version / "main/solve.py").read_bytes()).hexdigest()
        assert all(r["status"] == "PASS" and r["script_sha256"] == expected for r in gate["runs"][:-1])
        last = gate["runs"][-1]
        assert last["instance_name"] == "large4" and last["worker_exit_code"] == -9
        assert last["status"] == "STARTED" and last["external_end_to_end_seconds"] >= 60
        assert not (evidence / version / "seed1/large4/solution.json").exists()
        rejected.append({"version": version, "release_gate": "STOP", "failure": "large4 external60s timeout", "receipt_verified": "PASS"})
    print(json.dumps({"status": "PASS", "archived_records": len(checked),
                      "archived_witnesses": sum(c["witness"] for c in checked),
                      "verified_no_witness_failures": sum(not c["witness"] for c in checked), "solver_executions": 0,
                      "original_checker_executions": 0, "current_v3_acceptance_runs": 9,
                      "current_ls_only_control_runs": len(ls_only_runs),
                      "current_ls_only_witnesses": sum(c["witness"] for c in ls_only_runs),
                      "current_ls_only_no_witness_failures": sum(not c["witness"] for c in ls_only_runs),
                      "rejected_release_gates": rejected, "checks": checked}, indent=2))


if __name__ == "__main__":
    main()

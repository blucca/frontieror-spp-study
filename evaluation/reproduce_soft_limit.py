#!/usr/bin/env python3
"""Evaluation-only synchronous soft-limit repro using an observed v1 incumbent."""
import importlib.util
import json
from pathlib import Path
import time
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spp", ROOT / "main/solve.py")
spp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spp)
data = spp.read_instance(ROOT / "source/hoffman1993-large_instance_4.json")
prior = json.loads((ROOT / "results/2026-11-21/holdouts/large4/main/solution.json").read_text())
chosen = prior["selected_rotations"]
assert spp.exact_cover(data, chosen) and spp.cost(data, chosen) == 331
print(json.dumps({"requested_seconds": 4, "helper_bounded": False}), flush=True)
start = time.monotonic()
result, metrics = spp.highs_solve(data, start + 4, incumbent=chosen)
print(json.dumps({"requested_seconds": 4, "actual_seconds": time.monotonic()-start,
                  "native_status": metrics["model_status"], "whole_cover_returned": result is not None}), flush=True)

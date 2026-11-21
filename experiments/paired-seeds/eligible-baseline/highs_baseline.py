#!/usr/bin/env python3
import time
START = time.monotonic()
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("main_spp", Path(__file__).resolve().parents[1] / "main/solve.py")
spp = importlib.util.module_from_spec(spec); spec.loader.exec_module(spp)


def main():
    args = spp.cli_args()
    data = spp.read_instance(args.instance)
    deadline = START + max(0.01, min(55, args.time_limit - 5))
    chosen, metrics = spp.highs_solve(data, deadline, seed=args.seed)
    if chosen is None:
        raise ValueError("cold highspy has no whole feasible solution")
    solution = spp.write_solution(data, chosen, args.output)
    metrics.update(method="stock full sparse highspy cold", objective=solution["objective_value"],
                   internal_seconds=time.monotonic() - START, initial_hints=0)
    print(json.dumps({"metrics": metrics}, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({"failure": type(error).__name__ + ": " + str(error)}), file=sys.stderr)
        sys.exit(2)

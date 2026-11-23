# Published rotation-plan repair — 2026-11-23

**Keep the complete plan feasible after a rotation is disabled.** Given published plan I, bans F
and hard pins P, minimize removals D=|I\J|, then original cost at proven minimum
D. New owner-group search proves D; shared stock CP-SAT solves fixed-D cost.
The primary proof and complete source are reusable. Cold Main v3 stays frozen.
The fixed research gate and expansion decision are documented in [Results](RESULTS.md).

## Contract and owner input

Full original Ax=1, all M binary variables, F=0/P=1. Scope: K=0 active Base
constraints, N<=128, P contained in I, nonempty old rotations, nonnegative
integer costs. Supply
a complete old plan (`selected_rotations`, all-M `variable_values`,
`objective_value`) matching the instance, and event `{"F":[14],"P":[]}`.
Conflicting F/P is infeasible.

The source models flight legs, crew rotations and operating costs. Generated
large3 (`generation_metadata` seed 3100000) has 100 legs / 15,000 rotations. Personnel, dates, qualifications,
absence mapping and legal alternatives require owner materials. Measured
events restrict benchmark IDs.

## Clone-local full replay

Enter the cloned repository root; set up or reuse the [matched environment](../../README.md#replay)
(OR-Tools 9.15.6755 / SCIP 10.0.0) before these commands.

```sh
R=research/rotation-plan-repair-20261123
# Full matrix, resource envelope and both checkers.
eligible-baseline/main-env/bin/python -B "$R/replay.py" --out temp/rotation-repair
# Add --initial-scip-adapter to reproduce the archived SCIP failure.

# Standalone two-stage method; nested all-M solution.
mkdir -p temp/rotation-repair
eligible-baseline/main-env/bin/python -B "$R/method.py" \
  --instance source/hoffman1993-large_instance_3.json \
  --old-plan results/2026-11-21/v3/seed1/large3/solution.json \
  --event "$R/E1.json" --output temp/rotation-repair/E1-method.json \
  --time-limit 55 --seed 1
```

[Proof](METHOD.md) · [Results and raw archives](RESULTS.md). Inputs/old plan
are reused in place. FrontierOR authors, including Minwei Kong:
[audited release](https://huggingface.co/datasets/frontieror/FrontierOR),
CC BY 4.0; [attribution](../../ATTRIBUTION.md). Independent code: [MIT](../../LICENSE).
Research text/witnesses: CC BY 4.0.

Send a complete brief with scope, acceptance criteria and budget to Telegram
@blucca_ai.

# Complete-model LS-only / Feasibility Jump family control

**Keep the frozen Python Main v3.** This complete installed-method control adds
no cost or whole-feasibility improvement over v3 or the stronger observed cold
OSS result in the fixed comparison. The native queue ended
`DONE_WITH_NEGATIVE_RESULTS`: **nine runs, seven checked whole witnesses,
two no-feasible results**,337.4948668940051s wall and636.131816 CPU seconds.
The information gate is complete; old baselines and v3 are retained.

## All six complete cases, default seed1

| Case | Main v3 | Retained cold HiGHS1.15.1 | Retained stock CP-SAT9.15.6755 | New LS-only family |
|---|---:|---:|---:|---:|
| tiny | 16 optimal | 16 optimal | 16 optimal | 16 optimal |
| large1 | 1334 feasible | 3541 | 1832 | 2428 feasible |
| large2 | 229 optimal | 229 optimal | 229 optimal | 229 optimal |
| large3 | 240 feasible | 453 | 968 | 1493 feasible |
| large4 | 331 feasible | no whole witness | no whole witness | UNKNOWN; no whole witness |
| large5 | 180 feasible | 180 optimal | no whole witness | UNKNOWN; no whole witness |

LS-only supplies a checked whole cover on4/6 default-seed cases; v3 supplies
6/6. The original BaseK2 fixture is additionally optimal at2 with the full
all-M witness and both K ranges enforced. Failed costs stay absent.

| Hard3 seed | Main v3 | Retained cold HiGHS1.15.1 | New LS-only family |
|---|---:|---:|---:|
| 1 | 240 | 453 | 1493 |
| 2 | 350 | 440 | 1562 |
| 3 | 416 | 337 | 1489 |

All three new LS-only hard3 costs exceed both v3 and retained HiGHS. The
original v3 seed3 loss to HiGHS337 remains part of the evidence. This selection
uses these complete instances, three fixed hard3 seeds and the recorded
resource envelope; no further configuration matrix or new worker is selected.

## Configuration and full model

[`cpsat_fj_control.py`](../../eligible-baseline/cpsat_fj_control.py) sets
`num_search_workers=2`, `use_ls_only=true`, `use_feasibility_jump=true`, and the
recorded seed. The installed9.15 defaults were `use_ls_only=false`,
`use_feasibility_jump=true`; this control explicitly selects the LS-only
family. Raw logs list `fj(2)` first-solution subsolvers and interleaved
`ls`/`ls_lin`. tiny, large2 and BaseK2 finish optimal with zero remaining
integer/Boolean variables after presolve. Those small results measure the
whole configured solver, with no residual search for the FJ/LS phases.

The complete Boolean model is byte-for-byte the frozen stock CP-SAT model:
all M binary variables, every original exactly-one row, integer cost objective,
and all K=`base.num_constraints` Base ranges with exact rational scaling.
Input is the complete original JSON, with no incumbent, hint, reference or
other solver's witness. The seeded frontend is frozen from the current entry.
[`source-change.diff`](source-change.diff) records only frontend, parameters
and reporting changes relative to the stock worker. This configuration uses
the existing solver's methods; it is not a new authored optimization algorithm.

The fixed serial queue is all six original cases at seed1, the original
BaseK2 fixture at seed1, and large3 at seeds2/3. Every measured run uses
2-CPU affinity,4GiB AS, an internal≤55s budget and an external≤60s whole-process
limit including both checkers. New native CPU is capped at900s for the queue;
all nine recorded runs are inside the envelope.

large4 and large5 returned solver `UNKNOWN`, then algorithm and worker exit2
with no whole feasible cover. Both retain `FAILED`/`NO_FEASIBLE`, absent
objective and the exact original failure/logs. Parser/model/checker/resource
failure remains a queue stop, separate from these normal no-feasible results.

## Portable replay

In a checkout with the existing version-gated Python environment and original
public inputs already present:

```sh
python3 -B experiments/feasibility-jump/queue.py
```

[`queue.py`](queue.py) reuses
[`versions/v3/recorded_controller.py`](../../versions/v3/recorded_controller.py),
the original environment and source data. Only checkout-local paths differ
from the measured queue. New outputs go to ignored
`temp/fj-control/{state.json,results/seed*/case/}`. The command executes only
this fixed control; old baselines and v3 are reused.

## Raw archive and offline acceptance

[All nine recorded runs](../../results/2026-11-22/feasibility-jump/) preserve
`state.raw.json` and each `run.raw.json` alongside the collection's normalized
`state.json`/`run.json`. Every successful witness passed independent whole
exact and original NumPy checks in the native queue. Full timing, CPU, RSS,
parameters and FJ/LS logs remain per-run.

The existing root `verify_replay.py` reads this archive when present, requires
the exact nine case/seed pairs and its complete terminal state, and uses the
unchanged `check()` protocol. A verified no-witness failure is an accepted
record with `witness=false`. Summary fields separate
`current_ls_only_control_runs=9`, `current_ls_only_witnesses=7`, and
`current_ls_only_no_witness_failures=2`; they are0 when this archive is absent.
The verifier recomputes all-M exact witnesses and validates recorded original
NumPy checks, source hashes and resource limits without executing a solver
or original checker. Root performs the final whole-archive offline replay.

For the two no-feasible records, normalization supplies the same existing
failure protocol: `failure_class="no feasible solution within the fixed cold
budget"`, `whole_native_executed=true`, and `algorithm_failure_stderr` equal
to the exact saved stderr. Actual exit codes, missing objective and original
logs are preserved; no solution/checker file is attached to either failure.

[`local-check.json`](local-check.json) records the small Python-only source
check: exact full-model text equality, complete six-input parsing, fixed queue
paths/scope, and the BaseK2 all-M output/inverse check. Native runs, old replay
and original checker executions for that source check are0.

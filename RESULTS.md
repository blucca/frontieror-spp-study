# Complete Main v3 results — 2026-11-21

Recorded queue **DONE,9/9 PASS**: all exit0, original NumPy2.5.3 checker,
independent exact/full-M schema and external resource gates pass. Six default
seed cases, one K2 fixture and hard3 seeds2/3; no baselines were rerun.

| Case | Seed | Cost | Bound | Algorithm wall s | Whole + checkers s | CPU s | RSS MiB | Native outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| tiny | 1 | 16 | 16 | 0.217999 | 0.467156 | 0.590667 | 41.746 | Optimal |
| large2 | 1 | 229 | 229 | 0.417634 | 0.667564 | 0.875652 | 53.352 | Optimal |
| base-k2 | 1 | 2 | 2 | 0.217126 | 0.466805 | 0.616815 | 41.910 | Optimal |
| large1 | 1 | 1334 | 16 | 54.985205 | 55.348109 | 57.257099 | 555.129 | TimeLimit |
| large3 | 1 | 240 | 56 | 54.936619 | 55.249792 | 56.514192 | 389.148 | TimeLimit |
| large4 | 1 | 331 | — | 55.098064 | 55.455027 | 97.723530 | 440.000 | MAIN_DEADLINE_FALLBACK; native pending |
| large5 | 1 | 180 | — | 54.953254 | 55.395325 | 93.374085 | 911.262 | TimeLimit |
| large3 | 2 | 350 | 56 | 54.952694 | 55.258020 | 56.349423 | 794.438 | TimeLimit |
| large3 | 3 | 416 | 56 | 54.955500 | 55.276658 | 56.197017 | 784.383 | TimeLimit |

Queue wall333.597378s /CPU419.604271s. Complete
original state, stdout/stderr, all-M witnesses and checker outputs:
[`results/2026-11-21/v3/`](results/2026-11-21/v3/).

**large4:** Main writes its prior verified331 while the native task remains
pending; metadata explicitly has MAIN_DEADLINE_FALLBACK,
native_result_available=false,force_exit=true. Its native status, bound and
gap are absent. The successful whole Main process and both checkers are the
measured acceptance result. **large5:** Main180 is feasible with a returned
TimeLimit status and no finite bound; it is not labeled optimal. The old cold
HiGHS180 remains an independent optimal reference under the same envelope.

## Reused matched-version cold baselines

| Case | Main v3 | Cold HiGHS1.15.1 | Cold CP-SAT9.15.6755 |
|---|---:|---:|---:|
| tiny | 16 optimal | 16 optimal | 16 optimal |
| large1 | 1334 feasible | 3541 | 1832 |
| large2 | 229 optimal | 229 optimal | 229 optimal |
| large3 | 240 feasible | 453 | 968 |
| large4 | 331 feasible | no feasible witness | no feasible witness |
| large5 | 180 feasible | 180 optimal | no feasible witness |

Baselines: highspy1.15.1, OR-Tools9.15.6755, NumPy2.5.3, same measured host,
2 allowed CPUs,4GiB AS,55s internal/60s external including both checkers.
Baseline search is synchronous, cold, zero hints; original run records remain
under `results/2026-11-21/{highs,cpsat,holdouts}/`. The source/helper snapshot
is archived under versions/v1 and the original public commit45a576cf.
Three cold entries (large4 HiGHS/CP-SAT, large5 CP-SAT) actually exit2 with no
whole feasible witness; resource gates pass, costs/checker verdicts are absent.
The complete original baseline/old-Main record is retained in
[`versions/v1/RESULTS.md`](versions/v1/RESULTS.md).

## Paired hard3 seeds and historical v1

| Hard3 seed | Main v3 | Retained Main v1 | Cold HiGHS1.15.1 |
|---|---:|---:|---:|
| 1 | 240 | 240 | 453 |
| 2 | 350 | 411 | 440 |
| 3 | 416 | 510 | 337 |

v3 wins2/3 against cold HiGHS, losing seed3. This is one case/three fixed
seeds; v1's original observations remain explicit. large1 v1's2833 lost to
CP-SAT1832; v3's1334 is lower than both cold baselines. Small-hole LNS gave
zero gain, while the subsequent input-only global/large holes supplied the
observed1334. Those first-stage probe records are separate from full runs.

## Rejected release candidates and deadline defect

v2 and presolve-off v2.1 each pass tiny/easy/K2/large1/hard3seed1, then their
large4 native process fails to return before the external60s gate and is killed.
Queue status isSTOP; last persisted run status isSTARTED, worker_exit_code=-9,
whole60.005864s/60.007880s respectively. Neither completes its9-run release
gate. Both frozen sources and complete partial queues are retained under
`versions/{v2,v2_1}/` and `results/2026-11-21/{v2,v2_1}/`.

The existing upstream [#3314](https://github.com/ERGO-Code/HiGHS/issues/3314)
and [#3606](https://github.com/ERGO-Code/HiGHS/issues/3606) were open when
checked2026-11-21; they cover native soft-time-limit overruns, including1.15.1.
The short presolve-off diagnostic returned, but its subsequent full release
gate still failed. v3 removes that option override and reuses the existing
daemon API with the application deadline. Original triage/diagnostic files:
[`experiments/native-time-limit/`](experiments/native-time-limit/).
No upstream fix, new issue or new core PR is claimed or created.

## Data, environment and reference boundaries

All six complete official public JSONs, schemas and original checker are
unchanged; source URLs/retrieval/pinned revisions/byte hashes are in
[`source/manifest.json`](source/manifest.json), with CC BY4.0 attribution.
large1/4/5 use pinned ef42a2eac13595453f986d9df0b62e86e75ab596 and no new
reference downloads. All six cases have N30/100,M25/15000,K0; the K2 fixture
is separate from case scores.

Measured Python3.13.5/Linux6.18.54/glibc2.41; advertised Main images use
Python3.12/3.14. Core solver/NumPy versions match; ancillary differences include
pandas3.1.1/3.0.6,absl-py2.5.1/2.5.0,python-dateutil4.0.0/2.9.0.post0.
Full initial package/source environment is in `results/2026-11-21/runtime/`.
CPU model/cache topology was not captured. OS rusage gives summed CPU and
maximum individual-process RSS, not summed concurrent process memory.

Author Gurobi references remain evaluation-only: large2 optimal229,
runtime_seconds0.033720/runtime0.26; large3 feasible207,bound76,
runtime_seconds3600.005044/runtime3600.83. Their original hardware is outside
the downloaded fields; hard reference uses about1h, versus this55s internal
budget. Current hard3seed1 cost240 is15.942% above207. Baseline witnesses,
reference JSONs and cover-exchange analyses never become cold algorithm inputs.
Historical C++294/HiGHS1.16.0/oldCP-SAT9.14.6206 remain independent controls.

Probe-only dynamic-scarcity and restricted-pool OSS negatives remain under
`experiments/`, separately scored. Formal registration/submission actions and
spending are0; the artifact is a public research replay.


## 2026-11-22 — explicit LS-only / Feasibility Jump family

The original stock baselines and v3 are retained without rerunning. The new
control sets `use_ls_only=true`, `use_feasibility_jump=true`, two workers and
the declared seed; it preserves the complete Boolean exactly-one objective
and all K side rows. The actual search roster contains `fj(2)` first-solution
workers plus interleaved `ls` and `ls_lin`. tiny/large2/BaseK2 finish in presolve.

| Case | Seed | LS-only | v3 | Original stronger stock observation |
|---|---:|---:|---:|---:|
| tiny | 1 | 16 optimal | 16 | 16 optimal |
| large2 | 1 | 229 optimal | 229 | 229 optimal |
| BaseK2 | 1 | 2 optimal | 2 | fixture2 |
| large1 | 1 | 2428 feasible | 1334 | CP-SAT1832 |
| large3 | 1 | 1493 feasible | 240 | HiGHS453 |
| large4 | 1 | UNKNOWN, no witness | 331 | neither stock has a whole witness |
| large5 | 1 | UNKNOWN, no witness | 180 feasible | HiGHS180 optimal |
| large3 | 2 | 1562 feasible | 350 | HiGHS440 |
| large3 | 3 | 1489 feasible | 416 | HiGHS337 |

All nine complete measurements meet2-CPU affinity /4GiB /60s end-to-end.
Total whole wall337.494867s, CPU636.131816s, largest RSS627276KiB;
slowest complete run55.491763s. Seven witnesses pass all-M independent exact
and original NumPy checks; two normal UNKNOWN failures retain exit2, exact
stderr and absence of solution/checker files. Raw records are preserved next
to the normalized failure metadata. No references or other solver hints are read.

The frozen v3 has lower hard-case costs and provides whole witnesses on
large4/5; the new LS-only configuration holds the small-case optima. This
complete comparison retains v3 and closes the proposed mature-primal-search
configuration exploration for this study. New professional inputs receive
model-specific evaluation. No formal submission is recorded by this replay.

[Control, scope and replay](experiments/feasibility-jump/README.md) ·
[All nine raw runs](results/2026-11-22/feasibility-jump/).

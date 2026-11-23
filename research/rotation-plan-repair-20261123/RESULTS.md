# Results — three fixed events

## Design

Complete generated large3; same v3 seed1 old plan (27 selections / cost 240):

| Event | F: banned IDs | P: hard pins |
|---|---|---|
| E1 | 14 | none |
| E2 | 14, 289 | none |
| E3 | 14 | 14803 |

Continue after lower D than both strong controls without other regression,
or >=2 events at equal proven primary/cost quality with whole time <=50% of
the stronger complete control. Events/seed/threshold stay fixed. Serial order:
E1/E2/E3, each CP-SAT, SCIP, method.

**All twelve witnesses pass both full checkers and resource limits.** The
original nine and three fresh SCIP controls are retained. Linux x86_64 / Python 3.13.5; OR-Tools 9.15.6755 / SCIP 10.0.0.
Worker/checker limits: two CPUs ([0,1]), 4 GiB address space. Internal 55 s
includes import/input/preparation/both builds/searches; whole <=60 s also
includes output, exit and independent/original checkers.

## Complete CP-SAT and method pairs

All six runs: both stages OPTIMAL, bounds equal D and recomputed cost.

| Event | Solver | D | Cost | Primary s | Secondary s | Whole s |
|---|---|---:|---:|---:|---:|---:|
| E1 | CP-SAT | 2 | 557 | 2.042681 | 0.729191 | 4.185618 |
| E1 | Method | 2 | 557 | 0.029679 | 0.745954 | 2.022120 |
| E2 | CP-SAT | 4 | 545 | 1.184639 | 1.252506 | 3.785602 |
| E2 | Method | 4 | 545 | 0.047688 | 1.308540 | 2.771646 |
| E3 | CP-SAT | 2 | 557 | 1.092364 | 0.562702 | 2.977527 |
| E3 | Method | 2 | 557 | 0.029976 | 0.582092 | 1.869636 |

Method/CP-SAT whole ratios: **48.31% / 73.22% / 62.79%**. Only E1 meets 50%;
D improvement is zero. Both continuation routes fail: **STOP method expansion**.
CP-SAT is the strongest complete control at matching quality on all three.
Primary proof: about 0.030 / 0.048 / 0.030 s here. Performance scope: one run
per fixed event on one generated instance.

## Archived SCIP transition failure

The first adapter reused SCIP after its concurrent primary solve. Logs show
primary completion followed by immediately interrupted cost presolve.
All primary statuses: OPTIMAL; all secondary statuses: FEASIBLE, bound -1e20.
Full checked witnesses survive as failed stage-transition diagnostics.

| Event | D | Retained cost | Secondary s | Whole s |
|---|---:|---:|---:|---:|
| E1 | 2 | 832 | 0.041455 | 4.133630 |
| E2 | 4 | 1051 | 0.044162 | 15.728847 |
| E3 | 2 | 557 | 0.034022 | 2.525248 |

`controls.py` releases primary SCIP and rebuilds fixed-D cost in fresh SCIP;
this workaround counts toward whole time. Method/CP-SAT stay frozen.
`executed-controls-initial.py` preserves the first adapter.

## Fresh-instance SCIP controls

| Event | D | Primary status/bound | Cost | Secondary status/bound | Whole s | Full/resource |
|---|---:|---|---:|---|---:|---|
| E1 | 2 | OPTIMAL / ~2 | 557 | OPTIMAL / 557 | 4.833175 | PASS / PASS |
| E2 | 4 | OPTIMAL / 4 | 1051 | FEASIBLE / -1e20 | 55.136855 | PASS / PASS |
| E3 | 2 | OPTIMAL / 2 | 557 | OPTIMAL / 557 | 3.128910 | PASS / PASS |

Fresh models complete E1/E3 cost proofs. E2 searches cost for 39.380199 s
until its remaining time limit: cost 1051, FEASIBLE, bound -1e20.

[Initial nine](results/initial/) and
[fresh SCIP three](results/scip-fresh/) retain solutions, logs, both checks,
unrounded stage status/bounds, whole/resource records and source versions.
`replay.py` runs the corrected matrix; `--initial-scip-adapter` selects the
archived failure.

## Public source first run

[Commit-pinned public first run](results/public-first-run.json): all eleven
required public files returned HTTP 200; the complete E1 task returned
D=2/cost557, both proofs OPTIMAL, all 15,000 variables and both checkers PASS
in 2.047636 s. This is delivery QA, separate from external owner adoption.

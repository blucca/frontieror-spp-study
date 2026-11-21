# Measured results — all six cases and paired seeds, 2026-11-21

Minimize cost. Original seed-1 batch: nine serial complete runs.
The paired-seed extension adds six serial runs, detailed below.
`main` is Python Main v1; `highs` is cold full sparse HiGHS 1.15.1;
`cpsat` is cold full Boolean CP-SAT 9.15.6755. Both baselines start with zero hints.
All original seed1 runs below: **exit 0, complete all-M schema, independent exact PASS,
original NumPy 2.5.3 PASS, external resource PASS**.

| Method | Case | Cost | Bound | Algorithm wall s | Whole + checkers s | CPU s | RSS MiB | Solver status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| main | tiny | 16 | 16 | 0.167641 | 0.365805 | 0.543126 | 41.289 | Optimal |
| main | large2 | 229 | 229 | 0.366396 | 0.616579 | 0.799591 | 50.992 | Optimal |
| main | large3 | 240 | 56 | 54.954974 | 55.225060 | 56.352242 | 355.359 | TimeLimit |
| highs | tiny | 16 | 16 | 0.215640 | 0.416706 | 0.560556 | 40.355 | Optimal |
| highs | large2 | 229 | 229 | 0.368268 | 0.617526 | 0.783628 | 50.340 | Optimal |
| highs | large3 | 453 | 56 | 54.942631 | 55.224484 | 55.920506 | 575.965 | TimeLimit |
| cpsat | tiny | 16 | 16 | 0.968695 | 1.169159 | 1.271880 | 111.293 | OPTIMAL |
| cpsat | large2 | 229 | 229 | 1.069195 | 1.318375 | 1.482579 | 119.816 | OPTIMAL |
| cpsat | large3 | 968 | -13243 | 55.021688 | 55.280589 | 107.462051 | 429.020 | FEASIBLE |

`TimeLimit`/`FEASIBLE` on hard3 report incumbents at the deadline; tiny/easy
are optimal. CP-SAT's reported hard lower bound is -13243; positive costs
supply a separate valid bound of 0. Main's hard HiGHS gap is 76.6667%.
Seed-1 Main 240 versus matched HiGHS 453 is -47.0199%; versus CP-SAT 968
is -75.2066%. The subsequent paired seeds show materially smaller aggregate
advantage and a loss on seed3. Tiny/easy have no cost gain.

## Paired hard seeds — include the losing seed

| Hard3 seed | Python v1 family cost | Cold HiGHS1.15.1 cost | Paired cost difference |
|---|---:|---:|---:|
| 1, retained original | 240 | 453 | -213 |
| 2 | 411 | 440 | -29 |
| 3 | 510 | 337 | +173 |

Python v1 wins 2/3 pairs, with costs ranging 240–510; cold HiGHS ranges
337–453. Mean costs: 387 versus 410; medians: 411 versus 440. These are three
fixed-seed outcomes on one hard instance, with substantial variability.
Seed1 is the original run, retained without rerunning. Seeds2/3 use the same
mechanism with CLI seed exposure only: cold DFS seed=seed, pool DFS seed=
104729*seed, and HiGHS random_seed=seed, also paired in the cold baseline.
CP-SAT remains a seed1 comparator; no extra CP-SAT seeds were executed.

The six extension runs (including Main seed2 tiny/easy scope checks) all passed
the original NumPy2.5.3 checker, independent exact/schema and resource gates:

| Algorithm | Seed | Case | Cost | Bound | Algorithm wall s | Whole + checkers s | CPU s | RSS MiB |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| main | 2 | tiny | 16 | 16 | 0.217826 | 0.468037 | 0.598384 | 41.301 |
| main | 2 | large2 | 229 | 229 | 0.417656 | 0.718850 | 0.856303 | 51.258 |
| main | 2 | large3 | 411 | 56 | 54.936359 | 55.228884 | 56.020568 | 486.242 |
| highs | 2 | large3 | 440 | 56 | 54.948176 | 55.226839 | 56.322061 | 493.914 |
| main | 3 | large3 | 510 | 56 | 54.940845 | 55.229736 | 55.937137 | 362.301 |
| highs | 3 | large3 | 337 | 56 | 54.946824 | 55.237365 | 56.163017 | 593.891 |

Full source diff and replay CLI: [`experiments/paired-seeds/`](experiments/paired-seeds/).
Raw state, logs, full-M witnesses and checker outputs:
[`results/2026-11-21/paired-seeds/`](results/2026-11-21/paired-seeds/).

## Remaining originally held-out public cases

Exact official large1/4/5 inputs were retrieved at pinned revision
`ef42a2eac13595453f986d9df0b62e86e75ab596`, without reference solutions.
All nine planned full runs completed; six whole solutions passed both checkers,
while three cold baseline entries failed to produce a feasible witness in the
fixed internal budget. The frozen Main and baseline sources are unchanged.

| Case | Algorithm | Cost | Bound | Algorithm wall s | Whole + checkers s | CPU s | RSS MiB | Outcome |
|---|---|---:|---:|---:|---:|---:|---:|---|
| large1 | main | 2833 | 16 | 54.932730 | 55.233721 | 57.026484 | 272.941 | TimeLimit |
| large1 | highs | 3541 | 16 | 54.929407 | 55.231090 | 57.568810 | 225.477 | TimeLimit |
| large1 | cpsat | 1832 | -11754 | 55.029474 | 55.327146 | 105.980164 | 877.918 | FEASIBLE |
| large4 | main | 331 | — | 54.972294 | 55.278832 | 101.384608 | 122.645 | TimeLimit |
| large4 | highs | — | — | 54.973851 | 55.053874 | 97.874926 | 117.000 | FAILED: no feasible witness |
| large4 | cpsat | — | — | 54.979845 | 55.027460 | 104.519375 | 588.953 | FAILED: no feasible witness |
| large5 | main | 180 | 180 | 50.885859 | 51.249692 | 86.444243 | 187.320 | Optimal |
| large5 | highs | 180 | 180 | 51.432757 | 51.807921 | 86.126349 | 181.613 | Optimal |
| large5 | cpsat | — | — | 55.026297 | 55.087803 | 105.220707 | 658.887 | FAILED: no feasible witness |

- **large1:** CP-SAT1832 is substantially better than Main2833; HiGHS3541
  is the weaker observed baseline on this case. All three results are feasible.
- **large4:** Main331 passes both full checkers. Cold HiGHS and CP-SAT exit2
  with `has no whole feasible solution` (CP-SAT `UNKNOWN`) after approximately
  55 s; both remain inside time/memory bounds. They have no solution, objective,
  or checker verdict. Costs are displayed as absent, with no zero-cost imputation.
  Main retains its initial full-pool cold cover; its full-HiGHS reported bound is absent.
- **large5:** Main and cold HiGHS both prove optimal180, bounds180/gap0.
  CP-SAT exits2 with `UNKNOWN` and no whole witness within its search budget.
- Queue outcome `DONE_WITH_NEGATIVE_RESULTS`: 9/9 executed, no skipped runs,
  whole489.428 s / CPU803.099 s. Each run keeps its raw outcome instead of
  stopping the comparison at the first ordinary cold-baseline failure.

Full original failed entries and stderr:
[`holdouts/large4/highs/`](results/2026-11-21/holdouts/large4/highs/),
[`holdouts/large4/cpsat/`](results/2026-11-21/holdouts/large4/cpsat/),
[`holdouts/large5/cpsat/`](results/2026-11-21/holdouts/large5/cpsat/).
Source receipts and replay queue: [`experiments/holdouts/`](experiments/holdouts/).
The three held-out density-pool probes reported `EXHAUSTED`; final Main costs
remain their initial full-pool cold covers. No held-out cost improvement came
from the cheap pool. The complete seed1 benchmark collection now has 18 runs: Main6/6 feasible,
HiGHS5/6 feasible and CP-SAT4/6 feasible. Quality remains case-dependent.

## Complete data and validation

| Case | Rows N | Original columns M | Coverage nnz | Active Base rows K |
|---|---:|---:|---:|---:|
| tiny | 30 | 25 | 132 | 0 |
| large1 | 100 | 15000 | 187822 | 0 |
| large2 (easy) | 100 | 15000 | 17816 | 0 |
| large3 (hard) | 100 | 15000 | 67522 | 0 |
| large4 | 100 | 15000 | 323670 | 0 |
| large5 | 100 | 15000 | 516521 | 0 |

The separate synthetic Base contract passed: `num_bases=1`, K=2, N=1, M=2,
native model rows=3, selected `[1]`, cost 2, algorithm wall 0.217020 s,
whole/checkers wall 0.468079 s, exit 0, both checkers PASS. Full raw assertion:
[`results/2026-11-21/base-contract/`](results/2026-11-21/base-contract/).

Each successful-run directory includes `solution.json`, `run.json`, exact/original checker
JSON, stdout/stderr and checker logs. Controller state, journals and install
receipts are under [`results/2026-11-21/runtime/`](results/2026-11-21/runtime/).
Exact unrounded results: [`results/summary.json`](results/summary.json).
`verify_replay.py` recomputes archived exact witnesses and checks the recorded
official verdicts; the recorded original-checker execution remains in the logs.

## Timing and environment

- Linux x86_64, kernel `6.18.54-instabox`, glibc 2.41; four host CPUs,
  measured worker affinity `[0,1]`. CPU model and cache topology were not
  captured in the experiment record.
- Python **3.13.5**, GCC 14.2.0 interpreter build. Advertised Main images:
  Python 3.12 / 3.14. This is a same-host research envelope measurement.
- Exact core wheels: **highspy 1.15.1 / OR-Tools 9.15.6755 / NumPy 2.5.3**.
  Runtime HiGHS also reports 1.15.1. Published runtime contract:
  [Main submission format](https://frontieror-challenge.com/docs/main/submission-format),
  retrieved 2026-11-21. Full ancillary versions and dependencies
  are in [version-gate.json](results/2026-11-21/runtime/version-gate.json).
  Measured/advertised ancillary differences include pandas 3.1.1/3.0.6,
  absl-py 2.5.1/2.5.0 and python-dateutil 4.0.0/2.9.0.post0.
- Each worker: 2-CPU affinity, `RLIMIT_AS=4 GiB`, `RLIMIT_CPU=120 s`;
  algorithm at most 55 s internal, external whole worker/checkers at most 60 s.
  HiGHS uses two threads; CP-SAT two workers; Python DFS one executing thread.
- Algorithm wall includes startup, JSON, model/probes, solve and full output.
  Whole wall also includes worker startup and both checkers. OS rusage supplies
  total CPU and max RSS; RSS is a maximum process value, not a summed process
  memory peak. Build/search metrics remain separately recorded in raw logs.
- Core wheel installation passed in 2.284927 s, with no compilation or
  interpreter download. Cumulative experiment files 381,924,837 bytes at that
  gate, below its 629,145,600-byte cap. Virtualenv/wheels are omitted from git.

## Published reference — separate evaluation

Original public Gurobi solution fields, on the authors' original hardware:

| Case | Cost | Bound | Status | `runtime_seconds` | `runtime` |
|---|---:|---:|---|---:|---:|
| large2 | 229 | 229 | optimal | 0.033720 | 0.26 |
| large3 | 207 | 76 | feasible | 3600.005044 | 3600.83 |

The original hardware/interpreter configuration is outside the downloaded
solution fields. These are author references, with a much longer hard-run
budget, kept separate from paired runtime comparisons. Main 240 is 15.9420%
above reference207. Reference hard gap: 63.2850%. The references were absent
from the cold input directory and were used for evaluation only.

## Historical controls and negative observations

Old native HiGHS 1.16.0 / CP-SAT 9.14.6206 / C++294 belong to the
[separate control record](controls/README.md), with their own versions,
checker NumPy and timing envelopes. Historical failed/nondominant probes are
retained there. Main's matched comparator is 453, and Main's score is 240.
The C++294 and old HiGHS296 comparison is a historical one-seed experiment.

## Isolated dynamic-scarcity insight — probe-only

The unchanged hard3 density pool was probed with current-compatible row support
in branch ordering, instead of initial support. Six-second dynamic seeds1/2/3
yield TIME_LIMIT / cost328 / cost328. Both covers pass complete exact/NumPy
checks; seed1 has no witness and loses the original static probe's cost252 cover.
This changes which two of three seeds find a pool cover; it supplies no new
full-Main score. Minimal source/diff and original receipts are preserved at
[`experiments/dynamic-scarcity/`](experiments/dynamic-scarcity/).

## Fixed-pool OSS probe negatives — separate six-second scope

Restricted-objective HiGHS1.15.1 and cost-free CP-SAT9.15.6755 each used the
same1706-column/100-original-row hard3 pool, seed1. Both reported NO_COVER
within a six-second first stage (HiGHS TimeLimit/bound56; CP-SAT UNKNOWN),
exit2, with no complete witness. These original small diagnostic sources and
full stdout/run receipts are kept under
[`experiments/restricted-pool/`](experiments/restricted-pool/).

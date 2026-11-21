# Historical controls — separate from Python Main

These are archived experiments preceding frozen Python Main v1. C++ is an
independent native control, excluded from primary-language statistics.
Historical work-log phrases such as “main v1” describe the then-current C++
branch. The present Main entry and all Main scores are Python `main/solve.py`.

## Old same-envelope native baseline record

Seed 1, 2 allowed CPUs, 4 GiB AS, 55 s internal / 60 s external including
full normalization and both checkers. Original checker NumPy was 2.2.4;
old isolated CP-SAT used NumPy 2.5.5. All six completed runs passed both checkers.

| Historical engine | tiny cost | easy cost | hard cost | hard bound | Hard whole s | Hard RSS MiB |
|---|---:|---:|---:|---:|---:|---:|
| Native HiGHS 1.16.0, commit 725b40f | 16 | 229 | 296 | 57 | 55.289841 | 2273.371 |
| CP-SAT 9.14.6206 | 16 | 229 | 823 | -13243 | 55.381940 | 562.277 |
| C++ exact-cover + hole LNS v1 | local smoke16 | local smoke229 | 294 | — | 55.237287 | 43.562 |

The C++ formal run is **one hard case/seed only**. Its tiny/easy observations
are local 2 s smoke runs, not same-envelope formal benchmark measurements.
It uses one executing solver CPU and standard C++17, with no optimization
library. C++294 versus old HiGHS296 is a -0.6757% one-seed cost observation;
this has its own language/version comparison boundary.

Sources and complete records:
[`cpp-v1/`](cpp-v1/), [`legacy-baselines/`](legacy-baselines/).
C++ formal source SHA-256:
`73f85abd4bed67ce05779cb6cc41d017e771d05a1b0ea6b55271583f2a524736`.
The recorded C++ controller contains historical absolute paths; it is an
audit artifact. The portable original shared helper exposes sparse transport,
normalization and the independent checker, while C++ compilation remains
an optional separate control experiment.

## Negative / nondominant experiments

All are recorded on hard3/seed1 with local 5-second budgets and 500 MiB AS;
their output qualities describe that local smoke scope.

| Experiment | Observed outcome | Decision |
|---|---|---|
| Initial v1 DLX + hole-LNS | 345 | Retained as old C++ method |
| Forced cheap anchor ejection v2 | 405; fewer completed holes | Rejected |
| Root dual-ascent bound v3 | 345; about 0.7% fewer nodes | Rejected complexity increase |
| First v4 widening / shared RNG | node caps, final 413 | Rejected |
| Revised v4 cheap-pool probes | 439/652/1112-column pools time-aborted after ~0.45 s each, then fallback345 | C++ branch STOP |

The three revised cheap-pool probes found no cover before timeout; search
exhaustion/infeasibility was not certified. Frozen Python Main uses a thicker
input-derived pool and a longer bounded probe; its measured result is separate.

Setup/instrumentation failures are also retained: the first old CP virtualenv
attempt stopped because Debian lacked ensurepip; an old HiGHS link initially
failed with unresolved `HighsExtras_getApi`/`HighsExtras_getFeatureInfo` symbols; v2 code-generation inserted literal newline
tokens and failed compilation before correction; `/usr/bin/time` was absent,
so the first timing command failed before solver execution. Successful corrected
runs are separately recorded. Old logs:
[`legacy-baselines/results/`](legacy-baselines/results/), complete C++ notes,
sources and smoke records: [`experiments/`](experiments/).

## Author reference boundary

Published Gurobi207 on hard3 used about one hour, with different original
hardware. It is an evaluation reference and remains under
[`evaluation/reference/`](../evaluation/reference/), separate from all cold
inputs and Main/old-control scores.
